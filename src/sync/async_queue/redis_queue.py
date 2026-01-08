"""
Redis Queue Module.

Provides Redis-based message queue for lightweight async processing,
complementing Celery for simpler use cases and real-time messaging.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
from uuid import uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueueType(str, Enum):
    """Queue types."""
    FIFO = "fifo"          # First In, First Out
    LIFO = "lifo"          # Last In, First Out (stack)
    PRIORITY = "priority"   # Priority-based
    DELAYED = "delayed"     # Delayed execution
    STREAM = "stream"       # Redis Streams


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


@dataclass
class QueueMessage:
    """Represents a queue message."""
    id: str
    queue_name: str
    payload: Dict[str, Any]
    priority: int = 0
    delay_until: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "queue_name": self.queue_name,
            "payload": self.payload,
            "priority": self.priority,
            "delay_until": self.delay_until.isoformat() if self.delay_until else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMessage":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            queue_name=data["queue_name"],
            payload=data["payload"],
            priority=data.get("priority", 0),
            delay_until=datetime.fromisoformat(data["delay_until"]) if data.get("delay_until") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            created_at=datetime.fromisoformat(data["created_at"]),
            status=MessageStatus(data.get("status", "pending")),
            metadata=data.get("metadata", {})
        )


class RedisQueue:
    """
    Redis-based message queue with multiple queue types and features.
    
    Supports FIFO, LIFO, priority, delayed, and stream-based queues
    with retry logic, expiration, and monitoring.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        queue_name: str,
        queue_type: QueueType = QueueType.FIFO,
        default_ttl: int = 3600,
        max_retries: int = 3
    ):
        self.redis = redis_client
        self.queue_name = queue_name
        self.queue_type = queue_type
        self.default_ttl = default_ttl
        self.max_retries = max_retries
        
        # Redis key patterns
        self.queue_key = f"queue:{queue_name}"
        self.processing_key = f"queue:{queue_name}:processing"
        self.failed_key = f"queue:{queue_name}:failed"
        self.delayed_key = f"queue:{queue_name}:delayed"
        self.stats_key = f"queue:{queue_name}:stats"
        
        # For priority queues
        self.priority_key = f"queue:{queue_name}:priority"
        
        # For streams
        self.stream_key = f"stream:{queue_name}"
        self.consumer_group = f"{queue_name}_group"
        
        self._running = False
        self._workers: List[asyncio.Task] = []
    
    async def enqueue(
        self,
        payload: Dict[str, Any],
        priority: int = 0,
        delay: Optional[Union[int, timedelta]] = None,
        expires_in: Optional[Union[int, timedelta]] = None,
        message_id: Optional[str] = None
    ) -> str:
        """
        Enqueue a message.
        
        Args:
            payload: Message payload
            priority: Message priority (higher = more important)
            delay: Delay before processing
            expires_in: Message expiration time
            message_id: Optional custom message ID
            
        Returns:
            Message ID
        """
        msg_id = message_id or str(uuid4())
        
        # Calculate timestamps
        now = datetime.utcnow()
        delay_until = None
        expires_at = None
        
        if delay:
            if isinstance(delay, int):
                delay_until = now + timedelta(seconds=delay)
            else:
                delay_until = now + delay
        
        if expires_in:
            if isinstance(expires_in, int):
                expires_at = now + timedelta(seconds=expires_in)
            else:
                expires_at = now + expires_in
        
        # Create message
        message = QueueMessage(
            id=msg_id,
            queue_name=self.queue_name,
            payload=payload,
            priority=priority,
            delay_until=delay_until,
            expires_at=expires_at,
            max_retries=self.max_retries
        )
        
        # Store message data
        await self.redis.hset(
            f"msg:{msg_id}",
            mapping={
                "data": json.dumps(message.to_dict()),
                "created": int(now.timestamp())
            }
        )
        
        # Set expiration for message data
        if expires_at:
            await self.redis.expireat(f"msg:{msg_id}", int(expires_at.timestamp()))
        else:
            await self.redis.expire(f"msg:{msg_id}", self.default_ttl)
        
        # Add to appropriate queue
        if delay_until:
            # Add to delayed queue
            await self.redis.zadd(
                self.delayed_key,
                {msg_id: int(delay_until.timestamp())}
            )
        elif self.queue_type == QueueType.PRIORITY:
            # Add to priority queue
            await self.redis.zadd(
                self.priority_key,
                {msg_id: priority}
            )
        elif self.queue_type == QueueType.STREAM:
            # Add to stream
            await self.redis.xadd(
                self.stream_key,
                {"msg_id": msg_id, "payload": json.dumps(payload)}
            )
        elif self.queue_type == QueueType.LIFO:
            # Add to front of list (stack)
            await self.redis.lpush(self.queue_key, msg_id)
        else:  # FIFO
            # Add to end of list (queue)
            await self.redis.rpush(self.queue_key, msg_id)
        
        # Update stats
        await self.redis.hincrby(self.stats_key, "enqueued", 1)
        
        logger.debug(f"Enqueued message {msg_id} to queue {self.queue_name}")
        return msg_id
    
    async def dequeue(self, timeout: int = 0) -> Optional[QueueMessage]:
        """
        Dequeue a message.
        
        Args:
            timeout: Blocking timeout in seconds (0 = non-blocking)
            
        Returns:
            Message or None if queue is empty
        """
        # Process delayed messages first
        await self._process_delayed_messages()
        
        msg_id = None
        
        if self.queue_type == QueueType.PRIORITY:
            # Get highest priority message
            result = await self.redis.zpopmax(self.priority_key)
            if result:
                msg_id = result[0][0].decode() if isinstance(result[0][0], bytes) else result[0][0]
        
        elif self.queue_type == QueueType.STREAM:
            # Read from stream
            try:
                # Ensure consumer group exists
                try:
                    await self.redis.xgroup_create(
                        self.stream_key,
                        self.consumer_group,
                        id="0",
                        mkstream=True
                    )
                except redis.ResponseError:
                    pass  # Group already exists
                
                # Read messages
                messages = await self.redis.xreadgroup(
                    self.consumer_group,
                    "consumer",
                    {self.stream_key: ">"},
                    count=1,
                    block=timeout * 1000 if timeout > 0 else None
                )
                
                if messages:
                    stream_name, msgs = messages[0]
                    if msgs:
                        stream_id, fields = msgs[0]
                        msg_id = fields.get(b"msg_id", fields.get("msg_id"))
                        if isinstance(msg_id, bytes):
                            msg_id = msg_id.decode()
                        
                        # Acknowledge message
                        await self.redis.xack(self.stream_key, self.consumer_group, stream_id)
            
            except Exception as e:
                logger.error(f"Stream dequeue error: {e}")
                return None
        
        elif self.queue_type == QueueType.LIFO:
            # Pop from front (stack)
            if timeout > 0:
                result = await self.redis.blpop(self.queue_key, timeout=timeout)
                if result:
                    msg_id = result[1].decode() if isinstance(result[1], bytes) else result[1]
            else:
                result = await self.redis.lpop(self.queue_key)
                if result:
                    msg_id = result.decode() if isinstance(result, bytes) else result
        
        else:  # FIFO
            # Pop from front (queue)
            if timeout > 0:
                result = await self.redis.blpop(self.queue_key, timeout=timeout)
                if result:
                    msg_id = result[1].decode() if isinstance(result[1], bytes) else result[1]
            else:
                result = await self.redis.lpop(self.queue_key)
                if result:
                    msg_id = result.decode() if isinstance(result, bytes) else result
        
        if not msg_id:
            return None
        
        # Get message data
        msg_data = await self.redis.hget(f"msg:{msg_id}", "data")
        if not msg_data:
            logger.warning(f"Message data not found for {msg_id}")
            return None
        
        try:
            message = QueueMessage.from_dict(json.loads(msg_data))
            
            # Check if message has expired
            if message.expires_at and datetime.utcnow() > message.expires_at:
                await self._mark_expired(message)
                return None
            
            # Move to processing
            message.status = MessageStatus.PROCESSING
            await self.redis.hset(f"msg:{msg_id}", "data", json.dumps(message.to_dict()))
            await self.redis.sadd(self.processing_key, msg_id)
            
            # Update stats
            await self.redis.hincrby(self.stats_key, "dequeued", 1)
            
            return message
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message {msg_id}: {e}")
            return None
    
    async def ack(self, message_id: str) -> bool:
        """Acknowledge successful message processing."""
        try:
            # Remove from processing
            await self.redis.srem(self.processing_key, message_id)
            
            # Update message status
            msg_data = await self.redis.hget(f"msg:{message_id}", "data")
            if msg_data:
                message = QueueMessage.from_dict(json.loads(msg_data))
                message.status = MessageStatus.COMPLETED
                await self.redis.hset(f"msg:{message_id}", "data", json.dumps(message.to_dict()))
            
            # Update stats
            await self.redis.hincrby(self.stats_key, "completed", 1)
            
            logger.debug(f"Acknowledged message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False
    
    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """Negative acknowledge - message processing failed."""
        try:
            # Remove from processing
            await self.redis.srem(self.processing_key, message_id)
            
            # Get message data
            msg_data = await self.redis.hget(f"msg:{message_id}", "data")
            if not msg_data:
                return False
            
            message = QueueMessage.from_dict(json.loads(msg_data))
            message.retry_count += 1
            
            if requeue and message.retry_count <= message.max_retries:
                # Requeue for retry
                message.status = MessageStatus.RETRYING
                await self.redis.hset(f"msg:{message_id}", "data", json.dumps(message.to_dict()))
                
                # Add back to queue with exponential backoff delay
                delay = min(60 * (2 ** message.retry_count), 3600)  # Max 1 hour
                delay_until = datetime.utcnow() + timedelta(seconds=delay)
                
                await self.redis.zadd(
                    self.delayed_key,
                    {message_id: int(delay_until.timestamp())}
                )
                
                await self.redis.hincrby(self.stats_key, "retried", 1)
                logger.info(f"Requeued message {message_id} for retry {message.retry_count}")
            else:
                # Move to failed queue
                message.status = MessageStatus.FAILED
                await self.redis.hset(f"msg:{message_id}", "data", json.dumps(message.to_dict()))
                await self.redis.sadd(self.failed_key, message_id)
                
                await self.redis.hincrby(self.stats_key, "failed", 1)
                logger.warning(f"Message {message_id} failed after {message.retry_count} retries")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to nack message {message_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = await self.redis.hgetall(self.stats_key)
        
        # Convert bytes to int
        for key, value in stats.items():
            if isinstance(key, bytes):
                key = key.decode()
            if isinstance(value, bytes):
                stats[key] = int(value.decode())
        
        # Add current queue sizes
        queue_size = 0
        if self.queue_type == QueueType.PRIORITY:
            queue_size = await self.redis.zcard(self.priority_key)
        elif self.queue_type == QueueType.STREAM:
            info = await self.redis.xinfo_stream(self.stream_key)
            queue_size = info.get("length", 0)
        else:
            queue_size = await self.redis.llen(self.queue_key)
        
        stats.update({
            "queue_size": queue_size,
            "processing_size": await self.redis.scard(self.processing_key),
            "failed_size": await self.redis.scard(self.failed_key),
            "delayed_size": await self.redis.zcard(self.delayed_key),
        })
        
        return stats
    
    async def purge(self) -> int:
        """Purge all messages from queue."""
        count = 0
        
        # Get all message IDs
        if self.queue_type == QueueType.PRIORITY:
            msg_ids = await self.redis.zrange(self.priority_key, 0, -1)
            count = await self.redis.zcard(self.priority_key)
            await self.redis.delete(self.priority_key)
        elif self.queue_type == QueueType.STREAM:
            await self.redis.delete(self.stream_key)
            count = 1  # Approximate
        else:
            msg_ids = await self.redis.lrange(self.queue_key, 0, -1)
            count = await self.redis.llen(self.queue_key)
            await self.redis.delete(self.queue_key)
        
        # Clean up message data
        if self.queue_type != QueueType.STREAM:
            for msg_id in msg_ids:
                if isinstance(msg_id, bytes):
                    msg_id = msg_id.decode()
                await self.redis.delete(f"msg:{msg_id}")
        
        # Clean up other keys
        await self.redis.delete(self.processing_key, self.failed_key, self.delayed_key)
        
        logger.info(f"Purged {count} messages from queue {self.queue_name}")
        return count
    
    async def _process_delayed_messages(self) -> None:
        """Move delayed messages to main queue when ready."""
        now = int(datetime.utcnow().timestamp())
        
        # Get messages ready for processing
        ready_messages = await self.redis.zrangebyscore(
            self.delayed_key,
            0,
            now,
            withscores=False
        )
        
        if ready_messages:
            # Move to main queue
            for msg_id in ready_messages:
                if isinstance(msg_id, bytes):
                    msg_id = msg_id.decode()
                
                # Remove from delayed queue
                await self.redis.zrem(self.delayed_key, msg_id)
                
                # Add to main queue
                if self.queue_type == QueueType.PRIORITY:
                    # Get message to check priority
                    msg_data = await self.redis.hget(f"msg:{msg_id}", "data")
                    if msg_data:
                        message = QueueMessage.from_dict(json.loads(msg_data))
                        await self.redis.zadd(self.priority_key, {msg_id: message.priority})
                elif self.queue_type == QueueType.LIFO:
                    await self.redis.lpush(self.queue_key, msg_id)
                else:  # FIFO
                    await self.redis.rpush(self.queue_key, msg_id)
    
    async def _mark_expired(self, message: QueueMessage) -> None:
        """Mark message as expired."""
        message.status = MessageStatus.EXPIRED
        await self.redis.hset(f"msg:{message.id}", "data", json.dumps(message.to_dict()))
        await self.redis.hincrby(self.stats_key, "expired", 1)
        logger.debug(f"Message {message.id} expired")


class RedisQueueManager:
    """
    Manager for multiple Redis queues.
    
    Provides centralized management and monitoring of Redis-based queues.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._queues: Dict[str, RedisQueue] = {}
        self._workers: Dict[str, List[asyncio.Task]] = {}
    
    def create_queue(
        self,
        name: str,
        queue_type: QueueType = QueueType.FIFO,
        **kwargs
    ) -> RedisQueue:
        """Create a new queue."""
        queue = RedisQueue(
            redis_client=self.redis,
            queue_name=name,
            queue_type=queue_type,
            **kwargs
        )
        self._queues[name] = queue
        return queue
    
    def get_queue(self, name: str) -> Optional[RedisQueue]:
        """Get existing queue."""
        return self._queues.get(name)
    
    async def start_worker(
        self,
        queue_name: str,
        handler: Callable[[QueueMessage], Any],
        worker_count: int = 1
    ) -> None:
        """Start workers for a queue."""
        queue = self._queues.get(queue_name)
        if not queue:
            raise ValueError(f"Queue {queue_name} not found")
        
        workers = []
        for i in range(worker_count):
            worker = asyncio.create_task(
                self._worker_loop(queue, handler, f"worker-{i}")
            )
            workers.append(worker)
        
        self._workers[queue_name] = workers
        logger.info(f"Started {worker_count} workers for queue {queue_name}")
    
    async def stop_workers(self, queue_name: str) -> None:
        """Stop workers for a queue."""
        workers = self._workers.get(queue_name, [])
        
        for worker in workers:
            worker.cancel()
        
        # Wait for workers to finish
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        
        self._workers.pop(queue_name, None)
        logger.info(f"Stopped workers for queue {queue_name}")
    
    async def stop_all_workers(self) -> None:
        """Stop all workers."""
        for queue_name in list(self._workers.keys()):
            await self.stop_workers(queue_name)
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all queues."""
        stats = {}
        
        for name, queue in self._queues.items():
            stats[name] = await queue.get_stats()
        
        return stats
    
    async def _worker_loop(
        self,
        queue: RedisQueue,
        handler: Callable[[QueueMessage], Any],
        worker_name: str
    ) -> None:
        """Worker loop for processing messages."""
        logger.info(f"Worker {worker_name} started for queue {queue.queue_name}")
        
        while True:
            try:
                # Dequeue message
                message = await queue.dequeue(timeout=5)
                
                if message:
                    try:
                        # Process message
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                        
                        # Acknowledge success
                        await queue.ack(message.id)
                        
                    except Exception as e:
                        logger.error(f"Worker {worker_name} failed to process message {message.id}: {e}")
                        await queue.nack(message.id)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)


def create_redis_queue(
    redis_url: str = "redis://localhost:6379/0",
    queue_name: str = "default",
    queue_type: QueueType = QueueType.FIFO,
    **kwargs
) -> RedisQueue:
    """Factory function to create Redis queue."""
    redis_client = redis.from_url(redis_url)
    return RedisQueue(
        redis_client=redis_client,
        queue_name=queue_name,
        queue_type=queue_type,
        **kwargs
    )


__all__ = [
    "RedisQueue",
    "RedisQueueManager",
    "QueueMessage",
    "QueueType",
    "MessageStatus",
    "create_redis_queue",
]