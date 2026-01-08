"""
Backup manager implementation for data backup and disaster recovery.

This module provides backup capabilities including:
- Automated data backup strategies
- Cross-region data replication
- Disaster recovery orchestration
- Backup verification and restoration
"""

import asyncio
import gzip
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import boto3
import asyncpg
import redis.asyncio as redis

from .models import ServiceInstance, ServiceStatus
from ..monitoring.sync_metrics import SyncMetrics


logger = logging.getLogger(__name__)


class BackupStrategy:
    """Backup strategy enumeration."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    CONTINUOUS = "continuous"


class BackupStatus:
    """Backup status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackupJob:
    """Represents a backup job."""
    
    def __init__(self, job_id: str, strategy: str, source: str, destination: str):
        self.job_id = job_id
        self.strategy = strategy
        self.source = source
        self.destination = destination
        self.status = BackupStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.size_bytes = 0
        self.error_message: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    @property
    def duration(self) -> Optional[float]:
        """Get backup duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BackupManager:
    """Backup manager for automated data backup and disaster recovery."""
    
    def __init__(self, postgres_url: str, redis_url: str, 
                 backup_config: Dict[str, Any]):
        """
        Initialize backup manager.
        
        Args:
            postgres_url: PostgreSQL connection URL
            redis_url: Redis connection URL
            backup_config: Backup configuration
        """
        self.postgres_url = postgres_url
        self.redis_url = redis_url
        self.config = backup_config
        
        self.active_jobs: Dict[str, BackupJob] = {}
        self.job_history: List[BackupJob] = []
        self.backup_schedules: Dict[str, Dict[str, Any]] = {}
        
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._s3_client: Optional[boto3.client] = None
        
        # Initialize AWS S3 client if configured
        if self.config.get('aws_access_key_id'):
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config['aws_access_key_id'],
                aws_secret_access_key=self.config['aws_secret_access_key'],
                region_name=self.config.get('aws_region', 'us-east-1')
            )
    
    async def start(self) -> None:
        """Start backup manager."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        logger.info("Backup manager started")
    
    async def stop(self) -> None:
        """Stop backup manager."""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel active jobs
        for job in self.active_jobs.values():
            job.status = BackupStatus.CANCELLED
        
        logger.info("Backup manager stopped")
    
    async def create_backup(self, strategy: str, source: str, destination: str,
                          metadata: Optional[Dict[str, Any]] = None) -> BackupJob:
        """
        Create a new backup job.
        
        Args:
            strategy: Backup strategy (full, incremental, etc.)
            source: Source identifier (database, service, etc.)
            destination: Destination path or URL
            metadata: Additional metadata
            
        Returns:
            Created backup job
        """
        job_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{source}"
        
        job = BackupJob(job_id, strategy, source, destination)
        if metadata:
            job.metadata.update(metadata)
        
        self.active_jobs[job_id] = job
        
        # Execute backup asynchronously
        asyncio.create_task(self._execute_backup(job))
        
        logger.info(f"Created backup job {job_id}: {source} -> {destination}")
        return job
    
    async def _execute_backup(self, job: BackupJob) -> None:
        """Execute a backup job."""
        try:
            job.status = BackupStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            logger.info(f"Starting backup job {job.job_id}")
            
            # Determine backup type and execute
            if job.source.startswith('postgres:'):
                await self._backup_postgres(job)
            elif job.source.startswith('redis:'):
                await self._backup_redis(job)
            elif job.source.startswith('files:'):
                await self._backup_files(job)
            else:
                raise ValueError(f"Unknown backup source type: {job.source}")
            
            job.status = BackupStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            logger.info(f"Backup job {job.job_id} completed successfully")
        
        except Exception as e:
            job.status = BackupStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            
            logger.error(f"Backup job {job.job_id} failed: {e}")
        
        finally:
            # Move to history
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            
            self.job_history.append(job)
            
            # Keep only recent history (last 100 jobs)
            if len(self.job_history) > 100:
                self.job_history.pop(0)
    
    async def _backup_postgres(self, job: BackupJob) -> None:
        """Backup PostgreSQL database."""
        try:
            # Parse source
            parts = job.source.split(':', 2)
            database = parts[1] if len(parts) > 1 else 'superinsight'
            table_filter = parts[2] if len(parts) > 2 else None
            
            # Connect to database
            conn = await asyncpg.connect(self.postgres_url)
            
            try:
                backup_data = {}
                
                if job.strategy == BackupStrategy.FULL:
                    # Full backup - all tables
                    tables = await self._get_database_tables(conn, table_filter)
                    
                    for table in tables:
                        rows = await conn.fetch(f"SELECT * FROM {table}")
                        backup_data[table] = [dict(row) for row in rows]
                
                elif job.strategy == BackupStrategy.INCREMENTAL:
                    # Incremental backup - only changed data since last backup
                    last_backup_time = await self._get_last_backup_time(job.source)
                    tables = await self._get_database_tables(conn, table_filter)
                    
                    for table in tables:
                        # Assume tables have updated_at column for incremental backup
                        query = f"""
                            SELECT * FROM {table} 
                            WHERE updated_at > $1
                        """
                        try:
                            rows = await conn.fetch(query, last_backup_time)
                            if rows:
                                backup_data[table] = [dict(row) for row in rows]
                        except Exception:
                            # Table might not have updated_at column, skip
                            logger.warning(f"Cannot perform incremental backup for table {table}")
                
                # Compress and save backup
                await self._save_backup_data(job, backup_data)
                
            finally:
                await conn.close()
        
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {e}")
            raise
    
    async def _backup_redis(self, job: BackupJob) -> None:
        """Backup Redis data."""
        try:
            # Parse source
            parts = job.source.split(':', 2)
            db_index = int(parts[1]) if len(parts) > 1 else 0
            key_pattern = parts[2] if len(parts) > 2 else '*'
            
            # Connect to Redis
            redis_client = redis.from_url(self.redis_url, db=db_index)
            
            try:
                backup_data = {}
                
                # Get all keys matching pattern
                keys = await redis_client.keys(key_pattern)
                
                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    
                    # Get key type and value
                    key_type = await redis_client.type(key)
                    key_type_str = key_type.decode() if isinstance(key_type, bytes) else key_type
                    
                    if key_type_str == 'string':
                        value = await redis_client.get(key)
                        backup_data[key_str] = {
                            'type': 'string',
                            'value': value.decode() if isinstance(value, bytes) else value
                        }
                    
                    elif key_type_str == 'hash':
                        value = await redis_client.hgetall(key)
                        backup_data[key_str] = {
                            'type': 'hash',
                            'value': {
                                k.decode() if isinstance(k, bytes) else k: 
                                v.decode() if isinstance(v, bytes) else v
                                for k, v in value.items()
                            }
                        }
                    
                    elif key_type_str == 'list':
                        value = await redis_client.lrange(key, 0, -1)
                        backup_data[key_str] = {
                            'type': 'list',
                            'value': [
                                v.decode() if isinstance(v, bytes) else v
                                for v in value
                            ]
                        }
                    
                    elif key_type_str == 'set':
                        value = await redis_client.smembers(key)
                        backup_data[key_str] = {
                            'type': 'set',
                            'value': [
                                v.decode() if isinstance(v, bytes) else v
                                for v in value
                            ]
                        }
                    
                    elif key_type_str == 'zset':
                        value = await redis_client.zrange(key, 0, -1, withscores=True)
                        backup_data[key_str] = {
                            'type': 'zset',
                            'value': [
                                (v.decode() if isinstance(v, bytes) else v, score)
                                for v, score in value
                            ]
                        }
                
                # Save backup
                await self._save_backup_data(job, backup_data)
                
            finally:
                await redis_client.close()
        
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            raise
    
    async def _backup_files(self, job: BackupJob) -> None:
        """Backup file system data."""
        try:
            # Parse source
            parts = job.source.split(':', 1)
            source_path = parts[1] if len(parts) > 1 else '/tmp'
            
            source_dir = Path(source_path)
            if not source_dir.exists():
                raise FileNotFoundError(f"Source directory not found: {source_path}")
            
            # Create temporary backup directory
            backup_dir = Path(f"/tmp/backup_{job.job_id}")
            backup_dir.mkdir(exist_ok=True)
            
            try:
                if job.strategy == BackupStrategy.FULL:
                    # Full file backup
                    shutil.copytree(source_dir, backup_dir / "data", dirs_exist_ok=True)
                
                elif job.strategy == BackupStrategy.INCREMENTAL:
                    # Incremental file backup
                    last_backup_time = await self._get_last_backup_time(job.source)
                    
                    for file_path in source_dir.rglob('*'):
                        if file_path.is_file():
                            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_mtime > last_backup_time:
                                # Copy modified file
                                rel_path = file_path.relative_to(source_dir)
                                dest_path = backup_dir / "data" / rel_path
                                dest_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(file_path, dest_path)
                
                # Compress backup directory
                backup_archive = f"/tmp/{job.job_id}.tar.gz"
                shutil.make_archive(backup_archive.replace('.tar.gz', ''), 'gztar', backup_dir)
                
                # Upload to destination
                await self._upload_backup_file(job, backup_archive)
                
                # Get file size
                job.size_bytes = os.path.getsize(backup_archive)
                
                # Cleanup
                os.remove(backup_archive)
                
            finally:
                # Cleanup temporary directory
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
        
        except Exception as e:
            logger.error(f"File backup failed: {e}")
            raise
    
    async def _get_database_tables(self, conn: asyncpg.Connection, 
                                 table_filter: Optional[str] = None) -> List[str]:
        """Get list of database tables."""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """
        
        if table_filter:
            query += f" AND table_name LIKE '{table_filter}'"
        
        rows = await conn.fetch(query)
        return [row['table_name'] for row in rows]
    
    async def _get_last_backup_time(self, source: str) -> datetime:
        """Get timestamp of last backup for incremental backups."""
        # Find last successful backup for this source
        for job in reversed(self.job_history):
            if (job.source == source and 
                job.status == BackupStatus.COMPLETED and
                job.completed_at):
                return job.completed_at
        
        # Default to 24 hours ago if no previous backup
        return datetime.utcnow() - timedelta(hours=24)
    
    async def _save_backup_data(self, job: BackupJob, data: Dict[str, Any]) -> None:
        """Save backup data to destination."""
        try:
            # Serialize data
            json_data = json.dumps(data, default=str, indent=2)
            
            # Compress data
            compressed_data = gzip.compress(json_data.encode())
            job.size_bytes = len(compressed_data)
            
            # Save to destination
            if job.destination.startswith('s3://'):
                await self._upload_to_s3(job, compressed_data)
            elif job.destination.startswith('file://'):
                await self._save_to_file(job, compressed_data)
            else:
                raise ValueError(f"Unknown destination type: {job.destination}")
        
        except Exception as e:
            logger.error(f"Failed to save backup data: {e}")
            raise
    
    async def _upload_to_s3(self, job: BackupJob, data: bytes) -> None:
        """Upload backup data to S3."""
        if not self._s3_client:
            raise RuntimeError("S3 client not configured")
        
        try:
            # Parse S3 URL
            s3_url = job.destination.replace('s3://', '')
            parts = s3_url.split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else f"backups/{job.job_id}.json.gz"
            
            # Upload to S3
            self._s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                Metadata={
                    'backup-job-id': job.job_id,
                    'backup-strategy': job.strategy,
                    'backup-source': job.source,
                    'backup-timestamp': job.started_at.isoformat()
                }
            )
            
            logger.info(f"Uploaded backup to S3: s3://{bucket}/{key}")
        
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    async def _save_to_file(self, job: BackupJob, data: bytes) -> None:
        """Save backup data to local file."""
        try:
            # Parse file URL
            file_path = job.destination.replace('file://', '')
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write data
            with open(file_path, 'wb') as f:
                f.write(data)
            
            logger.info(f"Saved backup to file: {file_path}")
        
        except Exception as e:
            logger.error(f"File save failed: {e}")
            raise
    
    async def _upload_backup_file(self, job: BackupJob, file_path: str) -> None:
        """Upload backup file to destination."""
        try:
            if job.destination.startswith('s3://'):
                # Upload file to S3
                if not self._s3_client:
                    raise RuntimeError("S3 client not configured")
                
                s3_url = job.destination.replace('s3://', '')
                parts = s3_url.split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else f"backups/{job.job_id}.tar.gz"
                
                with open(file_path, 'rb') as f:
                    self._s3_client.upload_fileobj(f, bucket, key)
                
                logger.info(f"Uploaded backup file to S3: s3://{bucket}/{key}")
            
            elif job.destination.startswith('file://'):
                # Copy to local destination
                dest_path = job.destination.replace('file://', '')
                Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                
                logger.info(f"Copied backup file to: {dest_path}")
            
            else:
                raise ValueError(f"Unknown destination type: {job.destination}")
        
        except Exception as e:
            logger.error(f"Backup file upload failed: {e}")
            raise
    
    def schedule_backup(self, name: str, schedule_config: Dict[str, Any]) -> None:
        """
        Schedule recurring backups.
        
        Args:
            name: Schedule name
            schedule_config: Schedule configuration
        """
        self.backup_schedules[name] = {
            'config': schedule_config,
            'last_run': None,
            'next_run': self._calculate_next_run(schedule_config)
        }
        
        logger.info(f"Scheduled backup: {name}")
    
    def unschedule_backup(self, name: str) -> bool:
        """
        Remove a backup schedule.
        
        Args:
            name: Schedule name
            
        Returns:
            True if schedule was removed
        """
        if name in self.backup_schedules:
            del self.backup_schedules[name]
            logger.info(f"Unscheduled backup: {name}")
            return True
        return False
    
    async def _scheduler_loop(self) -> None:
        """Backup scheduler loop."""
        while self._running:
            try:
                current_time = datetime.utcnow()
                
                for name, schedule in self.backup_schedules.items():
                    if current_time >= schedule['next_run']:
                        # Execute scheduled backup
                        config = schedule['config']
                        
                        await self.create_backup(
                            strategy=config['strategy'],
                            source=config['source'],
                            destination=config['destination'],
                            metadata={'scheduled': True, 'schedule_name': name}
                        )
                        
                        # Update schedule
                        schedule['last_run'] = current_time
                        schedule['next_run'] = self._calculate_next_run(config)
                        
                        logger.info(f"Executed scheduled backup: {name}")
                
                await asyncio.sleep(60)  # Check every minute
            
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    def _calculate_next_run(self, config: Dict[str, Any]) -> datetime:
        """Calculate next run time for a schedule."""
        interval = config.get('interval', 'daily')
        current_time = datetime.utcnow()
        
        if interval == 'hourly':
            return current_time + timedelta(hours=1)
        elif interval == 'daily':
            return current_time + timedelta(days=1)
        elif interval == 'weekly':
            return current_time + timedelta(weeks=1)
        elif interval == 'monthly':
            return current_time + timedelta(days=30)
        else:
            # Custom interval in seconds
            seconds = int(config.get('interval_seconds', 3600))
            return current_time + timedelta(seconds=seconds)
    
    async def restore_backup(self, job_id: str, target: str) -> bool:
        """
        Restore data from a backup.
        
        Args:
            job_id: Backup job ID to restore
            target: Target location for restoration
            
        Returns:
            True if restoration successful
        """
        try:
            # Find backup job
            backup_job = None
            for job in self.job_history:
                if job.job_id == job_id and job.status == BackupStatus.COMPLETED:
                    backup_job = job
                    break
            
            if not backup_job:
                logger.error(f"Backup job not found or not completed: {job_id}")
                return False
            
            # Download backup data
            backup_data = await self._download_backup_data(backup_job)
            
            # Restore based on target type
            if target.startswith('postgres:'):
                return await self._restore_postgres(backup_data, target)
            elif target.startswith('redis:'):
                return await self._restore_redis(backup_data, target)
            elif target.startswith('files:'):
                return await self._restore_files(backup_job, target)
            else:
                logger.error(f"Unknown restore target type: {target}")
                return False
        
        except Exception as e:
            logger.error(f"Backup restoration failed: {e}")
            return False
    
    async def _download_backup_data(self, job: BackupJob) -> Dict[str, Any]:
        """Download and decompress backup data."""
        try:
            if job.destination.startswith('s3://'):
                # Download from S3
                if not self._s3_client:
                    raise RuntimeError("S3 client not configured")
                
                s3_url = job.destination.replace('s3://', '')
                parts = s3_url.split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else f"backups/{job.job_id}.json.gz"
                
                response = self._s3_client.get_object(Bucket=bucket, Key=key)
                compressed_data = response['Body'].read()
            
            elif job.destination.startswith('file://'):
                # Read from local file
                file_path = job.destination.replace('file://', '')
                with open(file_path, 'rb') as f:
                    compressed_data = f.read()
            
            else:
                raise ValueError(f"Unknown destination type: {job.destination}")
            
            # Decompress and parse
            json_data = gzip.decompress(compressed_data).decode()
            return json.loads(json_data)
        
        except Exception as e:
            logger.error(f"Failed to download backup data: {e}")
            raise
    
    async def _restore_postgres(self, backup_data: Dict[str, Any], target: str) -> bool:
        """Restore PostgreSQL data."""
        try:
            # Parse target
            parts = target.split(':', 2)
            database = parts[1] if len(parts) > 1 else 'superinsight'
            
            # Connect to database
            conn = await asyncpg.connect(self.postgres_url)
            
            try:
                # Restore each table
                for table_name, rows in backup_data.items():
                    if not rows:
                        continue
                    
                    # Clear existing data (optional - could be configurable)
                    await conn.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                    
                    # Insert backup data
                    if rows:
                        columns = list(rows[0].keys())
                        placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
                        
                        query = f"""
                            INSERT INTO {table_name} ({', '.join(columns)})
                            VALUES ({placeholders})
                        """
                        
                        for row in rows:
                            values = [row[col] for col in columns]
                            await conn.execute(query, *values)
                
                logger.info(f"PostgreSQL restoration completed for {len(backup_data)} tables")
                return True
            
            finally:
                await conn.close()
        
        except Exception as e:
            logger.error(f"PostgreSQL restoration failed: {e}")
            return False
    
    async def _restore_redis(self, backup_data: Dict[str, Any], target: str) -> bool:
        """Restore Redis data."""
        try:
            # Parse target
            parts = target.split(':', 2)
            db_index = int(parts[1]) if len(parts) > 1 else 0
            
            # Connect to Redis
            redis_client = redis.from_url(self.redis_url, db=db_index)
            
            try:
                # Restore each key
                for key, key_data in backup_data.items():
                    key_type = key_data['type']
                    value = key_data['value']
                    
                    if key_type == 'string':
                        await redis_client.set(key, value)
                    
                    elif key_type == 'hash':
                        await redis_client.hset(key, mapping=value)
                    
                    elif key_type == 'list':
                        await redis_client.delete(key)  # Clear existing
                        if value:
                            await redis_client.lpush(key, *reversed(value))
                    
                    elif key_type == 'set':
                        await redis_client.delete(key)  # Clear existing
                        if value:
                            await redis_client.sadd(key, *value)
                    
                    elif key_type == 'zset':
                        await redis_client.delete(key)  # Clear existing
                        if value:
                            for member, score in value:
                                await redis_client.zadd(key, {member: score})
                
                logger.info(f"Redis restoration completed for {len(backup_data)} keys")
                return True
            
            finally:
                await redis_client.close()
        
        except Exception as e:
            logger.error(f"Redis restoration failed: {e}")
            return False
    
    async def _restore_files(self, job: BackupJob, target: str) -> bool:
        """Restore file system data."""
        try:
            # Parse target
            parts = target.split(':', 1)
            target_path = parts[1] if len(parts) > 1 else '/tmp/restore'
            
            # Download backup file
            if job.destination.startswith('s3://'):
                # Download from S3
                if not self._s3_client:
                    raise RuntimeError("S3 client not configured")
                
                s3_url = job.destination.replace('s3://', '')
                parts = s3_url.split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else f"backups/{job.job_id}.tar.gz"
                
                temp_file = f"/tmp/restore_{job.job_id}.tar.gz"
                self._s3_client.download_file(bucket, key, temp_file)
            
            elif job.destination.startswith('file://'):
                temp_file = job.destination.replace('file://', '')
            
            else:
                raise ValueError(f"Unknown destination type: {job.destination}")
            
            # Extract backup
            shutil.unpack_archive(temp_file, target_path)
            
            # Cleanup temporary file if downloaded
            if job.destination.startswith('s3://'):
                os.remove(temp_file)
            
            logger.info(f"File restoration completed to: {target_path}")
            return True
        
        except Exception as e:
            logger.error(f"File restoration failed: {e}")
            return False
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup system statistics."""
        total_backups = len(self.job_history)
        successful_backups = sum(1 for j in self.job_history if j.status == BackupStatus.COMPLETED)
        
        if total_backups == 0:
            return {
                "total_backups": 0,
                "success_rate": 0.0,
                "total_size_bytes": 0,
                "active_jobs": len(self.active_jobs),
                "scheduled_backups": len(self.backup_schedules)
            }
        
        total_size = sum(j.size_bytes for j in self.job_history if j.status == BackupStatus.COMPLETED)
        
        return {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "success_rate": successful_backups / total_backups,
            "total_size_bytes": total_size,
            "active_jobs": len(self.active_jobs),
            "scheduled_backups": len(self.backup_schedules),
            "recent_backups": [
                {
                    "job_id": j.job_id,
                    "strategy": j.strategy,
                    "source": j.source,
                    "status": j.status,
                    "size_bytes": j.size_bytes,
                    "duration": j.duration,
                    "created_at": j.created_at.isoformat()
                }
                for j in self.job_history[-10:]  # Last 10 backups
            ]
        }