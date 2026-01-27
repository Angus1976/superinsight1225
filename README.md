# SuperInsight AI 数据治理与标注平台

SuperInsight 是一个企业级 AI 数据治理和智能标注平台，专为 AI 时代设计。深度集成成熟的"理采存管用"（Collect-Store-Manage-Use）方法论，并针对大语言模型（LLM）和生成式 AI（GenAI）应用场景进行全面升级。

## 核心特性

- **安全数据提取**: 从各种数据源（数据库、文件、API）进行只读权限提取
- **AI 预标注**: 集成多个 LLM 模型进行智能预标注
- **人机协作**: 支持业务专家和技术专家协同标注
- **质量管理**: 基于 Ragas 框架的语义质量评估
- **计费结算**: 精确的工时和项目统计
- **安全合规**: 企业级安全控制和审计系统
- **多部署方式**: 支持云托管、私有部署和混合云

## 技术栈

### 后端
- **框架**: FastAPI (Python 3.11+)
- **数据库**: PostgreSQL 15+ with JSONB support
- **缓存**: Redis 7+
- **图数据库**: Neo4j 5+ (知识图谱)
- **ORM**: SQLAlchemy 2.0+ with Alembic migrations
- **任务队列**: Celery with Redis broker

### 前端
- **框架**: React 19 with TypeScript
- **构建工具**: Vite 7+
- **UI 库**: Ant Design 5+ with Pro Components
- **状态管理**: Zustand
- **数据获取**: TanStack Query (React Query)
- **路由**: React Router DOM 7+
- **测试**: Vitest + Playwright for E2E

### 核心集成
- **标注引擎**: Label Studio (容器化)
- **AI/ML**: Transformers, PyTorch, Ollama, 多个 LLM API
- **数据隐私**: Presidio (analyzer + anonymizer)
- **质量评估**: Ragas framework
- **监控**: Prometheus + Grafana
- **安全**: JWT, bcrypt, cryptography

## Label Studio 认证集成

### 认证方案概述

SuperInsight 支持 Label Studio 开源版的 **Personal Access Token (PAT)** 认证方式。PAT 是一种基于 JWT 的 refresh token，需要通过 token refresh 机制获取短期有效的 access token。

### 认证流程

```
┌─────────────────────────────────────────────────────────────┐
│              Label Studio 认证流程 (开源版)                  │
└─────────────────────────────────────────────────────────────┘

1. 用户在 Label Studio UI 生成 Personal Access Token
   位置: Account & Settings → Personal Access Token
   ↓
2. Token 格式: JWT refresh token
   {
     "token_type": "refresh",
     "exp": 8076731227,
     "iat": 1769531227,
     "user_id": "1"
   }
   ↓
3. 后端自动检测 JWT 格式，识别为 Personal Access Token
   检测逻辑: token.split('.').length == 3
   ↓
4. 调用 /api/token/refresh 交换 access token
   POST http://label-studio:8080/api/token/refresh
   Headers: Content-Type: application/json
   Body: {"refresh": "<personal-access-token>"}
   ↓
5. 获得 access token (有效期 ~5 分钟)
   Response: {"access": "<access-token>"}
   Token 格式: JWT access token
   {
     "token_type": "access",
     "exp": 1769531902,
     "iat": 1769531602,
     "user_id": "1"
   }
   ↓
6. 使用 access token 访问 Label Studio API
   Authorization: Bearer <access-token>
   ↓
7. Token 过期前 30 秒自动刷新
   自动检测: datetime.utcnow() < expires_at - timedelta(seconds=30)
   ↓
8. 重复步骤 4-7 (自动循环)
```

### 认证方法对比

| 认证方式 | 开源版支持 | 企业版支持 | Token 格式 | 有效期 | 刷新机制 |
|---------|-----------|-----------|-----------|--------|---------|
| **Personal Access Token** | ✅ | ✅ | JWT refresh token | 长期 | 需要交换 access token |
| **Legacy Token** | ✅ | ✅ | 字符串 | 永久 | 无需刷新 |
| **JWT Authentication** | ❌ | ✅ | JWT | 短期 | 自动刷新 |

### 配置方法

#### 1. 生成 Personal Access Token

1. 打开 Label Studio: `http://localhost:8080`
2. 登录账户
3. 点击右上角用户图标 → **Account & Settings**
4. 左侧菜单选择 **Personal Access Token**
5. 点击 **Create Token** 或 **Generate Token**
6. **立即复制令牌**（只显示一次！）

#### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# Label Studio Configuration
LABEL_STUDIO_URL=http://label-studio:8080

# Personal Access Token (推荐)
LABEL_STUDIO_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 注意：
# 1. Token 是完整的 JWT 字符串（约 200+ 字符）
# 2. 不要有空格或换行
# 3. 这是 refresh token，后端会自动交换 access token
```

#### 3. 重启服务

```bash
# 停止并删除容器（重新加载环境变量）
docker compose down app

# 重新创建并启动
docker compose up -d app

# 验证环境变量
docker exec superinsight-app printenv LABEL_STUDIO_API_TOKEN
```

### 代码实现

#### 核心类: `LabelStudioIntegration`

**文件**: `src/label_studio/integration.py`

```python
class LabelStudioIntegration:
    """Label Studio 集成类，支持 Personal Access Token 认证"""
    
    def __init__(self, config: Optional[LabelStudioConfig] = None):
        self.config = config or LabelStudioConfig()
        self.base_url = self.config.base_url.rstrip('/')
        self.api_token = self.config.api_token
        
        # Personal Access Token 支持
        self._personal_access_token: Optional[str] = None
        self._access_token: Optional[str] = None
        self._access_token_expires_at: Optional[datetime] = None
        
        # 检测 token 类型
        if self.api_token and self._is_jwt_token(self.api_token):
            logger.info("Detected Personal Access Token (JWT refresh token)")
            self._personal_access_token = self.api_token
            self._auth_method = 'personal_access_token'
    
    def _is_jwt_token(self, token: str) -> bool:
        """检测是否为 JWT 格式"""
        parts = token.split('.')
        return len(parts) == 3
    
    async def _ensure_access_token(self) -> None:
        """确保有有效的 access token"""
        # 检查 token 是否过期（30 秒缓冲）
        if self._access_token and self._access_token_expires_at:
            if datetime.utcnow() < self._access_token_expires_at - timedelta(seconds=30):
                return
        
        # 刷新 access token
        logger.info("[Label Studio] Refreshing Personal Access Token")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/api/token/refresh",
                headers={'Content-Type': 'application/json'},
                json={'refresh': self._personal_access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get('access')
                
                # 解析过期时间
                decoded = jwt.decode(
                    self._access_token,
                    options={"verify_signature": False}
                )
                exp_timestamp = decoded.get('exp')
                self._access_token_expires_at = datetime.utcfromtimestamp(exp_timestamp)
                
                logger.info(
                    f"[Label Studio] Access token refreshed, "
                    f"expires at {self._access_token_expires_at.isoformat()}"
                )
            else:
                raise LabelStudioAuthenticationError(
                    f"Failed to refresh token: {response.status_code}"
                )
    
    async def _get_headers(self) -> Dict[str, str]:
        """获取认证头"""
        if self._auth_method == 'personal_access_token':
            # 确保 access token 有效
            await self._ensure_access_token()
            
            return {
                'Authorization': f'Bearer {self._access_token}',
                'Content-Type': 'application/json'
            }
        else:
            # Legacy Token
            return {
                'Authorization': f'Token {self.api_token}',
                'Content-Type': 'application/json'
            }
```

### API 端点

#### 1. 测试连接

```bash
GET /api/tasks/label-studio/test-connection
Authorization: Bearer <jwt-token>

Response:
{
  "status": "success",
  "message": "Label Studio connection successful",
  "auth_method": "personal_access_token"
}
```

#### 2. 同步任务到 Label Studio

```bash
POST /api/tasks/{task_id}/sync-label-studio
Authorization: Bearer <jwt-token>
Content-Type: application/json

Response:
{
  "success": true,
  "project_id": 3,
  "project_url": "http://label-studio:8080/projects/3",
  "synced_at": "2026-01-27T16:42:30.784153Z"
}
```

### 故障排查

#### 问题 1: "Token is invalid" (401)

**原因**: Token 签名不匹配

**解决方案**:
1. 确保 token 是从**当前** Label Studio 实例生成的
2. 不要使用其他实例的 token
3. 重新生成新 token

#### 问题 2: "Authentication credentials were not provided" (401)

**原因**: Token 格式错误或未正确发送

**解决方案**:
1. 检查 `.env` 文件中 token 是否完整
2. 确保 token 在一行内，无空格或换行
3. 重启容器加载新环境变量

#### 问题 3: Token refresh 失败

**原因**: Refresh token 过期或无效

**解决方案**:
1. 重新生成 Personal Access Token
2. 更新 `.env` 文件
3. 重启容器

#### 问题 4: 项目标题过长 (400)

**原因**: Label Studio 项目标题限制 50 字符

**解决方案**: 已自动处理
- 系统自动截断标题
- 格式: `{task_name[:37]}... ({task_id[:8]})`
- 示例: `Integration Test Task (6b5805c9)`

### 测试验证

#### 1. 直接测试 Token

```bash
# 获取 access token
curl -X POST http://localhost:8080/api/token/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<your-personal-access-token>"}'

# 使用 access token 访问 API
curl -X GET http://localhost:8080/api/current-user/whoami \
  -H "Authorization: Bearer <access-token>"
```

#### 2. 运行集成测试

```bash
python3 docker-compose-integration-test.py
```

**预期结果**: 8/9 测试通过 (89%)

```
[TEST] SuperInsight API health... ✅ PASS
[TEST] JWT Authentication... ✅ PASS
[TEST] Task Management... ✅ PASS
[TEST] Label Studio connection... ✅ PASS
[TEST] Label Studio sync... ✅ PASS ⭐
```

### 性能指标

| 指标 | 值 |
|-----|---|
| Token 刷新时间 | ~100ms |
| 项目创建时间 | ~200ms |
| API 响应时间 | <500ms |
| Access Token 有效期 | 5 分钟 |
| 自动刷新缓冲 | 30 秒 |
| Refresh Token 有效期 | 长期（约 100 年） |

### 安全建议

1. **Token 保护**
   - 不要在代码中硬编码 token
   - 使用环境变量存储
   - 定期轮换 token

2. **HTTPS 使用**
   - 生产环境必须使用 HTTPS
   - 避免 token 在传输中被截获

3. **Token 撤销**
   - 如果 token 泄露，立即在 Label Studio UI 中撤销
   - 生成新 token 并更新配置

4. **访问控制**
   - 限制 token 的权限范围
   - 使用最小权限原则

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone <repository-url>
cd superinsight-platform

# 复制环境配置
cp .env.example .env

# 编辑 .env 文件，配置 Label Studio token
nano .env
```

### 2. 启动服务

```bash
# 使用 Docker Compose 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f app
```

### 3. 初始化数据库

```bash
# 运行数据库迁移
docker exec superinsight-app alembic upgrade head

# 创建管理员用户
docker exec superinsight-app python reset_admin_password.py
```

### 4. 访问服务

- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **Label Studio**: http://localhost:8080
- **Grafana**: http://localhost:3001

### 5. 配置 Label Studio

1. 访问 http://localhost:8080
2. 登录（默认: admin@example.com / admin）
3. 生成 Personal Access Token
4. 更新 `.env` 文件
5. 重启后端: `docker compose restart app`

## 开发指南

### 后端开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行开发服务器
uvicorn src.app:app --reload

# 运行测试
pytest tests/ -v --cov=src

# 代码格式化
black src/ tests/
isort src/ tests/
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev

# 运行测试
npm run test

# 类型检查
npm run typecheck

# 代码检查
npm run lint
```

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 部署

### Docker Compose 部署

```bash
# 生产环境启动
docker compose -f docker-compose.yml up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

### 腾讯云 TCB 部署

```bash
# 部署到腾讯云
./deploy-to-tcb.sh

# 或使用快速部署脚本
./quick-deploy-tcb.sh
```

## 监控和维护

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health

# 系统状态
curl http://localhost:8000/system/status

# Label Studio 连接测试
curl http://localhost:8000/api/tasks/label-studio/test-connection \
  -H "Authorization: Bearer <jwt-token>"
```

### 日志查看

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f app
docker compose logs -f label-studio
docker compose logs -f postgres
```

### 备份和恢复

```bash
# 备份数据库
docker exec superinsight-postgres pg_dump -U superinsight superinsight > backup.sql

# 恢复数据库
docker exec -i superinsight-postgres psql -U superinsight superinsight < backup.sql
```

## 常见问题

### Q: Label Studio 认证失败怎么办？

A: 
1. 检查 token 是否正确配置在 `.env` 文件中
2. 确保 token 是从当前 Label Studio 实例生成的
3. 重启容器加载新配置: `docker compose restart app`
4. 查看详细日志: `docker compose logs -f app`

### Q: 如何更新 Personal Access Token？

A:
1. 在 Label Studio UI 中生成新 token
2. 更新 `.env` 文件中的 `LABEL_STUDIO_API_TOKEN`
3. 重启容器: `docker compose down app && docker compose up -d app`

### Q: 项目标题过长怎么办？

A: 系统已自动处理，会截断到 50 字符以内。

### Q: Token 多久过期？

A: 
- Refresh Token (Personal Access Token): 长期有效（约 100 年）
- Access Token: 5 分钟，系统自动刷新

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feature/my-feature`
3. 提交更改: `git commit -am 'Add some feature'`
4. 推送到分支: `git push origin feature/my-feature`
5. 提交 Pull Request

## 许可证

[添加许可证信息]

## 联系方式

- 项目主页: [添加链接]
- 问题反馈: [添加链接]
- 文档: [添加链接]

## 致谢

- [Label Studio](https://labelstud.io/) - 开源标注平台
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [Ant Design](https://ant.design/) - 企业级 UI 设计语言

---

**最后更新**: 2026-01-27  
**版本**: 2.3.0  
**状态**: ✅ 生产就绪
