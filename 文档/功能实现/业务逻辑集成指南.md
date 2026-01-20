# 业务逻辑功能系统集成指南

## 概述

本指南详细介绍如何将 SuperInsight 业务逻辑提炼与智能化功能集成到现有系统中，包括 API 集成、数据流配置、权限设置和最佳实践。

## 系统要求

### 硬件要求
- **CPU**: 4 核心以上，推荐 8 核心
- **内存**: 8GB 以上，推荐 16GB
- **存储**: 100GB 可用空间
- **网络**: 稳定的网络连接

### 软件要求
- **Python**: 3.8 或更高版本
- **PostgreSQL**: 12 或更高版本
- **Redis**: 6.0 或更高版本
- **Node.js**: 16 或更高版本（前端集成）

### 依赖库
```bash
# Python 依赖
pip install fastapi uvicorn sqlalchemy psycopg2-binary
pip install scikit-learn pandas numpy
pip install spacy nltk
pip install redis celery

# 下载 spaCy 模型
python -m spacy download zh_core_web_sm
python -m spacy download en_core_web_sm
```

## 快速集成

### 1. 基础配置

```python
# config/business_logic_config.py
from pydantic import BaseSettings

class BusinessLogicSettings(BaseSettings):
    # 数据库配置
    database_url: str = "postgresql://user:password@localhost/superinsight"
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"
    
    # 算法配置
    min_confidence: float = 0.7
    min_support: int = 5
    max_patterns: int = 1000
    
    # 性能配置
    enable_caching: bool = True
    cache_ttl: int = 3600
    max_workers: int = 4
    
    class Config:
        env_file = ".env"

settings = BusinessLogicSettings()
```

### 2. 服务初始化

```python
# services/business_logic_service.py
from src.business_logic.api import BusinessLogicService
from src.business_logic.advanced_algorithms import AdvancedAlgorithmManager
from config.business_logic_config import settings

class BusinessLogicIntegration:
    def __init__(self):
        self.service = BusinessLogicService()
        self.algorithm_manager = AdvancedAlgorithmManager()
        
    async def initialize(self):
        """初始化业务逻辑服务"""
        await self.service.initialize()
        await self.algorithm_manager.initialize()
        
    async def analyze_project_data(self, project_id: str, analysis_config: dict):
        """分析项目数据"""
        try:
            # 数据预处理
            data = await self.service.get_project_data(project_id)
            
            # 执行分析
            result = await self.service.analyze_patterns({
                "project_id": project_id,
                "analysis_types": analysis_config.get("types", ["sentiment_correlation"]),
                "min_confidence": analysis_config.get("min_confidence", settings.min_confidence)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"分析失败: {e}")
            raise
```

### 3. API 路由集成

```python
# routers/business_logic_router.py
from fastapi import APIRouter, Depends, HTTPException
from services.business_logic_service import BusinessLogicIntegration

router = APIRouter(prefix="/api/business-logic", tags=["business-logic"])
bl_service = BusinessLogicIntegration()

@router.post("/analyze")
async def analyze_business_patterns(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """分析业务模式"""
    # 权限检查
    if not has_permission(current_user, "business_logic.analyze"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        result = await bl_service.analyze_project_data(
            request.project_id, 
            request.dict()
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules/{project_id}")
async def get_business_rules(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取业务规则"""
    # 权限检查
    if not has_permission(current_user, "business_logic.view"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    rules = await bl_service.service.get_business_rules(project_id)
    return rules
```

## 前端集成

### 1. React 组件集成

```typescript
// components/BusinessLogicDashboard.tsx
import React, { useState, useEffect } from 'react';
import { Card, Button, Spin, message } from 'antd';
import { businessLogicApi } from '../services/api';

interface BusinessLogicDashboardProps {
  projectId: string;
}

export const BusinessLogicDashboard: React.FC<BusinessLogicDashboardProps> = ({
  projectId
}) => {
  const [loading, setLoading] = useState(false);
  const [patterns, setPatterns] = useState([]);
  const [rules, setRules] = useState([]);

  const analyzePatterns = async () => {
    setLoading(true);
    try {
      const result = await businessLogicApi.analyzePatterns({
        project_id: projectId,
        analysis_types: ['sentiment_correlation', 'keyword_cooccurrence'],
        min_confidence: 0.7
      });
      
      setPatterns(result.patterns);
      message.success('分析完成');
    } catch (error) {
      message.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  const loadRules = async () => {
    try {
      const rules = await businessLogicApi.getBusinessRules(projectId);
      setRules(rules);
    } catch (error) {
      message.error('加载规则失败');
    }
  };

  useEffect(() => {
    loadRules();
  }, [projectId]);

  return (
    <div className="business-logic-dashboard">
      <Card title="业务逻辑分析" extra={
        <Button type="primary" onClick={analyzePatterns} loading={loading}>
          开始分析
        </Button>
      }>
        <Spin spinning={loading}>
          {/* 模式展示组件 */}
          <PatternVisualization patterns={patterns} />
          
          {/* 规则管理组件 */}
          <RuleManager rules={rules} onRulesChange={loadRules} />
        </Spin>
      </Card>
    </div>
  );
};
```

### 2. API 服务封装

```typescript
// services/businessLogicApi.ts
import axios from 'axios';

class BusinessLogicApi {
  private baseURL = '/api/business-logic';

  async analyzePatterns(request: AnalysisRequest) {
    const response = await axios.post(`${this.baseURL}/analyze`, request);
    return response.data;
  }

  async getBusinessRules(projectId: string) {
    const response = await axios.get(`${this.baseURL}/rules/${projectId}`);
    return response.data;
  }

  async extractRules(request: ExtractionRequest) {
    const response = await axios.post(`${this.baseURL}/rules/extract`, request);
    return response.data;
  }

  async generateVisualization(request: VisualizationRequest) {
    const response = await axios.post(`${this.baseURL}/visualization`, request);
    return response.data;
  }

  async exportRules(request: ExportRequest) {
    const response = await axios.post(`${this.baseURL}/export`, request, {
      responseType: 'blob'
    });
    return response.data;
  }
}

export const businessLogicApi = new BusinessLogicApi();
```

## 权限配置

### 1. 权限定义

```python
# permissions/business_logic_permissions.py
from enum import Enum

class BusinessLogicPermission(Enum):
    VIEW_PATTERNS = "business_logic.view_patterns"
    ANALYZE_DATA = "business_logic.analyze"
    MANAGE_RULES = "business_logic.manage_rules"
    EXPORT_RULES = "business_logic.export"
    CONFIGURE_ALGORITHMS = "business_logic.configure"

# 角色权限映射
ROLE_PERMISSIONS = {
    "system_admin": [
        BusinessLogicPermission.VIEW_PATTERNS,
        BusinessLogicPermission.ANALYZE_DATA,
        BusinessLogicPermission.MANAGE_RULES,
        BusinessLogicPermission.EXPORT_RULES,
        BusinessLogicPermission.CONFIGURE_ALGORITHMS,
    ],
    "business_expert": [
        BusinessLogicPermission.VIEW_PATTERNS,
        BusinessLogicPermission.ANALYZE_DATA,
        BusinessLogicPermission.MANAGE_RULES,
        BusinessLogicPermission.EXPORT_RULES,
    ],
    "data_annotator": [
        BusinessLogicPermission.VIEW_PATTERNS,
    ],
    "report_viewer": [
        BusinessLogicPermission.VIEW_PATTERNS,
    ]
}
```

## 最佳实践

### 1. 数据准备
- 确保标注数据的质量和一致性
- 定期清理和验证数据
- 建立数据版本控制机制

### 2. 性能优化
- 使用缓存减少重复计算
- 实施数据分片和并行处理
- 定期清理过期的分析结果

### 3. 安全考虑
- 实施严格的权限控制
- 对敏感数据进行脱敏处理
- 记录所有操作的审计日志

### 4. 监控运维
- 设置关键指标的监控告警
- 定期备份分析结果和配置
- 建立故障恢复机制

## 技术支持

如需技术支持，请联系：
- 邮箱: support@superinsight.ai
- 文档: https://docs.superinsight.ai
- GitHub: https://github.com/superinsight/platform

---

**SuperInsight 业务逻辑功能系统集成指南** - 助您快速集成智能分析能力