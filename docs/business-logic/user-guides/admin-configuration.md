# 业务逻辑功能管理员配置指南

## 概述

本指南面向系统管理员，详细介绍如何配置和管理 SuperInsight 业务逻辑提炼与智能化功能，包括系统配置、用户权限、算法管理和系统维护。

## 系统配置

### 1. 基础配置文件

```yaml
# config/business_logic.yaml
business_logic:
  # 核心配置
  enabled: true
  version: "1.0.0"
  
  # 数据库配置
  database:
    url: "postgresql://bl_user:password@localhost:5432/superinsight"
    pool_size: 20
    max_overflow: 30
    pool_timeout: 30
    pool_recycle: 3600
    echo: false  # 生产环境设为 false
  
  # Redis 配置
  redis:
    url: "redis://localhost:6379/1"
    pool_size: 50
    socket_timeout: 10
    socket_connect_timeout: 10
    retry_on_timeout: true
  
  # 算法配置
  algorithms:
    # 默认算法参数
    default_config:
      min_confidence: 0.7
      min_support: 5
      max_patterns: 1000
      timeout: 300  # 5分钟
    
    # 算法特定配置
    sentiment_correlation:
      enabled: true
      min_confidence: 0.6
      max_features: 1000
      use_tfidf: true
    
    keyword_cooccurrence:
      enabled: true
      window_size: 5
      min_cooccurrence: 3
      max_keywords: 500
    
    time_series_analysis:
      enabled: true
      min_data_points: 10
      trend_threshold: 0.1
      seasonality_detection: true
    
    user_behavior_analysis:
      enabled: true
      min_user_actions: 5
      pattern_threshold: 0.05
  
  # 性能配置
  performance:
    max_concurrent_analyses: 10
    chunk_size: 1000
    max_workers: 8
    memory_limit: 8589934592  # 8GB
    enable_caching: true
    cache_ttl: 3600
  
  # 安全配置
  security:
    enable_rate_limiting: true
    rate_limit: 100  # 每分钟请求数
    enable_audit_log: true
    sensitive_data_masking: true
  
  # 通知配置
  notifications:
    enabled: true
    email:
      smtp_server: "smtp.company.com"
      smtp_port: 587
      username: "notifications@company.com"
      password: "${SMTP_PASSWORD}"
      use_tls: true
    
    webhook:
      enabled: true
      url: "https://hooks.company.com/business-logic"
      timeout: 30
  
  # 监控配置
  monitoring:
    enabled: true
    metrics_port: 9090
    health_check_interval: 30
    log_level: "INFO"
    log_format: "json"
```

### 2. 环境变量配置

```bash
# .env.business_logic
# 数据库配置
BL_DATABASE_URL=postgresql://bl_user:secure_password@localhost:5432/superinsight
BL_DATABASE_POOL_SIZE=20

# Redis 配置
BL_REDIS_URL=redis://localhost:6379/1
BL_REDIS_PASSWORD=redis_password

# 安全配置
BL_SECRET_KEY=your-secret-key-here
BL_JWT_SECRET=jwt-secret-key
BL_ENCRYPTION_KEY=encryption-key-32-chars-long

# 外部服务
BL_SMTP_PASSWORD=smtp_password
BL_WEBHOOK_SECRET=webhook_secret

# 性能配置
BL_MAX_WORKERS=8
BL_MEMORY_LIMIT=8589934592
BL_ENABLE_DEBUG=false

# 监控配置
BL_PROMETHEUS_ENABLED=true
BL_LOG_LEVEL=INFO
```

## 用户权限管理

### 1. 权限角色定义

```python
# config/permissions.py
from enum import Enum
from typing import Dict, List

class BusinessLogicRole(Enum):
    """业务逻辑角色"""
    SYSTEM_ADMIN = "system_admin"
    BUSINESS_EXPERT = "business_expert"
    DATA_ANALYST = "data_analyst"
    VIEWER = "viewer"

class BusinessLogicPermission(Enum):
    """业务逻辑权限"""
    # 查看权限
    VIEW_PATTERNS = "bl.view_patterns"
    VIEW_RULES = "bl.view_rules"
    VIEW_INSIGHTS = "bl.view_insights"
    
    # 分析权限
    ANALYZE_DATA = "bl.analyze_data"
    EXTRACT_RULES = "bl.extract_rules"
    GENERATE_INSIGHTS = "bl.generate_insights"
    
    # 管理权限
    MANAGE_ALGORITHMS = "bl.manage_algorithms"
    MANAGE_CONFIGURATIONS = "bl.manage_configurations"
    EXPORT_DATA = "bl.export_data"
    
    # 系统权限
    ADMIN_SYSTEM = "bl.admin_system"
    VIEW_LOGS = "bl.view_logs"
    MANAGE_USERS = "bl.manage_users"

# 角色权限映射
ROLE_PERMISSIONS: Dict[BusinessLogicRole, List[BusinessLogicPermission]] = {
    BusinessLogicRole.SYSTEM_ADMIN: [
        # 所有权限
        BusinessLogicPermission.VIEW_PATTERNS,
        BusinessLogicPermission.VIEW_RULES,
        BusinessLogicPermission.VIEW_INSIGHTS,
        BusinessLogicPermission.ANALYZE_DATA,
        BusinessLogicPermission.EXTRACT_RULES,
        BusinessLogicPermission.GENERATE_INSIGHTS,
        BusinessLogicPermission.MANAGE_ALGORITHMS,
        BusinessLogicPermission.MANAGE_CONFIGURATIONS,
        BusinessLogicPermission.EXPORT_DATA,
        BusinessLogicPermission.ADMIN_SYSTEM,
        BusinessLogicPermission.VIEW_LOGS,
        BusinessLogicPermission.MANAGE_USERS,
    ],
    
    BusinessLogicRole.BUSINESS_EXPERT: [
        BusinessLogicPermission.VIEW_PATTERNS,
        BusinessLogicPermission.VIEW_RULES,
        BusinessLogicPermission.VIEW_INSIGHTS,
        BusinessLogicPermission.ANALYZE_DATA,
        BusinessLogicPermission.EXTRACT_RULES,
        BusinessLogicPermission.GENERATE_INSIGHTS,
        BusinessLogicPermission.EXPORT_DATA,
    ],
    
    BusinessLogicRole.DATA_ANALYST: [
        BusinessLogicPermission.VIEW_PATTERNS,
        BusinessLogicPermission.VIEW_RULES,
        BusinessLogicPermission.VIEW_INSIGHTS,
        BusinessLogicPermission.ANALYZE_DATA,
        BusinessLogicPermission.EXTRACT_RULES,
    ],
    
    BusinessLogicRole.VIEWER: [
        BusinessLogicPermission.VIEW_PATTERNS,
        BusinessLogicPermission.VIEW_RULES,
        BusinessLogicPermission.VIEW_INSIGHTS,
    ]
}
```

### 2. 用户管理脚本

```python
# scripts/manage_bl_users.py
#!/usr/bin/env python3
"""
业务逻辑用户管理脚本
"""

import asyncio
import argparse
from typing import List
from src.business_logic.user_manager import BusinessLogicUserManager
from config.permissions import BusinessLogicRole

class BusinessLogicUserCLI:
    """业务逻辑用户命令行工具"""
    
    def __init__(self):
        self.user_manager = BusinessLogicUserManager()
    
    async def create_user(self, username: str, email: str, role: str, password: str = None):
        """创建用户"""
        try:
            role_enum = BusinessLogicRole(role)
            user = await self.user_manager.create_user(
                username=username,
                email=email,
                role=role_enum,
                password=password
            )
            print(f"用户创建成功: {user.username} ({user.role.value})")
            return user
        except Exception as e:
            print(f"创建用户失败: {e}")
            return None
    
    async def update_user_role(self, username: str, new_role: str):
        """更新用户角色"""
        try:
            role_enum = BusinessLogicRole(new_role)
            await self.user_manager.update_user_role(username, role_enum)
            print(f"用户角色更新成功: {username} -> {new_role}")
        except Exception as e:
            print(f"更新用户角色失败: {e}")
    
    async def list_users(self):
        """列出所有用户"""
        try:
            users = await self.user_manager.list_users()
            print("\n业务逻辑用户列表:")
            print("-" * 60)
            print(f"{'用户名':<20} {'邮箱':<30} {'角色':<15}")
            print("-" * 60)
            
            for user in users:
                print(f"{user.username:<20} {user.email:<30} {user.role.value:<15}")
            
            print(f"\n总计: {len(users)} 个用户")
        except Exception as e:
            print(f"列出用户失败: {e}")
    
    async def delete_user(self, username: str):
        """删除用户"""
        try:
            await self.user_manager.delete_user(username)
            print(f"用户删除成功: {username}")
        except Exception as e:
            print(f"删除用户失败: {e}")

async def main():
    parser = argparse.ArgumentParser(description="业务逻辑用户管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 创建用户命令
    create_parser = subparsers.add_parser('create', help='创建用户')
    create_parser.add_argument('username', help='用户名')
    create_parser.add_argument('email', help='邮箱')
    create_parser.add_argument('role', choices=['system_admin', 'business_expert', 'data_analyst', 'viewer'], help='角色')
    create_parser.add_argument('--password', help='密码（可选）')
    
    # 更新角色命令
    update_parser = subparsers.add_parser('update-role', help='更新用户角色')
    update_parser.add_argument('username', help='用户名')
    update_parser.add_argument('role', choices=['system_admin', 'business_expert', 'data_analyst', 'viewer'], help='新角色')
    
    # 列出用户命令
    subparsers.add_parser('list', help='列出所有用户')
    
    # 删除用户命令
    delete_parser = subparsers.add_parser('delete', help='删除用户')
    delete_parser.add_argument('username', help='用户名')
    
    args = parser.parse_args()
    cli = BusinessLogicUserCLI()
    
    if args.command == 'create':
        await cli.create_user(args.username, args.email, args.role, args.password)
    elif args.command == 'update-role':
        await cli.update_user_role(args.username, args.role)
    elif args.command == 'list':
        await cli.list_users()
    elif args.command == 'delete':
        await cli.delete_user(args.username)
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
```

## 算法管理

### 1. 算法配置管理

```python
# admin/algorithm_config_manager.py
import yaml
import json
from typing import Dict, Any, List
from pathlib import Path

class AlgorithmConfigManager:
    """算法配置管理器"""
    
    def __init__(self, config_dir: str = "config/algorithms"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def create_algorithm_config(self, algorithm_name: str, config: Dict[str, Any]) -> bool:
        """创建算法配置"""
        try:
            config_file = self.config_dir / f"{algorithm_name}.yaml"
            
            # 添加元数据
            full_config = {
                'metadata': {
                    'name': algorithm_name,
                    'version': config.get('version', '1.0.0'),
                    'created_at': str(datetime.utcnow()),
                    'description': config.get('description', ''),
                    'author': config.get('author', 'System Admin')
                },
                'config': config
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(full_config, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            print(f"创建算法配置失败: {e}")
            return False
    
    def update_algorithm_config(self, algorithm_name: str, config: Dict[str, Any]) -> bool:
        """更新算法配置"""
        try:
            config_file = self.config_dir / f"{algorithm_name}.yaml"
            
            if not config_file.exists():
                print(f"算法配置不存在: {algorithm_name}")
                return False
            
            # 读取现有配置
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f)
            
            # 更新配置
            existing_config['config'].update(config)
            existing_config['metadata']['updated_at'] = str(datetime.utcnow())
            
            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
            
            return True
        except Exception as e:
            print(f"更新算法配置失败: {e}")
            return False
    
    def get_algorithm_config(self, algorithm_name: str) -> Dict[str, Any]:
        """获取算法配置"""
        try:
            config_file = self.config_dir / f"{algorithm_name}.yaml"
            
            if not config_file.exists():
                return {}
            
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"读取算法配置失败: {e}")
            return {}
    
    def list_algorithm_configs(self) -> List[str]:
        """列出所有算法配置"""
        try:
            config_files = list(self.config_dir.glob("*.yaml"))
            return [f.stem for f in config_files]
        except Exception as e:
            print(f"列出算法配置失败: {e}")
            return []
    
    def delete_algorithm_config(self, algorithm_name: str) -> bool:
        """删除算法配置"""
        try:
            config_file = self.config_dir / f"{algorithm_name}.yaml"
            
            if config_file.exists():
                config_file.unlink()
                return True
            else:
                print(f"算法配置不存在: {algorithm_name}")
                return False
        except Exception as e:
            print(f"删除算法配置失败: {e}")
            return False
```

### 2. 算法部署管理

```python
# admin/algorithm_deployment.py
import subprocess
import sys
from typing import Dict, Any, List
from pathlib import Path

class AlgorithmDeploymentManager:
    """算法部署管理器"""
    
    def __init__(self, algorithms_dir: str = "algorithms"):
        self.algorithms_dir = Path(algorithms_dir)
        self.algorithms_dir.mkdir(parents=True, exist_ok=True)
    
    def deploy_algorithm(self, algorithm_file: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """部署算法"""
        try:
            # 验证算法文件
            if not algorithm_file.exists():
                return {'status': 'error', 'message': '算法文件不存在'}
            
            # 复制算法文件到部署目录
            target_file = self.algorithms_dir / algorithm_file.name
            import shutil
            shutil.copy2(algorithm_file, target_file)
            
            # 验证算法
            validation_result = self._validate_algorithm(target_file)
            if not validation_result['valid']:
                target_file.unlink()  # 删除无效文件
                return {'status': 'error', 'message': validation_result['error']}
            
            # 注册算法
            registration_result = self._register_algorithm(target_file, config)
            if not registration_result['success']:
                target_file.unlink()  # 删除注册失败的文件
                return {'status': 'error', 'message': registration_result['error']}
            
            return {
                'status': 'success',
                'algorithm_name': registration_result['algorithm_name'],
                'file_path': str(target_file)
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _validate_algorithm(self, algorithm_file: Path) -> Dict[str, Any]:
        """验证算法文件"""
        try:
            # 语法检查
            result = subprocess.run([
                sys.executable, '-m', 'py_compile', str(algorithm_file)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {'valid': False, 'error': f'语法错误: {result.stderr}'}
            
            # 导入检查
            spec = importlib.util.spec_from_file_location("temp_module", algorithm_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查是否包含算法类
            algorithm_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, '__bases__') and
                    any('BaseAlgorithm' in str(base) for base in attr.__bases__)):
                    algorithm_classes.append(attr)
            
            if not algorithm_classes:
                return {'valid': False, 'error': '未找到有效的算法类'}
            
            return {'valid': True, 'algorithm_classes': algorithm_classes}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _register_algorithm(self, algorithm_file: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """注册算法"""
        try:
            from src.business_logic.algorithm_registry import algorithm_registry
            
            # 动态导入算法
            module_name = algorithm_file.stem
            spec = importlib.util.spec_from_file_location(module_name, algorithm_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找算法类
            algorithm_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, '__bases__') and
                    any('BaseAlgorithm' in str(base) for base in attr.__bases__)):
                    algorithm_class = attr
                    break
            
            if not algorithm_class:
                return {'success': False, 'error': '未找到算法类'}
            
            # 注册算法
            algorithm_name = config.get('name', algorithm_class.__name__)
            algorithm_registry.register(algorithm_name, algorithm_class)
            
            return {'success': True, 'algorithm_name': algorithm_name}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def list_deployed_algorithms(self) -> List[Dict[str, Any]]:
        """列出已部署的算法"""
        algorithms = []
        
        for algorithm_file in self.algorithms_dir.glob("*.py"):
            if algorithm_file.name.startswith("__"):
                continue
                
            try:
                # 获取文件信息
                stat = algorithm_file.stat()
                
                algorithms.append({
                    'name': algorithm_file.stem,
                    'file_path': str(algorithm_file),
                    'size': stat.st_size,
                    'modified_time': stat.st_mtime,
                    'status': 'deployed'
                })
            except Exception as e:
                algorithms.append({
                    'name': algorithm_file.stem,
                    'file_path': str(algorithm_file),
                    'status': 'error',
                    'error': str(e)
                })
        
        return algorithms
    
    def undeploy_algorithm(self, algorithm_name: str) -> bool:
        """取消部署算法"""
        try:
            algorithm_file = self.algorithms_dir / f"{algorithm_name}.py"
            
            if algorithm_file.exists():
                algorithm_file.unlink()
                
                # 从注册表中移除
                from src.business_logic.algorithm_registry import algorithm_registry
                if hasattr(algorithm_registry, '_algorithms'):
                    algorithm_registry._algorithms.pop(algorithm_name, None)
                
                return True
            else:
                print(f"算法文件不存在: {algorithm_name}")
                return False
                
        except Exception as e:
            print(f"取消部署算法失败: {e}")
            return False
```

## 系统监控配置

### 1. 监控指标配置

```yaml
# config/monitoring.yaml
monitoring:
  # Prometheus 配置
  prometheus:
    enabled: true
    port: 9090
    path: "/metrics"
    
    # 自定义指标
    custom_metrics:
      - name: "bl_analysis_requests_total"
        type: "counter"
        description: "Total business logic analysis requests"
        labels: ["algorithm", "status", "user_role"]
      
      - name: "bl_analysis_duration_seconds"
        type: "histogram"
        description: "Business logic analysis duration"
        labels: ["algorithm", "data_size_range"]
        buckets: [0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
      
      - name: "bl_active_analyses"
        type: "gauge"
        description: "Number of active business logic analyses"
      
      - name: "bl_cache_hit_rate"
        type: "gauge"
        description: "Business logic cache hit rate"
      
      - name: "bl_memory_usage_bytes"
        type: "gauge"
        description: "Business logic memory usage in bytes"
  
  # 告警规则
  alerts:
    - name: "BusinessLogicHighLatency"
      condition: "bl_analysis_duration_seconds > 60"
      severity: "warning"
      description: "Business logic analysis taking too long"
      
    - name: "BusinessLogicHighErrorRate"
      condition: "rate(bl_analysis_requests_total{status='error'}[5m]) > 0.1"
      severity: "critical"
      description: "High error rate in business logic analyses"
      
    - name: "BusinessLogicHighMemoryUsage"
      condition: "bl_memory_usage_bytes > 6442450944"  # 6GB
      severity: "warning"
      description: "Business logic memory usage is high"
  
  # 日志配置
  logging:
    level: "INFO"
    format: "json"
    file: "/var/log/superinsight/business_logic.log"
    max_size: "100MB"
    backup_count: 10
    
    # 日志过滤器
    filters:
      - name: "sensitive_data"
        pattern: "password|token|secret"
        action: "mask"
      
      - name: "performance"
        level: "DEBUG"
        enabled: false  # 生产环境禁用
```

### 2. 健康检查配置

```python
# admin/health_check.py
import asyncio
import time
from typing import Dict, Any, List
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class BusinessLogicHealthChecker:
    """业务逻辑健康检查器"""
    
    def __init__(self):
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'algorithms': self._check_algorithms,
            'memory': self._check_memory,
            'disk_space': self._check_disk_space
        }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """运行健康检查"""
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for check_name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                duration = time.time() - start_time
                
                results[check_name] = {
                    'status': result['status'].value,
                    'message': result.get('message', ''),
                    'duration': duration,
                    'details': result.get('details', {})
                }
                
                # 更新整体状态
                if result['status'] == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result['status'] == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                    
            except Exception as e:
                results[check_name] = {
                    'status': HealthStatus.UNHEALTHY.value,
                    'message': f'检查失败: {str(e)}',
                    'duration': 0,
                    'details': {}
                }
                overall_status = HealthStatus.UNHEALTHY
        
        return {
            'overall_status': overall_status.value,
            'timestamp': time.time(),
            'checks': results
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            from src.database import get_db_session
            
            async with get_db_session() as session:
                result = await session.execute("SELECT 1")
                if result:
                    return {
                        'status': HealthStatus.HEALTHY,
                        'message': '数据库连接正常'
                    }
                else:
                    return {
                        'status': HealthStatus.UNHEALTHY,
                        'message': '数据库查询失败'
                    }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'数据库连接失败: {str(e)}'
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """检查 Redis 连接"""
        try:
            import redis
            from config.business_logic_config import settings
            
            redis_client = redis.from_url(settings.redis_url)
            redis_client.ping()
            
            return {
                'status': HealthStatus.HEALTHY,
                'message': 'Redis 连接正常'
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Redis 连接失败: {str(e)}'
            }
    
    async def _check_algorithms(self) -> Dict[str, Any]:
        """检查算法状态"""
        try:
            from src.business_logic.algorithm_registry import algorithm_registry
            
            algorithms = algorithm_registry.list_algorithms()
            
            if len(algorithms) == 0:
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': '没有可用的算法',
                    'details': {'algorithm_count': 0}
                }
            
            return {
                'status': HealthStatus.HEALTHY,
                'message': f'算法正常 ({len(algorithms)} 个)',
                'details': {
                    'algorithm_count': len(algorithms),
                    'algorithms': algorithms
                }
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'算法检查失败: {str(e)}'
            }
    
    async def _check_memory(self) -> Dict[str, Any]:
        """检查内存使用"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f'内存使用率过高: {memory.percent}%'
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f'内存使用率较高: {memory.percent}%'
            else:
                status = HealthStatus.HEALTHY
                message = f'内存使用正常: {memory.percent}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent
                }
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'内存检查失败: {str(e)}'
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        try:
            import psutil
            
            disk = psutil.disk_usage('/')
            
            if disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f'磁盘空间不足: {disk.percent}%'
            elif disk.percent > 80:
                status = HealthStatus.DEGRADED
                message = f'磁盘空间较少: {disk.percent}%'
            else:
                status = HealthStatus.HEALTHY
                message = f'磁盘空间充足: {disk.percent}%'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'total': disk.total,
                    'free': disk.free,
                    'percent': disk.percent
                }
            }
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'磁盘检查失败: {str(e)}'
            }
```

## 备份和恢复

### 1. 数据备份脚本

```bash
#!/bin/bash
# scripts/backup_business_logic.sh

# 配置
BACKUP_DIR="/var/backups/superinsight/business_logic"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="superinsight"
DB_USER="bl_user"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "开始业务逻辑数据备份 - $DATE"

# 1. 备份数据库
echo "备份数据库..."
pg_dump -h localhost -U "$DB_USER" -d "$DB_NAME" \
    --table=business_rules \
    --table=business_patterns \
    --table=business_insights \
    --table=algorithm_configs \
    > "$BACKUP_DIR/database_$DATE.sql"

# 2. 备份配置文件
echo "备份配置文件..."
tar -czf "$BACKUP_DIR/configs_$DATE.tar.gz" \
    config/business_logic.yaml \
    config/algorithms/ \
    .env.business_logic

# 3. 备份算法文件
echo "备份算法文件..."
tar -czf "$BACKUP_DIR/algorithms_$DATE.tar.gz" algorithms/

# 4. 备份日志文件
echo "备份日志文件..."
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" \
    /var/log/superinsight/business_logic.log* \
    2>/dev/null || echo "日志文件不存在，跳过"

# 5. 清理旧备份（保留30天）
echo "清理旧备份..."
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "备份完成 - $DATE"
echo "备份文件位置: $BACKUP_DIR"
```

### 2. 数据恢复脚本

```bash
#!/bin/bash
# scripts/restore_business_logic.sh

# 使用方法: ./restore_business_logic.sh BACKUP_DATE
# 例如: ./restore_business_logic.sh 20260105_143000

if [ $# -eq 0 ]; then
    echo "使用方法: $0 <备份日期>"
    echo "例如: $0 20260105_143000"
    exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="/var/backups/superinsight/business_logic"
DB_NAME="superinsight"
DB_USER="bl_user"

echo "开始恢复业务逻辑数据 - $BACKUP_DATE"

# 检查备份文件是否存在
if [ ! -f "$BACKUP_DIR/database_$BACKUP_DATE.sql" ]; then
    echo "错误: 备份文件不存在 - $BACKUP_DIR/database_$BACKUP_DATE.sql"
    exit 1
fi

# 1. 停止相关服务
echo "停止服务..."
systemctl stop superinsight-api
systemctl stop superinsight-worker

# 2. 恢复数据库
echo "恢复数据库..."
psql -h localhost -U "$DB_USER" -d "$DB_NAME" \
    -c "TRUNCATE business_rules, business_patterns, business_insights, algorithm_configs CASCADE;"

psql -h localhost -U "$DB_USER" -d "$DB_NAME" \
    < "$BACKUP_DIR/database_$BACKUP_DATE.sql"

# 3. 恢复配置文件
echo "恢复配置文件..."
if [ -f "$BACKUP_DIR/configs_$BACKUP_DATE.tar.gz" ]; then
    tar -xzf "$BACKUP_DIR/configs_$BACKUP_DATE.tar.gz" -C /
fi

# 4. 恢复算法文件
echo "恢复算法文件..."
if [ -f "$BACKUP_DIR/algorithms_$BACKUP_DATE.tar.gz" ]; then
    rm -rf algorithms/*
    tar -xzf "$BACKUP_DIR/algorithms_$BACKUP_DATE.tar.gz" -C /
fi

# 5. 重启服务
echo "重启服务..."
systemctl start superinsight-api
systemctl start superinsight-worker

# 6. 验证恢复
echo "验证恢复..."
sleep 10
curl -f http://localhost:8000/api/business-logic/health || echo "警告: 健康检查失败"

echo "恢复完成 - $BACKUP_DATE"
```

## 故障排查

### 1. 常见问题诊断

```python
# admin/diagnostics.py
import asyncio
import logging
from typing import Dict, Any, List

class BusinessLogicDiagnostics:
    """业务逻辑诊断工具"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def diagnose_performance_issues(self) -> Dict[str, Any]:
        """诊断性能问题"""
        issues = []
        recommendations = []
        
        # 检查数据库性能
        db_issues = await self._check_database_performance()
        if db_issues:
            issues.extend(db_issues)
            recommendations.append("优化数据库查询和索引")
        
        # 检查内存使用
        memory_issues = await self._check_memory_usage()
        if memory_issues:
            issues.extend(memory_issues)
            recommendations.append("增加内存或启用数据分片")
        
        # 检查算法性能
        algo_issues = await self._check_algorithm_performance()
        if algo_issues:
            issues.extend(algo_issues)
            recommendations.append("优化算法参数或使用缓存")
        
        return {
            'issues': issues,
            'recommendations': recommendations,
            'severity': 'high' if len(issues) > 3 else 'medium' if len(issues) > 0 else 'low'
        }
    
    async def _check_database_performance(self) -> List[str]:
        """检查数据库性能"""
        issues = []
        
        try:
            from src.database import get_db_session
            
            async with get_db_session() as session:
                # 检查慢查询
                result = await session.execute("""
                    SELECT query, mean_time, calls 
                    FROM pg_stat_statements 
                    WHERE mean_time > 1000 
                    ORDER BY mean_time DESC 
                    LIMIT 5
                """)
                
                slow_queries = result.fetchall()
                if slow_queries:
                    issues.append(f"发现 {len(slow_queries)} 个慢查询")
                
                # 检查连接数
                result = await session.execute("SELECT count(*) FROM pg_stat_activity")
                connection_count = result.scalar()
                
                if connection_count > 50:
                    issues.append(f"数据库连接数过多: {connection_count}")
                    
        except Exception as e:
            issues.append(f"数据库检查失败: {str(e)}")
        
        return issues
    
    async def _check_memory_usage(self) -> List[str]:
        """检查内存使用"""
        issues = []
        
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                issues.append(f"内存使用率过高: {memory.percent}%")
            
            # 检查进程内存使用
            process = psutil.Process()
            process_memory = process.memory_info()
            
            if process_memory.rss > 4 * 1024 * 1024 * 1024:  # 4GB
                issues.append(f"进程内存使用过高: {process_memory.rss / 1024 / 1024 / 1024:.2f}GB")
                
        except Exception as e:
            issues.append(f"内存检查失败: {str(e)}")
        
        return issues
    
    async def _check_algorithm_performance(self) -> List[str]:
        """检查算法性能"""
        issues = []
        
        try:
            # 这里可以添加算法性能检查逻辑
            # 例如检查平均执行时间、错误率等
            pass
        except Exception as e:
            issues.append(f"算法性能检查失败: {str(e)}")
        
        return issues
```

## 最佳实践

### 1. 安全配置
- 使用强密码和密钥
- 启用 HTTPS 和 TLS 加密
- 定期更新依赖库
- 实施访问控制和审计

### 2. 性能优化
- 合理配置连接池大小
- 启用缓存机制
- 使用数据分片处理大数据集
- 定期清理过期数据

### 3. 监控运维
- 设置关键指标监控
- 配置告警通知
- 定期备份重要数据
- 建立故障恢复流程

### 4. 用户管理
- 实施最小权限原则
- 定期审查用户权限
- 记录用户操作日志
- 提供用户培训

---

**SuperInsight 业务逻辑功能管理员配置指南** - 让系统管理更简单高效