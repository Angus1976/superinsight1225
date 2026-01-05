#!/usr/bin/env python3
"""
业务逻辑WebSocket服务
提供实时业务洞察通知和模式变化推送

实现需求 13.4: 通知相关业务专家
"""

import json
import logging
import asyncio
from typing import Dict, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessLogicWebSocketManager:
    """业务逻辑WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: {project_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 存储连接信息: {connection_id: {project_id, user_id, connected_at}}
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, project_id: str, user_id: Optional[str] = None):
        """建立WebSocket连接"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        
        # 初始化项目连接字典
        if project_id not in self.active_connections:
            self.active_connections[project_id] = {}
            
        # 存储连接
        self.active_connections[project_id][connection_id] = websocket
        self.connection_info[connection_id] = {
            "project_id": project_id,
            "user_id": user_id,
            "connected_at": datetime.now(),
        }
        
        logger.info(f"WebSocket连接已建立: project={project_id}, connection={connection_id}, user={user_id}")
        
        # 发送连接确认消息
        await self.send_to_connection(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "project_id": project_id,
            "timestamp": datetime.now().isoformat(),
        })
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id in self.connection_info:
            connection_info = self.connection_info[connection_id]
            project_id = connection_info["project_id"]
            
            # 移除连接
            if project_id in self.active_connections:
                self.active_connections[project_id].pop(connection_id, None)
                
                # 如果项目没有活跃连接，清理项目字典
                if not self.active_connections[project_id]:
                    del self.active_connections[project_id]
            
            # 移除连接信息
            del self.connection_info[connection_id]
            
            logger.info(f"WebSocket连接已断开: project={project_id}, connection={connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """向特定连接发送消息"""
        if connection_id in self.connection_info:
            connection_info = self.connection_info[connection_id]
            project_id = connection_info["project_id"]
            
            if project_id in self.active_connections and connection_id in self.active_connections[project_id]:
                websocket = self.active_connections[project_id][connection_id]
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"发送消息到连接 {connection_id} 失败: {e}")
                    # 连接可能已断开，清理连接
                    await self.disconnect(connection_id)
    
    async def broadcast_to_project(self, project_id: str, message: Dict[str, Any], exclude_connection: Optional[str] = None):
        """向项目的所有连接广播消息"""
        if project_id in self.active_connections:
            connections = self.active_connections[project_id].copy()
            
            for connection_id, websocket in connections.items():
                if exclude_connection and connection_id == exclude_connection:
                    continue
                    
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"广播消息到连接 {connection_id} 失败: {e}")
                    # 连接可能已断开，清理连接
                    await self.disconnect(connection_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        for project_id in list(self.active_connections.keys()):
            await self.broadcast_to_project(project_id, message)
    
    def get_project_connections(self, project_id: str) -> int:
        """获取项目的活跃连接数"""
        return len(self.active_connections.get(project_id, {}))
    
    def get_total_connections(self) -> int:
        """获取总连接数"""
        return len(self.connection_info)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        stats = {
            "total_connections": self.get_total_connections(),
            "projects_with_connections": len(self.active_connections),
            "project_stats": {},
        }
        
        for project_id, connections in self.active_connections.items():
            stats["project_stats"][project_id] = {
                "connection_count": len(connections),
                "connection_ids": list(connections.keys()),
            }
        
        return stats

# 全局WebSocket管理器实例
websocket_manager = BusinessLogicWebSocketManager()

class BusinessLogicNotificationService:
    """业务逻辑通知服务"""
    
    def __init__(self, ws_manager: BusinessLogicWebSocketManager):
        self.ws_manager = ws_manager
    
    async def notify_new_insight(self, project_id: str, insight: Dict[str, Any]):
        """通知新的业务洞察"""
        message = {
            "type": "business_insight",
            "payload": insight,
            "timestamp": datetime.now().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_project(project_id, message)
        logger.info(f"已向项目 {project_id} 广播新洞察: {insight.get('title', 'Unknown')}")
    
    async def notify_pattern_change(self, project_id: str, change_data: Dict[str, Any]):
        """通知业务模式变化"""
        message = {
            "type": "pattern_change",
            "payload": change_data,
            "timestamp": datetime.now().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_project(project_id, message)
        logger.info(f"已向项目 {project_id} 广播模式变化: {change_data.get('description', 'Unknown')}")
    
    async def notify_rule_update(self, project_id: str, rule_data: Dict[str, Any]):
        """通知业务规则更新"""
        message = {
            "type": "rule_update",
            "payload": rule_data,
            "timestamp": datetime.now().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_project(project_id, message)
        logger.info(f"已向项目 {project_id} 广播规则更新: {rule_data.get('name', 'Unknown')}")
    
    async def notify_analysis_complete(self, project_id: str, analysis_result: Dict[str, Any]):
        """通知分析完成"""
        message = {
            "type": "analysis_complete",
            "payload": analysis_result,
            "timestamp": datetime.now().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_project(project_id, message)
        logger.info(f"已向项目 {project_id} 广播分析完成通知")
    
    async def notify_export_ready(self, project_id: str, export_info: Dict[str, Any]):
        """通知导出就绪"""
        message = {
            "type": "export_ready",
            "payload": export_info,
            "timestamp": datetime.now().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_project(project_id, message)
        logger.info(f"已向项目 {project_id} 广播导出就绪通知")

# 全局通知服务实例
notification_service = BusinessLogicNotificationService(websocket_manager)

# WebSocket路由
router = APIRouter()

@router.websocket("/ws/business-logic/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """业务逻辑WebSocket端点"""
    connection_id = None
    
    try:
        # 建立连接
        connection_id = await websocket_manager.connect(websocket, project_id)
        
        # 发送欢迎消息
        await websocket_manager.send_to_connection(connection_id, {
            "type": "welcome",
            "message": f"欢迎连接到项目 {project_id} 的业务逻辑通知服务",
            "project_id": project_id,
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat(),
        })
        
        # 保持连接并处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理不同类型的消息
                await handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"客户端主动断开连接: {connection_id}")
                break
            except json.JSONDecodeError:
                logger.error(f"收到无效JSON消息: {data}")
                await websocket_manager.send_to_connection(connection_id, {
                    "type": "error",
                    "message": "无效的JSON格式",
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {e}")
                await websocket_manager.send_to_connection(connection_id, {
                    "type": "error",
                    "message": f"服务器内部错误: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                })
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
    finally:
        # 清理连接
        if connection_id:
            await websocket_manager.disconnect(connection_id)

async def handle_client_message(connection_id: str, message: Dict[str, Any]):
    """处理客户端消息"""
    message_type = message.get("type")
    
    if message_type == "ping":
        # 心跳检测
        await websocket_manager.send_to_connection(connection_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
        })
    
    elif message_type == "subscribe":
        # 订阅特定类型的通知
        subscription_types = message.get("subscription_types", [])
        await websocket_manager.send_to_connection(connection_id, {
            "type": "subscription_confirmed",
            "subscription_types": subscription_types,
            "timestamp": datetime.now().isoformat(),
        })
    
    elif message_type == "get_stats":
        # 获取连接统计
        stats = websocket_manager.get_connection_stats()
        await websocket_manager.send_to_connection(connection_id, {
            "type": "stats",
            "payload": stats,
            "timestamp": datetime.now().isoformat(),
        })
    
    else:
        logger.warning(f"收到未知消息类型: {message_type}")
        await websocket_manager.send_to_connection(connection_id, {
            "type": "error",
            "message": f"未知消息类型: {message_type}",
            "timestamp": datetime.now().isoformat(),
        })

# 定期清理断开的连接
async def cleanup_disconnected_connections():
    """定期清理断开的连接"""
    while True:
        try:
            # 每30秒检查一次
            await asyncio.sleep(30)
            
            # 发送心跳检测
            for project_id in list(websocket_manager.active_connections.keys()):
                connections = websocket_manager.active_connections[project_id].copy()
                
                for connection_id, websocket in connections.items():
                    try:
                        await websocket.ping()
                    except Exception:
                        # 连接已断开，清理
                        await websocket_manager.disconnect(connection_id)
                        logger.info(f"清理断开的连接: {connection_id}")
                        
        except Exception as e:
            logger.error(f"清理连接时出错: {e}")

# 导出主要组件
__all__ = [
    'websocket_manager',
    'notification_service',
    'router',
    'BusinessLogicWebSocketManager',
    'BusinessLogicNotificationService',
]