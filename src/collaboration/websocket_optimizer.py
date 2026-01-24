"""
本体专家协作 WebSocket 广播优化模块

提供 WebSocket 广播优化支持：
- Redis pub/sub 多实例广播
- 消息批处理
- 消息压缩
- 消息节流

Validates: Task 28.4 - Optimize WebSocket broadcasting
"""

import logging
import asyncio
import json
import zlib
import time
from typing import Dict, Any, List, Optional, Set, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessagePriority(str, Enum):
    """消息优先级"""
    HIGH = "high"      # 立即发送
    NORMAL = "normal"  # 正常批处理
    LOW = "low"        # 可延迟发送


class MessageType(str, Enum):
    """消息类型"""
    ELEMENT_LOCKED = "element_locked"
    ELEMENT_UNLOCKED = "element_unlocked"
    ELEMENT_EDITED = "element_edited"
    PRESENCE_UPDATE = "presence_update"
    CONFLICT_DETECTED = "conflict_detected"
    VERSION_CREATED = "version_created"
    APPROVAL_UPDATE = "approval_update"
    COMMENT_ADDED = "comment_added"


@dataclass
class BroadcastMessage:
    """广播消息"""
    message_type: MessageType
    session_id: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    compressed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.message_type.value,
            "session_id": self.session_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_json(self, compress: bool = False) -> bytes:
        """转换为 JSON 字节"""
        data = json.dumps(self.to_dict()).encode('utf-8')
        
        if compress and len(data) > 1024:  # 只压缩大于 1KB 的消息
            compressed = zlib.compress(data)
            if len(compressed) < len(data):
                self.compressed = True
                return compressed
        
        return data
    
    @classmethod
    def from_json(cls, data: bytes, compressed: bool = False) -> "BroadcastMessage":
        """从 JSON 字节创建"""
        if compressed:
            data = zlib.decompress(data)
        
        obj = json.loads(data.decode('utf-8'))
        return cls(
            message_type=MessageType(obj["type"]),
            session_id=obj["session_id"],
            payload=obj["payload"],
            timestamp=datetime.fromisoformat(obj["timestamp"]),
        )


@dataclass
class BroadcastStats:
    """广播统计"""
    total_messages: int = 0
    batched_messages: int = 0
    compressed_messages: int = 0
    throttled_messages: int = 0
    failed_messages: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    bytes_sent: int = 0
    bytes_saved_compression: int = 0


class MessageBatcher:
    """
    消息批处理器
    
    将多个消息合并为单个批次发送，减少网络开销
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        batch_interval_ms: int = 100,
    ):
        """
        初始化批处理器
        
        Args:
            batch_size: 批次大小
            batch_interval_ms: 批处理间隔（毫秒）
        """
        self._batch_size = batch_size
        self._batch_interval_ms = batch_interval_ms
        self._batches: Dict[str, List[BroadcastMessage]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"MessageBatcher initialized "
            f"(batch_size={batch_size}, interval={batch_interval_ms}ms)"
        )
    
    async def start(self) -> None:
        """启动批处理器"""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("MessageBatcher started")
    
    async def stop(self) -> None:
        """停止批处理器"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # 刷新剩余消息
        await self._flush_all()
        logger.info("MessageBatcher stopped")
    
    async def add_message(
        self,
        message: BroadcastMessage,
        flush_callback: Callable[[str, List[BroadcastMessage]], Awaitable[None]],
    ) -> None:
        """
        添加消息到批次
        
        Args:
            message: 消息
            flush_callback: 刷新回调
        """
        async with self._lock:
            self._batches[message.session_id].append(message)
            
            # 高优先级消息立即发送
            if message.priority == MessagePriority.HIGH:
                batch = self._batches.pop(message.session_id, [])
                if batch:
                    await flush_callback(message.session_id, batch)
            
            # 批次满时发送
            elif len(self._batches[message.session_id]) >= self._batch_size:
                batch = self._batches.pop(message.session_id, [])
                if batch:
                    await flush_callback(message.session_id, batch)
    
    async def _flush_loop(self) -> None:
        """定时刷新循环"""
        while self._running:
            await asyncio.sleep(self._batch_interval_ms / 1000.0)
            # 注意：实际刷新需要回调，这里只是示例
    
    async def _flush_all(self) -> None:
        """刷新所有批次"""
        async with self._lock:
            self._batches.clear()


class MessageThrottler:
    """
    消息节流器
    
    限制特定类型消息的发送频率，防止消息洪泛
    """
    
    def __init__(
        self,
        default_interval_ms: int = 100,
        type_intervals: Optional[Dict[MessageType, int]] = None,
    ):
        """
        初始化节流器
        
        Args:
            default_interval_ms: 默认节流间隔（毫秒）
            type_intervals: 按类型的节流间隔
        """
        self._default_interval_ms = default_interval_ms
        self._type_intervals = type_intervals or {
            MessageType.PRESENCE_UPDATE: 1000,  # 存在更新每秒最多1次
            MessageType.ELEMENT_EDITED: 200,    # 编辑更新每200ms最多1次
        }
        
        # 最后发送时间: {(session_id, message_type): timestamp}
        self._last_sent: Dict[tuple, float] = {}
        self._lock = asyncio.Lock()
        
        logger.info(f"MessageThrottler initialized (default={default_interval_ms}ms)")
    
    async def should_send(
        self,
        session_id: str,
        message_type: MessageType,
    ) -> bool:
        """
        检查是否应该发送消息
        
        Args:
            session_id: 会话 ID
            message_type: 消息类型
            
        Returns:
            是否应该发送
        """
        key = (session_id, message_type)
        interval_ms = self._type_intervals.get(
            message_type, self._default_interval_ms
        )
        
        current_time = time.time() * 1000  # 转换为毫秒
        
        async with self._lock:
            last_time = self._last_sent.get(key, 0)
            
            if current_time - last_time >= interval_ms:
                self._last_sent[key] = current_time
                return True
            
            return False
    
    async def clear(self, session_id: Optional[str] = None) -> None:
        """清除节流状态"""
        async with self._lock:
            if session_id:
                keys_to_delete = [
                    k for k in self._last_sent.keys()
                    if k[0] == session_id
                ]
                for key in keys_to_delete:
                    del self._last_sent[key]
            else:
                self._last_sent.clear()


class RedisPubSubBroadcaster:
    """
    Redis Pub/Sub 广播器
    
    使用 Redis Pub/Sub 实现多实例广播
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        channel_prefix: str = "ontology_collab:",
    ):
        """
        初始化 Redis 广播器
        
        Args:
            redis_url: Redis 连接 URL
            channel_prefix: 频道前缀
        """
        self._redis_url = redis_url
        self._channel_prefix = channel_prefix
        self._redis = None
        self._pubsub = None
        self._subscriptions: Dict[str, Set[Callable]] = defaultdict(set)
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        
        logger.info(f"RedisPubSubBroadcaster initialized (prefix={channel_prefix})")
    
    async def connect(self) -> bool:
        """连接 Redis"""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self._redis_url)
            self._pubsub = self._redis.pubsub()
            logger.info("Connected to Redis for pub/sub")
            return True
        except ImportError:
            logger.warning("redis package not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开 Redis 连接"""
        self._running = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        logger.info("Disconnected from Redis")
    
    def _make_channel(self, session_id: str) -> str:
        """生成频道名"""
        return f"{self._channel_prefix}session:{session_id}"
    
    async def publish(
        self,
        session_id: str,
        message: BroadcastMessage,
        compress: bool = True,
    ) -> bool:
        """
        发布消息
        
        Args:
            session_id: 会话 ID
            message: 消息
            compress: 是否压缩
            
        Returns:
            是否成功
        """
        if not self._redis:
            return False
        
        channel = self._make_channel(session_id)
        data = message.to_json(compress=compress)
        
        try:
            await self._redis.publish(channel, data)
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    async def subscribe(
        self,
        session_id: str,
        callback: Callable[[BroadcastMessage], Awaitable[None]],
    ) -> bool:
        """
        订阅会话消息
        
        Args:
            session_id: 会话 ID
            callback: 消息回调
            
        Returns:
            是否成功
        """
        if not self._pubsub:
            return False
        
        channel = self._make_channel(session_id)
        
        try:
            await self._pubsub.subscribe(channel)
            self._subscriptions[channel].add(callback)
            
            # 启动监听任务
            if not self._running:
                self._running = True
                self._listen_task = asyncio.create_task(self._listen_loop())
            
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            return False
    
    async def unsubscribe(
        self,
        session_id: str,
        callback: Optional[Callable] = None,
    ) -> bool:
        """
        取消订阅
        
        Args:
            session_id: 会话 ID
            callback: 特定回调（None 表示全部）
            
        Returns:
            是否成功
        """
        if not self._pubsub:
            return False
        
        channel = self._make_channel(session_id)
        
        try:
            if callback:
                self._subscriptions[channel].discard(callback)
            else:
                self._subscriptions[channel].clear()
            
            if not self._subscriptions[channel]:
                await self._pubsub.unsubscribe(channel)
                del self._subscriptions[channel]
            
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False
    
    async def _listen_loop(self) -> None:
        """监听消息循环"""
        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                
                if message and message["type"] == "message":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode('utf-8')
                    
                    data = message["data"]
                    
                    # 尝试解压
                    try:
                        broadcast_msg = BroadcastMessage.from_json(data, compressed=True)
                    except Exception:
                        broadcast_msg = BroadcastMessage.from_json(data, compressed=False)
                    
                    # 调用回调
                    callbacks = self._subscriptions.get(channel, set())
                    for callback in callbacks:
                        try:
                            await callback(broadcast_msg)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
                await asyncio.sleep(1)


class WebSocketBroadcastOptimizer:
    """
    WebSocket 广播优化器
    
    整合批处理、节流、压缩和 Redis pub/sub
    """
    
    def __init__(
        self,
        use_redis: bool = False,
        redis_url: str = "redis://localhost:6379",
        batch_size: int = 10,
        batch_interval_ms: int = 100,
        enable_compression: bool = True,
        enable_throttling: bool = True,
    ):
        """
        初始化广播优化器
        
        Args:
            use_redis: 是否使用 Redis
            redis_url: Redis 连接 URL
            batch_size: 批次大小
            batch_interval_ms: 批处理间隔
            enable_compression: 是否启用压缩
            enable_throttling: 是否启用节流
        """
        self._use_redis = use_redis
        self._enable_compression = enable_compression
        self._enable_throttling = enable_throttling
        
        # 组件
        self._batcher = MessageBatcher(batch_size, batch_interval_ms)
        self._throttler = MessageThrottler() if enable_throttling else None
        self._redis_broadcaster = (
            RedisPubSubBroadcaster(redis_url) if use_redis else None
        )
        
        # 本地连接
        self._local_connections: Dict[str, Set[Any]] = defaultdict(set)
        self._lock = asyncio.Lock()
        
        # 统计
        self._stats = BroadcastStats()
        
        logger.info(
            f"WebSocketBroadcastOptimizer initialized "
            f"(redis={use_redis}, compression={enable_compression}, "
            f"throttling={enable_throttling})"
        )
    
    async def start(self) -> None:
        """启动优化器"""
        await self._batcher.start()
        
        if self._redis_broadcaster:
            await self._redis_broadcaster.connect()
        
        logger.info("WebSocketBroadcastOptimizer started")
    
    async def stop(self) -> None:
        """停止优化器"""
        await self._batcher.stop()
        
        if self._redis_broadcaster:
            await self._redis_broadcaster.disconnect()
        
        logger.info("WebSocketBroadcastOptimizer stopped")
    
    async def register_connection(
        self,
        session_id: str,
        websocket: Any,
    ) -> None:
        """注册 WebSocket 连接"""
        async with self._lock:
            self._local_connections[session_id].add(websocket)
        
        # 订阅 Redis 频道
        if self._redis_broadcaster:
            await self._redis_broadcaster.subscribe(
                session_id,
                lambda msg: self._handle_redis_message(session_id, msg),
            )
    
    async def unregister_connection(
        self,
        session_id: str,
        websocket: Any,
    ) -> None:
        """注销 WebSocket 连接"""
        async with self._lock:
            self._local_connections[session_id].discard(websocket)
            
            if not self._local_connections[session_id]:
                del self._local_connections[session_id]
                
                # 取消 Redis 订阅
                if self._redis_broadcaster:
                    await self._redis_broadcaster.unsubscribe(session_id)
    
    async def broadcast(
        self,
        message: BroadcastMessage,
    ) -> bool:
        """
        广播消息
        
        Args:
            message: 消息
            
        Returns:
            是否成功
        """
        start_time = time.time()
        
        # 节流检查
        if self._throttler:
            should_send = await self._throttler.should_send(
                message.session_id,
                message.message_type,
            )
            if not should_send:
                self._stats.throttled_messages += 1
                return False
        
        # 添加到批处理
        await self._batcher.add_message(
            message,
            self._flush_batch,
        )
        
        self._stats.total_messages += 1
        
        # 记录延迟
        latency_ms = (time.time() - start_time) * 1000
        self._update_latency_stats(latency_ms)
        
        return True
    
    async def _flush_batch(
        self,
        session_id: str,
        messages: List[BroadcastMessage],
    ) -> None:
        """刷新批次"""
        if not messages:
            return
        
        self._stats.batched_messages += len(messages)
        
        # 合并消息
        batch_data = {
            "type": "batch",
            "messages": [msg.to_dict() for msg in messages],
            "count": len(messages),
        }
        
        # 压缩
        json_data = json.dumps(batch_data).encode('utf-8')
        original_size = len(json_data)
        
        if self._enable_compression and original_size > 1024:
            compressed = zlib.compress(json_data)
            if len(compressed) < original_size:
                json_data = compressed
                self._stats.compressed_messages += len(messages)
                self._stats.bytes_saved_compression += original_size - len(compressed)
        
        self._stats.bytes_sent += len(json_data)
        
        # 发送到本地连接
        async with self._lock:
            connections = self._local_connections.get(session_id, set()).copy()
        
        for ws in connections:
            try:
                await ws.send_bytes(json_data)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                self._stats.failed_messages += 1
        
        # 发布到 Redis
        if self._redis_broadcaster:
            for msg in messages:
                await self._redis_broadcaster.publish(
                    session_id,
                    msg,
                    compress=self._enable_compression,
                )
    
    async def _handle_redis_message(
        self,
        session_id: str,
        message: BroadcastMessage,
    ) -> None:
        """处理 Redis 消息"""
        # 发送到本地连接
        async with self._lock:
            connections = self._local_connections.get(session_id, set()).copy()
        
        json_data = message.to_json(compress=self._enable_compression)
        
        for ws in connections:
            try:
                await ws.send_bytes(json_data)
            except Exception as e:
                logger.error(f"Failed to send Redis message: {e}")
    
    def _update_latency_stats(self, latency_ms: float) -> None:
        """更新延迟统计"""
        n = self._stats.total_messages
        old_avg = self._stats.avg_latency_ms
        self._stats.avg_latency_ms = (old_avg * (n - 1) + latency_ms) / n
        
        if latency_ms > self._stats.max_latency_ms:
            self._stats.max_latency_ms = latency_ms
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "total_messages": self._stats.total_messages,
            "batched_messages": self._stats.batched_messages,
            "compressed_messages": self._stats.compressed_messages,
            "throttled_messages": self._stats.throttled_messages,
            "failed_messages": self._stats.failed_messages,
            "avg_latency_ms": self._stats.avg_latency_ms,
            "max_latency_ms": self._stats.max_latency_ms,
            "bytes_sent": self._stats.bytes_sent,
            "bytes_saved_compression": self._stats.bytes_saved_compression,
            "compression_ratio": (
                self._stats.bytes_saved_compression / 
                (self._stats.bytes_sent + self._stats.bytes_saved_compression)
                if self._stats.bytes_sent > 0 else 0.0
            ),
            "active_sessions": len(self._local_connections),
        }


# 全局实例
_broadcast_optimizer: Optional[WebSocketBroadcastOptimizer] = None


def get_websocket_broadcast_optimizer(
    use_redis: bool = False,
    redis_url: str = "redis://localhost:6379",
) -> WebSocketBroadcastOptimizer:
    """获取或创建全局广播优化器实例"""
    global _broadcast_optimizer
    
    if _broadcast_optimizer is None:
        _broadcast_optimizer = WebSocketBroadcastOptimizer(
            use_redis=use_redis,
            redis_url=redis_url,
        )
    
    return _broadcast_optimizer
