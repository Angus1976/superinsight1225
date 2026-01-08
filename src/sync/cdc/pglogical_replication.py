"""
PostgreSQL Logical Replication Module.

Provides pglogical-based logical replication for PostgreSQL,
supporting cross-database real-time synchronization with conflict detection.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import asyncpg
from pydantic import BaseModel, Field

from .database_cdc import BaseCDC, CDCConfig, CDCOperation, ChangeEvent, CDCPosition

logger = logging.getLogger(__name__)


class ReplicationMode(str, Enum):
    """Logical replication modes."""
    PUBLISHER = "publisher"    # Source database (publishes changes)
    SUBSCRIBER = "subscriber"  # Target database (receives changes)
    BIDIRECTIONAL = "bidirectional"  # Both publisher and subscriber


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    APPLY_REMOTE = "apply_remote"      # Remote changes win
    KEEP_LOCAL = "keep_local"          # Local changes win
    LAST_UPDATE_WINS = "last_update_wins"  # Timestamp-based
    FIRST_UPDATE_WINS = "first_update_wins"  # First writer wins
    MANUAL = "manual"                  # Manual resolution required


@dataclass
class PgLogicalConfig(CDCConfig):
    """pglogical replication configuration."""
    # Replication settings
    replication_mode: ReplicationMode = ReplicationMode.SUBSCRIBER
    node_name: str = "default_node"
    provider_dsn: Optional[str] = None  # Source database DSN
    subscriber_dsn: Optional[str] = None  # Target database DSN
    
    # Publication/Subscription settings
    publication_name: str = "sync_publication"
    subscription_name: str = "sync_subscription"
    replication_sets: List[str] = field(default_factory=lambda: ["default"])
    
    # Conflict resolution
    conflict_resolution: ConflictResolution = ConflictResolution.APPLY_REMOTE
    conflict_logging: bool = True
    
    # Performance settings
    synchronous_commit: str = "local"  # off, local, remote_write, remote_apply
    max_replication_slots: int = 10
    wal_level: str = "logical"
    max_wal_senders: int = 10
    
    # Monitoring
    apply_delay_threshold_ms: int = 5000
    sync_check_interval_s: int = 30
    
    # Table filtering
    replicate_insert: bool = True
    replicate_update: bool = True
    replicate_delete: bool = True
    replicate_truncate: bool = False


@dataclass
class ReplicationNode:
    """Represents a pglogical node."""
    name: str
    dsn: str
    node_id: Optional[int] = None
    is_local: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "dsn": self.dsn,
            "node_id": self.node_id,
            "is_local": self.is_local
        }


@dataclass
class ReplicationSet:
    """Represents a replication set."""
    name: str
    tables: List[str] = field(default_factory=list)
    sequences: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tables": self.tables,
            "sequences": self.sequences
        }


@dataclass
class ConflictInfo:
    """Information about a replication conflict."""
    id: str
    table_name: str
    conflict_type: str  # insert_exists, update_missing, delete_missing, etc.
    local_tuple: Optional[Dict[str, Any]]
    remote_tuple: Optional[Dict[str, Any]]
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime = field(default_factory=datetime.utcnow)


class PgLogicalReplication(BaseCDC):
    """
    PostgreSQL logical replication implementation using pglogical.
    
    Supports both publisher and subscriber modes, with conflict detection
    and resolution for bidirectional replication scenarios.
    """
    
    def __init__(self, config: PgLogicalConfig):
        super().__init__(config)
        self.pglogical_config = config
        self._local_conn: Optional[asyncpg.Connection] = None
        self._remote_conn: Optional[asyncpg.Connection] = None
        self._replication_conn: Optional[asyncpg.Connection] = None
        self._local_node: Optional[ReplicationNode] = None
        self._remote_node: Optional[ReplicationNode] = None
        self._conflicts: List[ConflictInfo] = []
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Connect to PostgreSQL databases for logical replication."""
        try:
            # Connect to local database
            local_dsn = self._build_dsn(
                self.config.host,
                self.config.port,
                self.config.database,
                self.config.username,
                self.config.password
            )
            
            self._local_conn = await asyncpg.connect(local_dsn)
            
            # Connect to remote database if specified
            if self.pglogical_config.provider_dsn:
                self._remote_conn = await asyncpg.connect(self.pglogical_config.provider_dsn)
            
            # Verify pglogical extension
            await self._verify_pglogical_extension()
            
            # Initialize nodes
            await self._initialize_nodes()
            
            logger.info("Connected to PostgreSQL for logical replication")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect for logical replication: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL databases."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._replication_conn:
            await self._replication_conn.close()
        
        if self._remote_conn:
            await self._remote_conn.close()
        
        if self._local_conn:
            await self._local_conn.close()
        
        logger.info("Disconnected from PostgreSQL logical replication")
    
    async def start_capture(self) -> None:
        """Start logical replication capture."""
        self._running = True
        self._stats["started_at"] = datetime.utcnow()
        
        if self.pglogical_config.replication_mode == ReplicationMode.PUBLISHER:
            await self._start_publisher()
        elif self.pglogical_config.replication_mode == ReplicationMode.SUBSCRIBER:
            await self._start_subscriber()
        else:  # BIDIRECTIONAL
            await self._start_bidirectional()
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_replication())
    
    async def stop_capture(self) -> None:
        """Stop logical replication capture."""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
    
    async def get_changes(
        self,
        from_position: Optional[CDCPosition] = None
    ) -> AsyncIterator[ChangeEvent]:
        """Get changes from logical replication stream."""
        # This is handled by the replication subscription
        # For manual polling, we could query the replication origin
        raise NotImplementedError("Use start_capture for streaming replication")
    
    async def _verify_pglogical_extension(self) -> None:
        """Verify pglogical extension is installed and configured."""
        # Check if pglogical extension exists
        result = await self._local_conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pglogical')"
        )
        
        if not result:
            raise Exception("pglogical extension is not installed")
        
        # Check configuration parameters
        wal_level = await self._local_conn.fetchval("SHOW wal_level")
        if wal_level != "logical":
            logger.warning(f"wal_level is {wal_level}, should be 'logical'")
        
        max_replication_slots = await self._local_conn.fetchval("SHOW max_replication_slots")
        if int(max_replication_slots) < self.pglogical_config.max_replication_slots:
            logger.warning(f"max_replication_slots is {max_replication_slots}, may need to increase")
    
    async def _initialize_nodes(self) -> None:
        """Initialize pglogical nodes."""
        # Create local node
        local_dsn = self._build_dsn(
            self.config.host,
            self.config.port,
            self.config.database,
            self.config.username,
            self.config.password
        )
        
        self._local_node = ReplicationNode(
            name=self.pglogical_config.node_name,
            dsn=local_dsn,
            is_local=True
        )
        
        # Create local node if it doesn't exist
        try:
            await self._local_conn.execute(
                "SELECT pglogical.create_node(node_name := $1, dsn := $2)",
                self._local_node.name,
                self._local_node.dsn
            )
            logger.info(f"Created local node: {self._local_node.name}")
        except asyncpg.exceptions.UniqueViolationError:
            logger.info(f"Local node already exists: {self._local_node.name}")
        
        # Create remote node if needed
        if self.pglogical_config.provider_dsn and self._remote_conn:
            remote_node_name = f"remote_{self.pglogical_config.node_name}"
            self._remote_node = ReplicationNode(
                name=remote_node_name,
                dsn=self.pglogical_config.provider_dsn,
                is_local=False
            )
    
    async def _start_publisher(self) -> None:
        """Start as a publisher (source)."""
        # Create replication set
        await self._create_replication_set()
        
        # Add tables to replication set
        await self._add_tables_to_replication_set()
        
        logger.info("Started as pglogical publisher")
    
    async def _start_subscriber(self) -> None:
        """Start as a subscriber (target)."""
        if not self.pglogical_config.provider_dsn:
            raise ValueError("provider_dsn is required for subscriber mode")
        
        # Create subscription
        await self._create_subscription()
        
        # Start monitoring replication lag
        asyncio.create_task(self._monitor_replication_lag())
        
        logger.info("Started as pglogical subscriber")
    
    async def _start_bidirectional(self) -> None:
        """Start bidirectional replication."""
        # Setup as both publisher and subscriber
        await self._start_publisher()
        await self._start_subscriber()
        
        # Enable conflict detection and resolution
        await self._setup_conflict_resolution()
        
        logger.info("Started bidirectional pglogical replication")
    
    async def _create_replication_set(self) -> None:
        """Create replication set for publishing."""
        for repl_set in self.pglogical_config.replication_sets:
            try:
                await self._local_conn.execute(
                    "SELECT pglogical.create_replication_set($1, $2, $3, $4, $5)",
                    repl_set,
                    self.pglogical_config.replicate_insert,
                    self.pglogical_config.replicate_update,
                    self.pglogical_config.replicate_delete,
                    self.pglogical_config.replicate_truncate
                )
                logger.info(f"Created replication set: {repl_set}")
            except asyncpg.exceptions.UniqueViolationError:
                logger.info(f"Replication set already exists: {repl_set}")
    
    async def _add_tables_to_replication_set(self) -> None:
        """Add tables to replication set."""
        for table in self.config.tables:
            for repl_set in self.pglogical_config.replication_sets:
                try:
                    await self._local_conn.execute(
                        "SELECT pglogical.replication_set_add_table($1, $2, $3)",
                        repl_set,
                        table,
                        True  # synchronize_data
                    )
                    logger.info(f"Added table {table} to replication set {repl_set}")
                except Exception as e:
                    logger.warning(f"Failed to add table {table} to replication set: {e}")
    
    async def _create_subscription(self) -> None:
        """Create subscription for receiving changes."""
        try:
            await self._local_conn.execute(
                """
                SELECT pglogical.create_subscription(
                    subscription_name := $1,
                    provider_dsn := $2,
                    replication_sets := $3,
                    synchronize_structure := false,
                    synchronize_data := true
                )
                """,
                self.pglogical_config.subscription_name,
                self.pglogical_config.provider_dsn,
                self.pglogical_config.replication_sets
            )
            logger.info(f"Created subscription: {self.pglogical_config.subscription_name}")
        except asyncpg.exceptions.UniqueViolationError:
            logger.info(f"Subscription already exists: {self.pglogical_config.subscription_name}")
    
    async def _setup_conflict_resolution(self) -> None:
        """Setup conflict detection and resolution."""
        # Configure conflict resolution for each table
        for table in self.config.tables:
            try:
                # Set conflict resolution method
                await self._local_conn.execute(
                    f"""
                    ALTER TABLE {table} 
                    SET (pglogical.conflict_resolution = '{self.pglogical_config.conflict_resolution.value}')
                    """
                )
                
                # Enable conflict logging if requested
                if self.pglogical_config.conflict_logging:
                    await self._local_conn.execute(
                        f"ALTER TABLE {table} SET (pglogical.conflict_log = true)"
                    )
                
                logger.info(f"Configured conflict resolution for table: {table}")
                
            except Exception as e:
                logger.warning(f"Failed to configure conflict resolution for {table}: {e}")
    
    async def _monitor_replication(self) -> None:
        """Monitor replication status and conflicts."""
        while self._running:
            try:
                # Check replication status
                await self._check_replication_status()
                
                # Check for conflicts
                await self._check_conflicts()
                
                # Update statistics
                await self._update_replication_stats()
                
                await asyncio.sleep(self.pglogical_config.sync_check_interval_s)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Replication monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _check_replication_status(self) -> None:
        """Check replication status and lag."""
        try:
            # Check subscription status
            if self.pglogical_config.replication_mode in [ReplicationMode.SUBSCRIBER, ReplicationMode.BIDIRECTIONAL]:
                status = await self._local_conn.fetch(
                    """
                    SELECT subscription_name, status, provider_node, replication_sets,
                           forward_origins, slot_name
                    FROM pglogical.show_subscription_status()
                    WHERE subscription_name = $1
                    """,
                    self.pglogical_config.subscription_name
                )
                
                for row in status:
                    if row['status'] != 'replicating':
                        logger.warning(f"Subscription {row['subscription_name']} status: {row['status']}")
            
            # Check replication slots
            slots = await self._local_conn.fetch(
                """
                SELECT slot_name, plugin, slot_type, datoid, database, active,
                       active_pid, xmin, catalog_xmin, restart_lsn, confirmed_flush_lsn
                FROM pg_replication_slots
                WHERE plugin = 'pglogical_output'
                """
            )
            
            for slot in slots:
                if not slot['active']:
                    logger.warning(f"Replication slot {slot['slot_name']} is not active")
                    
        except Exception as e:
            logger.error(f"Failed to check replication status: {e}")
    
    async def _check_conflicts(self) -> None:
        """Check for replication conflicts."""
        try:
            # Query conflict log
            conflicts = await self._local_conn.fetch(
                """
                SELECT * FROM pglogical.conflict_log
                WHERE resolved IS NULL
                ORDER BY conflict_time DESC
                LIMIT 100
                """
            )
            
            for conflict in conflicts:
                conflict_info = ConflictInfo(
                    id=str(conflict['conflict_id']),
                    table_name=conflict['table_name'],
                    conflict_type=conflict['conflict_type'],
                    local_tuple=json.loads(conflict['local_tuple']) if conflict['local_tuple'] else None,
                    remote_tuple=json.loads(conflict['remote_tuple']) if conflict['remote_tuple'] else None,
                    created_at=conflict['conflict_time']
                )
                
                self._conflicts.append(conflict_info)
                
                # Emit conflict event
                await self.emit_event(ChangeEvent(
                    id=f"conflict_{conflict_info.id}",
                    operation=CDCOperation.UPDATE,  # Conflicts are typically updates
                    table=conflict_info.table_name,
                    timestamp=conflict_info.created_at,
                    metadata={
                        "conflict_type": conflict_info.conflict_type,
                        "local_tuple": conflict_info.local_tuple,
                        "remote_tuple": conflict_info.remote_tuple,
                        "event_type": "conflict"
                    }
                ))
                
        except Exception as e:
            logger.error(f"Failed to check conflicts: {e}")
    
    async def _monitor_replication_lag(self) -> None:
        """Monitor replication lag."""
        while self._running:
            try:
                # Get replication lag
                lag = await self._local_conn.fetchval(
                    """
                    SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) * 1000
                    """
                )
                
                if lag and lag > self.pglogical_config.apply_delay_threshold_ms:
                    logger.warning(f"Replication lag is {lag:.2f}ms")
                    
                    # Emit lag warning event
                    await self.emit_event(ChangeEvent(
                        id=f"lag_warning_{int(time.time())}",
                        operation=CDCOperation.UPDATE,
                        table="system",
                        timestamp=datetime.utcnow(),
                        metadata={
                            "lag_ms": lag,
                            "threshold_ms": self.pglogical_config.apply_delay_threshold_ms,
                            "event_type": "replication_lag"
                        }
                    ))
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Replication lag monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _update_replication_stats(self) -> None:
        """Update replication statistics."""
        try:
            # Get subscription statistics
            if self.pglogical_config.replication_mode in [ReplicationMode.SUBSCRIBER, ReplicationMode.BIDIRECTIONAL]:
                stats = await self._local_conn.fetchrow(
                    """
                    SELECT received_lsn, last_msg_send_time, last_msg_receipt_time,
                           latest_end_lsn, latest_end_time
                    FROM pg_stat_subscription
                    WHERE subname = $1
                    """,
                    self.pglogical_config.subscription_name
                )
                
                if stats:
                    self._stats.update({
                        "received_lsn": str(stats['received_lsn']) if stats['received_lsn'] else None,
                        "last_msg_send_time": stats['last_msg_send_time'],
                        "last_msg_receipt_time": stats['last_msg_receipt_time'],
                        "latest_end_lsn": str(stats['latest_end_lsn']) if stats['latest_end_lsn'] else None,
                        "latest_end_time": stats['latest_end_time']
                    })
            
            # Update conflict count
            self._stats["conflicts_detected"] = len(self._conflicts)
            self._stats["unresolved_conflicts"] = len([c for c in self._conflicts if not c.resolved_at])
            
        except Exception as e:
            logger.error(f"Failed to update replication stats: {e}")
    
    def _build_dsn(self, host: str, port: int, database: str, username: str, password: str) -> str:
        """Build PostgreSQL DSN."""
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    async def resolve_conflict(self, conflict_id: str, resolution: str) -> bool:
        """Manually resolve a conflict."""
        try:
            # Find the conflict
            conflict = next((c for c in self._conflicts if c.id == conflict_id), None)
            if not conflict:
                return False
            
            # Apply resolution
            await self._local_conn.execute(
                "UPDATE pglogical.conflict_log SET resolved = $1 WHERE conflict_id = $2",
                resolution,
                int(conflict_id)
            )
            
            conflict.resolution = resolution
            conflict.resolved_at = datetime.utcnow()
            
            logger.info(f"Resolved conflict {conflict_id} with resolution: {resolution}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {e}")
            return False
    
    async def get_replication_info(self) -> Dict[str, Any]:
        """Get comprehensive replication information."""
        info = {
            "mode": self.pglogical_config.replication_mode.value,
            "node_name": self.pglogical_config.node_name,
            "publication_name": self.pglogical_config.publication_name,
            "subscription_name": self.pglogical_config.subscription_name,
            "replication_sets": self.pglogical_config.replication_sets,
            "conflict_resolution": self.pglogical_config.conflict_resolution.value,
            "stats": self._stats,
            "conflicts": [c.__dict__ for c in self._conflicts[-10:]]  # Last 10 conflicts
        }
        
        try:
            # Add subscription status
            if self.pglogical_config.replication_mode in [ReplicationMode.SUBSCRIBER, ReplicationMode.BIDIRECTIONAL]:
                status = await self._local_conn.fetchrow(
                    "SELECT * FROM pglogical.show_subscription_status() WHERE subscription_name = $1",
                    self.pglogical_config.subscription_name
                )
                if status:
                    info["subscription_status"] = dict(status)
            
            # Add replication slots info
            slots = await self._local_conn.fetch(
                "SELECT * FROM pg_replication_slots WHERE plugin = 'pglogical_output'"
            )
            info["replication_slots"] = [dict(slot) for slot in slots]
            
        except Exception as e:
            logger.error(f"Failed to get replication info: {e}")
        
        return info


class PgLogicalManager:
    """
    Manager for multiple pglogical replication instances.
    
    Coordinates multiple replication streams and provides
    centralized monitoring and management.
    """
    
    def __init__(self):
        self._replications: Dict[str, PgLogicalReplication] = {}
    
    def register(self, replication: PgLogicalReplication) -> None:
        """Register a pglogical replication instance."""
        self._replications[replication.config.name] = replication
        logger.info(f"Registered pglogical replication: {replication.config.name}")
    
    async def start_all(self) -> None:
        """Start all registered replication instances."""
        for name, repl in self._replications.items():
            try:
                if await repl.connect():
                    await repl.start_capture()
                    logger.info(f"Started pglogical replication: {name}")
                else:
                    logger.error(f"Failed to start pglogical replication: {name}")
            except Exception as e:
                logger.error(f"Error starting replication {name}: {e}")
    
    async def stop_all(self) -> None:
        """Stop all replication instances."""
        for name, repl in self._replications.items():
            try:
                await repl.stop_capture()
                await repl.disconnect()
                logger.info(f"Stopped pglogical replication: {name}")
            except Exception as e:
                logger.error(f"Error stopping replication {name}: {e}")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all replication instances."""
        return {
            name: repl.stats
            for name, repl in self._replications.items()
        }
    
    async def get_all_replication_info(self) -> Dict[str, Any]:
        """Get comprehensive information for all replications."""
        info = {}
        
        for name, repl in self._replications.items():
            try:
                info[name] = await repl.get_replication_info()
            except Exception as e:
                logger.error(f"Failed to get info for replication {name}: {e}")
                info[name] = {"error": str(e)}
        
        return info


def create_pglogical_replication(config: PgLogicalConfig) -> PgLogicalReplication:
    """Factory function to create pglogical replication instance."""
    return PgLogicalReplication(config)


__all__ = [
    "PgLogicalReplication",
    "PgLogicalConfig",
    "PgLogicalManager",
    "ReplicationMode",
    "ConflictResolution",
    "ReplicationNode",
    "ReplicationSet",
    "ConflictInfo",
    "create_pglogical_replication",
]