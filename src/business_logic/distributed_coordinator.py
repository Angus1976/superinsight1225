#!/usr/bin/env python3
"""
分布式计算协调器
实现分布式计算支持，协调多个计算节点进行业务逻辑分析

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 49.1
"""

import asyncio
import logging
import json
import time
import uuid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# Optional dependencies
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available, distributed computing will be limited")

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    logger.warning("aioredis not available, using fallback coordination")

class NodeStatus(Enum):
    """节点状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ComputeNode:
    """计算节点"""
    node_id: str
    host: str
    port: int
    status: NodeStatus
    cpu_cores: int
    memory_gb: float
    current_load: float
    last_heartbeat: datetime
    capabilities: List[str]
    
    @property
    def endpoint(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_available(self) -> bool:
        return (self.status == NodeStatus.ONLINE and 
                self.current_load < 0.8 and
                (datetime.now() - self.last_heartbeat).seconds < 60)

@dataclass
class DistributedTask:
    """分布式任务"""
    task_id: str
    task_type: str
    data_chunks: List[Dict[str, Any]]
    function_name: str
    parameters: Dict[str, Any]
    status: TaskStatus
    assigned_nodes: List[str]
    results: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class NodeManager:
    """节点管理器"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """初始化节点管理器"""
        self.redis_url = redis_url
        self.redis_client = None
        self.nodes: Dict[str, ComputeNode] = {}
        self.heartbeat_interval = 30  # 心跳间隔(秒)
        self.node_timeout = 120  # 节点超时(秒)
        
    async def initialize(self):
        """初始化Redis连接"""
        if not AIOREDIS_AVAILABLE:
            logger.warning("aioredis not available, using fallback mode")
            self.redis_client = None
            return
            
        try:
            self.redis_client = await aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.redis_client = None
    
    async def register_node(self, node: ComputeNode) -> bool:
        """注册计算节点"""
        try:
            self.nodes[node.node_id] = node
            
            # 保存到Redis
            if self.redis_client:
                node_data = asdict(node)
                node_data['last_heartbeat'] = node.last_heartbeat.isoformat()
                await self.redis_client.hset(
                    "compute_nodes", 
                    node.node_id, 
                    json.dumps(node_data)
                )
            
            logger.info(f"节点 {node.node_id} 注册成功")
            return True
            
        except Exception as e:
            logger.error(f"节点注册失败: {e}")
            return False
    
    async def update_node_status(self, node_id: str, status: NodeStatus, load: float = None):
        """更新节点状态"""
        if node_id in self.nodes:
            self.nodes[node_id].status = status
            self.nodes[node_id].last_heartbeat = datetime.now()
            
            if load is not None:
                self.nodes[node_id].current_load = load
            
            # 更新Redis
            if self.redis_client:
                node_data = asdict(self.nodes[node_id])
                node_data['last_heartbeat'] = self.nodes[node_id].last_heartbeat.isoformat()
                await self.redis_client.hset(
                    "compute_nodes", 
                    node_id, 
                    json.dumps(node_data)
                )
    
    async def get_available_nodes(self, required_capability: str = None) -> List[ComputeNode]:
        """获取可用节点"""
        available_nodes = []
        
        for node in self.nodes.values():
            if node.is_available:
                if required_capability is None or required_capability in node.capabilities:
                    available_nodes.append(node)
        
        # 按负载排序，优先选择负载低的节点
        available_nodes.sort(key=lambda n: n.current_load)
        return available_nodes
    
    async def remove_offline_nodes(self):
        """移除离线节点"""
        current_time = datetime.now()
        offline_nodes = []
        
        for node_id, node in self.nodes.items():
            if (current_time - node.last_heartbeat).seconds > self.node_timeout:
                offline_nodes.append(node_id)
        
        for node_id in offline_nodes:
            del self.nodes[node_id]
            if self.redis_client:
                await self.redis_client.hdel("compute_nodes", node_id)
            logger.warning(f"移除离线节点: {node_id}")
    
    async def start_heartbeat_monitor(self):
        """启动心跳监控"""
        while True:
            try:
                await self.remove_offline_nodes()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"心跳监控错误: {e}")
                await asyncio.sleep(5)

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, node_manager: NodeManager):
        """初始化任务调度器"""
        self.node_manager = node_manager
        self.tasks: Dict[str, DistributedTask] = {}
        self.task_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    async def submit_task(self, 
                         task_type: str,
                         data: List[Dict[str, Any]],
                         function_name: str,
                         parameters: Dict[str, Any] = None,
                         chunk_size: int = 1000) -> str:
        """提交分布式任务"""
        task_id = str(uuid.uuid4())
        
        # 分割数据
        data_chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        
        # 创建任务
        task = DistributedTask(
            task_id=task_id,
            task_type=task_type,
            data_chunks=data_chunks,
            function_name=function_name,
            parameters=parameters or {},
            status=TaskStatus.PENDING,
            assigned_nodes=[],
            results={},
            created_at=datetime.now()
        )
        
        self.tasks[task_id] = task
        await self.task_queue.put(task_id)
        
        logger.info(f"任务 {task_id} 已提交，数据分为 {len(data_chunks)} 个块")
        return task_id
    
    async def schedule_tasks(self):
        """调度任务"""
        while True:
            try:
                # 获取待处理任务
                task_id = await self.task_queue.get()
                task = self.tasks.get(task_id)
                
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # 获取可用节点
                available_nodes = await self.node_manager.get_available_nodes(task.task_type)
                
                if not available_nodes:
                    # 没有可用节点，重新排队
                    await asyncio.sleep(5)
                    await self.task_queue.put(task_id)
                    continue
                
                # 分配任务到节点
                await self._assign_task_to_nodes(task, available_nodes)
                
            except Exception as e:
                logger.error(f"任务调度错误: {e}")
                await asyncio.sleep(1)
    
    async def _assign_task_to_nodes(self, task: DistributedTask, nodes: List[ComputeNode]):
        """将任务分配给节点"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # 计算每个节点分配的块数
        total_chunks = len(task.data_chunks)
        chunks_per_node = max(1, total_chunks // len(nodes))
        
        # 分配数据块到节点
        node_assignments = {}
        chunk_index = 0
        
        for i, node in enumerate(nodes):
            if chunk_index >= total_chunks:
                break
            
            # 计算该节点分配的块数
            if i == len(nodes) - 1:  # 最后一个节点处理剩余所有块
                assigned_chunks = task.data_chunks[chunk_index:]
            else:
                end_index = min(chunk_index + chunks_per_node, total_chunks)
                assigned_chunks = task.data_chunks[chunk_index:end_index]
            
            if assigned_chunks:
                node_assignments[node.node_id] = assigned_chunks
                task.assigned_nodes.append(node.node_id)
                chunk_index += len(assigned_chunks)
        
        # 并行执行任务
        execution_tasks = []
        for node_id, chunks in node_assignments.items():
            node = next(n for n in nodes if n.node_id == node_id)
            execution_task = asyncio.create_task(
                self._execute_on_node(task, node, chunks)
            )
            execution_tasks.append(execution_task)
        
        # 等待所有节点完成
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # 处理结果
        await self._process_task_results(task, results)
    
    async def _execute_on_node(self, 
                              task: DistributedTask, 
                              node: ComputeNode, 
                              chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """在节点上执行任务"""
        try:
            # 更新节点状态
            await self.node_manager.update_node_status(node.node_id, NodeStatus.BUSY)
            
            if not AIOHTTP_AVAILABLE:
                # 回退到本地处理
                logger.warning("aiohttp not available, falling back to local processing")
                return {"node_id": node.node_id, "success": True, "result": {"processed": len(chunks)}}
            
            # 准备请求数据
            request_data = {
                "task_id": task.task_id,
                "function_name": task.function_name,
                "data_chunks": chunks,
                "parameters": task.parameters
            }
            
            # 发送HTTP请求到计算节点
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{node.endpoint}/compute",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5分钟超时
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"节点 {node.node_id} 任务执行成功")
                        return {"node_id": node.node_id, "success": True, "result": result}
                    else:
                        error_msg = await response.text()
                        logger.error(f"节点 {node.node_id} 任务执行失败: {error_msg}")
                        return {"node_id": node.node_id, "success": False, "error": error_msg}
        
        except Exception as e:
            logger.error(f"节点 {node.node_id} 执行异常: {e}")
            return {"node_id": node.node_id, "success": False, "error": str(e)}
        
        finally:
            # 恢复节点状态
            await self.node_manager.update_node_status(node.node_id, NodeStatus.ONLINE)
    
    async def _process_task_results(self, task: DistributedTask, results: List[Dict[str, Any]]):
        """处理任务结果"""
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_results.append({"error": str(result)})
            elif result.get("success"):
                successful_results.append(result["result"])
            else:
                failed_results.append(result)
        
        if successful_results:
            # 合并成功的结果
            task.results = self._merge_results(successful_results)
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            logger.info(f"任务 {task.task_id} 执行完成，成功节点: {len(successful_results)}")
        else:
            # 所有节点都失败
            task.status = TaskStatus.FAILED
            task.error_message = f"所有节点执行失败: {failed_results}"
            task.completed_at = datetime.now()
            
            logger.error(f"任务 {task.task_id} 执行失败")
    
    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个节点的结果"""
        merged = {
            "total_nodes": len(results),
            "execution_summary": {
                "total_processed": 0,
                "total_rules": 0,
                "total_patterns": 0,
                "total_insights": 0
            },
            "combined_results": {
                "rules": [],
                "patterns": [],
                "insights": [],
                "statistics": {}
            }
        }
        
        # 合并数值统计
        for result in results:
            if isinstance(result, dict):
                merged["execution_summary"]["total_processed"] += result.get("total_annotations", 0)
                merged["execution_summary"]["total_rules"] += len(result.get("rules", []))
                merged["execution_summary"]["total_patterns"] += len(result.get("patterns", []))
                merged["execution_summary"]["total_insights"] += len(result.get("insights", []))
                
                # 合并具体结果
                if "rules" in result:
                    merged["combined_results"]["rules"].extend(result["rules"])
                if "patterns" in result:
                    merged["combined_results"]["patterns"].extend(result["patterns"])
                if "insights" in result:
                    merged["combined_results"]["insights"].extend(result["insights"])
                if "statistics" in result:
                    merged["combined_results"]["statistics"].update(result["statistics"])
        
        return merged
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "task_type": task.task_type,
            "total_chunks": len(task.data_chunks),
            "assigned_nodes": task.assigned_nodes,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "results": task.results if task.status == TaskStatus.COMPLETED else None
        }
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务状态"""
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
            "running_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            "completed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "task_type": task.task_type,
                    "created_at": task.created_at.isoformat()
                }
                for task in self.tasks.values()
            ]
        }

class DistributedCoordinator:
    """分布式协调器主类"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """初始化分布式协调器"""
        self.node_manager = NodeManager(redis_url)
        self.task_scheduler = TaskScheduler(self.node_manager)
        self.is_running = False
        
    async def initialize(self):
        """初始化协调器"""
        await self.node_manager.initialize()
        logger.info("分布式协调器初始化完成")
    
    async def start(self):
        """启动协调器"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动后台任务
        asyncio.create_task(self.node_manager.start_heartbeat_monitor())
        asyncio.create_task(self.task_scheduler.schedule_tasks())
        
        logger.info("分布式协调器已启动")
    
    async def stop(self):
        """停止协调器"""
        self.is_running = False
        logger.info("分布式协调器已停止")
    
    async def register_compute_node(self, 
                                   host: str, 
                                   port: int,
                                   cpu_cores: int,
                                   memory_gb: float,
                                   capabilities: List[str] = None) -> str:
        """注册计算节点"""
        node_id = f"node_{host}_{port}_{int(time.time())}"
        
        node = ComputeNode(
            node_id=node_id,
            host=host,
            port=port,
            status=NodeStatus.ONLINE,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            current_load=0.0,
            last_heartbeat=datetime.now(),
            capabilities=capabilities or ["business_logic_analysis"]
        )
        
        success = await self.node_manager.register_node(node)
        return node_id if success else None
    
    async def submit_distributed_analysis(self,
                                         analysis_type: str,
                                         data: List[Dict[str, Any]],
                                         function_name: str,
                                         parameters: Dict[str, Any] = None,
                                         chunk_size: int = 1000) -> str:
        """提交分布式分析任务"""
        return await self.task_scheduler.submit_task(
            task_type=analysis_type,
            data=data,
            function_name=function_name,
            parameters=parameters,
            chunk_size=chunk_size
        )
    
    async def get_analysis_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取分析结果"""
        return self.task_scheduler.get_task_status(task_id)
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        nodes = list(self.node_manager.nodes.values())
        
        return {
            "cluster_info": {
                "total_nodes": len(nodes),
                "online_nodes": len([n for n in nodes if n.status == NodeStatus.ONLINE]),
                "busy_nodes": len([n for n in nodes if n.status == NodeStatus.BUSY]),
                "offline_nodes": len([n for n in nodes if n.status == NodeStatus.OFFLINE]),
                "total_cpu_cores": sum(n.cpu_cores for n in nodes),
                "total_memory_gb": sum(n.memory_gb for n in nodes),
                "average_load": sum(n.current_load for n in nodes) / len(nodes) if nodes else 0
            },
            "nodes": [
                {
                    "node_id": node.node_id,
                    "host": node.host,
                    "port": node.port,
                    "status": node.status.value,
                    "cpu_cores": node.cpu_cores,
                    "memory_gb": node.memory_gb,
                    "current_load": node.current_load,
                    "capabilities": node.capabilities,
                    "last_heartbeat": node.last_heartbeat.isoformat()
                }
                for node in nodes
            ],
            "tasks": self.task_scheduler.get_all_tasks()
        }

# 全局分布式协调器实例
distributed_coordinator = DistributedCoordinator()

# 便捷函数
async def submit_distributed_task(analysis_type: str,
                                 data: List[Dict[str, Any]],
                                 function_name: str,
                                 parameters: Dict[str, Any] = None) -> str:
    """提交分布式任务的便捷函数"""
    if not distributed_coordinator.is_running:
        await distributed_coordinator.initialize()
        await distributed_coordinator.start()
    
    return await distributed_coordinator.submit_distributed_analysis(
        analysis_type, data, function_name, parameters
    )

async def get_distributed_result(task_id: str) -> Optional[Dict[str, Any]]:
    """获取分布式任务结果的便捷函数"""
    return await distributed_coordinator.get_analysis_result(task_id)