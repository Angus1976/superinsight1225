"""
Real-time Security Monitor for SuperInsight Platform.

Optimized for < 5 second response time security monitoring with:
- Event streaming and real-time processing
- Optimized database queries with indexing
- Parallel threat detection
- In-memory caching for hot paths
- WebSocket real-time alerts
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from uuid import UUID
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, select, text
from sqlalchemy.pool import StaticPool
import redis
import asyncio_redis

from src.security.security_event_monitor import (
    SecurityEvent, SecurityEventType, ThreatLevel, ThreatPattern
)
from src.security.threat_detector import AdvancedThreatDetector
from src.security.models import AuditLogModel, AuditAction
from src.database.connection import get_db_session


class RealTimeSecurityMonitor:
    """
    实时安全监控器 - 优化版本
    
    性能目标：
    - 威胁检测响应时间 < 5秒
    - 事件处理延迟 < 1秒
    - 告警发送延迟 < 2秒
    - 支持并发处理
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 性能配置
        self.scan_interval = 5  # 5秒扫描间隔
        self.batch_size = 100   # 批处理大小
        self.max_workers = 4    # 并发工作线程数
        
        # 实时事件队列
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.processing_queue = asyncio.Queue(maxsize=5000)
        
        # 缓存系统
        self.threat_cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        self.last_cache_cleanup = time.time()
        
        # Redis连接（用于分布式缓存）
        self.redis_client = None
        self.redis_enabled = False
        
        # 威胁检测器
        self.threat_detector = AdvancedThreatDetector()
        
        # 性能监控
        self.performance_metrics = {
            'events_processed': 0,
            'threats_detected': 0,
            'avg_processing_time': 0.0,
            'max_processing_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # 实时状态
        self.monitoring_active = False
        self.last_scan_time = datetime.utcnow()
        self.active_threats = {}
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # WebSocket连接管理
        self.websocket_connections = set()
        
        self.logger.info("Real-time Security Monitor initialized")
    
    async def initialize(self):
        """初始化监控器"""
        try:
            # 初始化Redis连接
            await self._initialize_redis()
            
            # 预热缓存
            await self._warm_cache()
            
            # 创建数据库索引
            await self._ensure_database_indexes()
            
            self.logger.info("Real-time Security Monitor initialization completed")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize real-time monitor: {e}")
            raise
    
    async def _initialize_redis(self):
        """初始化Redis连接"""
        try:
            self.redis_client = await asyncio_redis.Connection.create(
                host='localhost', 
                port=6379,
                db=1,  # 使用专用数据库
                poolsize=10
            )
            self.redis_enabled = True
            self.logger.info("Redis connection established for real-time monitoring")
            
        except Exception as e:
            self.logger.warning(f"Redis not available, using in-memory cache only: {e}")
            self.redis_enabled = False
    
    async def _ensure_database_indexes(self):
        """确保数据库索引存在以优化查询性能"""
        
        indexes = [
            # 审计日志优化索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp_tenant ON audit_logs(timestamp DESC, tenant_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_ip_timestamp ON audit_logs(ip_address, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_action_timestamp ON audit_logs(action, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_resource_timestamp ON audit_logs(resource_type, timestamp DESC)",
            
            # 复合索引用于威胁检测
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_threat_detection ON audit_logs(tenant_id, action, timestamp DESC, user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_security_scan ON audit_logs(timestamp DESC, action, resource_type) WHERE timestamp > NOW() - INTERVAL '1 hour'"
        ]
        
        try:
            with get_db_session() as db:
                for index_sql in indexes:
                    try:
                        db.execute(text(index_sql))
                        db.commit()
                    except Exception as e:
                        # 索引可能已存在，继续处理其他索引
                        self.logger.debug(f"Index creation skipped (may exist): {e}")
                        db.rollback()
            
            self.logger.info("Database indexes ensured for optimal performance")
            
        except Exception as e:
            self.logger.error(f"Failed to create database indexes: {e}")
    
    async def _warm_cache(self):
        """预热缓存"""
        try:
            # 预加载威胁模式
            threat_patterns = self.threat_detector.threat_signatures
            for pattern_id, pattern in threat_patterns.items():
                cache_key = f"threat_pattern:{pattern_id}"
                await self._set_cache(cache_key, pattern.__dict__, ttl=3600)
            
            # 预加载用户行为基线
            for user_id, profile in self.threat_detector.behavior_profiles.items():
                cache_key = f"behavior_profile:{user_id}"
                await self._set_cache(cache_key, profile.__dict__, ttl=1800)
            
            self.logger.info("Cache warmed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to warm cache: {e}")
    
    async def start_monitoring(self):
        """启动实时监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # 启动监控任务
        tasks = [
            asyncio.create_task(self._real_time_event_processor()),
            asyncio.create_task(self._threat_detection_worker()),
            asyncio.create_task(self._performance_monitor()),
            asyncio.create_task(self._cache_cleanup_worker())
        ]
        
        self.logger.info("Real-time security monitoring started")
        
        # 等待所有任务完成（或监控停止）
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Real-time monitoring tasks cancelled")
    
    async def stop_monitoring(self):
        """停止实时监控"""
        self.monitoring_active = False
        
        # 关闭Redis连接
        if self.redis_client:
            self.redis_client.close()
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        self.logger.info("Real-time security monitoring stopped")
    
    async def _real_time_event_processor(self):
        """实时事件处理器"""
        
        while self.monitoring_active:
            try:
                start_time = time.time()
                
                # 获取最新审计事件
                recent_events = await self._get_recent_audit_events()
                
                # 批量处理事件
                if recent_events:
                    await self._process_events_batch(recent_events)
                
                # 更新性能指标
                processing_time = time.time() - start_time
                self._update_performance_metrics(processing_time, len(recent_events))
                
                # 短暂休眠以避免过度CPU使用
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Real-time event processor error: {e}")
                await asyncio.sleep(5)  # 错误时等待更长时间
    
    async def _get_recent_audit_events(self) -> List[AuditLogModel]:
        """获取最近的审计事件（优化查询）"""
        
        # 使用缓存的最后扫描时间
        cache_key = "last_scan_timestamp"
        last_scan = await self._get_cache(cache_key)
        
        if last_scan:
            time_threshold = datetime.fromisoformat(last_scan)
        else:
            time_threshold = datetime.utcnow() - timedelta(seconds=self.scan_interval)
        
        try:
            with get_db_session() as db:
                # 优化的查询，使用索引
                stmt = select(AuditLogModel).where(
                    AuditLogModel.timestamp > time_threshold
                ).order_by(
                    desc(AuditLogModel.timestamp)
                ).limit(self.batch_size)
                
                events = db.execute(stmt).scalars().all()
                
                # 更新最后扫描时间
                current_time = datetime.utcnow()
                await self._set_cache(cache_key, current_time.isoformat(), ttl=60)
                self.last_scan_time = current_time
                
                return list(events)
                
        except Exception as e:
            self.logger.error(f"Failed to get recent audit events: {e}")
            return []
    
    async def _process_events_batch(self, events: List[AuditLogModel]):
        """批量处理事件"""
        
        # 按租户分组以并行处理
        events_by_tenant = defaultdict(list)
        for event in events:
            events_by_tenant[event.tenant_id].append(event)
        
        # 并行处理每个租户的事件
        tasks = []
        for tenant_id, tenant_events in events_by_tenant.items():
            task = asyncio.create_task(
                self._process_tenant_events(tenant_id, tenant_events)
            )
            tasks.append(task)
        
        # 等待所有租户处理完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_tenant_events(self, tenant_id: str, events: List[AuditLogModel]):
        """处理单个租户的事件"""
        
        try:
            # 快速威胁检测
            threats = await self._fast_threat_detection(events)
            
            # 处理检测到的威胁
            for threat_event, confidence in threats:
                await self._handle_real_time_threat(threat_event, confidence)
            
            # 更新统计
            self.performance_metrics['events_processed'] += len(events)
            self.performance_metrics['threats_detected'] += len(threats)
            
        except Exception as e:
            self.logger.error(f"Failed to process tenant events ({tenant_id}): {e}")
    
    async def _fast_threat_detection(self, events: List[AuditLogModel]) -> List[Tuple[SecurityEvent, float]]:
        """快速威胁检测（优化版本）"""
        
        threats = []
        
        # 并行检测不同威胁类型
        detection_tasks = [
            self._detect_brute_force_fast(events),
            self._detect_privilege_escalation_fast(events),
            self._detect_data_exfiltration_fast(events),
            self._detect_malicious_requests_fast(events)
        ]
        
        # 等待所有检测完成
        detection_results = await asyncio.gather(*detection_tasks, return_exceptions=True)
        
        # 合并结果
        for result in detection_results:
            if isinstance(result, list):
                threats.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Threat detection error: {result}")
        
        return threats
    
    async def _detect_brute_force_fast(self, events: List[AuditLogModel]) -> List[Tuple[SecurityEvent, float]]:
        """快速暴力破解检测"""
        
        threats = []
        
        # 筛选登录失败事件
        login_failures = [
            event for event in events
            if (event.action == AuditAction.LOGIN and 
                event.details and 
                event.details.get('status') in ['failed', 'invalid', 'blocked'])
        ]
        
        if len(login_failures) < 3:  # 快速过滤
            return threats
        
        # 按IP分组
        failures_by_ip = defaultdict(list)
        for event in login_failures:
            ip_key = str(event.ip_address) if event.ip_address else 'unknown'
            failures_by_ip[ip_key].append(event)
        
        # 检测每个IP的攻击模式
        for ip_address, ip_failures in failures_by_ip.items():
            if len(ip_failures) >= 5:  # 快速阈值
                
                # 检查缓存中是否已经报告过
                cache_key = f"brute_force_detected:{ip_address}"
                if await self._get_cache(cache_key):
                    continue  # 已经检测过，避免重复告警
                
                # 创建威胁事件
                threat_event = SecurityEvent(
                    event_id=self._generate_fast_event_id("BF"),
                    event_type=SecurityEventType.BRUTE_FORCE_ATTACK,
                    threat_level=ThreatLevel.HIGH,
                    tenant_id=ip_failures[0].tenant_id,
                    user_id=None,
                    ip_address=ip_address if ip_address != 'unknown' else None,
                    timestamp=datetime.utcnow(),
                    description=f"实时检测：暴力破解攻击来自 {ip_address}，{len(ip_failures)} 次失败",
                    details={
                        'detection_method': 'real_time_fast',
                        'failure_count': len(ip_failures),
                        'time_window': '5_seconds',
                        'confidence_score': 0.9
                    },
                    source_audit_log_id=ip_failures[0].id
                )
                
                threats.append((threat_event, 0.9))
                
                # 缓存检测结果
                await self._set_cache(cache_key, True, ttl=300)
        
        return threats
    
    async def _detect_privilege_escalation_fast(self, events: List[AuditLogModel]) -> List[Tuple[SecurityEvent, float]]:
        """快速权限提升检测"""
        
        threats = []
        
        # 筛选权限相关操作
        privilege_events = [
            event for event in events
            if (event.action in [AuditAction.UPDATE, AuditAction.CREATE] and
                event.resource_type in ['user', 'role', 'permission'])
        ]
        
        if len(privilege_events) < 2:
            return threats
        
        # 按用户分组
        events_by_user = defaultdict(list)
        for event in privilege_events:
            if event.user_id:
                events_by_user[str(event.user_id)].append(event)
        
        # 检测异常权限操作
        for user_id, user_events in events_by_user.items():
            if len(user_events) >= 3:  # 快速阈值
                
                cache_key = f"privilege_escalation:{user_id}"
                if await self._get_cache(cache_key):
                    continue
                
                threat_event = SecurityEvent(
                    event_id=self._generate_fast_event_id("PE"),
                    event_type=SecurityEventType.PRIVILEGE_ESCALATION,
                    threat_level=ThreatLevel.CRITICAL,
                    tenant_id=user_events[0].tenant_id,
                    user_id=UUID(user_id),
                    ip_address=str(user_events[0].ip_address) if user_events[0].ip_address else None,
                    timestamp=datetime.utcnow(),
                    description=f"实时检测：权限提升攻击用户 {user_id}，{len(user_events)} 个操作",
                    details={
                        'detection_method': 'real_time_fast',
                        'operations_count': len(user_events),
                        'confidence_score': 0.85
                    },
                    source_audit_log_id=user_events[0].id
                )
                
                threats.append((threat_event, 0.85))
                await self._set_cache(cache_key, True, ttl=600)
        
        return threats
    
    async def _detect_data_exfiltration_fast(self, events: List[AuditLogModel]) -> List[Tuple[SecurityEvent, float]]:
        """快速数据泄露检测"""
        
        threats = []
        
        # 筛选导出事件
        export_events = [
            event for event in events
            if event.action == AuditAction.EXPORT
        ]
        
        if not export_events:
            return threats
        
        # 按用户分组
        exports_by_user = defaultdict(list)
        for event in export_events:
            if event.user_id:
                exports_by_user[str(event.user_id)].append(event)
        
        # 检测大量导出
        for user_id, user_exports in exports_by_user.items():
            total_size = sum(
                event.details.get('export_size_mb', 0)
                for event in user_exports if event.details
            )
            
            if total_size > 100 or len(user_exports) > 10:  # 快速阈值
                
                cache_key = f"data_exfiltration:{user_id}"
                if await self._get_cache(cache_key):
                    continue
                
                threat_event = SecurityEvent(
                    event_id=self._generate_fast_event_id("DE"),
                    event_type=SecurityEventType.DATA_EXFILTRATION,
                    threat_level=ThreatLevel.HIGH,
                    tenant_id=user_exports[0].tenant_id,
                    user_id=UUID(user_id),
                    ip_address=str(user_exports[0].ip_address) if user_exports[0].ip_address else None,
                    timestamp=datetime.utcnow(),
                    description=f"实时检测：数据泄露风险用户 {user_id}，导出 {total_size}MB",
                    details={
                        'detection_method': 'real_time_fast',
                        'export_size_mb': total_size,
                        'export_count': len(user_exports),
                        'confidence_score': 0.8
                    },
                    source_audit_log_id=user_exports[0].id
                )
                
                threats.append((threat_event, 0.8))
                await self._set_cache(cache_key, True, ttl=900)
        
        return threats
    
    async def _detect_malicious_requests_fast(self, events: List[AuditLogModel]) -> List[Tuple[SecurityEvent, float]]:
        """快速恶意请求检测"""
        
        threats = []
        
        # 恶意模式（预编译正则表达式会更快，这里简化）
        malicious_patterns = [
            'union select', 'drop table', '<script>', 'javascript:',
            '../../../', 'cmd.exe', 'powershell'
        ]
        
        # 检查每个事件
        malicious_events = []
        for event in events:
            if event.details:
                details_str = json.dumps(event.details).lower()
                if any(pattern in details_str for pattern in malicious_patterns):
                    malicious_events.append(event)
        
        if len(malicious_events) >= 2:  # 快速阈值
            
            # 按IP分组
            by_ip = defaultdict(list)
            for event in malicious_events:
                ip_key = str(event.ip_address) if event.ip_address else 'unknown'
                by_ip[ip_key].append(event)
            
            for ip_address, ip_events in by_ip.items():
                if len(ip_events) >= 2:
                    
                    cache_key = f"malicious_requests:{ip_address}"
                    if await self._get_cache(cache_key):
                        continue
                    
                    threat_event = SecurityEvent(
                        event_id=self._generate_fast_event_id("MR"),
                        event_type=SecurityEventType.MALICIOUS_REQUEST,
                        threat_level=ThreatLevel.CRITICAL,
                        tenant_id=ip_events[0].tenant_id,
                        user_id=ip_events[0].user_id,
                        ip_address=ip_address if ip_address != 'unknown' else None,
                        timestamp=datetime.utcnow(),
                        description=f"实时检测：恶意请求攻击来自 {ip_address}，{len(ip_events)} 个请求",
                        details={
                            'detection_method': 'real_time_fast',
                            'malicious_requests': len(ip_events),
                            'confidence_score': 0.95
                        },
                        source_audit_log_id=ip_events[0].id
                    )
                    
                    threats.append((threat_event, 0.95))
                    await self._set_cache(cache_key, True, ttl=300)
        
        return threats
    
    async def _handle_real_time_threat(self, threat_event: SecurityEvent, confidence: float):
        """处理实时威胁"""
        
        # 存储威胁
        self.active_threats[threat_event.event_id] = threat_event
        
        # 立即发送WebSocket告警
        await self._send_websocket_alert(threat_event)
        
        # 记录到审计日志（异步）
        asyncio.create_task(self._log_threat_async(threat_event))
        
        # 自动响应（如果需要）
        if threat_event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            asyncio.create_task(self._execute_auto_response_async(threat_event))
        
        self.logger.warning(f"Real-time threat detected: {threat_event.description}")
    
    async def _send_websocket_alert(self, threat_event: SecurityEvent):
        """发送WebSocket实时告警"""
        
        alert_data = {
            'type': 'security_threat',
            'event_id': threat_event.event_id,
            'threat_level': threat_event.threat_level.value,
            'event_type': threat_event.event_type.value,
            'tenant_id': threat_event.tenant_id,
            'description': threat_event.description,
            'timestamp': threat_event.timestamp.isoformat(),
            'details': threat_event.details
        }
        
        # 发送给所有连接的WebSocket客户端
        if self.websocket_connections:
            message = json.dumps(alert_data)
            disconnected = set()
            
            for websocket in self.websocket_connections:
                try:
                    await websocket.send(message)
                except Exception:
                    disconnected.add(websocket)
            
            # 清理断开的连接
            self.websocket_connections -= disconnected
    
    async def _log_threat_async(self, threat_event: SecurityEvent):
        """异步记录威胁到审计日志"""
        
        try:
            with get_db_session() as db:
                audit_log = AuditLogModel(
                    user_id=threat_event.user_id,
                    tenant_id=threat_event.tenant_id,
                    action=AuditAction.CREATE,
                    resource_type="real_time_security_threat",
                    resource_id=threat_event.event_id,
                    ip_address=threat_event.ip_address,
                    details={
                        "threat_level": threat_event.threat_level.value,
                        "event_type": threat_event.event_type.value,
                        "description": threat_event.description,
                        "detection_method": "real_time",
                        "confidence_score": threat_event.details.get('confidence_score', 0.0)
                    }
                )
                
                db.add(audit_log)
                db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to log threat to audit: {e}")
    
    async def _execute_auto_response_async(self, threat_event: SecurityEvent):
        """异步执行自动响应"""
        
        try:
            # 根据威胁类型执行相应的自动响应
            if threat_event.event_type == SecurityEventType.BRUTE_FORCE_ATTACK:
                await self._auto_block_ip(threat_event.ip_address, threat_event.tenant_id)
            elif threat_event.event_type == SecurityEventType.PRIVILEGE_ESCALATION:
                await self._auto_suspend_user(threat_event.user_id, threat_event.tenant_id)
            elif threat_event.event_type == SecurityEventType.MALICIOUS_REQUEST:
                await self._auto_block_ip(threat_event.ip_address, threat_event.tenant_id)
            
            self.logger.info(f"Auto-response executed for threat: {threat_event.event_id}")
            
        except Exception as e:
            self.logger.error(f"Auto-response failed for threat {threat_event.event_id}: {e}")
    
    async def _auto_block_ip(self, ip_address: str, tenant_id: str):
        """自动封禁IP地址"""
        if ip_address:
            # 这里应该调用防火墙或网关API
            self.logger.warning(f"AUTO-RESPONSE: Blocking IP {ip_address} for tenant {tenant_id}")
    
    async def _auto_suspend_user(self, user_id: UUID, tenant_id: str):
        """自动暂停用户"""
        if user_id:
            # 这里应该调用用户管理API
            self.logger.warning(f"AUTO-RESPONSE: Suspending user {user_id} for tenant {tenant_id}")
    
    async def _threat_detection_worker(self):
        """威胁检测工作线程"""
        
        while self.monitoring_active:
            try:
                # 处理队列中的事件
                if not self.processing_queue.empty():
                    events_batch = []
                    
                    # 批量获取事件
                    for _ in range(min(self.batch_size, self.processing_queue.qsize())):
                        try:
                            event = self.processing_queue.get_nowait()
                            events_batch.append(event)
                        except asyncio.QueueEmpty:
                            break
                    
                    if events_batch:
                        await self._process_events_batch(events_batch)
                
                await asyncio.sleep(0.1)  # 短暂休眠
                
            except Exception as e:
                self.logger.error(f"Threat detection worker error: {e}")
                await asyncio.sleep(1)
    
    async def _performance_monitor(self):
        """性能监控"""
        
        while self.monitoring_active:
            try:
                # 每30秒报告性能指标
                await asyncio.sleep(30)
                
                metrics = self.performance_metrics.copy()
                
                self.logger.info(
                    f"Performance metrics: "
                    f"Events: {metrics['events_processed']}, "
                    f"Threats: {metrics['threats_detected']}, "
                    f"Avg time: {metrics['avg_processing_time']:.3f}s, "
                    f"Cache hits: {metrics['cache_hits']}, "
                    f"Cache misses: {metrics['cache_misses']}"
                )
                
                # 重置计数器
                self.performance_metrics['events_processed'] = 0
                self.performance_metrics['threats_detected'] = 0
                
            except Exception as e:
                self.logger.error(f"Performance monitor error: {e}")
    
    async def _cache_cleanup_worker(self):
        """缓存清理工作线程"""
        
        while self.monitoring_active:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                
                current_time = time.time()
                
                # 清理过期的内存缓存
                expired_keys = [
                    key for key, (value, timestamp, ttl) in self.threat_cache.items()
                    if current_time - timestamp > ttl
                ]
                
                for key in expired_keys:
                    del self.threat_cache[key]
                
                self.logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
                
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
    
    # 缓存操作方法
    
    async def _get_cache(self, key: str) -> Any:
        """获取缓存值"""
        
        # 首先尝试Redis
        if self.redis_enabled and self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value:
                    self.performance_metrics['cache_hits'] += 1
                    return json.loads(value)
            except Exception as e:
                self.logger.debug(f"Redis cache get error: {e}")
        
        # 回退到内存缓存
        if key in self.threat_cache:
            value, timestamp, ttl = self.threat_cache[key]
            if time.time() - timestamp < ttl:
                self.performance_metrics['cache_hits'] += 1
                return value
            else:
                del self.threat_cache[key]
        
        self.performance_metrics['cache_misses'] += 1
        return None
    
    async def _set_cache(self, key: str, value: Any, ttl: int = 300):
        """设置缓存值"""
        
        # 设置Redis缓存
        if self.redis_enabled and self.redis_client:
            try:
                await self.redis_client.setex(key, ttl, json.dumps(value, default=str))
            except Exception as e:
                self.logger.debug(f"Redis cache set error: {e}")
        
        # 设置内存缓存
        self.threat_cache[key] = (value, time.time(), ttl)
    
    def _update_performance_metrics(self, processing_time: float, events_count: int):
        """更新性能指标"""
        
        if events_count > 0:
            # 更新平均处理时间
            current_avg = self.performance_metrics['avg_processing_time']
            new_avg = (current_avg + processing_time) / 2
            self.performance_metrics['avg_processing_time'] = new_avg
            
            # 更新最大处理时间
            if processing_time > self.performance_metrics['max_processing_time']:
                self.performance_metrics['max_processing_time'] = processing_time
    
    def _generate_fast_event_id(self, prefix: str) -> str:
        """生成快速事件ID"""
        timestamp = int(time.time() * 1000)  # 毫秒时间戳
        return f"RT_{prefix}_{timestamp}_{hash(timestamp) % 10000:04d}"
    
    # WebSocket连接管理
    
    def add_websocket_connection(self, websocket):
        """添加WebSocket连接"""
        self.websocket_connections.add(websocket)
    
    def remove_websocket_connection(self, websocket):
        """移除WebSocket连接"""
        self.websocket_connections.discard(websocket)
    
    # 公共接口
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            **self.performance_metrics,
            'monitoring_active': self.monitoring_active,
            'last_scan_time': self.last_scan_time.isoformat(),
            'active_threats_count': len(self.active_threats),
            'websocket_connections': len(self.websocket_connections),
            'cache_size': len(self.threat_cache),
            'redis_enabled': self.redis_enabled
        }
    
    def get_active_threats(self, tenant_id: Optional[str] = None) -> List[SecurityEvent]:
        """获取活跃威胁"""
        
        threats = list(self.active_threats.values())
        
        if tenant_id:
            threats = [threat for threat in threats if threat.tenant_id == tenant_id]
        
        return sorted(threats, key=lambda x: x.timestamp, reverse=True)


# 全局实时安全监控器实例
real_time_security_monitor = RealTimeSecurityMonitor()


# 便捷函数
async def start_real_time_monitoring():
    """启动实时安全监控"""
    await real_time_security_monitor.initialize()
    await real_time_security_monitor.start_monitoring()


async def stop_real_time_monitoring():
    """停止实时安全监控"""
    await real_time_security_monitor.stop_monitoring()


def get_real_time_monitor() -> RealTimeSecurityMonitor:
    """获取实时监控器实例"""
    return real_time_security_monitor