# Label Studio 企业版功能扩展设计方案

**版本**: 1.0  
**日期**: 2026-01-26  
**状态**: 设计中

## 1. 问题背景

### 1.1 当前状况
- 使用开源版 Label Studio 作为标注引擎
- 需要企业版功能（如 Workspace、高级权限管理等）
- 希望保持对开源版的最小干预
- 需要能够无缝升级 Label Studio 开源版

### 1.2 核心挑战
1. **不能修改 Label Studio 源码** - 否则无法升级
2. **需要扩展企业功能** - Workspace、RBAC、审计等
3. **保持数据一致性** - SuperInsight 和 Label Studio 之间
4. **用户体验统一** - 在 SuperInsight 中无缝集成

## 2. 架构设计原则

### 2.1 核心原则

#### 原则 1: 外部代理层（Proxy Layer）
```
用户请求 → SuperInsight API → 代理层 → Label Studio API
                ↓
         企业功能增强层
                ↓
         PostgreSQL 数据库
```

**关键点**:
- Label Studio 保持原样，不做任何修改
- 所有企业功能在 SuperInsight 层实现
- 通过 API 代理拦截和增强请求

#### 原则 2: 元数据映射（Metadata Mapping）
```
Label Studio 原生字段 → SuperInsight 扩展字段
- Project.title        → Workspace.name
- Project.description  → Workspace metadata (JSON)
- Task.meta           → 扩展元数据
- User.username       → 用户权限映射
```

#### 原则 3: 双写策略（Dual Write）
```
SuperInsight PostgreSQL ←→ Label Studio PostgreSQL
         ↓                           ↓
   企业功能数据              标注核心数据
   (Workspace, RBAC)         (Projects, Tasks)
```

## 3. Workspace 功能实现方案

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                  SuperInsight 前端                       │
│  (Workspace 选择器、项目管理、权限控制)                  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              SuperInsight API 层                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Workspace Service (企业功能)                     │  │
│  │  - Workspace CRUD                                 │  │
│  │  - 项目分组管理                                   │  │
│  │  - 权限控制                                       │  │
│  │  - 审计日志                                       │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │                                    │
│  ┌──────────────────▼───────────────────────────────┐  │
│  │  Label Studio Proxy (代理增强层)                 │  │
│  │  - 请求拦截                                       │  │
│  │  - 元数据注入                                     │  │
│  │  - 权限验证                                       │  │
│  │  - 响应增强                                       │  │
│  └──────────────────┬───────────────────────────────┘  │
└────────────────────┬┴───────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│         Label Studio 开源版 (不修改)                     │
│  - 标注界面                                              │
│  - 项目管理                                              │
│  - 任务分配                                              │
│  - 标注存储                                              │
└─────────────────────────────────────────────────────────┘
```

### 3.2 数据模型设计

#### 3.2.1 SuperInsight 数据库扩展

```sql
-- Workspace 表
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT workspace_name_unique UNIQUE (name)
);

-- Workspace 成员表
CREATE TABLE workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- owner, admin, member, viewer
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT workspace_member_unique UNIQUE (workspace_id, user_id)
);

-- Workspace 项目映射表
CREATE TABLE workspace_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL, -- Label Studio project ID
    superinsight_project_id UUID REFERENCES tasks(id), -- SuperInsight 内部项目 ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT workspace_project_unique UNIQUE (workspace_id, project_id)
);

-- 创建索引
CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);
CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id);
CREATE INDEX idx_workspace_projects_workspace ON workspace_projects(workspace_id);
CREATE INDEX idx_workspace_projects_project ON workspace_projects(project_id);
```

#### 3.2.2 Label Studio 元数据注入

在 Label Studio 的 Project 中注入 Workspace 信息：

```json
{
  "title": "项目名称",
  "description": "项目描述",
  "meta": {
    "superinsight": {
      "workspace_id": "uuid-here",
      "workspace_name": "研发部门",
      "created_by": "user-id",
      "permissions": {
        "can_edit": true,
        "can_delete": false
      }
    }
  }
}
```

### 3.3 API 代理层实现

#### 3.3.1 代理服务架构

```python
# src/label_studio/proxy.py
"""
Label Studio API Proxy with Enterprise Features
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, status
import httpx

from src.label_studio.workspace_service import WorkspaceService
from src.security.rbac_service import RBACService
from src.security.audit_service import AuditService

logger = logging.getLogger(__name__)


class LabelStudioProxy:
    """
    代理层：拦截和增强 Label Studio API 请求
    
    功能：
    1. 请求拦截 - 在请求到达 Label Studio 前进行处理
    2. 权限验证 - 基于 Workspace 的权限控制
    3. 元数据注入 - 自动注入 Workspace 信息
    4. 响应增强 - 在响应中添加企业功能数据
    5. 审计日志 - 记录所有操作
    """
    
    def __init__(self,
                 label_studio_url: str,
                 label_studio_token: str,
                 workspace_service: WorkspaceService,
                 rbac_service: RBACService,
                 audit_service: AuditService):
        self.ls_url = label_studio_url.rstrip('/')
        self.ls_token = label_studio_token
        self.workspace_service = workspace_service
        self.rbac_service = rbac_service
        self.audit_service = audit_service
        
        self.headers = {
            'Authorization': f'Token {self.ls_token}',
            'Content-Type': 'application/json'
        }
    
    async def proxy_request(self,
                           method: str,
                           path: str,
                           user_id: str,
                           workspace_id: Optional[str] = None,
                           body: Optional[Dict[str, Any]] = None,
                           params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        代理请求到 Label Studio，并进行企业功能增强
        
        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            path: API 路径 (如 /api/projects/)
            user_id: 当前用户 ID
            workspace_id: Workspace ID (可选)
            body: 请求体
            params: 查询参数
            
        Returns:
            增强后的响应数据
        """
        try:
            # 1. 权限验证
            await self._verify_permissions(method, path, user_id, workspace_id)
            
            # 2. 请求预处理
            body = await self._preprocess_request(method, path, user_id, workspace_id, body)
            
            # 3. 发送请求到 Label Studio
            async with httpx.AsyncClient(timeout=60.0) as client:
                url = f"{self.ls_url}{path}"
                
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=body if body else None,
                    params=params
                )
                
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Label Studio error: {response.text}"
                    )
                
                result = response.json() if response.text else {}
            
            # 4. 响应后处理
            result = await self._postprocess_response(method, path, user_id, workspace_id, result)
            
            # 5. 记录审计日志
            await self._log_audit(method, path, user_id, workspace_id, result)
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Proxy request error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Proxy error: {str(e)}"
            )
    
    async def _verify_permissions(self,
                                  method: str,
                                  path: str,
                                  user_id: str,
                                  workspace_id: Optional[str]) -> None:
        """验证用户权限"""
        # 如果指定了 workspace，验证用户是否有权限
        if workspace_id:
            # 检查用户是否是 workspace 成员
            is_member = await self.workspace_service.is_member(workspace_id, user_id)
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this workspace"
                )
            
            # 检查操作权限
            required_permission = self._get_required_permission(method, path)
            has_permission = await self.rbac_service.check_permission(
                user_id, workspace_id, required_permission
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions for {required_permission}"
                )
    
    async def _preprocess_request(self,
                                  method: str,
                                  path: str,
                                  user_id: str,
                                  workspace_id: Optional[str],
                                  body: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """请求预处理：注入 Workspace 元数据"""
        if not body:
            return body
        
        # 创建项目时注入 workspace 信息
        if method == "POST" and "/api/projects" in path:
            if workspace_id:
                # 注入 workspace 元数据到项目描述
                workspace = await self.workspace_service.get_workspace(workspace_id)
                
                # 在 description 中嵌入 workspace 信息（JSON 格式）
                workspace_meta = {
                    "workspace_id": workspace_id,
                    "workspace_name": workspace.name,
                    "created_by": user_id
                }
                
                # 将元数据编码到 description
                original_desc = body.get("description", "")
                body["description"] = self._encode_metadata(original_desc, workspace_meta)
                
                logger.info(f"Injected workspace metadata into project: {workspace_id}")
        
        return body
    
    async def _postprocess_response(self,
                                    method: str,
                                    path: str,
                                    user_id: str,
                                    workspace_id: Optional[str],
                                    result: Dict[str, Any]) -> Dict[str, Any]:
        """响应后处理：提取和增强 Workspace 信息"""
        # 列出项目时，添加 workspace 信息
        if method == "GET" and "/api/projects" in path:
            if isinstance(result, list):
                # 批量处理项目列表
                for project in result:
                    await self._enhance_project_with_workspace(project)
            elif isinstance(result, dict) and "results" in result:
                # 分页结果
                for project in result["results"]:
                    await self._enhance_project_with_workspace(project)
            elif isinstance(result, dict) and "id" in result:
                # 单个项目
                await self._enhance_project_with_workspace(result)
        
        return result
    
    async def _enhance_project_with_workspace(self, project: Dict[str, Any]) -> None:
        """增强项目数据，添加 workspace 信息"""
        try:
            # 从 description 中提取 workspace 元数据
            description = project.get("description", "")
            workspace_meta = self._decode_metadata(description)
            
            if workspace_meta:
                # 添加 workspace 信息到响应
                project["workspace"] = workspace_meta
                
                # 恢复原始 description
                project["description"] = workspace_meta.get("original_description", "")
                
                # 获取完整的 workspace 信息
                workspace_id = workspace_meta.get("workspace_id")
                if workspace_id:
                    workspace = await self.workspace_service.get_workspace(workspace_id)
                    if workspace:
                        project["workspace"]["name"] = workspace.name
                        project["workspace"]["owner"] = workspace.owner_id
        except Exception as e:
            logger.warning(f"Failed to enhance project with workspace: {str(e)}")
    
    def _encode_metadata(self, original_desc: str, metadata: Dict[str, Any]) -> str:
        """将元数据编码到 description 中"""
        import json
        import base64
        
        # 保存原始描述
        metadata["original_description"] = original_desc
        
        # 编码元数据
        meta_json = json.dumps(metadata)
        meta_b64 = base64.b64encode(meta_json.encode()).decode()
        
        # 格式: [SUPERINSIGHT_META:base64_data]原始描述
        return f"[SUPERINSIGHT_META:{meta_b64}]{original_desc}"
    
    def _decode_metadata(self, description: str) -> Optional[Dict[str, Any]]:
        """从 description 中解码元数据"""
        import json
        import base64
        import re
        
        # 匹配元数据标记
        pattern = r'\[SUPERINSIGHT_META:([A-Za-z0-9+/=]+)\]'
        match = re.match(pattern, description)
        
        if match:
            try:
                meta_b64 = match.group(1)
                meta_json = base64.b64decode(meta_b64).decode()
                return json.loads(meta_json)
            except Exception as e:
                logger.warning(f"Failed to decode metadata: {str(e)}")
        
        return None
    
    def _get_required_permission(self, method: str, path: str) -> str:
        """根据请求类型获取所需权限"""
        if method == "GET":
            return "project.view"
        elif method == "POST":
            return "project.create"
        elif method in ["PUT", "PATCH"]:
            return "project.edit"
        elif method == "DELETE":
            return "project.delete"
        else:
            return "project.view"
    
    async def _log_audit(self,
                        method: str,
                        path: str,
                        user_id: str,
                        workspace_id: Optional[str],
                        result: Dict[str, Any]) -> None:
        """记录审计日志"""
        try:
            await self.audit_service.log_action(
                user_id=user_id,
                action=f"{method} {path}",
                resource_type="label_studio_project",
                resource_id=result.get("id") if isinstance(result, dict) else None,
                workspace_id=workspace_id,
                details={
                    "method": method,
                    "path": path,
                    "success": True
                }
            )
        except Exception as e:
            logger.error(f"Failed to log audit: {str(e)}")
```

### 3.4 Workspace Service 实现

```python
# src/label_studio/workspace_service.py
"""
Workspace Management Service
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from src.database.connection import get_db_session
from src.database.models import (
    WorkspaceModel,
    WorkspaceMemberModel,
    WorkspaceProjectModel
)

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Workspace 管理服务"""
    
    async def create_workspace(self,
                              name: str,
                              description: str,
                              owner_id: str,
                              settings: Optional[Dict[str, Any]] = None) -> WorkspaceModel:
        """创建 Workspace"""
        with get_db_session() as db:
            workspace = WorkspaceModel(
                name=name,
                description=description,
                owner_id=UUID(owner_id),
                settings=settings or {}
            )
            
            db.add(workspace)
            db.commit()
            db.refresh(workspace)
            
            # 自动添加创建者为 owner
            await self.add_member(
                workspace_id=str(workspace.id),
                user_id=owner_id,
                role="owner"
            )
            
            logger.info(f"Created workspace: {workspace.id}")
            return workspace
    
    async def get_workspace(self, workspace_id: str) -> Optional[WorkspaceModel]:
        """获取 Workspace"""
        with get_db_session() as db:
            stmt = select(WorkspaceModel).where(
                WorkspaceModel.id == UUID(workspace_id)
            )
            return db.execute(stmt).scalar_one_or_none()
    
    async def list_workspaces(self, user_id: str) -> List[WorkspaceModel]:
        """列出用户可访问的 Workspaces"""
        with get_db_session() as db:
            # 查询用户是成员的所有 workspaces
            stmt = select(WorkspaceModel).join(
                WorkspaceMemberModel,
                WorkspaceModel.id == WorkspaceMemberModel.workspace_id
            ).where(
                and_(
                    WorkspaceMemberModel.user_id == UUID(user_id),
                    WorkspaceModel.is_active == True
                )
            )
            
            result = db.execute(stmt)
            return result.scalars().all()
    
    async def add_member(self,
                        workspace_id: str,
                        user_id: str,
                        role: str = "member") -> WorkspaceMemberModel:
        """添加成员到 Workspace"""
        with get_db_session() as db:
            member = WorkspaceMemberModel(
                workspace_id=UUID(workspace_id),
                user_id=UUID(user_id),
                role=role
            )
            
            db.add(member)
            db.commit()
            db.refresh(member)
            
            logger.info(f"Added member {user_id} to workspace {workspace_id}")
            return member
    
    async def is_member(self, workspace_id: str, user_id: str) -> bool:
        """检查用户是否是 Workspace 成员"""
        with get_db_session() as db:
            stmt = select(WorkspaceMemberModel).where(
                and_(
                    WorkspaceMemberModel.workspace_id == UUID(workspace_id),
                    WorkspaceMemberModel.user_id == UUID(user_id)
                )
            )
            
            member = db.execute(stmt).scalar_one_or_none()
            return member is not None
    
    async def add_project_to_workspace(self,
                                      workspace_id: str,
                                      project_id: int,
                                      superinsight_project_id: Optional[str] = None) -> WorkspaceProjectModel:
        """将 Label Studio 项目添加到 Workspace"""
        with get_db_session() as db:
            wp = WorkspaceProjectModel(
                workspace_id=UUID(workspace_id),
                project_id=project_id,
                superinsight_project_id=UUID(superinsight_project_id) if superinsight_project_id else None
            )
            
            db.add(wp)
            db.commit()
            db.refresh(wp)
            
            logger.info(f"Added project {project_id} to workspace {workspace_id}")
            return wp
    
    async def get_workspace_projects(self, workspace_id: str) -> List[int]:
        """获取 Workspace 中的所有项目 ID"""
        with get_db_session() as db:
            stmt = select(WorkspaceProjectModel.project_id).where(
                WorkspaceProjectModel.workspace_id == UUID(workspace_id)
            )
            
            result = db.execute(stmt)
            return [row[0] for row in result.all()]
```

## 4. 实施步骤

### 4.1 阶段 1: 数据库扩展（1-2 天）

1. 创建 Workspace 相关表
2. 创建数据库迁移脚本
3. 添加索引和约束

### 4.2 阶段 2: 代理层实现（3-5 天）

1. 实现 `LabelStudioProxy` 类
2. 实现元数据编码/解码
3. 实现权限验证
4. 添加审计日志

### 4.3 阶段 3: Workspace Service（2-3 天）

1. 实现 `WorkspaceService` 类
2. 实现 CRUD 操作
3. 实现成员管理
4. 实现项目关联

### 4.4 阶段 4: API 端点（2-3 天）

1. 创建 Workspace API 端点
2. 修改现有 Label Studio API 端点使用代理
3. 添加权限中间件

### 4.5 阶段 5: 前端集成（3-5 天）

1. 创建 Workspace 选择器组件
2. 修改项目列表页面
3. 添加 Workspace 管理界面
4. 集成权限控制

### 4.6 阶段 6: 测试和优化（2-3 天）

1. 单元测试
2. 集成测试
3. 性能优化
4. 文档编写

**总计**: 13-21 天

## 5. 优势分析

### 5.1 最小干预
- ✅ Label Studio 源码零修改
- ✅ 使用标准 API 接口
- ✅ 元数据存储在标准字段中

### 5.2 可升级性
- ✅ Label Studio 可以随时升级
- ✅ 不依赖特定版本
- ✅ API 兼容性好

### 5.3 功能完整性
- ✅ 完整的 Workspace 功能
- ✅ 细粒度权限控制
- ✅ 审计日志
- ✅ 数据隔离

### 5.4 性能
- ✅ 代理层开销小
- ✅ 可以缓存元数据
- ✅ 异步处理

## 6. 风险和缓解

### 6.1 风险 1: Label Studio API 变更
**缓解**: 
- 使用稳定的 API 端点
- 添加版本检测
- 实现降级策略

### 6.2 风险 2: 元数据编码冲突
**缓解**:
- 使用唯一标识符
- Base64 编码避免冲突
- 添加版本号

### 6.3 风险 3: 性能开销
**缓解**:
- 缓存 Workspace 信息
- 批量处理
- 异步操作

## 7. 未来扩展

### 7.1 企业版功能路线图

1. **Workspace** (当前)
   - 项目分组
   - 成员管理
   - 权限控制

2. **高级 RBAC** (下一步)
   - 自定义角色
   - 细粒度权限
   - 权限继承

3. **审计和合规** (后续)
   - 完整审计日志
   - 合规报告
   - 数据追踪

4. **高级协作** (未来)
   - 工作流
   - 审批流程
   - 通知系统

### 7.2 迁移到企业版

如果未来决定使用 Label Studio 企业版：

1. 导出 Workspace 数据
2. 映射到企业版 Workspace
3. 迁移权限配置
4. 切换代理层配置

**迁移时间**: 预计 1-2 天

## 8. 总结

这个方案通过**外部代理层 + 元数据注入**的方式，在不修改 Label Studio 源码的情况下，实现了企业版 Workspace 功能。

**核心优势**:
- 零侵入性
- 完全可升级
- 功能完整
- 性能优秀

**适用场景**:
- 需要企业功能但预算有限
- 需要保持开源版可升级性
- 需要自定义企业功能
- 需要与现有系统深度集成

---

**下一步**: 开始实施阶段 1 - 数据库扩展
