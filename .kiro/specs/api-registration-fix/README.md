# API 注册修复 - Spec 概览

## 📋 Spec 状态

- **状态**: ✅ 完成，待执行
- **创建日期**: 2026-01-19
- **优先级**: P0 (紧急)
- **预计工时**: 16-20 小时

## 🎯 目标

修复 35个已实现但未注册的 API，重点解决 12个高优先级 API，确保前端页面能够正常访问后端服务。

## 📁 Spec 文件

| 文件 | 描述 | 状态 |
|------|------|------|
| [requirements.md](./requirements.md) | 需求文档 - 用户故事和验收标准 | ✅ 完成 |
| [design.md](./design.md) | 设计文档 - 架构和技术决策 | ✅ 完成 |
| [tasks.md](./tasks.md) | 任务清单 - 21个可执行任务 | ✅ 完成 |

## 🔥 高优先级 API (12个)

### License 模块 (3个)
- `/api/v1/license` - License 管理
- `/api/v1/license/usage` - 使用监控
- `/api/v1/license/activation` - 许可证激活

### Quality 子模块 (3个)
- `/api/v1/quality/rules` - 质量规则
- `/api/v1/quality/reports` - 质量报告
- `/api/v1/quality/workflow` - 质量工单

### Augmentation 模块 (1个)
- `/api/v1/augmentation` - 数据增强

### Security 子模块 (4个)
- `/api/v1/security/sessions` - 会话管理
- `/api/v1/security/sso` - SSO 配置
- `/api/v1/security/rbac` - RBAC 管理
- `/api/v1/security/data-permissions` - 数据权限

### Versioning 模块 (1个)
- `/api/v1/versioning` - 数据版本管理

## 🚀 快速开始

### 1. 阅读 Spec 文件

```bash
# 阅读需求文档
cat .kiro/specs/api-registration-fix/requirements.md

# 阅读设计文档
cat .kiro/specs/api-registration-fix/design.md

# 阅读任务清单
cat .kiro/specs/api-registration-fix/tasks.md
```

### 2. 开始实现

打开 `tasks.md` 文件，按照任务顺序执行：

```bash
# Phase 1: 准备工作
# Task 1: 创建 API 注册管理器
# Task 1.1: 实现 APIRegistrationManager 类
# ...
```

### 3. 验证实现

每完成一个任务，运行对应的验证命令：

```bash
# 验证 API 注册
curl http://localhost:8000/api/v1/license

# 验证前端页面
# 访问 http://localhost:5173/license

# 检查日志
docker logs superinsight-api | grep "API"
```

## 📊 任务分解

| Phase | 任务数 | 预计时长 | 描述 |
|-------|--------|----------|------|
| Phase 1 | 1 | 2-3h | 准备工作 - 创建注册管理器 |
| Phase 2 | 4 | 2-3h | License 模块注册 |
| Phase 3 | 4 | 2-3h | Quality 子模块注册 |
| Phase 4 | 2 | 1-1.5h | Augmentation 模块注册 |
| Phase 5 | 2 | 2-3h | Security 子模块注册 |
| Phase 6 | 2 | 1h | Versioning 模块注册 |
| Phase 7 | 4 | 3-4h | 系统级改进 |
| Phase 8 | 3 | 2-3h | 文档和部署 |
| **总计** | **21** | **16-20h** | |

## 🎨 核心设计

### API 注册管理器

```python
class APIRegistrationManager:
    """统一管理 API 路由注册"""
    
    def register_router(
        self,
        module_path: str,
        router_name: str = "router",
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        required: bool = False
    ) -> bool:
        """注册单个 API 路由"""
        pass
    
    def register_batch(
        self,
        routers: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """批量注册 API 路由"""
        pass
```

### 错误处理模式

```python
try:
    from src.api.module_name import router as module_router
    app.include_router(module_router, prefix="/api/v1/module", tags=["module"])
    logger.info(f"✅ Module API registered: /api/v1/module")
except ImportError as e:
    logger.warning(f"⚠️ Module API not available: {e}")
except Exception as e:
    logger.error(f"❌ Module API failed to load: {e}")
```

## ✅ 验收标准

### 功能验收
- [ ] 所有 12个高优先级 API 成功注册
- [ ] 所有前端页面无 404 错误
- [ ] 所有 API 端点可访问

### 质量验收
- [ ] 所有单元测试通过
- [ ] 代码通过类型检查
- [ ] 日志记录完整

### 性能验收
- [ ] 应用启动时间增加 < 2秒
- [ ] API 响应时间无显著变化

## 📚 相关文档

- [API 注册审计报告](../API_REGISTRATION_AUDIT_2026_01_19.md)
- [Doc-First 工作流](.kiro/steering/doc-first-workflow.md)
- [PIV 方法论](.kiro/steering/piv-methodology-integration.md)
- [Async/Sync 安全规范](.kiro/steering/async-sync-safety.md)

## 🔗 依赖关系

```
准备工作 → License 模块 → Quality 模块 → Augmentation 模块 → Security 模块 → Versioning 模块 → 系统改进 → 文档部署
```

## ⚠️ 风险提示

### 高风险任务
1. **License API 注册** - 可能存在依赖缺失
2. **Quality API 注册** - 可能与现有 quality.py 冲突
3. **Security API 注册** - 可能影响现有安全功能

### 缓解措施
- 使用 try-except 包装每个注册
- 详细的错误日志记录
- 逐步测试，发现问题立即回滚

## 📞 支持

如有问题，请参考：
1. [requirements.md](./requirements.md) - 了解需求背景
2. [design.md](./design.md) - 了解技术细节
3. [tasks.md](./tasks.md) - 了解具体任务

---

**准备好开始了吗？打开 `tasks.md` 开始第一个任务！** 🚀
