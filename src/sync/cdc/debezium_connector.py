"""
Debezium CDC Connector Module.

Provides integration with Debezium for Change Data Capture,
supporting Kafka Connect and embedded Debezium engine.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field

from .database_cdc import BaseCDC, CDCConfig, CDCOperation, ChangeEvent, CDCPosition

logger = logging.getLogger(__name__)


class DebeziumConnectorType(str, Enum):
    """Debezium connector types."""
    MYSQL = "io.debezium.connector.mysql.MySqlConnector"
    POSTGRESQL = "io.debezium.connector.postgresql.PostgreSqlConnector"
    MONGODB = "io.debezium.connector.mongodb.MongoDbConnector"
    SQLSERVER = "io.debezium.connector.sqlserver.SqlServerConnector"
    ORACLE = "io.debezium.connector.oracle.OracleConnector"


class DebeziumMode(str, Enum):
    """Debezium deployment modes."""
    KAFKA_CONNECT = "kafka_connect"  # Kafka Connect cluster
    EMBEDDED = "embedded"            # Embedded Debezium engine


@dataclass
class DebeziumConfig(CDCConfig):
    """Debezium-specific configuration."""
    # Debezium settings
    connector_type: DebeziumConnectorType
    mode: DebeziumMode = DebeziumMode.KAFKA_CONNECT
    
    # Kafka Connect settings (for KAFKA_CONNECT mode)
    kafka_connect_url: str = "http://localhost:8083"
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # Topic settings
    topic_prefix: str = "dbserver1"
    schema_registry_url: Optional[str] = None
    
    # Connector-specific settings
    server_id: Optional[int] = None  # MySQL
    slot_name: Optional[str] = None  # PostgreSQL
    publication_name: Optional[str] = None  # PostgreSQL
    
    # Snapshot settings
    snapshot_mode: str = "initial"  # initial, when_needed, never, etc.
    snapshot_locking_mode: str = "minimal"
    
    # Filtering
    table_include_list: Optional[str] = None
    table_exclude_list: Optional[str] = None
    column_include_list: Optional[str] = None
    column_exclude_list: Optional[str] = None
    
    # Performance settings
    max_batch_size: int = 2048
    max_queue_size: int = 8192
    poll_interval_ms: int = 1000
    
    # Monitoring
    enable_metrics: bool = True
    jmx_port: Optional[int] = None


class KafkaConnectClient:
    """Client for Kafka Connect REST API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
    
    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Kafka Connect."""
        url = f"{self.base_url}{path}"
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        async with self._session.request(method, url, **kwargs) as response:
            if response.status >= 400:
                text = await response.text()
                raise Exception(f"Kafka Connect API error {response.status}: {text}")
            
            return await response.json()
    
    async def get_connectors(self) -> List[str]:
        """Get list of connector names."""
        return await self._request("GET", "/connectors")
    
    async def get_connector_info(self, name: str) -> Dict[str, Any]:
        """Get connector information."""
        return await self._request("GET", f"/connectors/{name}")
    
    async def get_connector_status(self, name: str) -> Dict[str, Any]:
        """Get connector status."""
        return await self._request("GET", f"/connectors/{name}/status")
    
    async def create_connector(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new connector."""
        payload = {
            "name": name,
            "config": config
        }
        return await self._request("POST", "/connectors", json=payload)
    
    async def update_connector(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update connector configuration."""
        return await self._request("PUT", f"/connectors/{name}/config", json=config)
    
    async def delete_connector(self, name: str) -> None:
        """Delete a connector."""
        await self._request("DELETE", f"/connectors/{name}")
    
    async def pause_connector(self, name: str) -> None:
        """Pause a connector."""
        await self._request("PUT", f"/connectors/{name}/pause")
    
    async def resume_connector(self, name: str) -> None:
        """Resume a connector."""
        await self._request("PUT", f"/connectors/{name}/resume")
    
    async def restart_connector(self, name: str) -> None:
        """Restart a connector."""
        await self._request("POST", f"/connectors/{name}/restart")


class KafkaConsumer:
    """Simple Kafka consumer for Debezium events."""
    
    def __init__(self, bootstrap_servers: str, topics: List[str], group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.group_id = group_id
        self._consumer = None
        self._running = False
    
    async def start(self) -> None:
        """Start the Kafka consumer."""
        try:
            from aiokafka import AIOKafkaConsumer
            
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None
            )
            
            await self._consumer.start()
            self._running = True
            logger.info(f"Kafka consumer started for topics: {self.topics}")
            
        except ImportError:
            raise ImportError("aiokafka is required for Kafka integration")
    
    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def consume(self) -> AsyncIterator[Dict[str, Any]]:
        """Consume messages from Kafka."""
        if not self._consumer or not self._running:
            return
        
        async for message in self._consumer:
            if not self._running:
                break
            
            yield {
                'topic': message.topic,
                'partition': message.partition,
                'offset': message.offset,
                'key': message.key.decode('utf-8') if message.key else None,
                'value': message.value,
                'timestamp': message.timestamp,
                'headers': dict(message.headers) if message.headers else {}
            }


class DebeziumCDC(BaseCDC):
    """
    Debezium CDC implementation.
    
    Supports both Kafka Connect and embedded modes for capturing
    database changes using Debezium connectors.
    """
    
    def __init__(self, config: DebeziumConfig):
        super().__init__(config)
        self.debezium_config = config
        self._kafka_client: Optional[KafkaConnectClient] = None
        self._kafka_consumer: Optional[KafkaConsumer] = None
        self._connector_name = f"debezium-{config.name}"
        self._topics: List[str] = []
    
    async def connect(self) -> bool:
        """Connect to Debezium infrastructure."""
        try:
            if self.debezium_config.mode == DebeziumMode.KAFKA_CONNECT:
                return await self._connect_kafka_connect()
            else:
                return await self._connect_embedded()
        except Exception as e:
            logger.error(f"Failed to connect to Debezium: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Debezium."""
        if self._kafka_consumer:
            await self._kafka_consumer.stop()
        
        if self._kafka_client:
            await self._kafka_client.__aexit__(None, None, None)
        
        logger.info("Disconnected from Debezium")
    
    async def start_capture(self) -> None:
        """Start capturing changes via Debezium."""
        if self.debezium_config.mode == DebeziumMode.KAFKA_CONNECT:
            await self._start_kafka_connect_capture()
        else:
            await self._start_embedded_capture()
    
    async def stop_capture(self) -> None:
        """Stop capturing changes."""
        self._running = False
        
        if self._kafka_consumer:
            await self._kafka_consumer.stop()
        
        if self._kafka_client and self.debezium_config.mode == DebeziumMode.KAFKA_CONNECT:
            try:
                await self._kafka_client.pause_connector(self._connector_name)
            except Exception as e:
                logger.warning(f"Failed to pause connector: {e}")
    
    async def get_changes(
        self,
        from_position: Optional[CDCPosition] = None
    ) -> AsyncIterator[ChangeEvent]:
        """Get changes from Debezium stream."""
        if not self._kafka_consumer:
            return
        
        async for message in self._kafka_consumer.consume():
            if not self._running:
                break
            
            try:
                change_event = self._parse_debezium_message(message)
                if change_event:
                    yield change_event
            except Exception as e:
                logger.error(f"Failed to parse Debezium message: {e}")
                await self._handle_error(e)
    
    async def _connect_kafka_connect(self) -> bool:
        """Connect to Kafka Connect cluster."""
        self._kafka_client = KafkaConnectClient(self.debezium_config.kafka_connect_url)
        await self._kafka_client.__aenter__()
        
        # Test connection
        try:
            connectors = await self._kafka_client.get_connectors()
            logger.info(f"Connected to Kafka Connect. Existing connectors: {connectors}")
            
            # Setup Kafka consumer for topics
            self._topics = self._get_topic_names()
            self._kafka_consumer = KafkaConsumer(
                bootstrap_servers=self.debezium_config.kafka_bootstrap_servers,
                topics=self._topics,
                group_id=f"debezium-cdc-{self.config.name}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka Connect: {e}")
            return False
    
    async def _connect_embedded(self) -> bool:
        """Connect to embedded Debezium engine."""
        # Embedded mode would require Java integration
        # For now, we'll focus on Kafka Connect mode
        raise NotImplementedError("Embedded Debezium mode not yet implemented")
    
    async def _start_kafka_connect_capture(self) -> None:
        """Start capture using Kafka Connect."""
        # Create or update connector
        connector_config = self._build_connector_config()
        
        try:
            # Check if connector exists
            await self._kafka_client.get_connector_info(self._connector_name)
            # Update existing connector
            await self._kafka_client.update_connector(self._connector_name, connector_config)
            logger.info(f"Updated Debezium connector: {self._connector_name}")
        except:
            # Create new connector
            await self._kafka_client.create_connector(self._connector_name, connector_config)
            logger.info(f"Created Debezium connector: {self._connector_name}")
        
        # Wait for connector to be ready
        await self._wait_for_connector_ready()
        
        # Start Kafka consumer
        await self._kafka_consumer.start()
        
        # Start consuming messages
        self._running = True
        self._stats["started_at"] = datetime.utcnow()
        
        async for message in self._kafka_consumer.consume():
            if not self._running:
                break
            
            try:
                change_event = self._parse_debezium_message(message)
                if change_event:
                    await self.emit_event(change_event)
                    
                    # Update position
                    self._position = CDCPosition(
                        source="debezium",
                        position={
                            "topic": message["topic"],
                            "partition": message["partition"],
                            "offset": message["offset"]
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Failed to process Debezium message: {e}")
                await self._handle_error(e)
    
    async def _start_embedded_capture(self) -> None:
        """Start capture using embedded Debezium engine."""
        raise NotImplementedError("Embedded Debezium mode not yet implemented")
    
    def _build_connector_config(self) -> Dict[str, Any]:
        """Build Debezium connector configuration."""
        config = {
            "connector.class": self.debezium_config.connector_type.value,
            "tasks.max": "1",
            "database.hostname": self.debezium_config.host,
            "database.port": str(self.debezium_config.port),
            "database.user": self.debezium_config.username,
            "database.password": self.debezium_config.password,
            "database.server.name": self.debezium_config.topic_prefix,
            "topic.prefix": self.debezium_config.topic_prefix,
            "snapshot.mode": self.debezium_config.snapshot_mode,
            "snapshot.locking.mode": self.debezium_config.snapshot_locking_mode,
            "max.batch.size": str(self.debezium_config.max_batch_size),
            "max.queue.size": str(self.debezium_config.max_queue_size),
            "poll.interval.ms": str(self.debezium_config.poll_interval_ms),
        }
        
        # Database-specific configuration
        if self.debezium_config.connector_type == DebeziumConnectorType.MYSQL:
            config.update({
                "database.server.id": str(self.debezium_config.server_id or 184054),
                "database.include.list": self.debezium_config.database,
                "binlog.buffer.size": "32768",
            })
        
        elif self.debezium_config.connector_type == DebeziumConnectorType.POSTGRESQL:
            config.update({
                "database.dbname": self.debezium_config.database,
                "slot.name": self.debezium_config.slot_name or f"debezium_{self.config.name}",
                "publication.name": self.debezium_config.publication_name or f"dbz_publication_{self.config.name}",
                "plugin.name": "pgoutput",
            })
        
        # Table filtering
        if self.debezium_config.table_include_list:
            config["table.include.list"] = self.debezium_config.table_include_list
        elif self.config.tables:
            # Convert table list to Debezium format
            if self.debezium_config.connector_type == DebeziumConnectorType.MYSQL:
                table_list = ",".join([f"{self.config.database}.{table}" for table in self.config.tables])
            else:
                table_list = ",".join([f"public.{table}" for table in self.config.tables])
            config["table.include.list"] = table_list
        
        if self.debezium_config.table_exclude_list:
            config["table.exclude.list"] = self.debezium_config.table_exclude_list
        
        # Column filtering
        if self.debezium_config.column_include_list:
            config["column.include.list"] = self.debezium_config.column_include_list
        
        if self.debezium_config.column_exclude_list:
            config["column.exclude.list"] = self.debezium_config.column_exclude_list
        
        # Schema registry
        if self.debezium_config.schema_registry_url:
            config.update({
                "key.converter": "io.confluent.connect.avro.AvroConverter",
                "value.converter": "io.confluent.connect.avro.AvroConverter",
                "key.converter.schema.registry.url": self.debezium_config.schema_registry_url,
                "value.converter.schema.registry.url": self.debezium_config.schema_registry_url,
            })
        else:
            config.update({
                "key.converter": "org.apache.kafka.connect.json.JsonConverter",
                "value.converter": "org.apache.kafka.connect.json.JsonConverter",
                "key.converter.schemas.enable": "false",
                "value.converter.schemas.enable": "false",
            })
        
        return config
    
    def _get_topic_names(self) -> List[str]:
        """Get expected topic names for the connector."""
        topics = []
        
        if self.config.tables:
            for table in self.config.tables:
                topic = f"{self.debezium_config.topic_prefix}.{self.config.database}.{table}"
                topics.append(topic)
        else:
            # Subscribe to all topics with the prefix
            topic_pattern = f"{self.debezium_config.topic_prefix}.*"
            topics.append(topic_pattern)
        
        return topics
    
    async def _wait_for_connector_ready(self, timeout: int = 60) -> None:
        """Wait for connector to be in RUNNING state."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = await self._kafka_client.get_connector_status(self._connector_name)
                
                if status.get("connector", {}).get("state") == "RUNNING":
                    logger.info(f"Connector {self._connector_name} is running")
                    return
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Failed to check connector status: {e}")
                await asyncio.sleep(2)
        
        raise TimeoutError(f"Connector {self._connector_name} did not start within {timeout} seconds")
    
    def _parse_debezium_message(self, message: Dict[str, Any]) -> Optional[ChangeEvent]:
        """Parse Debezium message into ChangeEvent."""
        import uuid
        
        value = message.get("value")
        if not value:
            return None
        
        # Extract operation
        op = value.get("op")
        if not op:
            return None
        
        operation_map = {
            "c": CDCOperation.INSERT,  # create
            "u": CDCOperation.UPDATE,  # update
            "d": CDCOperation.DELETE,  # delete
            "r": CDCOperation.INSERT,  # read (snapshot)
            "t": CDCOperation.TRUNCATE,  # truncate
        }
        
        operation = operation_map.get(op)
        if not operation:
            return None
        
        # Check if we should capture this operation
        if not self._should_capture_operation(operation):
            return None
        
        # Extract table information
        source = value.get("source", {})
        table = source.get("table")
        schema = source.get("schema") or source.get("db")
        
        if not table or not self._should_capture_table(table):
            return None
        
        # Extract data
        before = value.get("before")
        after = value.get("after")
        
        # Extract timestamp
        ts_ms = source.get("ts_ms") or value.get("ts_ms")
        timestamp = datetime.utcfromtimestamp(ts_ms / 1000) if ts_ms else datetime.utcnow()
        
        return ChangeEvent(
            id=f"debezium_{uuid.uuid4().hex[:12]}",
            operation=operation,
            table=table,
            schema=schema,
            database=schema,
            timestamp=timestamp,
            before=before,
            after=after,
            position={
                "topic": message["topic"],
                "partition": message["partition"],
                "offset": message["offset"],
                "lsn": source.get("lsn"),
                "file": source.get("file"),
                "pos": source.get("pos"),
            },
            metadata={
                "connector": source.get("connector"),
                "version": source.get("version"),
                "server_id": source.get("server_id"),
                "gtid": source.get("gtid"),
                "binlog_file": source.get("file"),
                "binlog_pos": source.get("pos"),
                "row": source.get("row"),
                "thread": source.get("thread"),
                "query": source.get("query"),
            }
        )


class DebeziumManager:
    """
    Manager for multiple Debezium CDC instances.
    
    Provides centralized management of Debezium connectors
    and monitoring of their health and performance.
    """
    
    def __init__(self, kafka_connect_url: str):
        self.kafka_connect_url = kafka_connect_url
        self._cdcs: Dict[str, DebeziumCDC] = {}
        self._client: Optional[KafkaConnectClient] = None
    
    async def __aenter__(self):
        self._client = KafkaConnectClient(self.kafka_connect_url)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def register_cdc(self, cdc: DebeziumCDC) -> None:
        """Register a Debezium CDC instance."""
        self._cdcs[cdc.config.name] = cdc
        logger.info(f"Registered Debezium CDC: {cdc.config.name}")
    
    async def start_all(self) -> None:
        """Start all registered CDC instances."""
        for name, cdc in self._cdcs.items():
            try:
                if await cdc.connect():
                    await cdc.start_capture()
                    logger.info(f"Started Debezium CDC: {name}")
                else:
                    logger.error(f"Failed to start Debezium CDC: {name}")
            except Exception as e:
                logger.error(f"Error starting CDC {name}: {e}")
    
    async def stop_all(self) -> None:
        """Stop all CDC instances."""
        for name, cdc in self._cdcs.items():
            try:
                await cdc.stop_capture()
                await cdc.disconnect()
                logger.info(f"Stopped Debezium CDC: {name}")
            except Exception as e:
                logger.error(f"Error stopping CDC {name}: {e}")
    
    async def get_connector_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific connector."""
        if not self._client:
            return None
        
        try:
            connector_name = f"debezium-{name}"
            return await self._client.get_connector_status(connector_name)
        except Exception as e:
            logger.error(f"Failed to get connector status for {name}: {e}")
            return None
    
    async def get_all_connector_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all managed connectors."""
        status = {}
        
        for name in self._cdcs.keys():
            connector_status = await self.get_connector_status(name)
            if connector_status:
                status[name] = connector_status
        
        return status
    
    async def restart_connector(self, name: str) -> bool:
        """Restart a specific connector."""
        if not self._client:
            return False
        
        try:
            connector_name = f"debezium-{name}"
            await self._client.restart_connector(connector_name)
            logger.info(f"Restarted connector: {connector_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart connector {name}: {e}")
            return False
    
    def get_cdc_stats(self) -> Dict[str, Any]:
        """Get statistics for all CDC instances."""
        return {
            name: cdc.stats
            for name, cdc in self._cdcs.items()
        }


def create_debezium_cdc(config: DebeziumConfig) -> DebeziumCDC:
    """Factory function to create Debezium CDC instance."""
    return DebeziumCDC(config)


__all__ = [
    "DebeziumCDC",
    "DebeziumConfig",
    "DebeziumConnectorType",
    "DebeziumMode",
    "DebeziumManager",
    "KafkaConnectClient",
    "KafkaConsumer",
    "create_debezium_cdc",
]