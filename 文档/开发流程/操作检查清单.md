# ✅ 操作清单

## 📋 Docker 容器重建和功能测试清单

### 第一阶段：准备工作

- [ ] 确认 Docker 已安装在 `/Applications/Docker.app/Contents/Resources/bin/docker`
- [ ] 确认本地代码已推送到 GitHub
- [ ] 确认 git 配置正确
- [ ] 打开终端，进入项目根目录

### 第二阶段：环境配置

- [ ] 运行 Docker 环境设置脚本
  ```bash
  chmod +x scripts/docker-setup.sh
  ./scripts/docker-setup.sh
  ```
- [ ] 验证 Docker 别名已创建
  ```bash
  alias docker
  ```
- [ ] 重新加载 shell 配置
  ```bash
  source ~/.zshrc  # 或 source ~/.bash_profile
  ```

### 第三阶段：容器重建

- [ ] 运行容器重建脚本
  ```bash
  chmod +x scripts/rebuild-containers.sh
  ./scripts/rebuild-containers.sh
  ```
- [ ] 等待脚本完成（通常需要 5-10 分钟）
- [ ] 验证所有容器已启动
  ```bash
  docker compose ps
  ```
- [ ] 检查容器状态
  - [ ] frontend: Up
  - [ ] app: Up
  - [ ] postgres: Up
  - [ ] redis: Up
  - [ ] label-studio: Up
  - [ ] argilla: Up
  - [ ] elasticsearch: Up
  - [ ] ollama: Up
  - [ ] prometheus: Up
  - [ ] grafana: Up

### 第四阶段：服务验证

- [ ] 验证后端服务
  ```bash
  curl http://localhost:8000/health/live
  ```
- [ ] 验证前端服务
  ```bash
  curl http://localhost:5173
  ```
- [ ] 访问前端应用
  - [ ] 打开浏览器访问 http://localhost:5173
  - [ ] 确认页面加载正常
  - [ ] 检查浏览器控制台是否有错误

- [ ] 访问后端 API 文档
  - [ ] 打开 http://localhost:8000/docs
  - [ ] 确认 Swagger UI 加载正常

### 第五阶段：功能测试

- [ ] 运行功能测试脚本
  ```bash
  chmod +x scripts/test-roles-functionality.sh
  ./scripts/test-roles-functionality.sh
  ```
- [ ] 验证测试结果
  - [ ] 系统健康检查: ✓
  - [ ] 管理员功能: ✓
  - [ ] 标注员功能: ✓
  - [ ] 专家功能: ✓
  - [ ] 品牌系统功能: ✓
  - [ ] 管理配置功能: ✓
  - [ ] AI 标注功能: ✓
  - [ ] 文本转 SQL 功能: ✓
  - [ ] 本体协作功能: ✓
  - [ ] 前端功能: ✓

### 第六阶段：角色功能测试

#### 管理员功能测试

- [ ] 管理员登录
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin"}'
  ```
- [ ] 获取用户列表
  ```bash
  curl http://localhost:8000/api/v1/admin/users
  ```
- [ ] 获取系统配置
  ```bash
  curl http://localhost:8000/api/v1/admin/config
  ```
- [ ] 获取审计日志
  ```bash
  curl http://localhost:8000/api/v1/admin/audit-logs
  ```
- [ ] 在前端访问管理员面板
  - [ ] 打开 http://localhost:5173
  - [ ] 以 admin 身份登录
  - [ ] 验证管理员菜单可见
  - [ ] 验证可以访问用户管理
  - [ ] 验证可以访问系统配置
  - [ ] 验证可以访问审计日志

#### 标注员功能测试

- [ ] 标注员登录
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"annotator","password":"password"}'
  ```
- [ ] 获取标注任务列表
  ```bash
  curl http://localhost:8000/api/v1/annotation/tasks
  ```
- [ ] 获取标注项目
  ```bash
  curl http://localhost:8000/api/v1/annotation/projects
  ```
- [ ] 获取质量指标
  ```bash
  curl http://localhost:8000/api/v1/annotation/quality-metrics
  ```
- [ ] 在前端访问标注功能
  - [ ] 打开 http://localhost:5173
  - [ ] 以 annotator 身份登录
  - [ ] 验证标注菜单可见
  - [ ] 验证可以查看标注任务
  - [ ] 验证可以查看质量指标

#### 专家功能测试

- [ ] 专家登录
  ```bash
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"expert","password":"password"}'
  ```
- [ ] 获取本体信息
  ```bash
  curl http://localhost:8000/api/v1/ontology/info
  ```
- [ ] 获取协作请求
  ```bash
  curl http://localhost:8000/api/v1/ontology/collaboration/requests
  ```
- [ ] 获取变更历史
  ```bash
  curl http://localhost:8000/api/v1/ontology/change-history
  ```
- [ ] 在前端访问专家功能
  - [ ] 打开 http://localhost:5173
  - [ ] 以 expert 身份登录
  - [ ] 验证本体菜单可见
  - [ ] 验证可以查看协作请求
  - [ ] 验证可以查看变更历史

### 第七阶段：新功能测试

#### 品牌系统功能测试

- [ ] 获取品牌主题
  ```bash
  curl http://localhost:8000/api/v1/brand/themes
  ```
- [ ] 获取品牌配置
  ```bash
  curl http://localhost:8000/api/v1/brand/config
  ```
- [ ] 获取 A/B 测试配置
  ```bash
  curl http://localhost:8000/api/v1/brand/ab-tests
  ```
- [ ] 在前端验证品牌功能
  - [ ] 检查主题切换功能
  - [ ] 检查品牌配置面板
  - [ ] 检查 A/B 测试功能

#### 管理配置功能测试

- [ ] 获取数据库配置
  ```bash
  curl http://localhost:8000/api/v1/admin/config/database
  ```
- [ ] 获取 LLM 配置
  ```bash
  curl http://localhost:8000/api/v1/admin/config/llm
  ```
- [ ] 获取同步策略
  ```bash
  curl http://localhost:8000/api/v1/admin/config/sync-strategy
  ```
- [ ] 在前端验证管理配置
  - [ ] 访问数据库配置页面
  - [ ] 访问 LLM 配置页面
  - [ ] 访问同步策略页面

#### AI 标注功能测试

- [ ] 获取 AI 标注方法
  ```bash
  curl http://localhost:8000/api/v1/ai/annotation-methods
  ```
- [ ] 获取标注缓存
  ```bash
  curl http://localhost:8000/api/v1/ai/annotation-cache
  ```
- [ ] 获取标注指标
  ```bash
  curl http://localhost:8000/api/v1/ai/annotation-metrics
  ```

#### 文本转 SQL 功能测试

- [ ] 获取 SQL 方法
  ```bash
  curl http://localhost:8000/api/v1/text-to-sql/methods
  ```
- [ ] 获取数据库架构
  ```bash
  curl http://localhost:8000/api/v1/text-to-sql/schema
  ```

#### 本体协作功能测试

- [ ] 获取协作专家
  ```bash
  curl http://localhost:8000/api/v1/ontology/collaboration/experts
  ```
- [ ] 获取协作历史
  ```bash
  curl http://localhost:8000/api/v1/ontology/collaboration/history
  ```

### 第八阶段：监控和日志

- [ ] 访问 Grafana 监控仪表板
  - [ ] 打开 http://localhost:3001
  - [ ] 使用 admin/admin 登录
  - [ ] 验证仪表板加载正常
  - [ ] 检查系统指标

- [ ] 访问 Prometheus
  - [ ] 打开 http://localhost:9090
  - [ ] 验证指标收集正常

- [ ] 查看容器日志
  ```bash
  docker compose logs -f app
  docker compose logs -f frontend
  docker compose logs -f postgres
  ```

### 第九阶段：性能测试

- [ ] 检查后端响应时间
  ```bash
  time curl http://localhost:8000/api/v1/admin/users
  ```
- [ ] 检查前端加载时间
  - [ ] 打开浏览器开发者工具
  - [ ] 检查页面加载时间
  - [ ] 检查网络请求时间

- [ ] 检查容器资源使用
  ```bash
  docker stats
  ```

### 第十阶段：最终验证

- [ ] 所有容器正常运行
- [ ] 所有服务可访问
- [ ] 所有功能测试通过
- [ ] 所有角色功能正常
- [ ] 监控仪表板正常
- [ ] 日志无错误

### 第十一阶段：提交和推送

- [ ] 提交测试结果
  ```bash
  git add .
  git commit -m "test: Verify all containers and functionality"
  git push origin feature/system-optimization
  ```

- [ ] 创建测试报告
  - [ ] 记录测试时间
  - [ ] 记录测试结果
  - [ ] 记录任何问题

## 📊 测试结果记录

| 项目 | 状态 | 备注 |
|------|------|------|
| Docker 环境 | ☐ | |
| 容器重建 | ☐ | |
| 服务验证 | ☐ | |
| 功能测试 | ☐ | |
| 管理员功能 | ☐ | |
| 标注员功能 | ☐ | |
| 专家功能 | ☐ | |
| 品牌系统 | ☐ | |
| 管理配置 | ☐ | |
| AI 标注 | ☐ | |
| 文本转 SQL | ☐ | |
| 本体协作 | ☐ | |
| 监控仪表板 | ☐ | |
| 性能测试 | ☐ | |

## 🎯 完成标志

- [ ] 所有检查项已完成
- [ ] 所有测试已通过
- [ ] 所有功能已验证
- [ ] 文档已更新
- [ ] 代码已提交

---

**开始时间**: _______________  
**完成时间**: _______________  
**测试人员**: _______________  
**备注**: _______________
