# 脚本工具目录说明

本目录包含 SuperInsight 项目的所有 Python 脚本和自动化工具。

## 📁 目录结构

```
脚本/
├── README.md                    # 本文件
├── 测试/                        # 单元测试和集成测试脚本
├── 演示/                        # 功能演示脚本
├── 诊断/                        # 系统诊断脚本
├── 验证/                        # 验证和性能测试脚本
└── 其他/                        # 其他工具脚本
```

## 📚 各目录说明

### 测试 (test_*.py)
- **用途**: 单元测试和集成测试
- **数量**: 80+ 个脚本
- **包含**:
  - API 端点测试
  - 前端路由测试
  - 数据库连接测试
  - 业务逻辑测试
  - 权限控制测试
  - 安全性测试
  - 集成测试

**常用脚本**:
- `test_api_simple.py` - 简单 API 测试
- `test_login_comprehensive.py` - 登录综合测试
- `test_business_logic.py` - 业务逻辑测试
- `test_multi_tenant_comprehensive.py` - 多租户测试
- `test_frontend_verification.py` - 前端验证

### 演示 (demo_*.py)
- **用途**: 功能演示和原型验证
- **数量**: 17 个脚本
- **包含**:
  - 评估系统演示
  - 审计系统演示
  - 数据脱敏演示
  - 监控系统演示
  - 告警系统演示
  - 质量改进演示
  - 系统集成演示

**常用脚本**:
- `demo_assessment_system.py` - 评估系统演示
- `demo_monitoring_system.py` - 监控系统演示
- `demo_label_studio_integration.py` - Label Studio 集成演示
- `demo_system_integration.py` - 系统集成演示

### 诊断 (debug_*.py, diagnose_*.py)
- **用途**: 系统诊断和问题排查
- **数量**: 5 个脚本
- **包含**:
  - 导入诊断
  - API 诊断
  - 角色模型诊断
  - 零泄露诊断

**常用脚本**:
- `diagnose_api.py` - API 诊断
- `debug_import.py` - 导入调试
- `diagnose_imports.py` - 导入诊断
- `debug_zero_leakage.py` - 零泄露调试

### 验证 (validate_*.py)
- **用途**: 性能验证和合规性检查
- **数量**: 5 个脚本
- **包含**:
  - 10ms 性能验证
  - 30s 合规性验证
  - 权限控制验证
  - 多租户验证
  - 实时安全验证

**常用脚本**:
- `validate_10ms_performance.py` - 10ms 性能验证
- `validate_compliance_performance_30s.py` - 30s 合规性验证
- `validate_fine_grained_permission_control.py` - 权限控制验证
- `validate_multi_tenant_implementation.py` - 多租户验证

### 其他 (其他 .py 脚本)
- **用途**: 工具和辅助脚本
- **数量**: 30+ 个脚本
- **包含**:
  - 数据库操作脚本
  - 用户管理脚本
  - 性能测试脚本
  - 集成测试脚本
  - 启动脚本

**常用脚本**:
- `main.py` - 主程序
- `create_test_db.py` - 创建测试数据库
- `create_test_users_for_login.py` - 创建测试用户
- `init_test_accounts.py` - 初始化测试账户
- `fullstack_integration_test.py` - 全栈集成测试
- `performance_load_test.py` - 性能负载测试
- `simple_app.py` - 简单应用
- `user_acceptance_test.py` - 用户验收测试

## 🚀 使用指南

### 运行测试
```bash
# 运行所有测试
pytest 脚本/测试/ -v

# 运行特定测试
python 脚本/测试/test_api_simple.py

# 运行测试并生成覆盖率报告
pytest 脚本/测试/ --cov=src --cov-report=html
```

### 运行演示
```bash
# 运行演示脚本
python 脚本/演示/demo_assessment_system.py

# 运行系统集成演示
python 脚本/演示/demo_system_integration.py
```

### 运行诊断
```bash
# 诊断 API
python 脚本/诊断/diagnose_api.py

# 调试导入
python 脚本/诊断/debug_import.py
```

### 运行验证
```bash
# 验证 10ms 性能
python 脚本/验证/validate_10ms_performance.py

# 验证权限控制
python 脚本/验证/validate_fine_grained_permission_control.py
```

## 📊 脚本统计

| 类别 | 数量 | 用途 |
|------|------|------|
| 测试脚本 | 80+ | 单元和集成测试 |
| 演示脚本 | 17 | 功能演示 |
| 诊断脚本 | 5 | 系统诊断 |
| 验证脚本 | 5 | 性能验证 |
| 其他脚本 | 30+ | 工具和辅助 |
| **总计** | **137+** | - |

## 🔍 快速查找

### 按功能查找
| 功能 | 脚本 |
|------|------|
| API 测试 | test_api_*.py |
| 登录测试 | test_login_*.py |
| 前端测试 | test_frontend_*.py |
| 业务逻辑 | test_business_logic*.py |
| 权限测试 | test_*permission*.py |
| 数据库 | test_db_*.py |
| 集成测试 | test_*integration*.py |

### 按系统查找
| 系统 | 脚本 |
|------|------|
| 评估系统 | demo_assessment_system.py |
| 监控系统 | demo_monitoring_*.py |
| 告警系统 | demo_*alert*.py |
| 审计系统 | demo_*audit*.py |
| Label Studio | demo_label_studio_integration.py |
| 质量管理 | demo_quality_*.py |

## 💡 使用建议

1. **新手**: 从 `脚本/演示/` 开始了解功能
2. **开发**: 使用 `脚本/测试/` 进行单元测试
3. **调试**: 使用 `脚本/诊断/` 排查问题
4. **验证**: 使用 `脚本/验证/` 检查性能
5. **集成**: 使用 `脚本/其他/` 中的集成脚本

## 📝 维护说明

- **更新频率**: 每周更新一次
- **最后更新**: 2026-01-20
- **维护者**: 开发团队
- **反馈方式**: 提交 Issue 或 PR

## ⚠️ 注意事项

1. 运行脚本前确保环境已配置
2. 某些脚本需要数据库连接
3. 某些脚本需要特定的权限
4. 建议在测试环境中运行
5. 查看脚本头部的注释了解使用方法

---

**提示**: 大多数脚本都有详细的注释和使用说明，查看脚本头部了解更多信息。
