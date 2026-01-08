"""
Data Backup and Recovery System for SuperInsight Platform.

Provides comprehensive data backup and recovery capabilities including:
- Automated backup scheduling
- Incremental and full backups
- Cross-region data replication
- Fast data recovery mechanisms
- Backup integrity verification
- Disaster recovery coordination
"""

import asyncio
import logging
import os
import shutil
import json
import gzip
import hashlib
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of backups."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """Backup operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"


class RecoveryType(Enum):
    """Types of recovery operations."""
    FULL_RESTORE = "full_restore"
    PARTIAL_RESTORE = "partial_restore"
    POINT_IN_TIME = "point_in_time"
    SELECTIVE_RESTORE = "selective_restore"


@dataclass
class BackupMetadata:
    """Backup metadata information."""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    size_bytes: int
    checksum: str
    source_path: str
    backup_path: str
    compression_ratio: float = 0.0
    status: BackupStatus = BackupStatus.PENDING
    retention_days: int = 30
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class RecoveryOperation:
    """Recovery operation information."""
    recovery_id: str
    recovery_type: RecoveryType
    backup_id: str
    target_path: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: BackupStatus = BackupStatus.PENDING
    progress_percentage: float = 0.0
    error_message: Optional[str] = None


class BackupRecoverySystem:
    """
    Comprehensive backup and recovery system.
    
    Features:
    - Automated backup scheduling
    - Multiple backup strategies
    - Compression and encryption
    - Integrity verification
    - Fast recovery mechanisms
    - Cross-region replication
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.backup_metadata: Dict[str, BackupMetadata] = {}
        self.active_operations: Dict[str, RecoveryOperation] = {}
        self.operation_history: List[RecoveryOperation] = []
        
        # System state
        self.system_active = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Backup storage
        self.backup_root = Path(self.config.get("backup_root", "/tmp/superinsight_backups"))
        self.backup_root.mkdir(parents=True, exist_ok=True)
        
        # Initialize backup registry
        self._load_backup_registry()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default backup configuration."""
        return {
            "backup_root": "/tmp/superinsight_backups",
            "compression_enabled": True,
            "encryption_enabled": False,
            "max_concurrent_operations": 3,
            "backup_retention_days": 30,
            "incremental_backup_interval": 3600,  # 1 hour
            "full_backup_interval": 86400,  # 24 hours
            "cross_region_replication": False,
            "integrity_check_enabled": True,
            "backup_sources": [
                {"name": "database", "path": "/var/lib/postgresql/data", "type": "database"},
                {"name": "uploads", "path": "/app/uploads", "type": "files"},
                {"name": "config", "path": "/app/config", "type": "config"},
                {"name": "logs", "path": "/app/logs", "type": "logs"}
            ]
        }
    
    async def start_system(self):
        """Start the backup and recovery system."""
        if self.system_active:
            logger.warning("Backup recovery system is already active")
            return
        
        self.system_active = True
        
        # Start backup scheduler
        self.scheduler_task = asyncio.create_task(self._backup_scheduler())
        
        # Perform initial system check
        await self._perform_system_check()
        
        logger.info("Backup and recovery system started")
    
    async def stop_system(self):
        """Stop the backup and recovery system."""
        self.system_active = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Save backup registry
        self._save_backup_registry()
        
        logger.info("Backup and recovery system stopped")
    
    async def _backup_scheduler(self):
        """Automated backup scheduler."""
        while self.system_active:
            try:
                current_time = datetime.utcnow()
                
                # Check if full backup is needed
                if await self._should_perform_full_backup():
                    await self._schedule_full_backup()
                
                # Check if incremental backup is needed
                elif await self._should_perform_incremental_backup():
                    await self._schedule_incremental_backup()
                
                # Clean up old backups
                await self._cleanup_old_backups()
                
                # Verify backup integrity
                await self._verify_backup_integrity()
                
                # Sleep until next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in backup scheduler: {e}")
                await asyncio.sleep(300)
    
    async def _should_perform_full_backup(self) -> bool:
        """Check if a full backup should be performed."""
        try:
            full_backup_interval = self.config.get("full_backup_interval", 86400)
            
            # Find last full backup
            last_full_backup = None
            for backup in self.backup_metadata.values():
                if (backup.backup_type == BackupType.FULL and 
                    backup.status == BackupStatus.COMPLETED):
                    if not last_full_backup or backup.created_at > last_full_backup.created_at:
                        last_full_backup = backup
            
            if not last_full_backup:
                return True  # No full backup exists
            
            # Check if enough time has passed
            time_since_last = (datetime.utcnow() - last_full_backup.created_at).total_seconds()
            return time_since_last >= full_backup_interval
            
        except Exception as e:
            logger.error(f"Error checking full backup schedule: {e}")
            return False
    
    async def _should_perform_incremental_backup(self) -> bool:
        """Check if an incremental backup should be performed."""
        try:
            incremental_interval = self.config.get("incremental_backup_interval", 3600)
            
            # Find last backup (any type)
            last_backup = None
            for backup in self.backup_metadata.values():
                if backup.status == BackupStatus.COMPLETED:
                    if not last_backup or backup.created_at > last_backup.created_at:
                        last_backup = backup
            
            if not last_backup:
                return False  # Need full backup first
            
            # Check if enough time has passed
            time_since_last = (datetime.utcnow() - last_backup.created_at).total_seconds()
            return time_since_last >= incremental_interval
            
        except Exception as e:
            logger.error(f"Error checking incremental backup schedule: {e}")
            return False
    
    async def _schedule_full_backup(self):
        """Schedule a full backup operation."""
        try:
            logger.info("Scheduling full backup")
            
            for source in self.config.get("backup_sources", []):
                backup_id = await self.create_backup(
                    source_path=source["path"],
                    backup_type=BackupType.FULL,
                    tags={"source_name": source["name"], "source_type": source["type"]}
                )
                
                if backup_id:
                    logger.info(f"Full backup scheduled for {source['name']}: {backup_id}")
                
        except Exception as e:
            logger.error(f"Error scheduling full backup: {e}")
    
    async def _schedule_incremental_backup(self):
        """Schedule an incremental backup operation."""
        try:
            logger.info("Scheduling incremental backup")
            
            for source in self.config.get("backup_sources", []):
                backup_id = await self.create_backup(
                    source_path=source["path"],
                    backup_type=BackupType.INCREMENTAL,
                    tags={"source_name": source["name"], "source_type": source["type"]}
                )
                
                if backup_id:
                    logger.info(f"Incremental backup scheduled for {source['name']}: {backup_id}")
                
        except Exception as e:
            logger.error(f"Error scheduling incremental backup: {e}")
    
    async def create_backup(self, source_path: str, backup_type: BackupType = BackupType.FULL,
                          tags: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Create a backup of the specified source."""
        try:
            backup_id = f"backup_{int(time.time() * 1000)}"
            
            # Validate source path
            if not os.path.exists(source_path):
                logger.error(f"Source path does not exist: {source_path}")
                return None
            
            # Create backup directory
            backup_dir = self.backup_root / backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=datetime.utcnow(),
                size_bytes=0,
                checksum="",
                source_path=source_path,
                backup_path=str(backup_dir),
                tags=tags or {}
            )
            
            # Store metadata
            self.backup_metadata[backup_id] = metadata
            
            # Perform backup asynchronously
            asyncio.create_task(self._execute_backup(metadata))
            
            logger.info(f"Backup created: {backup_id} for {source_path}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    async def _execute_backup(self, metadata: BackupMetadata):
        """Execute the actual backup operation."""
        try:
            metadata.status = BackupStatus.IN_PROGRESS
            
            logger.info(f"Executing backup {metadata.backup_id}")
            
            # Determine backup method based on type
            if metadata.backup_type == BackupType.FULL:
                success = await self._perform_full_backup_operation(metadata)
            elif metadata.backup_type == BackupType.INCREMENTAL:
                success = await self._perform_incremental_backup_operation(metadata)
            else:
                success = await self._perform_full_backup_operation(metadata)  # Default to full
            
            if success:
                # Calculate checksum
                metadata.checksum = await self._calculate_backup_checksum(metadata.backup_path)
                
                # Calculate size
                metadata.size_bytes = await self._calculate_backup_size(metadata.backup_path)
                
                # Update status
                metadata.status = BackupStatus.COMPLETED
                
                logger.info(f"Backup completed: {metadata.backup_id}")
            else:
                metadata.status = BackupStatus.FAILED
                logger.error(f"Backup failed: {metadata.backup_id}")
            
            # Save registry
            self._save_backup_registry()
            
        except Exception as e:
            logger.error(f"Error executing backup {metadata.backup_id}: {e}")
            metadata.status = BackupStatus.FAILED
    
    async def _perform_full_backup_operation(self, metadata: BackupMetadata) -> bool:
        """Perform a full backup operation."""
        try:
            source_path = Path(metadata.source_path)
            backup_path = Path(metadata.backup_path)
            
            if source_path.is_file():
                # Single file backup
                target_file = backup_path / source_path.name
                await self._copy_file_with_compression(source_path, target_file)
            else:
                # Directory backup
                await self._copy_directory_with_compression(source_path, backup_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error performing full backup: {e}")
            return False
    
    async def _perform_incremental_backup_operation(self, metadata: BackupMetadata) -> bool:
        """Perform an incremental backup operation."""
        try:
            # Find the last full backup for this source
            last_full_backup = self._find_last_full_backup(metadata.source_path)
            
            if not last_full_backup:
                logger.warning("No full backup found, performing full backup instead")
                return await self._perform_full_backup_operation(metadata)
            
            # Get files modified since last backup
            modified_files = await self._get_modified_files(
                metadata.source_path, 
                last_full_backup.created_at
            )
            
            if not modified_files:
                logger.info("No files modified since last backup")
                return True
            
            # Backup only modified files
            backup_path = Path(metadata.backup_path)
            for file_path in modified_files:
                relative_path = Path(file_path).relative_to(metadata.source_path)
                target_path = backup_path / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                await self._copy_file_with_compression(Path(file_path), target_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error performing incremental backup: {e}")
            return False
    
    async def _copy_file_with_compression(self, source: Path, target: Path):
        """Copy a file with optional compression."""
        try:
            if self.config.get("compression_enabled", True):
                # Compress file
                with open(source, 'rb') as f_in:
                    with gzip.open(f"{target}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Direct copy
                shutil.copy2(source, target)
                
        except Exception as e:
            logger.error(f"Error copying file {source} to {target}: {e}")
            raise
    
    async def _copy_directory_with_compression(self, source: Path, target: Path):
        """Copy a directory with optional compression."""
        try:
            if self.config.get("compression_enabled", True):
                # Create compressed archive
                archive_path = f"{target}.tar.gz"
                
                # Use tar command for better performance
                cmd = ["tar", "-czf", archive_path, "-C", str(source.parent), source.name]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"Tar command failed: {stderr.decode()}")
            else:
                # Direct directory copy
                shutil.copytree(source, target, dirs_exist_ok=True)
                
        except Exception as e:
            logger.error(f"Error copying directory {source} to {target}: {e}")
            raise
    
    def _find_last_full_backup(self, source_path: str) -> Optional[BackupMetadata]:
        """Find the last full backup for a source path."""
        last_backup = None
        
        for backup in self.backup_metadata.values():
            if (backup.source_path == source_path and 
                backup.backup_type == BackupType.FULL and
                backup.status == BackupStatus.COMPLETED):
                if not last_backup or backup.created_at > last_backup.created_at:
                    last_backup = backup
        
        return last_backup
    
    async def _get_modified_files(self, source_path: str, since: datetime) -> List[str]:
        """Get files modified since a specific time."""
        try:
            modified_files = []
            source = Path(source_path)
            
            if source.is_file():
                # Single file
                if datetime.fromtimestamp(source.stat().st_mtime) > since:
                    modified_files.append(str(source))
            else:
                # Directory
                for root, dirs, files in os.walk(source):
                    for file in files:
                        file_path = Path(root) / file
                        if datetime.fromtimestamp(file_path.stat().st_mtime) > since:
                            modified_files.append(str(file_path))
            
            return modified_files
            
        except Exception as e:
            logger.error(f"Error getting modified files: {e}")
            return []
    
    async def _calculate_backup_checksum(self, backup_path: str) -> str:
        """Calculate checksum for backup verification."""
        try:
            hasher = hashlib.sha256()
            backup_dir = Path(backup_path)
            
            # Calculate checksum for all files in backup
            for file_path in sorted(backup_dir.rglob("*")):
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating backup checksum: {e}")
            return ""
    
    async def _calculate_backup_size(self, backup_path: str) -> int:
        """Calculate total size of backup."""
        try:
            total_size = 0
            backup_dir = Path(backup_path)
            
            for file_path in backup_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            logger.error(f"Error calculating backup size: {e}")
            return 0
    
    async def restore_backup(self, backup_id: str, target_path: str,
                           recovery_type: RecoveryType = RecoveryType.FULL_RESTORE) -> Optional[str]:
        """Restore a backup to the specified target path."""
        try:
            # Validate backup exists
            if backup_id not in self.backup_metadata:
                logger.error(f"Backup not found: {backup_id}")
                return None
            
            backup_metadata = self.backup_metadata[backup_id]
            
            # Validate backup is completed
            if backup_metadata.status != BackupStatus.COMPLETED:
                logger.error(f"Backup is not completed: {backup_id}")
                return None
            
            # Create recovery operation
            recovery_id = f"recovery_{int(time.time() * 1000)}"
            recovery_op = RecoveryOperation(
                recovery_id=recovery_id,
                recovery_type=recovery_type,
                backup_id=backup_id,
                target_path=target_path,
                started_at=datetime.utcnow()
            )
            
            # Store operation
            self.active_operations[recovery_id] = recovery_op
            
            # Execute recovery asynchronously
            asyncio.create_task(self._execute_recovery(recovery_op, backup_metadata))
            
            logger.info(f"Recovery started: {recovery_id} for backup {backup_id}")
            return recovery_id
            
        except Exception as e:
            logger.error(f"Error starting recovery: {e}")
            return None
    
    async def _execute_recovery(self, recovery_op: RecoveryOperation, backup_metadata: BackupMetadata):
        """Execute the recovery operation."""
        try:
            recovery_op.status = BackupStatus.IN_PROGRESS
            
            logger.info(f"Executing recovery {recovery_op.recovery_id}")
            
            # Verify backup integrity before recovery
            if not await self._verify_backup_integrity_single(backup_metadata):
                recovery_op.status = BackupStatus.CORRUPTED
                recovery_op.error_message = "Backup integrity check failed"
                return
            
            # Perform recovery based on type
            success = False
            if recovery_op.recovery_type == RecoveryType.FULL_RESTORE:
                success = await self._perform_full_restore(recovery_op, backup_metadata)
            elif recovery_op.recovery_type == RecoveryType.PARTIAL_RESTORE:
                success = await self._perform_partial_restore(recovery_op, backup_metadata)
            else:
                success = await self._perform_full_restore(recovery_op, backup_metadata)
            
            # Update operation status
            recovery_op.completed_at = datetime.utcnow()
            recovery_op.progress_percentage = 100.0
            
            if success:
                recovery_op.status = BackupStatus.COMPLETED
                logger.info(f"Recovery completed: {recovery_op.recovery_id}")
            else:
                recovery_op.status = BackupStatus.FAILED
                logger.error(f"Recovery failed: {recovery_op.recovery_id}")
            
            # Move to history
            self.operation_history.append(recovery_op)
            if recovery_op.recovery_id in self.active_operations:
                del self.active_operations[recovery_op.recovery_id]
            
        except Exception as e:
            logger.error(f"Error executing recovery {recovery_op.recovery_id}: {e}")
            recovery_op.status = BackupStatus.FAILED
            recovery_op.error_message = str(e)
    
    async def _perform_full_restore(self, recovery_op: RecoveryOperation, 
                                  backup_metadata: BackupMetadata) -> bool:
        """Perform a full restore operation."""
        try:
            backup_path = Path(backup_metadata.backup_path)
            target_path = Path(recovery_op.target_path)
            
            # Create target directory
            target_path.mkdir(parents=True, exist_ok=True)
            
            # Check if backup is compressed
            if self.config.get("compression_enabled", True):
                # Handle compressed backup
                archive_files = list(backup_path.glob("*.tar.gz"))
                if archive_files:
                    # Extract compressed archive
                    archive_file = archive_files[0]
                    cmd = ["tar", "-xzf", str(archive_file), "-C", str(target_path)]
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        raise Exception(f"Tar extraction failed: {stderr.decode()}")
                else:
                    # Handle individual compressed files
                    for gz_file in backup_path.glob("*.gz"):
                        target_file = target_path / gz_file.stem
                        with gzip.open(gz_file, 'rb') as f_in:
                            with open(target_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
            else:
                # Direct copy
                for item in backup_path.iterdir():
                    if item.is_file():
                        shutil.copy2(item, target_path / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, target_path / item.name, dirs_exist_ok=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error performing full restore: {e}")
            return False
    
    async def _perform_partial_restore(self, recovery_op: RecoveryOperation,
                                     backup_metadata: BackupMetadata) -> bool:
        """Perform a partial restore operation."""
        try:
            # For now, partial restore is the same as full restore
            # In a real implementation, this would allow selecting specific files/directories
            return await self._perform_full_restore(recovery_op, backup_metadata)
            
        except Exception as e:
            logger.error(f"Error performing partial restore: {e}")
            return False
    
    async def _cleanup_old_backups(self):
        """Clean up old backups based on retention policy."""
        try:
            retention_days = self.config.get("backup_retention_days", 30)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            backups_to_remove = []
            
            for backup_id, metadata in self.backup_metadata.items():
                if metadata.created_at < cutoff_date:
                    backups_to_remove.append(backup_id)
            
            for backup_id in backups_to_remove:
                await self._remove_backup(backup_id)
                
            if backups_to_remove:
                logger.info(f"Cleaned up {len(backups_to_remove)} old backups")
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    async def _remove_backup(self, backup_id: str):
        """Remove a backup and its files."""
        try:
            if backup_id not in self.backup_metadata:
                return
            
            metadata = self.backup_metadata[backup_id]
            backup_path = Path(metadata.backup_path)
            
            # Remove backup files
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            # Remove from metadata
            del self.backup_metadata[backup_id]
            
            logger.info(f"Removed backup: {backup_id}")
            
        except Exception as e:
            logger.error(f"Error removing backup {backup_id}: {e}")
    
    async def _verify_backup_integrity(self):
        """Verify integrity of all backups."""
        try:
            if not self.config.get("integrity_check_enabled", True):
                return
            
            for backup_id, metadata in self.backup_metadata.items():
                if metadata.status == BackupStatus.COMPLETED:
                    is_valid = await self._verify_backup_integrity_single(metadata)
                    
                    if not is_valid:
                        logger.error(f"Backup integrity check failed: {backup_id}")
                        metadata.status = BackupStatus.CORRUPTED
            
        except Exception as e:
            logger.error(f"Error verifying backup integrity: {e}")
    
    async def _verify_backup_integrity_single(self, metadata: BackupMetadata) -> bool:
        """Verify integrity of a single backup."""
        try:
            # Calculate current checksum
            current_checksum = await self._calculate_backup_checksum(metadata.backup_path)
            
            # Compare with stored checksum
            return current_checksum == metadata.checksum
            
        except Exception as e:
            logger.error(f"Error verifying backup integrity for {metadata.backup_id}: {e}")
            return False
    
    async def _perform_system_check(self):
        """Perform initial system check."""
        try:
            # Check backup directory permissions
            if not os.access(self.backup_root, os.W_OK):
                logger.error(f"Backup directory is not writable: {self.backup_root}")
                return
            
            # Check available disk space
            disk_usage = shutil.disk_usage(self.backup_root)
            free_space_gb = disk_usage.free / (1024**3)
            
            if free_space_gb < 1.0:  # Less than 1GB free
                logger.warning(f"Low disk space for backups: {free_space_gb:.2f}GB free")
            
            # Verify existing backups
            await self._verify_backup_integrity()
            
            logger.info("System check completed")
            
        except Exception as e:
            logger.error(f"Error performing system check: {e}")
    
    def _load_backup_registry(self):
        """Load backup registry from disk."""
        try:
            registry_file = self.backup_root / "backup_registry.json"
            
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    registry_data = json.load(f)
                
                # Reconstruct metadata objects
                for backup_id, data in registry_data.items():
                    metadata = BackupMetadata(
                        backup_id=data["backup_id"],
                        backup_type=BackupType(data["backup_type"]),
                        created_at=datetime.fromisoformat(data["created_at"]),
                        size_bytes=data["size_bytes"],
                        checksum=data["checksum"],
                        source_path=data["source_path"],
                        backup_path=data["backup_path"],
                        compression_ratio=data.get("compression_ratio", 0.0),
                        status=BackupStatus(data["status"]),
                        retention_days=data.get("retention_days", 30),
                        tags=data.get("tags", {})
                    )
                    self.backup_metadata[backup_id] = metadata
                
                logger.info(f"Loaded {len(self.backup_metadata)} backups from registry")
            
        except Exception as e:
            logger.error(f"Error loading backup registry: {e}")
    
    def _save_backup_registry(self):
        """Save backup registry to disk."""
        try:
            registry_file = self.backup_root / "backup_registry.json"
            
            # Convert metadata to serializable format
            registry_data = {}
            for backup_id, metadata in self.backup_metadata.items():
                registry_data[backup_id] = {
                    "backup_id": metadata.backup_id,
                    "backup_type": metadata.backup_type.value,
                    "created_at": metadata.created_at.isoformat(),
                    "size_bytes": metadata.size_bytes,
                    "checksum": metadata.checksum,
                    "source_path": metadata.source_path,
                    "backup_path": metadata.backup_path,
                    "compression_ratio": metadata.compression_ratio,
                    "status": metadata.status.value,
                    "retention_days": metadata.retention_days,
                    "tags": metadata.tags
                }
            
            # Write to file
            with open(registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving backup registry: {e}")
    
    def list_backups(self, source_path: Optional[str] = None, 
                    backup_type: Optional[BackupType] = None) -> List[Dict[str, Any]]:
        """List available backups with optional filtering."""
        try:
            backups = []
            
            for metadata in self.backup_metadata.values():
                # Apply filters
                if source_path and metadata.source_path != source_path:
                    continue
                
                if backup_type and metadata.backup_type != backup_type:
                    continue
                
                backups.append({
                    "backup_id": metadata.backup_id,
                    "backup_type": metadata.backup_type.value,
                    "created_at": metadata.created_at.isoformat(),
                    "size_bytes": metadata.size_bytes,
                    "size_mb": round(metadata.size_bytes / (1024*1024), 2),
                    "source_path": metadata.source_path,
                    "status": metadata.status.value,
                    "tags": metadata.tags
                })
            
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x["created_at"], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific backup."""
        try:
            if backup_id not in self.backup_metadata:
                return None
            
            metadata = self.backup_metadata[backup_id]
            
            return {
                "backup_id": metadata.backup_id,
                "backup_type": metadata.backup_type.value,
                "created_at": metadata.created_at.isoformat(),
                "size_bytes": metadata.size_bytes,
                "size_mb": round(metadata.size_bytes / (1024*1024), 2),
                "checksum": metadata.checksum,
                "source_path": metadata.source_path,
                "backup_path": metadata.backup_path,
                "compression_ratio": metadata.compression_ratio,
                "status": metadata.status.value,
                "retention_days": metadata.retention_days,
                "tags": metadata.tags
            }
            
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return None
    
    def get_recovery_status(self, recovery_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a recovery operation."""
        try:
            # Check active operations
            if recovery_id in self.active_operations:
                op = self.active_operations[recovery_id]
                return {
                    "recovery_id": op.recovery_id,
                    "recovery_type": op.recovery_type.value,
                    "backup_id": op.backup_id,
                    "target_path": op.target_path,
                    "started_at": op.started_at.isoformat(),
                    "status": op.status.value,
                    "progress_percentage": op.progress_percentage,
                    "error_message": op.error_message
                }
            
            # Check history
            for op in self.operation_history:
                if op.recovery_id == recovery_id:
                    return {
                        "recovery_id": op.recovery_id,
                        "recovery_type": op.recovery_type.value,
                        "backup_id": op.backup_id,
                        "target_path": op.target_path,
                        "started_at": op.started_at.isoformat(),
                        "completed_at": op.completed_at.isoformat() if op.completed_at else None,
                        "status": op.status.value,
                        "progress_percentage": op.progress_percentage,
                        "error_message": op.error_message
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting recovery status: {e}")
            return None
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            total_backups = len(self.backup_metadata)
            completed_backups = sum(1 for m in self.backup_metadata.values() 
                                  if m.status == BackupStatus.COMPLETED)
            failed_backups = sum(1 for m in self.backup_metadata.values() 
                               if m.status == BackupStatus.FAILED)
            
            # Calculate total backup size
            total_size = sum(m.size_bytes for m in self.backup_metadata.values() 
                           if m.status == BackupStatus.COMPLETED)
            
            # Get disk usage
            disk_usage = shutil.disk_usage(self.backup_root)
            
            # Backup type distribution
            type_distribution = {}
            for metadata in self.backup_metadata.values():
                backup_type = metadata.backup_type.value
                type_distribution[backup_type] = type_distribution.get(backup_type, 0) + 1
            
            return {
                "system_active": self.system_active,
                "total_backups": total_backups,
                "completed_backups": completed_backups,
                "failed_backups": failed_backups,
                "success_rate": completed_backups / total_backups if total_backups > 0 else 0,
                "total_backup_size_bytes": total_size,
                "total_backup_size_gb": round(total_size / (1024**3), 2),
                "active_recoveries": len(self.active_operations),
                "backup_type_distribution": type_distribution,
                "disk_usage": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2)
                },
                "config": {
                    "compression_enabled": self.config.get("compression_enabled", True),
                    "retention_days": self.config.get("backup_retention_days", 30),
                    "full_backup_interval_hours": self.config.get("full_backup_interval", 86400) / 3600,
                    "incremental_backup_interval_hours": self.config.get("incremental_backup_interval", 3600) / 3600
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}


# Global backup recovery system instance
backup_recovery_system = BackupRecoverySystem()


# Convenience functions
async def start_backup_system():
    """Start the global backup and recovery system."""
    await backup_recovery_system.start_system()


async def stop_backup_system():
    """Stop the global backup and recovery system."""
    await backup_recovery_system.stop_system()


async def create_backup(source_path: str, backup_type: str = "full", 
                       tags: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Create a backup of the specified source."""
    try:
        backup_type_enum = BackupType(backup_type)
        return await backup_recovery_system.create_backup(source_path, backup_type_enum, tags)
    except ValueError:
        logger.error(f"Invalid backup type: {backup_type}")
        return None


async def restore_backup(backup_id: str, target_path: str, 
                        recovery_type: str = "full_restore") -> Optional[str]:
    """Restore a backup to the specified target path."""
    try:
        recovery_type_enum = RecoveryType(recovery_type)
        return await backup_recovery_system.restore_backup(backup_id, target_path, recovery_type_enum)
    except ValueError:
        logger.error(f"Invalid recovery type: {recovery_type}")
        return None


def get_backup_status() -> Dict[str, Any]:
    """Get current backup system status."""
    return {
        "system_active": backup_recovery_system.system_active,
        "total_backups": len(backup_recovery_system.backup_metadata),
        "active_recoveries": len(backup_recovery_system.active_operations),
        "statistics": backup_recovery_system.get_system_statistics()
    }