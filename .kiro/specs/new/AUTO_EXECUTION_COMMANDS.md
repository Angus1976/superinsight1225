# SuperInsight 2.3 全自动执行命令速查表

## 🚀 一键执行命令

### 全局执行
```bash
# 执行所有模块 (按推荐顺序，全自动确认)
kiro run-all-modules --auto-approve-all --follow-sequence

# 并行执行模式 (适合多团队)
kiro run-all-modules --auto-approve-all --parallel --max-concurrent=3

# 测试模式 (不实际修改代码)
kiro run-all-modules --dry-run --auto-approve-all
```

### 单模块执行 (按推荐顺序)

#### Phase 1: 基础设施层 🔴 最高优先级
```bash
# 1. Multi-Tenant Workspace (Week 1)
kiro run-module multi-tenant-workspace --auto-approve-all

# 2. Audit Security (Week 2)  
kiro run-module audit-security --auto-approve-all
```

#### Phase 2: 核心功能层 🟡 高优先级
```bash
# 3. Frontend Management (Week 3-4)
kiro run-module frontend-management --auto-approve-all

# 4. Data Sync Pipeline (Week 5)
kiro run-module data-sync-pipeline --auto-approve-all
```

#### Phase 3: 高级功能层 🟢 中优先级
```bash
# 5. Quality Workflow (Week 6)
kiro run-module quality-workflow --auto-approve-all

# 6. Data Version Lineage (Week 7)
kiro run-module data-version-lineage --auto-approve-all

# 7. Billing Advanced (Week 8)
kiro run-module billing-advanced --auto-approve-all
```

#### Phase 4: 基础设施完善 🔵 中低优先级
```bash
# 8. High Availability (Week 9)
kiro run-module high-availability --auto-approve-all

# 9. Deployment TCB Fullstack (Week 10)
kiro run-module deployment-tcb-fullstack --auto-approve-all
```

## 🛠️ 管理和监控命令

### 环境检查
```bash
# 全面环境检查
kiro check-environment --comprehensive

# 权限检查
kiro check-permissions --all-modules

# 依赖服务检查
kiro check-dependencies --external-services

# 一键环境准备
kiro setup-environment --auto-fix
```

### 执行监控
```bash
# 查看实时状态
kiro status --detailed

# 监控执行进度
kiro monitor-execution --real-time

# 查看日志
kiro logs --follow --module current
kiro logs --level error --last 24h
```

### 故障处理
```bash
# 自动诊断修复
kiro auto-fix --comprehensive

# 诊断特定模块
kiro diagnose --module [module-name]

# 重置失败任务
kiro reset-task --task "[task-name]" --module [module-name]

# 从中断点继续
kiro resume-execution --auto-approve-all
```

### 回滚操作
```bash
# 紧急回滚
kiro emergency-rollback --confirm

# 部分回滚
kiro rollback --module [module-name] --to-checkpoint "[checkpoint-name]"
```

### 验证和报告
```bash
# 完整验证
kiro verify-deployment --comprehensive

# 业务目标验证
kiro verify-business-goals

# 生成报告
kiro generate-report --format pdf --include-metrics
```

## 📊 状态查询命令

### 模块状态
```bash
# 查看所有模块状态
kiro list-modules --status

# 查看特定模块详情
kiro module-info [module-name] --detailed

# 查看依赖关系
kiro show-dependencies --graph
```

### 任务状态
```bash
# 查看当前任务
kiro current-task --detailed

# 查看任务历史
kiro task-history --module [module-name]

# 查看失败任务
kiro failed-tasks --last 7d
```

### 性能监控
```bash
# 系统资源使用
kiro system-resources --real-time

# 执行性能统计
kiro performance-stats --summary

# 数据库连接状态
kiro db-status --all-connections
```

## 🎛️ 高级配置命令

### 自定义执行
```bash
# 自定义模块顺序
kiro run-modules --sequence "module1,module2,module3" --auto-approve-all

# 跳过特定任务
kiro run-module [module-name] --skip-tasks "task1,task2" --auto-approve-all

# 只执行特定阶段
kiro run-module [module-name] --phases "1,2" --auto-approve-all
```

### 配置管理
```bash
# 查看当前配置
kiro config --show-all

# 更新配置
kiro config --set execution.auto_approve=true
kiro config --set execution.max_retries=3
kiro config --set execution.timeout=3600

# 重置配置
kiro config --reset-defaults
```

### 备份管理
```bash
# 创建备份
kiro backup --create --name "before-execution"

# 列出备份
kiro backup --list

# 恢复备份
kiro backup --restore --name "before-execution"
```

## 🔧 开发和调试命令

### 调试模式
```bash
# 启用详细日志
kiro run-module [module-name] --auto-approve-all --verbose

# 调试模式执行
kiro run-module [module-name] --auto-approve-all --debug

# 单步执行模式
kiro run-module [module-name] --step-by-step
```

### 测试命令
```bash
# 运行单元测试
kiro test --unit --module [module-name]

# 运行集成测试
kiro test --integration --all-modules

# 运行性能测试
kiro test --performance --benchmarks
```

### 代码质量
```bash
# 代码质量检查
kiro lint --all-modules

# 安全扫描
kiro security-scan --comprehensive

# 依赖漏洞检查
kiro vulnerability-scan --dependencies
```

## 📱 快捷命令别名

### 常用操作
```bash
# 快速状态查看
alias ss='kiro status --summary'

# 快速日志查看
alias ll='kiro logs --follow --tail 50'

# 快速错误查看
alias ee='kiro logs --level error --last 1h'

# 快速重启失败任务
alias rr='kiro resume-execution --auto-approve-all'
```

### 模块快捷方式
```bash
# 快速执行基础模块
alias run-base='kiro run-module multi-tenant-workspace --auto-approve-all && kiro run-module audit-security --auto-approve-all'

# 快速执行核心模块
alias run-core='kiro run-module frontend-management --auto-approve-all && kiro run-module data-sync-pipeline --auto-approve-all'

# 快速执行高级模块
alias run-advanced='kiro run-module quality-workflow --auto-approve-all && kiro run-module data-version-lineage --auto-approve-all && kiro run-module billing-advanced --auto-approve-all'
```

## 🆘 紧急命令

### 紧急停止
```bash
# 立即停止所有执行
kiro emergency-stop --force

# 优雅停止当前任务
kiro stop --graceful --wait-timeout=300
```

### 紧急恢复
```bash
# 紧急系统检查
kiro emergency-check --full-system

# 紧急服务重启
kiro emergency-restart --all-services

# 紧急数据库修复
kiro emergency-db-repair --auto-fix
```

## 📋 执行清单

### 执行前检查清单
```bash
# 运行完整检查清单
kiro pre-execution-checklist

# 预期输出:
✅ 系统环境检查通过
✅ 权限验证通过  
✅ 依赖服务检查通过
✅ 磁盘空间充足 (>50GB)
✅ 内存资源充足 (>8GB)
✅ 网络连接正常
✅ 备份创建完成
🚀 系统就绪，可以开始执行！
```

### 执行后验证清单
```bash
# 运行完整验证清单
kiro post-execution-checklist

# 预期输出:
✅ 所有模块部署成功
✅ 功能测试全部通过
✅ 性能指标达标
✅ 安全扫描通过
✅ 集成测试通过
✅ 用户验收测试通过
🎉 SuperInsight 2.3 部署完成！
```

---

## 💡 使用建议

1. **首次使用**: 建议先运行 `kiro run-all-modules --dry-run --auto-approve-all` 进行测试
2. **生产环境**: 建议分阶段执行，每个Phase完成后进行验证
3. **多团队协作**: 使用并行模式 `--parallel --max-concurrent=3`
4. **问题排查**: 遇到问题时使用 `kiro diagnose` 和 `kiro auto-fix`
5. **监控执行**: 在单独终端运行 `kiro monitor-execution --real-time`

**记住**: 所有命令都支持 `--help` 参数查看详细说明！