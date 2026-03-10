# 设计文档：数据生命周期管理平台（数据闭环）

**版本**: 2.0  
**创建日期**: 2026-03-10  
**更新日期**: 2026-03-10  
**状态**: 草稿

---

## 1. 系统架构

### 1.1 数据闭环整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        数据生命周期闭环架构                                │
└─────────────────────────────────────────────────────────────────────────┘

数据源层                统一操作平台              数据消费层
┌──────────────┐      ┌──────────────┐        ┌──────────────┐
│ 数据结构化    │──┐   │              │        │              │
│ 数据增强      │──┼──→│  数据流转    │←──查询─│  AI助手      │
│ 数据源同步    │──┘   │  (CRUD)      │        │  (技能配置)  │
│ 标注任务(完成)│──┐   │              │        └──────────────┘
│ AI助手处理    │──┼──→│  • 临时存储   │
│ 手动创建      │──┘   │  • 样本库     │
└──────────────┘      │  • 待标注     │
                      └──────┬───────┘
                             │
                        创建标注任务
                             ↓
                      ┌──────────────┐
                      │  标注管理    │
                      │  (Annotation)│
                      └──────────────┘

数据操作：转存(TRANSFER) 增(CREATE) 删(DELETE) 改(UPDATE) 查(READ) 
         合并(MERGE) 拆分(SPLIT)
```

### 1.2 核心设计原则

1. **数据闭环**: 数据可在各环节流转并形成完整循环
2. **统一接口**: 所有数据操作使用统一的 API
3. **权限优先**: 所有操作前先检查权限（扩展支持CRUD）
4. **审批可选**: 根据角色和操作类型决定是否需要审批
5. **技能配置**: AI助手基于技能配置访问数据
6. **国际化完整**: 所有用户可见文本支持中英文
7. **向后兼容**: 旧接口保持 3 个月兼容期
8. **可追溯性**: 所有数据操作可追溯完整路径


---

## 2. 数据模型设计

### 2.1 转存请求模型（扩展）

```python
from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DataTransferRequest(BaseModel):
    """统一转存请求模型（扩展支持新数据源）"""
    source_type: Literal[
        "structuring",    # 数据结构化
        "augmentation",   # 数据增强
        "sync",          # 数据源同步
        "annotation",    # 标注任务完成（新增）
        "ai_assistant",  # AI助手处理（新增）
        "manual"         # 手动创建（新增）
    ]
    source_id: str = Field(..., min_length=1)
    target_state: Literal["temp_stored", "in_sample_library", "annotation_pending"]
    data_attributes: "DataAttributes"
    records: List["TransferRecord"]
    request_approval: bool = False  # 是否主动请求审批

class DataAttributes(BaseModel):
    """数据属性配置"""
    category: str = Field(..., min_length=1, max_length=50)
    tags: List[str] = Field(default_factory=list, max_items=10)
    quality_score: float = Field(default=0.8, ge=0.0, le=1.0)
    description: Optional[str] = Field(None, max_length=500)

class TransferRecord(BaseModel):
    """单条转存记录"""
    id: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
```

### 2.2 权限模型

```python
from enum import Enum

class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    DATA_MANAGER = "data_manager"
    DATA_ANALYST = "data_analyst"
    USER = "user"

class PermissionResult(BaseModel):
    """权限检查结果"""
    allowed: bool
    requires_approval: bool
    current_role: UserRole
    required_role: Optional[UserRole] = None
    reason: Optional[str] = None
```

### 2.3 AI技能配置模型（新增）

```python
class AISkillConfig(BaseModel):
    """AI助手技能配置"""
    skill_id: str = Field(..., description="技能唯一标识")
    skill_name: str = Field(..., description="技能名称")
    allowed_source_types: List[str] = Field(
        default_factory=list,
        description="允许访问的数据源类型"
    )
    allowed_target_states: List[str] = Field(
        default_factory=list,
        description="允许访问的目标状态"
    )
    allowed_categories: List[str] = Field(
        default_factory=list,
        description="允许访问的数据分类"
    )
    read_only: bool = Field(
        default=True,
        description="是否只读（AI助手默认只读）"
    )
    max_records_per_query: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="单次查询最大记录数"
    )
```

### 2.4 数据操作请求模型（新增）

```python
class DataRecordCreateRequest(BaseModel):
    """创建数据记录请求"""
    source_type: Literal["manual", "ai_assistant"]
    target_state: str
    data_attributes: DataAttributes
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class DataRecordUpdateRequest(BaseModel):
    """更新数据记录请求"""
    data_attributes: Optional[DataAttributes] = None
    content: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DataMergeRequest(BaseModel):
    """数据合并请求"""
    record_ids: List[str] = Field(..., min_items=2, max_items=100)
    merge_strategy: Dict[str, str] = Field(
        ...,
        description="合并策略: {field: 'concat'|'first'|'last'|'max'|'min'}"
    )
    target_state: str
    data_attributes: DataAttributes

class DataSplitRequest(BaseModel):
    """数据拆分请求"""
    split_rules: List["SplitRule"] = Field(..., min_items=1)

class SplitRule(BaseModel):
    """拆分规则"""
    condition: str = Field(..., description="拆分条件表达式")
    target_state: str
    data_attributes: Optional[DataAttributes] = None
```


### 2.3 审批模型

```python
from datetime import datetime

class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ApprovalRequest(BaseModel):
    """审批请求"""
    id: str
    transfer_request: DataTransferRequest
    requester_id: str
    requester_role: UserRole
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime
    expires_at: datetime  # 默认 7 天后
    approver_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    comment: Optional[str] = None
```

---

## 3. 权限控制设计

### 3.1 权限矩阵实现

```python
class PermissionService:
    """权限服务"""
    
    # 权限矩阵配置
    PERMISSION_MATRIX = {
        UserRole.ADMIN: {
            "temp_stored": {"allowed": True, "requires_approval": False},
            "in_sample_library": {"allowed": True, "requires_approval": False},
            "annotation_pending": {"allowed": True, "requires_approval": False},
            "batch_transfer": {"allowed": True, "requires_approval": False},
            "cross_project": {"allowed": True, "requires_approval": False},
        },
        UserRole.DATA_MANAGER: {
            "temp_stored": {"allowed": True, "requires_approval": False},
            "in_sample_library": {"allowed": True, "requires_approval": False},
            "annotation_pending": {"allowed": True, "requires_approval": False},
            "batch_transfer": {"allowed": True, "requires_approval": False},
            "cross_project": {"allowed": False, "requires_approval": False},
        },
        UserRole.DATA_ANALYST: {
            "temp_stored": {"allowed": True, "requires_approval": False},
            "in_sample_library": {"allowed": True, "requires_approval": True},
            "annotation_pending": {"allowed": True, "requires_approval": True},
            "batch_transfer": {"allowed": False, "requires_approval": False},
            "cross_project": {"allowed": False, "requires_approval": False},
        },
        UserRole.USER: {
            "temp_stored": {"allowed": True, "requires_approval": False},
            "in_sample_library": {"allowed": True, "requires_approval": True},
            "annotation_pending": {"allowed": True, "requires_approval": True},
            "batch_transfer": {"allowed": False, "requires_approval": False},
            "cross_project": {"allowed": False, "requires_approval": False},
        },
    }


    # CRUD操作权限矩阵（新增）
    CRUD_PERMISSION_MATRIX = {
        UserRole.ADMIN: {
            "create": {"allowed": True, "requires_approval": False},
            "read": {"allowed": True, "requires_approval": False},
            "update": {"allowed": True, "requires_approval": False},
            "delete": {"allowed": True, "requires_approval": False},
            "merge": {"allowed": True, "requires_approval": False},
            "split": {"allowed": True, "requires_approval": False},
        },
        UserRole.DATA_MANAGER: {
            "create": {"allowed": True, "requires_approval": False},
            "read": {"allowed": True, "requires_approval": False},
            "update": {"allowed": True, "requires_approval": False},
            "delete": {"allowed": True, "requires_approval": True},  # 删除需审批
            "merge": {"allowed": True, "requires_approval": False},
            "split": {"allowed": True, "requires_approval": False},
        },
        UserRole.DATA_ANALYST: {
            "create": {"allowed": True, "requires_approval": False},
            "read": {"allowed": True, "requires_approval": False},
            "update": {"allowed": True, "requires_approval": True},  # 更新需审批
            "delete": {"allowed": False, "requires_approval": False},
            "merge": {"allowed": False, "requires_approval": False},
            "split": {"allowed": False, "requires_approval": False},
        },
        UserRole.USER: {
            "create": {"allowed": True, "requires_approval": True},  # 创建需审批
            "read": {"allowed": True, "requires_approval": False},
            "update": {"allowed": False, "requires_approval": False},
            "delete": {"allowed": False, "requires_approval": False},
            "merge": {"allowed": False, "requires_approval": False},
            "split": {"allowed": False, "requires_approval": False},
        },
    }


    def check_permission(
        self,
        user_role: UserRole,
        target_state: str,
        record_count: int = 1,
        is_cross_project: bool = False
    ) -> PermissionResult:
        """检查用户权限"""
        # 检查批量转存权限
        if record_count > 1000:
            operation = "batch_transfer"
        elif is_cross_project:
            operation = "cross_project"
        else:
            operation = target_state
        
        permission = self.PERMISSION_MATRIX.get(user_role, {}).get(operation)
        
        if not permission:
            return PermissionResult(
                allowed=False,
                requires_approval=False,
                current_role=user_role,
                reason="Operation not defined for this role"
            )
        
        return PermissionResult(
            allowed=permission["allowed"],
            requires_approval=permission["requires_approval"],
            current_role=user_role
        )
```

### 3.2 权限检查中间件

```python
from fastapi import Depends, HTTPException, status
from src.auth.dependencies import get_current_user

async def check_transfer_permission(
    request: DataTransferRequest,
    current_user: User = Depends(get_current_user)
) -> PermissionResult:
    """转存权限检查中间件"""
    permission_service = PermissionService()
    
    result = permission_service.check_permission(
        user_role=current_user.role,
        target_state=request.target_state,
        record_count=len(request.records)
    )
    
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "PERMISSION_DENIED",
                "message": "You don't have permission for this operation",
                "required_role": "data_manager",
                "current_role": result.current_role
            }
        )
    
    return result
```


---

## 4. 审批流程设计

### 4.1 审批服务

```python
class ApprovalService:
    """审批服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_approval_request(
        self,
        transfer_request: DataTransferRequest,
        requester: User
    ) -> ApprovalRequest:
        """创建审批请求"""
        approval = ApprovalRequest(
            id=str(uuid4()),
            transfer_request=transfer_request,
            requester_id=requester.id,
            requester_role=requester.role,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        # 保存到数据库
        self.db.add(approval)
        self.db.commit()
        
        # 发送通知给审批人
        await self._notify_approvers(approval)
        
        return approval
    
    async def _notify_approvers(self, approval: ApprovalRequest):
        """通知审批人"""
        # 查找有权限的审批人（data_manager 或 admin）
        approvers = self.db.query(User).filter(
            User.role.in_([UserRole.DATA_MANAGER, UserRole.ADMIN])
        ).all()
        
        for approver in approvers:
            # 发送站内消息
            await self._send_internal_message(approver, approval)
            # 发送邮件
            await self._send_email_notification(approver, approval)
    
    async def approve_request(
        self,
        approval_id: str,
        approver: User,
        approved: bool,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """审批请求"""
        approval = self.db.query(ApprovalRequest).filter_by(id=approval_id).first()
        
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found")
        
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval request already {approval.status}")
        
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        approval.approver_id = approver.id
        approval.approved_at = datetime.utcnow()
        approval.comment = comment
        
        self.db.commit()
        
        # 通知申请人
        await self._notify_requester(approval)
        
        # 如果批准，执行转存
        if approved:
            await self._execute_transfer(approval.transfer_request)
        
        return approval
```


---

## 5. 统一转存服务设计

### 5.1 转存服务核心逻辑

```python
class DataTransferService:
    """统一数据转存服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.permission_service = PermissionService()
        self.approval_service = ApprovalService(db)
    
    async def transfer(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """执行数据转存"""
        # 1. 检查权限
        permission = self.permission_service.check_permission(
            user_role=current_user.role,
            target_state=request.target_state,
            record_count=len(request.records)
        )
        
        # 2. 如果需要审批
        if permission.requires_approval and not request.request_approval:
            approval = await self.approval_service.create_approval_request(
                transfer_request=request,
                requester=current_user
            )
            return {
                "success": True,
                "approval_required": True,
                "approval_id": approval.id,
                "message": "Transfer request submitted for approval",
                "estimated_approval_time": "2-3 business days"
            }
        
        # 3. 验证源数据
        await self._validate_source(request.source_type, request.source_id)
        
        # 4. 执行转存
        result = await self._execute_transfer(request, current_user)
        
        # 5. 记录审计日志
        await self._log_audit(request, current_user, result)
        
        return result


    async def _execute_transfer(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """执行实际的转存操作"""
        if request.target_state == "temp_stored":
            return await self._transfer_to_temp_data(request, current_user)
        elif request.target_state == "in_sample_library":
            return await self._transfer_to_sample_library(request, current_user)
        elif request.target_state == "annotation_pending":
            return await self._transfer_to_annotation_pending(request, current_user)
        else:
            raise ValueError(f"Unsupported target state: {request.target_state}")
    
    async def _transfer_to_temp_data(
        self,
        request: DataTransferRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """转存到临时数据"""
        lifecycle_ids = []
        
        for record in request.records:
            temp_data = TempDataModel(
                source_document_id=request.source_id,
                content=record.content,
                state="temp_stored",
                uploaded_by=current_user.id,
                metadata={
                    "source_type": request.source_type,
                    "source_id": request.source_id,
                    "category": request.data_attributes.category,
                    "tags": request.data_attributes.tags,
                    "quality_score": request.data_attributes.quality_score,
                    "description": request.data_attributes.description,
                    **(record.metadata or {})
                }
            )
            self.db.add(temp_data)
            self.db.flush()
            lifecycle_ids.append(str(temp_data.id))
        
        self.db.commit()
        
        return {
            "success": True,
            "transferred_count": len(lifecycle_ids),
            "lifecycle_ids": lifecycle_ids,
            "target_state": "temp_stored",
            "message": f"Successfully transferred {len(lifecycle_ids)} records",
            "navigation_url": "/data-lifecycle/temp-data"
        }
```


---

## 6. API 端点设计

### 6.1 统一转存接口

```python
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

router = APIRouter(prefix="/api/data-lifecycle", tags=["Data Transfer"])

@router.post("/transfer")
async def transfer_data(
    request: DataTransferRequest,
    current_user: User = Depends(get_current_user),
    accept_language: Optional[str] = Header(None)
):
    """统一数据转存接口"""
    try:
        service = DataTransferService(db=get_db())
        result = await service.transfer(request, current_user)
        
        # 国际化响应消息
        if accept_language and accept_language.startswith("zh"):
            result["message"] = translate_zh(result["message"])
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-transfer")
async def batch_transfer_data(
    requests: List[DataTransferRequest],
    current_user: User = Depends(get_current_user)
):
    """批量转存接口"""
    # 检查批量转存权限
    if current_user.role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
        raise HTTPException(
            status_code=403,
            detail="Batch transfer requires data_manager or admin role"
        )
    
    service = DataTransferService(db=get_db())
    results = []
    
    for req in requests:
        try:
            result = await service.transfer(req, current_user)
            results.append({"success": True, **result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {
        "total_transfers": len(requests),
        "successful_transfers": sum(1 for r in results if r["success"]),
        "failed_transfers": sum(1 for r in results if not r["success"]),
        "results": results
    }
```


### 6.2 审批接口

```python
@router.get("/approvals")
async def list_approvals(
    status: Optional[ApprovalStatus] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user)
):
    """查询审批列表"""
    query = db.query(ApprovalRequest)
    
    # 普通用户只能看自己的审批
    if current_user.role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
        query = query.filter(ApprovalRequest.requester_id == current_user.id)
    
    if status:
        query = query.filter(ApprovalRequest.status == status)
    
    total = query.count()
    approvals = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": approvals,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.post("/approvals/{approval_id}/approve")
async def approve_transfer(
    approval_id: str,
    approved: bool,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """审批转存请求"""
    # 检查审批权限
    if current_user.role not in [UserRole.ADMIN, UserRole.DATA_MANAGER]:
        raise HTTPException(
            status_code=403,
            detail="Only admin or data_manager can approve requests"
        )
    
    service = ApprovalService(db=get_db())
    result = await service.approve_request(
        approval_id=approval_id,
        approver=current_user,
        approved=approved,
        comment=comment
    )
    
    return {"success": True, "approval": result}

@router.get("/permissions/check")
async def check_permissions(
    operation: str,
    current_user: User = Depends(get_current_user)
):
    """检查用户权限"""
    service = PermissionService()
    result = service.check_permission(
        user_role=current_user.role,
        target_state=operation
    )
    
    return {
        "has_permission": result.allowed,
        "requires_approval": result.requires_approval,
        "role": result.current_role
    }
```


---

## 7. 前端组件设计

### 7.1 转存按钮组件

**文件**: `frontend/src/components/DataLifecycle/Transfer/TransferButton.tsx`

```tsx
import React from 'react';
import { Button } from 'antd';
import { useTranslation } from 'react-i18next';
import { TransferModal } from './TransferModal';

interface TransferButtonProps {
  sourceType: 'structuring' | 'augmentation' | 'sync';
  sourceId: string;
  records: any[];
  onSuccess?: (result: any) => void;
  disabled?: boolean;
}

export const TransferButton: React.FC<TransferButtonProps> = ({
  sourceType,
  sourceId,
  records,
  onSuccess,
  disabled
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [modalVisible, setModalVisible] = React.useState(false);

  return (
    <>
      <Button
        type="primary"
        onClick={() => setModalVisible(true)}
        disabled={disabled}
      >
        {t('transfer.button')}
      </Button>
      
      <TransferModal
        visible={modalVisible}
        sourceType={sourceType}
        sourceId={sourceId}
        records={records}
        onClose={() => setModalVisible(false)}
        onSuccess={(result) => {
          setModalVisible(false);
          onSuccess?.(result);
        }}
      />
    </>
  );
};
```

### 7.2 转存配置弹窗

**文件**: `frontend/src/components/DataLifecycle/Transfer/TransferModal.tsx`

```tsx
import React from 'react';
import { Modal, Form, Select, Input, Slider, Tag, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { transferDataAPI, checkPermissionAPI } from '@/api/dataLifecycle';

export const TransferModal: React.FC<TransferModalProps> = ({
  visible,
  sourceType,
  sourceId,
  records,
  onClose,
  onSuccess
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const [loading, setLoading] = React.useState(false);
  const [permissions, setPermissions] = React.useState<any>(null);

  // 检查权限
  React.useEffect(() => {
    if (visible) {
      checkPermissionAPI().then(setPermissions);
    }
  }, [visible]);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const values = await form.validateFields();
      
      const result = await transferDataAPI({
        source_type: sourceType,
        source_id: sourceId,
        target_state: values.targetState,
        data_attributes: {
          category: values.category,
          tags: values.tags || [],
          quality_score: values.qualityScore,
          description: values.description
        },
        records
      });

      if (result.approval_required) {
        message.info(t('transfer.approvalRequired'));
      } else {
        message.success(t('transfer.successMessage', {
          count: result.transferred_count,
          state: t(`transfer.states.${result.target_state}`)
        }));
      }
      
      onSuccess(result);
    } catch (error) {
      message.error(t('transfer.errorMessage', { error: error.message }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={t('transfer.modalTitle')}
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={loading}
      okText={t('transfer.confirm')}
      cancelText={t('transfer.cancel')}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Form.Item label={t('transfer.targetState')} name="targetState" required>
          <Select placeholder={t('transfer.targetStateRequired')}>
            <Select.Option value="temp_stored">
              {t('transfer.states.temp_stored')}
            </Select.Option>
            <Select.Option 
              value="in_sample_library"
              disabled={permissions?.requires_approval}
            >
              {t('transfer.states.in_sample_library')}
              {permissions?.requires_approval && ' (需审批)'}
            </Select.Option>
            <Select.Option 
              value="annotation_pending"
              disabled={permissions?.requires_approval}
            >
              {t('transfer.states.annotation_pending')}
              {permissions?.requires_approval && ' (需审批)'}
            </Select.Option>
          </Select>
        </Form.Item>

        <Form.Item 
          label={t('transfer.category')} 
          name="category" 
          required
        >
          <Input placeholder={t('transfer.categoryPlaceholder')} />
        </Form.Item>

        <Form.Item label={t('transfer.tags')} name="tags">
          <Select mode="tags" placeholder={t('transfer.tagsPlaceholder')} />
        </Form.Item>

        <Form.Item 
          label={t('transfer.qualityScore')} 
          name="qualityScore"
          initialValue={0.8}
        >
          <Slider min={0} max={1} step={0.05} />
        </Form.Item>

        <Form.Item label={t('transfer.description')} name="description">
          <Input.TextArea 
            rows={3} 
            placeholder={t('transfer.descriptionPlaceholder')} 
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
```


---

## 8. 国际化设计

### 8.1 翻译文件结构

**中文翻译**: `frontend/src/locales/zh/dataLifecycle.json`

```json
{
  "transfer": {
    "button": "转存到数据流转",
    "modalTitle": "转存到数据流转系统",
    "dataSummary": "数据摘要",
    "source": "来源",
    "recordCount": "记录数",
    "targetState": "目标状态",
    "targetStateRequired": "请选择目标状态",
    "category": "分类",
    "categoryRequired": "请输入分类",
    "categoryPlaceholder": "例如: 商品信息",
    "tags": "标签",
    "tagsPlaceholder": "添加标签",
    "qualityScore": "质量评分",
    "description": "描述",
    "descriptionPlaceholder": "输入数据描述（可选）",
    "cancel": "取消",
    "confirm": "确认转存",
    "transferring": "正在转存...",
    "successMessage": "已成功将 {{count}} 条记录转存到{{state}}",
    "errorMessage": "转存失败: {{error}}",
    "approvalRequired": "转存请求已提交，等待审批",
    "permissionDenied": "您没有权限执行此操作",
    "states": {
      "temp_stored": "临时存储",
      "in_sample_library": "样本库",
      "annotation_pending": "待标注"
    }
  }
}
```

**英文翻译**: `frontend/src/locales/en/dataLifecycle.json`

```json
{
  "transfer": {
    "button": "Transfer to Data Flow",
    "modalTitle": "Transfer to Data Flow System",
    "dataSummary": "Data Summary",
    "source": "Source",
    "recordCount": "Record Count",
    "targetState": "Target State",
    "targetStateRequired": "Please select target state",
    "category": "Category",
    "categoryRequired": "Please enter category",
    "categoryPlaceholder": "e.g., Product Information",
    "tags": "Tags",
    "tagsPlaceholder": "Add tag",
    "qualityScore": "Quality Score",
    "description": "Description",
    "descriptionPlaceholder": "Enter data description (optional)",
    "cancel": "Cancel",
    "confirm": "Confirm Transfer",
    "transferring": "Transferring...",
    "successMessage": "Successfully transferred {{count}} records to {{state}}",
    "errorMessage": "Transfer failed: {{error}}",
    "approvalRequired": "Transfer request submitted for approval",
    "permissionDenied": "You don't have permission for this operation",
    "states": {
      "temp_stored": "Temporary Storage",
      "in_sample_library": "Sample Library",
      "annotation_pending": "Pending Annotation"
    }
  }
}
```

### 8.2 后端国际化

```python
# src/i18n/transfer_messages.py

TRANSFER_MESSAGES = {
    "zh": {
        "success": "成功转存 {count} 条记录到{state}",
        "approval_required": "转存请求已提交，等待审批",
        "permission_denied": "您没有权限执行此操作",
        "invalid_source": "源数据不存在或未完成",
        "states": {
            "temp_stored": "临时存储",
            "in_sample_library": "样本库",
            "annotation_pending": "待标注"
        }
    },
    "en": {
        "success": "Successfully transferred {count} records to {state}",
        "approval_required": "Transfer request submitted for approval",
        "permission_denied": "You don't have permission for this operation",
        "invalid_source": "Source data not found or incomplete",
        "states": {
            "temp_stored": "temporary storage",
            "in_sample_library": "sample library",
            "annotation_pending": "pending annotation"
        }
    }
}

def get_message(key: str, lang: str = "zh", **kwargs) -> str:
    """获取国际化消息"""
    messages = TRANSFER_MESSAGES.get(lang, TRANSFER_MESSAGES["zh"])
    template = messages.get(key, key)
    return template.format(**kwargs)
```


---

## 9. 旧接口兼容设计

### 9.1 废弃标记

```python
# src/api/enhancement_api.py

@router.post(
    "/{job_id}/add-to-library",
    response_model=AddToLibraryResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,  # 标记为废弃
    description="DEPRECATED: Use POST /api/data-lifecycle/transfer instead"
)
async def add_to_library(
    job_id: str,
    request: AddToLibraryRequest,
    service: EnhancementService = Depends(get_enhancement_service),
):
    """
    Add enhanced data to the sample library.
    
    DEPRECATED: This endpoint will be removed after 2026-06-10.
    Please use POST /api/data-lifecycle/transfer instead.
    """
    # 内部调用新接口
    transfer_service = DataTransferService(db=get_db())
    
    # 获取增强数据
    enhanced_data = service.get_enhanced_data(job_id)
    
    # 转换为新接口格式
    transfer_request = DataTransferRequest(
        source_type="augmentation",
        source_id=job_id,
        target_state="in_sample_library",
        data_attributes=DataAttributes(
            category="enhanced_data",
            tags=["augmentation"],
            quality_score=enhanced_data.quality_overall
        ),
        records=[{
            "id": enhanced_data.id,
            "content": enhanced_data.content,
            "metadata": enhanced_data.metadata
        }]
    )
    
    # 调用新接口
    result = await transfer_service.transfer(
        transfer_request,
        current_user=get_current_user()
    )
    
    # 转换为旧格式响应
    return AddToLibraryResponse(
        id=result["lifecycle_ids"][0],
        data_id=enhanced_data.id,
        content=enhanced_data.content,
        category="enhanced_data",
        quality_overall=enhanced_data.quality_overall,
        # ... 其他字段
    )
```

### 9.2 迁移指南

在 API 响应头中添加迁移提示：

```python
@router.post("/{job_id}/add-to-library")
async def add_to_library(...):
    response = await handle_request(...)
    
    # 添加废弃警告头
    response.headers["X-Deprecated"] = "true"
    response.headers["X-Deprecated-Since"] = "2026-03-10"
    response.headers["X-Deprecated-Removal"] = "2026-06-10"
    response.headers["X-Deprecated-Replacement"] = "POST /api/data-lifecycle/transfer"
    
    return response
```


---

## 10. 数据库设计

### 10.1 审批表

```sql
CREATE TABLE approval_requests (
    id VARCHAR(36) PRIMARY KEY,
    transfer_request JSONB NOT NULL,
    requester_id VARCHAR(36) NOT NULL,
    requester_role VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    approver_id VARCHAR(36),
    approved_at TIMESTAMP,
    comment TEXT,
    INDEX idx_status (status),
    INDEX idx_requester (requester_id),
    INDEX idx_created_at (created_at)
);
```

### 10.2 审计日志表

```sql
CREATE TABLE transfer_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    user_role VARCHAR(20) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_id VARCHAR(36) NOT NULL,
    target_state VARCHAR(30) NOT NULL,
    record_count INT NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_source (source_type, source_id),
    INDEX idx_created_at (created_at)
);
```

---

## 11. 安全设计

### 11.1 防止权限绕过

```python
class SecurityMiddleware:
    """安全中间件"""
    
    async def verify_no_privilege_escalation(
        self,
        request: DataTransferRequest,
        current_user: User
    ):
        """防止权限提升攻击"""
        # 检查请求中是否包含试图绕过权限的字段
        if hasattr(request, 'force_approve'):
            raise SecurityException("Privilege escalation attempt detected")
        
        # 验证用户角色未被篡改
        if request.get('user_role') != current_user.role:
            raise SecurityException("Role tampering detected")
```

### 11.2 审计日志

```python
async def log_transfer_operation(
    user: User,
    request: DataTransferRequest,
    result: Dict[str, Any],
    success: bool,
    error: Optional[str] = None
):
    """记录转存操作审计日志"""
    log = TransferAuditLog(
        id=str(uuid4()),
        user_id=user.id,
        user_role=user.role,
        operation="transfer",
        source_type=request.source_type,
        source_id=request.source_id,
        target_state=request.target_state,
        record_count=len(request.records),
        success=success,
        error_message=error,
        created_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
```

---

## 12. 性能优化

### 12.1 批量插入优化

```python
async def _transfer_to_temp_data_batch(
    self,
    request: DataTransferRequest,
    current_user: User
) -> Dict[str, Any]:
    """批量转存优化"""
    # 使用批量插入而非逐条插入
    temp_data_list = [
        TempDataModel(
            source_document_id=request.source_id,
            content=record.content,
            state="temp_stored",
            uploaded_by=current_user.id,
            metadata={...}
        )
        for record in request.records
    ]
    
    # 批量插入
    self.db.bulk_save_objects(temp_data_list)
    self.db.commit()
    
    # 批量获取 ID
    lifecycle_ids = [str(obj.id) for obj in temp_data_list]
    
    return {...}
```

### 12.2 权限检查缓存

```python
from functools import lru_cache

class PermissionService:
    @lru_cache(maxsize=1000)
    def check_permission_cached(
        self,
        user_role: str,
        target_state: str
    ) -> PermissionResult:
        """缓存权限检查结果"""
        return self.check_permission(
            UserRole(user_role),
            target_state
        )
```

---

## 13. 测试策略

### 13.1 单元测试

- 权限检查逻辑测试
- 审批流程测试
- 数据转存逻辑测试
- 国际化消息测试

### 13.2 集成测试

- 完整转存流程测试
- 审批流程端到端测试
- 旧接口兼容性测试

### 13.3 性能测试

- 1000 条记录转存性能测试
- 10000 条记录批量转存测试
- 并发转存压力测试

---

## 14. 部署计划

### 14.1 阶段 1：基础功能（Week 1-2）
- 统一转存接口实现
- 基本权限控制
- 前端转存按钮和弹窗

### 14.2 阶段 2：审批流程（Week 3）
- 审批工作流实现
- 审批通知系统
- 审批管理界面

### 14.3 阶段 3：国际化和优化（Week 4）
- 完整国际化覆盖
- 性能优化
- 旧接口迁移

### 14.4 阶段 4：测试和上线（Week 5）
- 完整测试
- 文档编写
- 生产环境部署


---

## 15. 数据CRUD服务设计（新增）

### 15.1 数据记录服务

```python
class DataRecordService:
    """数据记录CRUD服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.permission_service = PermissionService()
    
    async def create_record(
        self,
        request: DataRecordCreateRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """创建数据记录"""
        # 检查权限
        permission = self.permission_service.check_crud_permission(
            user_role=current_user.role,
            operation="create"
        )
        
        if not permission.allowed:
            raise PermissionDenied("No permission to create records")
        
        if permission.requires_approval:
            return await self._create_approval_request(request, current_user)
        
        # 创建记录
        record = DataLifecycleModel(
            source_type=request.source_type,
            target_state=request.target_state,
            content=request.content,
            metadata=request.metadata,
            created_by=current_user.id,
            **request.data_attributes.dict()
        )
        
        self.db.add(record)
        self.db.commit()
        
        return {
            "success": True,
            "record_id": str(record.id),
            "message": "Record created successfully"
        }
    
    async def update_record(
        self,
        record_id: str,
        request: DataRecordUpdateRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """更新数据记录"""
        # 检查权限
        permission = self.permission_service.check_crud_permission(
            user_role=current_user.role,
            operation="update"
        )
        
        if not permission.allowed:
            raise PermissionDenied("No permission to update records")
        
        # 获取记录
        record = self.db.query(DataLifecycleModel).filter_by(id=record_id).first()
        if not record:
            raise RecordNotFound(f"Record {record_id} not found")
        
        if permission.requires_approval:
            return await self._create_update_approval(record_id, request, current_user)
        
        # 更新记录
        if request.data_attributes:
            for key, value in request.data_attributes.dict(exclude_none=True).items():
                setattr(record, key, value)
        
        if request.content:
            record.content = request.content
        
        if request.metadata:
            record.metadata = {**record.metadata, **request.metadata}
        
        record.updated_by = current_user.id
        record.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "Record updated successfully"
        }
    
    async def delete_record(
        self,
        record_id: str,
        current_user: User
    ) -> Dict[str, Any]:
        """删除数据记录"""
        # 检查权限
        permission = self.permission_service.check_crud_permission(
            user_role=current_user.role,
            operation="delete"
        )
        
        if not permission.allowed:
            raise PermissionDenied("No permission to delete records")
        
        if permission.requires_approval:
            return await self._create_delete_approval(record_id, current_user)
        
        # 软删除
        record = self.db.query(DataLifecycleModel).filter_by(id=record_id).first()
        if not record:
            raise RecordNotFound(f"Record {record_id} not found")
        
        record.deleted = True
        record.deleted_by = current_user.id
        record.deleted_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "Record deleted successfully"
        }
    
    async def query_records(
        self,
        filters: Dict[str, Any],
        current_user: User,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """查询数据记录"""
        # 检查权限
        permission = self.permission_service.check_crud_permission(
            user_role=current_user.role,
            operation="read"
        )
        
        if not permission.allowed:
            raise PermissionDenied("No permission to read records")
        
        # 构建查询
        query = self.db.query(DataLifecycleModel).filter_by(deleted=False)
        
        # 应用过滤条件
        if filters.get("source_type"):
            query = query.filter_by(source_type=filters["source_type"])
        
        if filters.get("target_state"):
            query = query.filter_by(target_state=filters["target_state"])
        
        if filters.get("category"):
            query = query.filter_by(category=filters["category"])
        
        if filters.get("tags"):
            # 标签过滤（JSONB数组包含）
            for tag in filters["tags"]:
                query = query.filter(DataLifecycleModel.tags.contains([tag]))
        
        # 分页
        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return {
            "success": True,
            "records": [record.to_dict() for record in records],
            "total": total,
            "page": page,
            "page_size": page_size
        }
```

---

## 16. 数据合并与拆分设计（新增）

### 16.1 数据合并服务

```python
class DataMergeService:
    """数据合并服务"""
    
    MERGE_STRATEGIES = {
        "concat": lambda values: " ".join(str(v) for v in values if v),
        "first": lambda values: values[0] if values else None,
        "last": lambda values: values[-1] if values else None,
        "max": lambda values: max(values) if values else None,
        "min": lambda values: min(values) if values else None,
        "sum": lambda values: sum(values) if all(isinstance(v, (int, float)) for v in values) else None,
        "avg": lambda values: sum(values) / len(values) if values and all(isinstance(v, (int, float)) for v in values) else None,
    }
    
    async def merge_records(
        self,
        request: DataMergeRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """合并多条数据记录"""
        # 检查权限
        permission = self.permission_service.check_crud_permission(
            user_role=current_user.role,
            operation="merge"
        )
        
        if not permission.allowed:
            raise PermissionDenied("No permission to merge records")
        
        # 获取要合并的记录
        records = self.db.query(DataLifecycleModel).filter(
            DataLifecycleModel.id.in_(request.record_ids)
        ).all()
        
        if len(records) != len(request.record_ids):
            raise RecordNotFound("Some records not found")
        
        # 执行合并
        merged_content = {}
        
        for field, strategy in request.merge_strategy.items():
            values = [record.content.get(field) for record in records]
            merge_func = self.MERGE_STRATEGIES.get(strategy)
            
            if merge_func:
                merged_content[field] = merge_func(values)
            else:
                raise ValueError(f"Unknown merge strategy: {strategy}")
        
        # 创建合并后的新记录
        merged_record = DataLifecycleModel(
            source_type="manual",
            target_state=request.target_state,
            content=merged_content,
            metadata={
                "merged_from": request.record_ids,
                "merge_strategy": request.merge_strategy,
                "merged_at": datetime.utcnow().isoformat()
            },
            created_by=current_user.id,
            **request.data_attributes.dict()
        )
        
        self.db.add(merged_record)
        self.db.commit()
        
        return {
            "success": True,
            "merged_record_id": str(merged_record.id),
            "source_record_ids": request.record_ids,
            "message": f"Successfully merged {len(records)} records"
        }
```

### 16.2 数据拆分服务

```python
class DataSplitService:
    """数据拆分服务"""
    
    async def split_record(
        self,
        record_id: str,
        request: DataSplitRequest,
        current_user: User
    ) -> Dict[str, Any]:
        """拆分单条数据记录"""
        # 检查权限
        permission = self.permission_service.check_crud_permission(
            user_role=current_user.role,
            operation="split"
        )
        
        if not permission.allowed:
            raise PermissionDenied("No permission to split records")
        
        # 获取原始记录
        original_record = self.db.query(DataLifecycleModel).filter_by(id=record_id).first()
        if not original_record:
            raise RecordNotFound(f"Record {record_id} not found")
        
        # 执行拆分
        split_records = []
        
        for rule in request.split_rules:
            # 评估拆分条件
            if self._evaluate_condition(original_record.content, rule.condition):
                # 创建拆分后的记录
                split_record = DataLifecycleModel(
                    source_type="manual",
                    target_state=rule.target_state,
                    content=original_record.content.copy(),
                    metadata={
                        "split_from": record_id,
                        "split_condition": rule.condition,
                        "split_at": datetime.utcnow().isoformat()
                    },
                    created_by=current_user.id,
                    **(rule.data_attributes.dict() if rule.data_attributes else {})
                )
                
                self.db.add(split_record)
                split_records.append(split_record)
        
        self.db.commit()
        
        return {
            "success": True,
            "original_record_id": record_id,
            "split_record_ids": [str(r.id) for r in split_records],
            "split_count": len(split_records),
            "message": f"Successfully split into {len(split_records)} records"
        }
    
    def _evaluate_condition(self, content: Dict[str, Any], condition: str) -> bool:
        """评估拆分条件"""
        # 简单的条件评估（实际应使用更安全的表达式解析器）
        try:
            # 创建安全的评估环境
            safe_dict = {"content": content}
            return eval(condition, {"__builtins__": {}}, safe_dict)
        except Exception:
            return False
```

---

## 17. AI助手数据访问设计（新增）

### 17.1 AI技能配置服务

```python
class AISkillConfigService:
    """AI技能配置服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_skill_config(self, skill_id: str) -> AISkillConfig:
        """获取技能配置"""
        config = self.db.query(AISkillConfigModel).filter_by(skill_id=skill_id).first()
        
        if not config:
            raise SkillNotFound(f"Skill {skill_id} not found")
        
        return AISkillConfig(**config.to_dict())
    
    async def validate_skill_access(
        self,
        skill_id: str,
        query_params: Dict[str, Any]
    ) -> bool:
        """验证技能访问权限"""
        config = await self.get_skill_config(skill_id)
        
        # 检查数据源类型
        if query_params.get("source_type"):
            if query_params["source_type"] not in config.allowed_source_types:
                return False
        
        # 检查目标状态
        if query_params.get("target_state"):
            if query_params["target_state"] not in config.allowed_target_states:
                return False
        
        # 检查数据分类
        if query_params.get("category"):
            if config.allowed_categories and query_params["category"] not in config.allowed_categories:
                return False
        
        return True
```

### 17.2 AI查询服务

```python
class AIQueryService:
    """AI助手查询服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.skill_service = AISkillConfigService(db)
    
    async def query_for_ai(
        self,
        skill_id: str,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> Dict[str, Any]:
        """AI助手查询数据"""
        # 获取技能配置
        config = await self.skill_service.get_skill_config(skill_id)
        
        # 验证访问权限
        if not await self.skill_service.validate_skill_access(skill_id, filters):
            raise PermissionDenied(f"Skill {skill_id} does not have access to requested data")
        
        # 限制查询数量
        limit = min(limit, config.max_records_per_query)
        
        # 构建查询
        query = self.db.query(DataLifecycleModel).filter_by(deleted=False)
        
        # 应用技能配置的过滤条件
        if config.allowed_source_types:
            query = query.filter(DataLifecycleModel.source_type.in_(config.allowed_source_types))
        
        if config.allowed_target_states:
            query = query.filter(DataLifecycleModel.target_state.in_(config.allowed_target_states))
        
        # 应用查询参数
        if filters.get("source_type"):
            query = query.filter_by(source_type=filters["source_type"])
        
        if filters.get("target_state"):
            query = query.filter_by(target_state=filters["target_state"])
        
        if filters.get("category"):
            query = query.filter_by(category=filters["category"])
        
        # 执行查询
        records = query.limit(limit).all()
        
        # 记录访问日志
        await self._log_ai_access(skill_id, filters, len(records))
        
        return {
            "success": True,
            "skill_id": skill_id,
            "skill_name": config.skill_name,
            "records": [record.to_dict() for record in records],
            "total": len(records),
            "max_allowed": config.max_records_per_query
        }
    
    async def _log_ai_access(
        self,
        skill_id: str,
        filters: Dict[str, Any],
        record_count: int
    ):
        """记录AI访问日志"""
        log = AIAccessLog(
            skill_id=skill_id,
            filters=filters,
            record_count=record_count,
            accessed_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()
```

---

## 18. 数据闭环追溯设计（新增）

### 18.1 数据流转历史

```python
class DataFlowHistory:
    """数据流转历史追溯"""
    
    async def get_flow_path(self, record_id: str) -> List[Dict[str, Any]]:
        """获取数据完整流转路径"""
        path = []
        current_id = record_id
        
        while current_id:
            record = self.db.query(DataLifecycleModel).filter_by(id=current_id).first()
            
            if not record:
                break
            
            path.append({
                "record_id": current_id,
                "source_type": record.source_type,
                "target_state": record.target_state,
                "created_at": record.created_at.isoformat(),
                "created_by": record.created_by,
                "operation": self._get_operation_type(record)
            })
            
            # 查找父记录
            if record.metadata.get("merged_from"):
                # 合并操作：显示所有源记录
                for parent_id in record.metadata["merged_from"]:
                    parent_path = await self.get_flow_path(parent_id)
                    path.extend(parent_path)
                break
            elif record.metadata.get("split_from"):
                # 拆分操作：追溯到原始记录
                current_id = record.metadata["split_from"]
            elif record.metadata.get("annotation_task_id"):
                # 标注回流：追溯到标注前的数据
                current_id = record.metadata.get("original_record_id")
            else:
                break
        
        return path
    
    def _get_operation_type(self, record: DataLifecycleModel) -> str:
        """获取操作类型"""
        if record.metadata.get("merged_from"):
            return "MERGE"
        elif record.metadata.get("split_from"):
            return "SPLIT"
        elif record.metadata.get("annotation_task_id"):
            return "ANNOTATION_BACKFLOW"
        elif record.source_type == "ai_assistant":
            return "AI_PROCESSING"
        elif record.source_type == "manual":
            return "MANUAL_CREATE"
        else:
            return "TRANSFER"
```

---

## 19. 部署计划更新

### 19.1 阶段 1：基础功能（Week 1-2）
- 统一转存接口实现
- 基本权限控制
- 前端转存按钮和弹窗

### 19.2 阶段 2：审批流程（Week 3）
- 审批工作流实现
- 审批通知系统
- 审批管理界面

### 19.3 阶段 3：CRUD功能（Week 4）
- 数据CRUD API实现
- 数据管理界面
- 权限矩阵扩展

### 19.4 阶段 4：高级功能（Week 5）
- 数据合并/拆分功能
- AI助手查询接口
- 技能配置管理

### 19.5 阶段 5：数据闭环（Week 6）
- 标注数据回流
- 数据流转可视化
- 完整的操作历史追溯

### 19.6 阶段 6：国际化和优化（Week 7）
- 完整国际化覆盖
- 性能优化
- 旧接口迁移

### 19.7 阶段 7：测试和上线（Week 8）
- 完整测试
- 文档编写
- 生产环境部署
