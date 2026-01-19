# PIV 方法论快速开始

## 什么是 PIV？

PIV (Prime-Implement-Validate) 是一个系统化的开发循环：

```
Prime (准备) → Plan (规划) → Execute (执行) → Validate (验证) → 循环
```

## 5 分钟快速开始

### 1. Prime - 了解项目

```bash
# 查看项目结构
git ls-files | head -30

# 阅读核心文档
cat README.md
cat .kiro/steering/tech.md
cat .kiro/steering/structure.md
```

### 2. Plan - 创建功能计划

创建 `.agents/plans/my-feature.md`:

```markdown
# Feature: 我的功能

## 功能描述
[简短描述]

## 用户故事
作为 [用户类型]
我想要 [功能]
以便 [收益]

## 代码库参考
- `src/api/example.py` (lines 10-20) - 参考模式
- `tests/test_example.py` - 测试模式

## 实现步骤

### 1. CREATE src/new_file.py
- **实现**: 创建新模块
- **模式**: 参考 src/api/example.py:10-20
- **验证**: `python -c "import src.new_file; print('OK')"`

### 2. UPDATE src/main.py
- **实现**: 注册新路由
- **验证**: `curl http://localhost:8000/api/new`

### 3. CREATE tests/test_new_file.py
- **实现**: 单元测试
- **验证**: `pytest tests/test_new_file.py -v`

## 验证命令
```bash
# 后端
pytest tests/ -v
mypy src/

# 前端
npx tsc --noEmit
npm run test
```
```

### 3. Execute - 执行计划

按顺序执行每个任务，每完成一个任务运行验证命令。

### 4. Validate - 全面验证

```bash
# 运行所有验证
cd backend && pytest tests/ -v --cov=src
cd frontend && npx tsc --noEmit && npm run test
```

## 常用命令

### 创建新计划

```bash
mkdir -p .agents/plans
cp .kiro/piv-methodology/templates/plan-template.md .agents/plans/my-feature.md
```

### 执行验证

```bash
# 后端
cd backend
pytest tests/ -v --cov=src
mypy src/
black src/ tests/
isort src/ tests/

# 前端
cd frontend
npx tsc --noEmit
npm run test
npm run lint
```

## 与 Kiro Spec 集成

PIV 可以与 Kiro Spec 工作流结合使用：

```
.kiro/specs/my-feature/
├── requirements.md    ← 使用 Kiro Spec 创建
├── design.md          ← 使用 Kiro Spec 创建
├── tasks.md           ← 使用 PIV Plan 创建详细任务
└── implementation/    ← 使用 PIV Execute 执行
```

## 示例：添加新 API 端点

### 1. Prime
```bash
# 查看现有 API 结构
ls -la src/api/
cat src/api/auth.py | head -50
```

### 2. Plan
创建 `.agents/plans/add-profile-api.md`:
```markdown
# Feature: 用户个人资料 API

## 实现步骤

### 1. CREATE src/schemas/profile.py
- **实现**: ProfileSchema(name, email, avatar)
- **模式**: 参考 src/schemas/user.py:15-30
- **验证**: `python -c "from src.schemas.profile import ProfileSchema; print('OK')"`

### 2. CREATE src/api/profile.py
- **实现**: GET /api/profile/{id} 端点
- **模式**: 参考 src/api/auth.py:45-80
- **验证**: `curl http://localhost:8000/api/profile/1`

### 3. UPDATE src/app.py
- **实现**: 注册 profile router
- **验证**: `curl http://localhost:8000/docs` (检查 API 文档)

### 4. CREATE tests/test_api_profile.py
- **实现**: 测试 GET /api/profile/{id}
- **验证**: `pytest tests/test_api_profile.py -v`
```

### 3. Execute
按顺序执行每个任务

### 4. Validate
```bash
pytest tests/test_api_profile.py -v
pytest tests/ --cov=src
mypy src/
```

## 更多资源

- 完整文档: `.kiro/steering/piv-methodology-integration.md`
- PIV 命令: `.kiro/piv-methodology/commands/`
- 参考文档: `.kiro/piv-methodology/reference/`
- 原始项目: https://github.com/coleam00/habit-tracker

## 提示

1. **计划要详细** - 包含具体的文件路径、行号、验证命令
2. **任务要原子** - 每个任务 5-15 分钟完成
3. **验证要可执行** - 使用具体的命令，不要用"测试一下"
4. **模式要引用** - 指向现有代码的具体位置

---

**开始使用 PIV，提高开发效率！**
