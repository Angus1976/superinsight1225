# Label Studio 本地配置文件设置完成

**日期**: 2026-01-27  
**状态**: ✅ 配置文件已创建  
**优先级**: HIGH

## 完成的工作

### 1. 创建本地配置文件 `.env`

✅ **文件位置**: 项目根目录 `.env`

**特点**:
- ✅ 不会被上传到 Git（已在 `.gitignore` 第 105 行配置）
- ✅ 包含所有必要的环境变量
- ✅ 预配置了 Label Studio URL
- ✅ 包含中英文注释说明
- ✅ 为 `LABEL_STUDIO_API_TOKEN` 预留了空白位置

**内容**:
```bash
# Label Studio Configuration
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_TOKEN=

# 其他配置...
DATABASE_URL=postgresql://superinsight:password@postgres:5432/superinsight
REDIS_URL=redis://redis:6379/0
ARGILLA_URL=http://argilla:6900
OLLAMA_BASE_URL=http://ollama:11434
```

### 2. 更新 `docker-compose.yml`

✅ **修改内容**: 将硬编码的环境变量改为从 `.env` 文件读取

**修改前**:
```yaml
environment:
  - APP_ENV=development
  - LABEL_STUDIO_URL=http://label-studio:8080
```

**修改后**:
```yaml
environment:
  - APP_ENV=${APP_ENV:-development}
  - LABEL_STUDIO_URL=${LABEL_STUDIO_URL:-http://label-studio:8080}
  - LABEL_STUDIO_API_TOKEN=${LABEL_STUDIO_API_TOKEN}
```

**优势**:
- ✅ 支持从 `.env` 文件读取配置
- ✅ 提供默认值（使用 `:-` 语法）
- ✅ 敏感信息不再硬编码在 `docker-compose.yml` 中

### 3. 创建自动化配置脚本

✅ **文件**: `setup-label-studio-token.sh`

**功能**:
1. 🔍 检查 Label Studio 容器状态
2. 🚀 自动启动 Label Studio（如果未运行）
3. 📋 引导用户获取 API Token
4. 📝 自动更新 `.env` 文件
5. 🔄 重启后端容器
6. ✅ 验证配置是否成功

**使用方法**:
```bash
./setup-label-studio-token.sh
```

### 4. 创建配置指南文档

✅ **文件**: `LABEL_STUDIO_SETUP.md`

**内容**:
- 快速开始指南
- 自动化配置方法
- 手动配置步骤
- 文件说明
- 安全提示
- 故障排查
- 测试连接方法

### 5. 更新详细设置指南

✅ **文件**: `.kiro/LABEL_STUDIO_TOKEN_SETUP_GUIDE.md`

**更新内容**:
- 添加了快速配置方法（使用自动化脚本）
- 更新了手动配置步骤（使用 `.env` 文件）
- 强调了 `.env` 文件不会被上传到 Git
- 简化了配置流程

## 文件结构

```
superdata/
├── .env                                    # ✅ 新建 - 本地配置文件（不会上传到 Git）
├── .env.example                            # 已存在 - 配置模板
├── .gitignore                              # 已存在 - 确认 .env 被忽略
├── docker-compose.yml                      # ✅ 已更新 - 使用环境变量
├── setup-label-studio-token.sh            # ✅ 新建 - 自动化配置脚本
├── LABEL_STUDIO_SETUP.md                  # ✅ 新建 - 快速配置指南
└── .kiro/
    ├── LABEL_STUDIO_TOKEN_SETUP_GUIDE.md  # ✅ 已更新 - 详细设置指南
    └── LABEL_STUDIO_LOCAL_CONFIG_SETUP.md # ✅ 新建 - 本文档
```

## 安全性验证

### ✅ Git 忽略验证

```bash
$ grep -n "^\.env$" .gitignore
105:.env
```

**结果**: `.env` 文件已在 `.gitignore` 第 105 行配置，不会被上传到 Git。

### ✅ 文件权限

```bash
$ ls -la setup-label-studio-token.sh
-rwxr-xr-x  1 user  staff  4567 Jan 27 10:30 setup-label-studio-token.sh
```

**结果**: 配置脚本已设置为可执行。

## 下一步操作

用户需要完成以下步骤来启用 Label Studio 集成：

### 选项 1: 使用自动化脚本（推荐）⚡

```bash
./setup-label-studio-token.sh
```

脚本会自动完成所有配置。

### 选项 2: 手动配置 📝

1. **访问 Label Studio**
   ```
   http://localhost:8080
   ```

2. **登录并获取 API Token**
   - Email: `admin@example.com`
   - Password: `admin`
   - 进入 Account & Settings → Access Token

3. **编辑 .env 文件**
   ```bash
   nano .env
   ```
   
   修改：
   ```bash
   LABEL_STUDIO_API_TOKEN=your_actual_token_here
   ```

4. **重启后端容器**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose restart app
   ```

5. **验证配置**
   ```bash
   /Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep LABEL_STUDIO
   ```

## 配置验证清单

完成配置后，请验证以下项目：

- [ ] `.env` 文件已创建
- [ ] `LABEL_STUDIO_API_TOKEN` 已设置
- [ ] 后端容器已重启
- [ ] 环境变量在容器中可见
- [ ] Label Studio 连接测试通过
- [ ] "开始标注" 按钮可以工作
- [ ] "在新窗口中打开" 按钮可以工作

## 测试命令

### 1. 检查环境变量

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep LABEL_STUDIO
```

**期望输出**:
```
LABEL_STUDIO_URL=http://label-studio:8080
LABEL_STUDIO_API_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

### 2. 测试 Label Studio 连接

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c "
from src.label_studio.integration import LabelStudioIntegration
import asyncio

async def test():
    ls = LabelStudioIntegration()
    result = await ls.test_connection()
    print(f'Connection test: {\"SUCCESS\" if result else \"FAILED\"}')

asyncio.run(test())
"
```

**期望输出**:
```
Connection test: SUCCESS
```

### 3. 检查后端日志

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose logs app --tail=50 | grep -i "label"
```

**期望**: 没有 401 或认证错误

## 优势总结

### 🔒 安全性
- ✅ 敏感信息不会被提交到 Git
- ✅ 本地开发环境专用配置
- ✅ 符合安全最佳实践

### 🚀 便利性
- ✅ 自动化配置脚本，一键完成
- ✅ 清晰的中英文文档
- ✅ 详细的故障排查指南

### 🔧 可维护性
- ✅ 配置集中管理在 `.env` 文件
- ✅ 易于更新和修改
- ✅ 支持多环境配置

### 📚 文档完善
- ✅ 快速开始指南
- ✅ 详细设置指南
- ✅ 故障排查文档
- ✅ 测试验证方法

## 相关文档

1. **快速配置指南**: `LABEL_STUDIO_SETUP.md`
2. **详细设置指南**: `.kiro/LABEL_STUDIO_TOKEN_SETUP_GUIDE.md`
3. **配置模板**: `.env.example`
4. **自动化脚本**: `setup-label-studio-token.sh`

## 技术细节

### Docker Compose 环境变量语法

```yaml
- VARIABLE_NAME=${ENV_VAR_NAME:-default_value}
```

**说明**:
- `${ENV_VAR_NAME}`: 从 `.env` 文件或系统环境变量读取
- `:-default_value`: 如果未设置，使用默认值
- 如果不需要默认值，直接使用 `${ENV_VAR_NAME}`

### .env 文件加载顺序

Docker Compose 按以下顺序加载环境变量：
1. Shell 环境变量
2. `.env` 文件
3. `docker-compose.yml` 中的 `environment` 部分
4. Dockerfile 中的 `ENV` 指令

**优先级**: Shell > .env > docker-compose.yml > Dockerfile

## 故障排查

### 问题 1: .env 文件不生效

**原因**: Docker Compose 缓存了旧的配置

**解决方案**:
```bash
# 停止所有容器
/Applications/Docker.app/Contents/Resources/bin/docker compose down

# 重新启动
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
```

### 问题 2: Token 包含特殊字符

**原因**: Shell 可能会解释某些特殊字符

**解决方案**: 在 `.env` 文件中，不需要给 token 加引号：
```bash
# ✅ 正确
LABEL_STUDIO_API_TOKEN=abc123def456

# ❌ 错误（会包含引号）
LABEL_STUDIO_API_TOKEN="abc123def456"
```

### 问题 3: 权限错误

**原因**: 脚本没有执行权限

**解决方案**:
```bash
chmod +x setup-label-studio-token.sh
```

## 总结

✅ **配置文件已完成**: 所有必要的配置文件和脚本已创建  
✅ **安全性已确保**: `.env` 文件不会被上传到 Git  
✅ **文档已完善**: 提供了详细的配置和故障排查指南  
✅ **自动化已实现**: 提供了一键配置脚本  

**下一步**: 用户需要运行 `./setup-label-studio-token.sh` 或手动配置 `.env` 文件中的 `LABEL_STUDIO_API_TOKEN`。

---

**创建时间**: 2026-01-27  
**创建者**: Kiro AI Assistant  
**状态**: ✅ 完成
