"""
Stream Data Extractor for SuperInsight Platform.

Provides extraction from streaming data sources:
- Kafka consumer
- RabbitMQ consumer
- Redis Streams
- WebSocket streams
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from src.extractors.base import BaseExtractor, ExtractionResult
from src.models.document import Document

logger = logging.getLogger(__name__)


class StreamType(str, Enum):
    """Supported stream types."""
    KAFKA = "kafka"
    RABBITMQ = "rabbitmq"
    REDIS_STREAM = "redis_stream"
    WEBSOCKET = "websocket"


@dataclass
class StreamConfig:
    """Base stream configuration."""
    stream_type: StreamType
    name: str
    
    # Connection settings
    hosts: List[str] = field(default_factory=lambda: ["localhost"])
    port: int = 9092
    
    # Authentication
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Consumer settings
    group_id: Optional[str] = None
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    
    # Processing settings
    batch_size: int = 100
    poll_timeout_ms: int = 1000
    max_poll_records: int = 500
    
    # SSL settings
    use_ssl: bool = False
    ssl_cert_path: Optional[str] = None


@dataclass
class KafkaConfig(StreamConfig):
    """Kafka-specific configuration."""
    topics: List[str] = field(default_factory=list)
    consumer_timeout_ms: int = 10000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    
    def __post_init__(self):
        self.stream_type = StreamType.KAFKA
        if not self.port:
            self.port = 9092


@dataclass
class RabbitMQConfig(StreamConfig):
    """RabbitMQ-specific configuration."""
    queues: List[str] = field(default_factory=list)
    exchange: str = ""
    routing_key: str = "#"
    prefetch_count: int = 10
    virtual_host: str = "/"
    
    def __post_init__(self):
        self.stream_type = StreamType.RABBITMQ
        if not self.port:
            self.port = 5672


@dataclass
class RedisStreamConfig(StreamConfig):
    """Redis Stream-specific configuration."""
    streams: List[str] = field(default_factory=list)
    consumer_name: str = "superinsight-consumer"
    block_ms: int = 5000
    count: int = 100
    
    def __post_init__(self):
        self.stream_type = StreamType.REDIS_STREAM
        if not self.port:
            self.port = 6379


@dataclass
class StreamMessage:
    """A message from a stream."""
    id: str
    topic: str
    partition: Optional[int] = None
    offset: Optional[int] = None
    key: Optional[str] = None
    value: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStreamExtractor(ABC):
    """Abstract base class for stream extractors."""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._running = False
        self._handlers: List[Callable[[StreamMessage], None]] = []
        self._stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "bytes_received": 0
        }
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the stream."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the stream."""
        pass
    
    @abstractmethod
    async def consume(self) -> AsyncIterator[StreamMessage]:
        """Consume messages from the stream."""
        pass
    
    @abstractmethod
    async def commit(self, message: StreamMessage) -> None:
        """Commit message offset."""
        pass
    
    def on_message(self, handler: Callable[[StreamMessage], None]) -> None:
        """Register a message handler."""
        self._handlers.append(handler)
    
    async def start_consuming(self) -> None:
        """Start consuming messages."""
        self._running = True
        
        async for message in self.consume():
            if not self._running:
                break
            
            self._stats["messages_received"] += 1
            
            for handler in self._handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                    self._stats["messages_processed"] += 1
                except Exception as e:
                    self._stats["messages_failed"] += 1
                    logger.error(f"Message handler error: {e}")
    
    async def stop_consuming(self) -> None:
        """Stop consuming messages."""
        self._running = False
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        return {
            **self._stats,
            "running": self._running
        }


class KafkaExtractor(BaseStreamExtractor):
    """
    Kafka stream extractor.
    
    Features:
    - Multi-topic consumption
    - Consumer group support
    - Offset management
    - Batch processing
    """
    
    def __init__(self, config: KafkaConfig):
        super().__init__(config)
        self.kafka_config = config
        self._consumer = None
    
    async def connect(self) -> bool:
        """Connect to Kafka."""
        try:
            from aiokafka import AIOKafkaConsumer
            
            bootstrap_servers = [
                f"{host}:{self.kafka_config.port}"
                for host in self.kafka_config.hosts
            ]
            
            self._consumer = AIOKafkaConsumer(
                *self.kafka_config.topics,
                bootstrap_servers=bootstrap_servers,
                group_id=self.kafka_config.group_id,
                auto_offset_reset=self.kafka_config.auto_offset_reset,
                enable_auto_commit=self.kafka_config.enable_auto_commit,
                consumer_timeout_ms=self.kafka_config.consumer_timeout_ms,
                session_timeout_ms=self.kafka_config.session_timeout_ms,
                heartbeat_interval_ms=self.kafka_config.heartbeat_interval_ms,
                max_poll_records=self.kafka_config.max_poll_records
            )
            
            await self._consumer.start()
            logger.info(f"Connected to Kafka: {bootstrap_servers}")
            return True
            
        except ImportError:
            logger.error("aiokafka is required. Install with: pip install aiokafka")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka."""
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        logger.info("Disconnected from Kafka")
    
    async def consume(self) -> AsyncIterator[StreamMessage]:
        """Consume messages from Kafka."""
        if not self._consumer:
            raise RuntimeError("Not connected to Kafka")
        
        async for msg in self._consumer:
            yield StreamMessage(
                id=f"{msg.topic}:{msg.partition}:{msg.offset}",
                topic=msg.topic,
                partition=msg.partition,
                offset=msg.offset,
                key=msg.key.decode() if msg.key else None,
                value=msg.value.decode() if msg.value else None,
                headers={k: v.decode() for k, v in (msg.headers or [])},
                timestamp=datetime.fromtimestamp(msg.timestamp / 1000),
                metadata={
                    "serialized_key_size": msg.serialized_key_size,
                    "serialized_value_size": msg.serialized_value_size
                }
            )
    
    async def commit(self, message: StreamMessage) -> None:
        """Commit message offset."""
        if self._consumer and not self.kafka_config.enable_auto_commit:
            await self._consumer.commit()
    
    async def seek_to_beginning(self, topic: str = None) -> None:
        """Seek to beginning of topic(s)."""
        if self._consumer:
            await self._consumer.seek_to_beginning()
    
    async def seek_to_end(self, topic: str = None) -> None:
        """Seek to end of topic(s)."""
        if self._consumer:
            await self._consumer.seek_to_end()


class RabbitMQExtractor(BaseStreamExtractor):
    """
    RabbitMQ stream extractor.
    
    Features:
    - Queue consumption
    - Exchange binding
    - Message acknowledgment
    - Prefetch control
    """
    
    def __init__(self, config: RabbitMQConfig):
        super().__init__(config)
        self.rabbitmq_config = config
        self._connection = None
        self._channel = None
    
    async def connect(self) -> bool:
        """Connect to RabbitMQ."""
        try:
            import aio_pika
            
            url = f"amqp://{self.rabbitmq_config.username or 'guest'}:{self.rabbitmq_config.password or 'guest'}@{self.rabbitmq_config.hosts[0]}:{self.rabbitmq_config.port}/{self.rabbitmq_config.virtual_host}"
            
            self._connection = await aio_pika.connect_robust(url)
            self._channel = await self._connection.channel()
            
            await self._channel.set_qos(prefetch_count=self.rabbitmq_config.prefetch_count)
            
            logger.info(f"Connected to RabbitMQ: {self.rabbitmq_config.hosts[0]}")
            return True
            
        except ImportError:
            logger.error("aio-pika is required. Install with: pip install aio-pika")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
        logger.info("Disconnected from RabbitMQ")
    
    async def consume(self) -> AsyncIterator[StreamMessage]:
        """Consume messages from RabbitMQ."""
        if not self._channel:
            raise RuntimeError("Not connected to RabbitMQ")
        
        for queue_name in self.rabbitmq_config.queues:
            queue = await self._channel.declare_queue(queue_name, durable=True)
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    yield StreamMessage(
                        id=message.message_id or str(message.delivery_tag),
                        topic=queue_name,
                        key=message.routing_key,
                        value=message.body.decode(),
                        headers=dict(message.headers) if message.headers else {},
                        timestamp=message.timestamp or datetime.utcnow(),
                        metadata={
                            "delivery_tag": message.delivery_tag,
                            "redelivered": message.redelivered,
                            "exchange": message.exchange
                        }
                    )
    
    async def commit(self, message: StreamMessage) -> None:
        """Acknowledge message."""
        # In RabbitMQ, acknowledgment is typically done via the message object
        pass


class RedisStreamExtractor(BaseStreamExtractor):
    """
    Redis Streams extractor.
    
    Features:
    - Consumer group support
    - Stream reading with blocking
    - Message acknowledgment
    - Pending message handling
    """
    
    def __init__(self, config: RedisStreamConfig):
        super().__init__(config)
        self.redis_config = config
        self._redis = None
    
    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            import redis.asyncio as redis
            
            self._redis = redis.Redis(
                host=self.redis_config.hosts[0],
                port=self.redis_config.port,
                password=self.redis_config.password,
                decode_responses=True
            )
            
            # Test connection
            await self._redis.ping()
            
            # Create consumer group if needed
            for stream in self.redis_config.streams:
                try:
                    await self._redis.xgroup_create(
                        stream,
                        self.redis_config.group_id or "superinsight-group",
                        id="0",
                        mkstream=True
                    )
                except redis.ResponseError as e:
                    if "BUSYGROUP" not in str(e):
                        raise
            
            logger.info(f"Connected to Redis: {self.redis_config.hosts[0]}")
            return True
            
        except ImportError:
            logger.error("redis is required. Install with: pip install redis")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        logger.info("Disconnected from Redis")
    
    async def consume(self) -> AsyncIterator[StreamMessage]:
        """Consume messages from Redis Streams."""
        if not self._redis:
            raise RuntimeError("Not connected to Redis")
        
        group_id = self.redis_config.group_id or "superinsight-group"
        consumer_name = self.redis_config.consumer_name
        
        streams = {stream: ">" for stream in self.redis_config.streams}
        
        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    groupname=group_id,
                    consumername=consumer_name,
                    streams=streams,
                    count=self.redis_config.count,
                    block=self.redis_config.block_ms
                )
                
                if not messages:
                    continue
                
                for stream_name, stream_messages in messages:
                    for msg_id, msg_data in stream_messages:
                        yield StreamMessage(
                            id=msg_id,
                            topic=stream_name,
                            value=msg_data,
                            timestamp=datetime.utcnow(),
                            metadata={
                                "group_id": group_id,
                                "consumer": consumer_name
                            }
                        )
                        
            except Exception as e:
                logger.error(f"Redis stream read error: {e}")
                await asyncio.sleep(1)
    
    async def commit(self, message: StreamMessage) -> None:
        """Acknowledge message in Redis Stream."""
        if self._redis:
            group_id = self.redis_config.group_id or "superinsight-group"
            await self._redis.xack(message.topic, group_id, message.id)


class StreamExtractorFactory:
    """Factory for creating stream extractors."""
    
    @staticmethod
    def create(config: StreamConfig) -> BaseStreamExtractor:
        """Create appropriate stream extractor."""
        if config.stream_type == StreamType.KAFKA:
            return KafkaExtractor(config)
        elif config.stream_type == StreamType.RABBITMQ:
            return RabbitMQExtractor(config)
        elif config.stream_type == StreamType.REDIS_STREAM:
            return RedisStreamExtractor(config)
        else:
            raise ValueError(f"Unsupported stream type: {config.stream_type}")


__all__ = [
    "StreamType",
    "StreamConfig",
    "KafkaConfig",
    "RabbitMQConfig",
    "RedisStreamConfig",
    "StreamMessage",
    "BaseStreamExtractor",
    "KafkaExtractor",
    "RabbitMQExtractor",
    "RedisStreamExtractor",
    "StreamExtractorFactory",
]
