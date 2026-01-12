# Design Document

## Overview

TCB全栈Docker部署系统为SuperInsight 2.3提供云原生的单镜像部署方案。系统采用容器化架构，将FastAPI后端、Label Studio、PostgreSQL和Redis集成到单一Docker镜像中，支持TCB Serverless自动扩缩容和持久存储，实现高效的云原生部署和运维。

## Architecture Design

### System Architecture

```
TCB Fullstack Deployment System
├── Container Integration Layer
│   ├── Multi-Process Manager
│   ├── Service Orchestrator
│   └── Health Monitor
├── TCB Serverless Integration
│   ├── Cloud Run Adapter
│   ├── Auto Scaling Controller
│   └── Resource Manager
├── Persistent Storage Layer
│   ├── CFS Integration
│   ├── Database Persistence
│   └── Media Storage
├── Configuration Management
│   ├── Environment Handler
│   ├── Secrets Manager
│   └── Config Validator
└── Monitoring & Logging
    ├── Cloud Monitor Integration
    ├── Log Aggregator
    └── Alert Manager
```

### Component Architecture

```typescript
interface TCBDeploymentSystem {
  containerManager: ContainerManager;
  serverlessAdapter: ServerlessAdapter;
  storageManager: StorageManager;
  configManager: ConfigManager;
  monitoringService: MonitoringService;
}

interface ContainerManager {
  startServices(): Promise<void>;
  stopServices(): Promise<void>;
  healthCheck(): Promise<HealthStatus>;
  restartService(serviceName: string): Promise<void>;
}

interface ServerlessAdapter {
  deployToCloudRun(config: DeploymentConfig): Promise<DeploymentResult>;
  configureAutoScaling(rules: ScalingRules): Promise<void>;
  updateDeployment(version: string): Promise<void>;
}
```

## Container Design

### Multi-Service Container Architecture

```dockerfile
# 基于现有 Dockerfile.backend 扩展
FROM python:3.11-slim as base

# 系统依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 应用层
FROM base as app
WORKDIR /app

# 复制现有应用代码
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY main.py .
COPY alembic/ ./alembic/
COPY alembic.ini .

# Label Studio集成
RUN pip install label-studio==1.9.2

# 配置文件
COPY config/supervisor/ /etc/supervisor/conf.d/
COPY config/nginx/ /etc/nginx/sites-available/
COPY config/postgresql/ /etc/postgresql/
COPY config/redis/ /etc/redis/

# 启动脚本
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000 8080 5432 6379

CMD ["/usr/local/bin/docker-entrypoint.sh"]
```

### Service Configuration

```yaml
# supervisor配置 - 基于现有服务管理
# config/supervisor/superinsight.conf
[program:fastapi]
command=uvicorn main:app --host 0.0.0.0 --port 8000
directory=/app
user=app
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/fastapi.log
stderr_logfile=/var/log/supervisor/fastapi.log

[program:label-studio]
command=label-studio start --host 0.0.0.0 --port 8080 --data-dir /data/label-studio
directory=/app
user=app
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/label-studio.log
stderr_logfile=/var/log/supervisor/label-studio.log

[program:postgresql]
command=/usr/lib/postgresql/14/bin/postgres -D /data/postgresql -c config_file=/etc/postgresql/postgresql.conf
user=postgres
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/postgresql.log
stderr_logfile=/var/log/supervisor/postgresql.log

[program:redis]
command=redis-server /etc/redis/redis.conf
user=redis
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/redis.log
stderr_logfile=/var/log/supervisor/redis.log

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/nginx.log
stderr_logfile=/var/log/supervisor/nginx.log
```

## TCB Integration Design

### Cloud Run Deployment Configuration

```yaml
# cloudbaserc.json - 扩展现有配置
{
  "envId": "superinsight-prod",
  "region": "ap-shanghai",
  "framework": {
    "name": "superinsight",
    "plugins": {
      "container": {
        "use": "@cloudbase/framework-plugin-container",
        "inputs": {
          "serviceName": "superinsight-fullstack",
          "servicePath": "/",
          "containerPort": 8000,
          "dockerfilePath": "./Dockerfile.tcb",
          "buildDir": ".",
          "cpu": 2,
          "mem": 4,
          "minNum": 1,
          "maxNum": 10,
          "policyType": "cpu",
          "policyThreshold": 70,
          "envVariables": {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/superinsight",
            "REDIS_URL": "redis://localhost:6379/0",
            "LABEL_STUDIO_URL": "http://localhost:8080",
            "TCB_ENV_ID": "{{env.TCB_ENV_ID}}",
            "TCB_SECRET_ID": "{{env.TCB_SECRET_ID}}",
            "TCB_SECRET_KEY": "{{env.TCB_SECRET_KEY}}"
          },
          "customLogs": "stdout",
          "dataBaseName": "superinsight",
          "executeSQLs": [
            "CREATE DATABASE IF NOT EXISTS superinsight;"
          ]
        }
      },
      "database": {
        "use": "@cloudbase/framework-plugin-database",
        "inputs": {
          "envId": "superinsight-prod",
          "instanceName": "superinsight-db"
        }
      },
      "storage": {
        "use": "@cloudbase/framework-plugin-storage",
        "inputs": {
          "rules": [
            {
              "resource": "/uploads/*",
              "allow": true
            },
            {
              "resource": "/media/*",
              "allow": true
            }
          ]
        }
      }
    }
  }
}
```

### Auto Scaling Configuration

```python
# 基于现有监控系统扩展
# src/system/tcb_scaling.py
from src.system.prometheus_integration import PrometheusIntegration

class TCBAutoScaler:
    """TCB自动扩缩容管理器"""
    
    def __init__(self):
        self.prometheus = PrometheusIntegration()  # 复用现有监控
        self.tcb_client = self.init_tcb_client()
    
    async def configure_scaling_rules(self):
        """配置自动扩缩容规则"""
        scaling_config = {
            "cpu_threshold": 70,      # CPU使用率阈值
            "memory_threshold": 80,   # 内存使用率阈值
            "request_rate_threshold": 100,  # 请求速率阈值
            "min_instances": 1,
            "max_instances": 10,
            "scale_up_cooldown": 300,   # 扩容冷却时间
            "scale_down_cooldown": 600  # 缩容冷却时间
        }
        
        return await self.tcb_client.update_service_config(
            service_name="superinsight-fullstack",
            scaling_config=scaling_config
        )
    
    async def monitor_and_scale(self):
        """监控指标并触发扩缩容"""
        metrics = await self.prometheus.get_current_metrics()
        
        if self.should_scale_up(metrics):
            await self.scale_up()
        elif self.should_scale_down(metrics):
            await self.scale_down()
```

## Storage Integration Design

### Persistent Storage Architecture

```python
# 扩展现有存储管理
# src/storage/tcb_storage.py
from src.storage.manager import StorageManager

class TCBStorageManager(StorageManager):
    """TCB云存储管理器"""
    
    def __init__(self):
        super().__init__()  # 保持现有存储逻辑
        self.cfs_client = self.init_cfs_client()
        self.cos_client = self.init_cos_client()
    
    async def setup_persistent_volumes(self):
        """设置持久化存储卷"""
        volumes = {
            "database": {
                "mount_path": "/data/postgresql",
                "size": "20Gi",
                "storage_class": "cfs-standard"
            },
            "redis": {
                "mount_path": "/data/redis", 
                "size": "5Gi",
                "storage_class": "cfs-standard"
            },
            "label_studio": {
                "mount_path": "/data/label-studio",
                "size": "50Gi", 
                "storage_class": "cfs-standard"
            },
            "uploads": {
                "mount_path": "/app/uploads",
                "size": "100Gi",
                "storage_class": "cos-standard"
            }
        }
        
        for name, config in volumes.items():
            await self.create_persistent_volume(name, config)
    
    async def backup_data(self):
        """数据备份到云存储"""
        # 基于现有备份逻辑扩展
        backup_tasks = [
            self.backup_database(),
            self.backup_redis_data(),
            self.backup_label_studio_data(),
            self.backup_uploaded_files()
        ]
        
        results = await asyncio.gather(*backup_tasks)
        return results
```

### Database Persistence Configuration

```bash
#!/bin/bash
# scripts/setup-persistence.sh
# 基于现有数据库管理脚本扩展

# 创建数据目录
mkdir -p /data/postgresql /data/redis /data/label-studio

# 初始化PostgreSQL数据目录
if [ ! -d "/data/postgresql/base" ]; then
    su - postgres -c "/usr/lib/postgresql/14/bin/initdb -D /data/postgresql"
    
    # 复制现有数据库配置
    cp /app/config/postgresql/postgresql.conf /data/postgresql/
    cp /app/config/postgresql/pg_hba.conf /data/postgresql/
fi

# 设置Redis持久化
cp /app/config/redis/redis.conf /data/redis/
sed -i 's|dir .*|dir /data/redis|' /data/redis/redis.conf
sed -i 's|# save|save|' /data/redis/redis.conf

# 设置Label Studio数据目录
export LABEL_STUDIO_BASE_DATA_DIR=/data/label-studio

# 设置权限
chown -R postgres:postgres /data/postgresql
chown -R redis:redis /data/redis
chown -R app:app /data/label-studio
```

## Configuration Management

### Environment Configuration

```python
# 扩展现有配置管理
# src/config/tcb_config.py
from src.config.settings import Settings

class TCBSettings(Settings):
    """TCB环境配置管理"""
    
    # TCB特定配置
    tcb_env_id: str = Field(..., env="TCB_ENV_ID")
    tcb_secret_id: str = Field(..., env="TCB_SECRET_ID") 
    tcb_secret_key: str = Field(..., env="TCB_SECRET_KEY")
    tcb_region: str = Field(default="ap-shanghai", env="TCB_REGION")
    
    # 存储配置
    cfs_mount_point: str = Field(default="/data", env="CFS_MOUNT_POINT")
    cos_bucket: str = Field(..., env="COS_BUCKET")
    cos_region: str = Field(default="ap-shanghai", env="COS_REGION")
    
    # 服务配置
    container_port: int = Field(default=8000, env="CONTAINER_PORT")
    label_studio_port: int = Field(default=8080, env="LABEL_STUDIO_PORT")
    
    # 扩缩容配置
    min_instances: int = Field(default=1, env="MIN_INSTANCES")
    max_instances: int = Field(default=10, env="MAX_INSTANCES")
    cpu_threshold: int = Field(default=70, env="CPU_THRESHOLD")
    memory_threshold: int = Field(default=80, env="MEMORY_THRESHOLD")
    
    class Config:
        env_file = ".env.tcb"
        case_sensitive = False
```

### Secrets Management

```python
# src/security/tcb_secrets.py
import json
from tencentcloud.common import credential
from tencentcloud.ssm.v20190923 import ssm_client, models

class TCBSecretsManager:
    """TCB密钥管理服务"""
    
    def __init__(self, secret_id: str, secret_key: str, region: str):
        cred = credential.Credential(secret_id, secret_key)
        self.client = ssm_client.SsmClient(cred, region)
    
    async def get_secret(self, secret_name: str) -> dict:
        """获取密钥值"""
        try:
            req = models.GetSecretValueRequest()
            req.SecretName = secret_name
            
            resp = self.client.GetSecretValue(req)
            return json.loads(resp.SecretString)
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            raise
    
    async def create_secret(self, secret_name: str, secret_value: dict):
        """创建密钥"""
        req = models.CreateSecretRequest()
        req.SecretName = secret_name
        req.SecretString = json.dumps(secret_value)
        req.Description = f"Secret for SuperInsight {secret_name}"
        
        return self.client.CreateSecret(req)
```

## Monitoring and Logging

### Cloud Monitor Integration

```python
# 扩展现有监控系统
# src/monitoring/tcb_monitor.py
from src.monitoring.prometheus_integration import PrometheusIntegration

class TCBMonitoringService(PrometheusIntegration):
    """TCB云监控集成服务"""
    
    def __init__(self):
        super().__init__()  # 保持现有Prometheus集成
        self.tcb_monitor = self.init_tcb_monitor()
    
    async def setup_cloud_monitoring(self):
        """设置云监控"""
        # 基于现有监控指标扩展
        metrics_config = {
            "custom_metrics": [
                {
                    "name": "superinsight_api_requests_total",
                    "type": "counter",
                    "description": "Total API requests"
                },
                {
                    "name": "superinsight_task_processing_duration",
                    "type": "histogram", 
                    "description": "Task processing duration"
                },
                {
                    "name": "superinsight_active_users",
                    "type": "gauge",
                    "description": "Number of active users"
                }
            ],
            "alert_rules": [
                {
                    "name": "HighErrorRate",
                    "condition": "error_rate > 0.05",
                    "duration": "5m",
                    "action": "scale_up"
                },
                {
                    "name": "HighCPUUsage", 
                    "condition": "cpu_usage > 0.8",
                    "duration": "3m",
                    "action": "scale_up"
                }
            ]
        }
        
        return await self.tcb_monitor.configure_monitoring(metrics_config)
    
    async def collect_container_metrics(self):
        """收集容器指标"""
        # 复用现有指标收集逻辑
        base_metrics = await self.collect_metrics()
        
        # 添加容器特定指标
        container_metrics = {
            "container_cpu_usage": await self.get_cpu_usage(),
            "container_memory_usage": await self.get_memory_usage(),
            "container_disk_usage": await self.get_disk_usage(),
            "service_health_status": await self.check_services_health()
        }
        
        return {**base_metrics, **container_metrics}
```

### Centralized Logging

```python
# src/logging/tcb_logger.py
import logging
from pythonjsonlogger import jsonlogger

class TCBLogHandler:
    """TCB日志处理器"""
    
    def __init__(self):
        self.setup_json_logging()
    
    def setup_json_logging(self):
        """设置JSON格式日志"""
        # 基于现有日志配置扩展
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台输出 (TCB会自动收集)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.INFO)
        
        # 配置应用日志器
        app_logger = logging.getLogger('superinsight')
        app_logger.setLevel(logging.DEBUG)
    
    def log_request(self, request_id: str, method: str, path: str, duration: float):
        """记录API请求日志"""
        logger = logging.getLogger('superinsight.api')
        logger.info(
            "API request completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "duration_ms": duration * 1000,
                "service": "superinsight-api"
            }
        )
```

## Deployment Strategy

### Multi-Environment Support

```python
# src/deployment/tcb_deployer.py
class TCBDeployer:
    """TCB部署管理器"""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.config = self.load_environment_config(environment)
    
    async def deploy(self, version: str):
        """部署到TCB环境"""
        deployment_steps = [
            self.validate_configuration(),
            self.build_container_image(version),
            self.push_to_registry(version),
            self.update_cloud_run_service(version),
            self.run_health_checks(),
            self.update_traffic_routing()
        ]
        
        for step in deployment_steps:
            result = await step
            if not result.success:
                await self.rollback_deployment()
                raise DeploymentError(f"Deployment failed at step: {step.__name__}")
        
        return DeploymentResult(success=True, version=version)
    
    async def rollback_deployment(self):
        """回滚部署"""
        previous_version = await self.get_previous_version()
        return await self.deploy(previous_version)
```

### Blue-Green Deployment

```python
class BlueGreenDeployer(TCBDeployer):
    """蓝绿部署管理器"""
    
    async def blue_green_deploy(self, new_version: str):
        """执行蓝绿部署"""
        # 1. 部署到绿色环境
        green_service = await self.deploy_to_green_environment(new_version)
        
        # 2. 运行验证测试
        validation_result = await self.run_validation_tests(green_service)
        if not validation_result.passed:
            await self.cleanup_green_environment()
            raise ValidationError("Green environment validation failed")
        
        # 3. 切换流量
        await self.switch_traffic_to_green()
        
        # 4. 监控新版本
        monitoring_result = await self.monitor_green_environment(duration=300)
        if not monitoring_result.healthy:
            await self.switch_traffic_to_blue()
            raise DeploymentError("Green environment monitoring failed")
        
        # 5. 清理蓝色环境
        await self.cleanup_blue_environment()
        
        return DeploymentResult(success=True, version=new_version)
```

## Performance Optimization

### Container Optimization

```dockerfile
# 多阶段构建优化镜像大小
FROM python:3.11-slim as builder

# 构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行时镜像
FROM python:3.11-slim as runtime

# 只安装运行时依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制构建的依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 应用代码
WORKDIR /app
COPY . .

# 优化启动脚本
COPY scripts/optimized-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/optimized-entrypoint.sh

EXPOSE 8000
CMD ["/usr/local/bin/optimized-entrypoint.sh"]
```

### Service Startup Optimization

```bash
#!/bin/bash
# scripts/optimized-entrypoint.sh
# 优化的服务启动脚本

set -e

# 并行启动数据库服务
start_database() {
    echo "Starting PostgreSQL..."
    su - postgres -c "/usr/lib/postgresql/14/bin/postgres -D /data/postgresql" &
    
    # 等待数据库就绪
    until pg_isready -h localhost -p 5432; do
        echo "Waiting for PostgreSQL..."
        sleep 2
    done
    
    # 运行数据库迁移
    alembic upgrade head
}

start_redis() {
    echo "Starting Redis..."
    redis-server /etc/redis/redis.conf &
    
    # 等待Redis就绪
    until redis-cli ping; do
        echo "Waiting for Redis..."
        sleep 1
    done
}

start_label_studio() {
    echo "Starting Label Studio..."
    export LABEL_STUDIO_BASE_DATA_DIR=/data/label-studio
    label-studio start --host 0.0.0.0 --port 8080 &
}

start_fastapi() {
    echo "Starting FastAPI..."
    uvicorn main:app --host 0.0.0.0 --port 8000 &
}

# 并行启动服务
start_database &
start_redis &

# 等待基础服务就绪
wait

# 启动应用服务
start_label_studio &
start_fastapi &

# 启动nginx反向代理
nginx -g "daemon off;" &

# 等待所有服务
wait
```

This comprehensive design provides a robust foundation for TCB fullstack deployment in SuperInsight 2.3, ensuring cloud-native scalability, reliability, and performance while maintaining integration with existing system components.