# SuperInsight 2.3 执行指南

## 🚀 快速开始

### 一键全自动执行
```bash
# 最简单的方式：全自动执行所有模块
python3 run-all-modules.py

# 或者使用控制器启动
python3 execution-control.py start --auto-approve-all
```

### 监控执行进度
```bash
# 在另一个终端窗口监控进度
python3 monitor-execution.py

# 或者查看状态
python3 execution-control.py status
```

## 📋 可用工具

### 1. 全模块执行器 (`run-all-modules.py`)
**功能**: 按推荐顺序自动执行所有9个模块

**使用方法**:
```bash
# 基本执行（会询问确认）
python3 run-all-modules.py

# 全自动执行（自动确认所有步骤）
python3 run-all-modules.py --auto-approve-all

# 自定义顺序执行
python3 run-all-modules.py --custom-sequence
```

**特性**:
- ✅ 智能依赖检查
- ✅ 实时进度显示
- ✅ 错误自动重试
- ✅ 人工干预支持
- ✅ 完整日志记录

### 2. 单模块执行器 (`run-single-module.py`)
**功能**: 执行指定的单个模块

**使用方法**:
```bash
# 执行单个模块
python3 run-single-module.py multi-tenant-workspace

# 自动确认所有步骤
python3 run-single-module.py multi-tenant-workspace --auto-approve-all

# 查看可用模块
python3 run-single-module.py --help
```

**可用模块**:
- `multi-tenant-workspace` - 多租户工作空间
- `audit-security` - 审计安全系统
- `frontend-management` - 前端管理界面
- `data-sync-pipeline` - 数据同步管道
- `quality-workflow` - 质量工作流
- `data-version-lineage` - 数据版本血缘
- `billing-advanced` - 高级计费系统
- `high-availability` - 高可用性系统
- `deployment-tcb-fullstack` - TCB全栈部署

### 3. 执行监控器 (`monitor-execution.py`)
**功能**: 实时监控执行进度和状态

**使用方法**:
```bash
# 默认5秒刷新间隔
python3 monitor-execution.py

# 自定义刷新间隔（2秒）
python3 monitor-execution.py --interval 2
```

**监控内容**:
- 📊 总体执行进度
- 🔄 当前执行模块详情
- 📋 所有模块状态列表
- 📝 最近执行日志
- ⚠️ 健康状态检查

### 4. 执行控制器 (`execution-control.py`)
**功能**: 提供完整的执行控制功能

**使用方法**:
```bash
# 启动执行
python3 execution-control.py start --auto-approve-all

# 停止执行
python3 execution-control.py stop

# 暂停执行
python3 execution-control.py pause

# 恢复执行
python3 execution-control.py resume

# 重启执行
python3 execution-control.py restart --auto-approve-all

# 查看状态
python3 execution-control.py status

# 查看日志
python3 execution-control.py logs --lines 100

# 实时跟踪日志
python3 execution-control.py logs --follow

# 清理执行数据
python3 execution-control.py clean
```

## 🎯 推荐工作流程

### 场景1: 首次完整部署
```bash
# 1. 启动全自动执行
python3 execution-control.py start --auto-approve-all

# 2. 在另一个终端监控进度
python3 monitor-execution.py

# 3. 如果需要查看详细日志
python3 execution-control.py logs --follow
```

### 场景2: 单模块开发测试
```bash
# 1. 执行特定模块
python3 run-single-module.py frontend-management --auto-approve-all

# 2. 查看执行结果
python3 execution-control.py status
```

### 场景3: 故障恢复
```bash
# 1. 查看当前状态
python3 execution-control.py status

# 2. 查看错误日志
python3 execution-control.py logs --lines 200

# 3. 清理并重启
python3 execution-control.py clean
python3 execution-control.py start --auto-approve-all
```

### 场景4: 开发调试
```bash
# 1. 暂停当前执行
python3 execution-control.py pause

# 2. 进行必要的修复

# 3. 恢复执行
python3 execution-control.py resume
```

## 📊 执行状态说明

### 模块状态
- ⏳ `pending` - 等待执行
- 🔄 `running` - 正在执行
- ✅ `completed` - 执行完成
- ❌ `failed` - 执行失败
- ⏸️ `paused` - 已暂停

### 进度指标
- **总体进度**: 已完成模块数 / 总模块数
- **模块进度**: 当前模块内任务完成百分比
- **执行时间**: 从开始到当前的总用时
- **预计剩余**: 基于平均速度的剩余时间估算

## 🔧 高级功能

### 依赖管理
系统会自动检查模块间依赖关系：
- `frontend-management` 依赖 `multi-tenant-workspace`, `audit-security`
- `data-version-lineage` 依赖 `data-sync-pipeline`
- `deployment-tcb-fullstack` 依赖 `high-availability`

### 错误处理
- **自动重试**: 临时错误会自动重试最多3次
- **人工干预**: 严重错误会暂停等待人工处理
- **跳过选项**: 可以选择跳过失败的模块继续执行
- **回滚机制**: 支持回滚到执行前状态

### 并行执行
某些模块可以并行执行以提高效率：
- Phase 1: `multi-tenant-workspace` 和 `audit-security` 可部分并行
- Phase 3: `data-version-lineage` 和 `billing-advanced` 可完全并行

## 📁 文件结构

### 执行文件
```
├── run-all-modules.py          # 全模块执行器
├── run-single-module.py        # 单模块执行器  
├── monitor-execution.py        # 执行监控器
├── execution-control.py        # 执行控制器
└── EXECUTION_GUIDE.md         # 本指南
```

### 状态文件
```
.kiro/
├── execution_status.json      # 执行状态
├── execution.log              # 执行日志
├── execution.pid              # 进程PID
├── control_signal.json        # 控制信号
└── [module]_execution.log     # 单模块日志
```

## 🚨 故障排除

### 常见问题

#### 1. 执行卡死不动
```bash
# 检查进程状态
python3 execution-control.py status

# 查看详细日志
python3 execution-control.py logs --lines 100

# 如果确实卡死，强制重启
python3 execution-control.py restart --auto-approve-all
```

#### 2. 依赖检查失败
```bash
# 检查依赖模块是否存在
ls -la .kiro/specs/new/

# 手动执行依赖模块
python3 run-single-module.py [dependency-module] --auto-approve-all
```

#### 3. 权限错误
```bash
# 检查文件权限
ls -la .kiro/

# 修复权限
chmod +x *.py
chmod -R 755 .kiro/
```

#### 4. 环境问题
```bash
# 检查Python版本
python3 --version

# 检查必要的目录
ls -la src/
ls -la .kiro/specs/new/
```

### 日志分析

#### 错误级别
- `[ERROR]` - 严重错误，需要人工处理
- `[WARNING]` - 警告信息，可能影响执行
- `[INFO]` - 一般信息
- `[SUCCESS]` - 成功完成的操作

#### 关键日志模式
```bash
# 查找错误
grep "ERROR" .kiro/execution.log

# 查找特定模块的日志
grep "multi-tenant-workspace" .kiro/execution.log

# 查找执行时间信息
grep "执行完成" .kiro/execution.log
```

## 📈 性能优化

### 提高执行速度
1. **并行执行**: 使用多个终端同时执行独立模块
2. **跳过测试**: 开发阶段可以跳过某些测试步骤
3. **增量执行**: 只执行修改过的模块

### 资源监控
```bash
# 监控系统资源
top -p $(cat .kiro/execution.pid)

# 监控磁盘使用
df -h

# 监控内存使用
free -h
```

## 🎯 最佳实践

### 执行前准备
1. ✅ 确保所有依赖服务正常运行
2. ✅ 检查磁盘空间充足
3. ✅ 备份重要数据
4. ✅ 确保网络连接稳定

### 执行中监控
1. 📊 定期检查执行进度
2. 📝 关注错误日志
3. 🔍 监控系统资源使用
4. ⚠️ 及时处理异常情况

### 执行后验证
1. ✅ 检查所有模块状态
2. 🧪 运行验证测试
3. 📋 生成执行报告
4. 🔄 必要时进行回滚

---

## 总结

SuperInsight 2.3 执行系统提供了完整的自动化执行解决方案：

🚀 **一键执行**: 全自动完成所有9个模块的部署  
📊 **实时监控**: 全程可视化进度跟踪  
🛡️ **故障处理**: 完善的错误处理和恢复机制  
🔧 **灵活控制**: 支持启动、停止、暂停、恢复等操作  
📝 **详细日志**: 完整的执行过程记录  

**立即开始您的SuperInsight 2.3自动化部署之旅！**

```bash
python3 execution-control.py start --auto-approve-all
```