"""
Real-time Security WebSocket API for SuperInsight Platform.

Provides WebSocket endpoints for real-time security event streaming
and alerts with < 2 second latency.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel

from src.security.real_time_security_monitor import real_time_security_monitor
from src.security.security_event_monitor import SecurityEventType, ThreatLevel
from src.database.connection import get_db_session


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/security/ws", tags=["Real-time Security WebSocket"])


class WebSocketConnection:
    """WebSocket连接管理"""
    
    def __init__(self, websocket: WebSocket, tenant_id: str, user_id: str):
        self.websocket = websocket
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        
    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        try:
            await self.websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            raise
    
    async def send_ping(self):
        """发送心跳"""
        try:
            await self.send_message({
                'type': 'ping',
                'timestamp': datetime.utcnow().isoformat()
            })
            self.last_ping = datetime.utcnow()
        except Exception:
            pass  # 连接可能已断开


class RealTimeSecurityWebSocketManager:
    """实时安全WebSocket管理器"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.tenant_connections: Dict[str, Set[str]] = {}
        self.heartbeat_interval = 30  # 30秒心跳
        
    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str) -> str:
        """建立WebSocket连接"""
        
        await websocket.accept()
        
        # 生成连接ID
        connection_id = f"{tenant_id}_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # 创建连接对象
        connection = WebSocketConnection(websocket, tenant_id, user_id)
        self.connections[connection_id] = connection
        
        # 按租户分组连接
        if tenant_id not in self.tenant_connections:
            self.tenant_connections[tenant_id] = set()
        self.tenant_connections[tenant_id].add(connection_id)
        
        # 注册到实时监控器
        real_time_security_monitor.add_websocket_connection(websocket)
        
        # 发送连接确认
        await connection.send_message({
            'type': 'connection_established',
            'connection_id': connection_id,
            'tenant_id': tenant_id,
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Real-time security monitoring connected'
        })
        
        logger.info(f"WebSocket connected: {connection_id} (tenant: {tenant_id})")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            
            # 从实时监控器注销
            real_time_security_monitor.remove_websocket_connection(connection.websocket)
            
            # 从租户连接中移除
            if connection.tenant_id in self.tenant_connections:
                self.tenant_connections[connection.tenant_id].discard(connection_id)
                if not self.tenant_connections[connection.tenant_id]:
                    del self.tenant_connections[connection.tenant_id]
            
            # 移除连接
            del self.connections[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_to_tenant(self, tenant_id: str, message: Dict[str, Any]):
        """向特定租户的所有连接发送消息"""
        
        if tenant_id not in self.tenant_connections:
            return
        
        disconnected_connections = []
        
        for connection_id in self.tenant_connections[tenant_id]:
            if connection_id in self.connections:
                try:
                    await self.connections[connection_id].send_message(message)
                except Exception:
                    disconnected_connections.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected_connections:
            await self.disconnect(connection_id)
    
    async def send_to_all(self, message: Dict[str, Any]):
        """向所有连接发送消息"""
        
        disconnected_connections = []
        
        for connection_id, connection in self.connections.items():
            try:
                await connection.send_message(message)
            except Exception:
                disconnected_connections.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected_connections:
            await self.disconnect(connection_id)
    
    async def start_heartbeat(self):
        """启动心跳检测"""
        
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                disconnected_connections = []
                current_time = datetime.utcnow()
                
                for connection_id, connection in self.connections.items():
                    try:
                        # 检查连接是否超时
                        if (current_time - connection.last_ping).total_seconds() > self.heartbeat_interval * 2:
                            disconnected_connections.append(connection_id)
                        else:
                            await connection.send_ping()
                    except Exception:
                        disconnected_connections.append(connection_id)
                
                # 清理超时连接
                for connection_id in disconnected_connections:
                    await self.disconnect(connection_id)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        
        return {
            'total_connections': len(self.connections),
            'tenant_connections': {
                tenant_id: len(connections) 
                for tenant_id, connections in self.tenant_connections.items()
            },
            'heartbeat_interval': self.heartbeat_interval
        }


# 全局WebSocket管理器
websocket_manager = RealTimeSecurityWebSocketManager()


@router.websocket("/security-alerts/{tenant_id}")
async def security_alerts_websocket(
    websocket: WebSocket,
    tenant_id: str,
    user_id: str = None  # 在实际应用中应该从认证中获取
):
    """
    实时安全告警WebSocket端点
    
    Args:
        websocket: WebSocket连接
        tenant_id: 租户ID
        user_id: 用户ID（可选，用于审计）
    """
    
    connection_id = None
    
    try:
        # 建立连接
        if not user_id:
            user_id = "anonymous"  # 在实际应用中应该验证用户身份
        
        connection_id = await websocket_manager.connect(websocket, tenant_id, user_id)
        
        # 发送当前活跃威胁
        active_threats = real_time_security_monitor.get_active_threats(tenant_id)
        if active_threats:
            await websocket_manager.send_to_tenant(tenant_id, {
                'type': 'active_threats',
                'threats': [
                    {
                        'event_id': threat.event_id,
                        'event_type': threat.event_type.value,
                        'threat_level': threat.threat_level.value,
                        'description': threat.description,
                        'timestamp': threat.timestamp.isoformat(),
                        'details': threat.details
                    }
                    for threat in active_threats[:10]  # 最多10个
                ],
                'total_count': len(active_threats)
            })
        
        # 保持连接并处理消息
        while True:
            try:
                # 等待客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理客户端消息
                await handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                await websocket_manager.connections[connection_id].send_message({
                    'type': 'error',
                    'message': 'Invalid JSON format'
                })
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                await websocket_manager.connections[connection_id].send_message({
                    'type': 'error',
                    'message': f'Message handling error: {str(e)}'
                })
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    
    finally:
        # 清理连接
        if connection_id:
            await websocket_manager.disconnect(connection_id)


async def handle_client_message(connection_id: str, message: Dict[str, Any]):
    """处理客户端消息"""
    
    message_type = message.get('type')
    connection = websocket_manager.connections.get(connection_id)
    
    if not connection:
        return
    
    if message_type == 'pong':
        # 心跳响应
        connection.last_ping = datetime.utcnow()
    
    elif message_type == 'get_threats':
        # 获取威胁列表
        tenant_id = connection.tenant_id
        threat_level = message.get('threat_level')
        limit = min(message.get('limit', 50), 100)
        
        active_threats = real_time_security_monitor.get_active_threats(tenant_id)
        
        # 过滤威胁等级
        if threat_level:
            try:
                level_filter = ThreatLevel(threat_level)
                active_threats = [
                    threat for threat in active_threats
                    if threat.threat_level == level_filter
                ]
            except ValueError:
                pass
        
        # 限制数量
        active_threats = active_threats[:limit]
        
        await connection.send_message({
            'type': 'threats_response',
            'threats': [
                {
                    'event_id': threat.event_id,
                    'event_type': threat.event_type.value,
                    'threat_level': threat.threat_level.value,
                    'description': threat.description,
                    'timestamp': threat.timestamp.isoformat(),
                    'user_id': str(threat.user_id) if threat.user_id else None,
                    'ip_address': threat.ip_address,
                    'details': threat.details
                }
                for threat in active_threats
            ],
            'total_count': len(active_threats)
        })
    
    elif message_type == 'get_performance':
        # 获取性能指标
        metrics = real_time_security_monitor.get_performance_metrics()
        
        await connection.send_message({
            'type': 'performance_response',
            'metrics': metrics
        })
    
    elif message_type == 'subscribe_events':
        # 订阅特定事件类型
        event_types = message.get('event_types', [])
        threat_levels = message.get('threat_levels', [])
        
        # 存储订阅信息（简化实现）
        connection.subscriptions = {
            'event_types': event_types,
            'threat_levels': threat_levels
        }
        
        await connection.send_message({
            'type': 'subscription_confirmed',
            'event_types': event_types,
            'threat_levels': threat_levels
        })
    
    else:
        await connection.send_message({
            'type': 'error',
            'message': f'Unknown message type: {message_type}'
        })


@router.get("/connections/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    
    return {
        'status': 'success',
        'timestamp': datetime.utcnow().isoformat(),
        'connection_stats': websocket_manager.get_connection_stats(),
        'real_time_monitor_stats': real_time_security_monitor.get_performance_metrics()
    }


@router.post("/broadcast/alert")
async def broadcast_security_alert(
    alert_data: Dict[str, Any],
    tenant_id: str = None
):
    """
    广播安全告警
    
    Args:
        alert_data: 告警数据
        tenant_id: 可选的租户ID，如果指定则只发送给该租户
    """
    
    try:
        message = {
            'type': 'security_alert_broadcast',
            'timestamp': datetime.utcnow().isoformat(),
            'alert': alert_data
        }
        
        if tenant_id:
            await websocket_manager.send_to_tenant(tenant_id, message)
        else:
            await websocket_manager.send_to_all(message)
        
        return {
            'status': 'success',
            'message': 'Alert broadcasted successfully',
            'recipients': len(websocket_manager.tenant_connections.get(tenant_id, [])) if tenant_id else len(websocket_manager.connections)
        }
        
    except Exception as e:
        logger.error(f"Failed to broadcast alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to broadcast alert: {str(e)}")


# 启动心跳检测
async def start_websocket_heartbeat():
    """启动WebSocket心跳检测"""
    asyncio.create_task(websocket_manager.start_heartbeat())


def get_websocket_manager():
    """获取WebSocket管理器"""
    return websocket_manager