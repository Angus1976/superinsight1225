# Label Studio 集成需求文档

## 1. 项目概述

### 1.1 背景
SuperInsight 平台需要集成 Label Studio 作为数据标注引擎。Label Studio Community Edition 不支持 iframe 嵌入集成，需要采用新窗口打开的方式。

### 1.2 目标
- 为用户提供流畅的标注体验
- 解决 Label Studio Community Edition 的认证限制
- 确保用户能够直接访问标注界面而非仪表盘

### 1.3 范围
- 任务详情页的"在新窗口中打开"功能
- 标注页面的引导界面
- Label Studio URL 配置和路由

## 2. 用户故事

### 2.1 作为标注员，我希望能够快速开始标注任务
**验收标准**:
- 点击"开始标注"按钮后，显示清晰的引导界面
- 引导界面提供"在新窗口中打开 Label Studio"按钮
- 点击按钮后，在新窗口中打开 Label Studio 数据管理器
- 数据管理器显示项目的所有待标注任务

### 2.2 作为标注员，我希望能够从任务详情页直接打开 Label Studio
**验收标准**:
- 任务详情页显示"在新窗口中打开"按钮
- 点击按钮后，在新窗口中打开 Label Studio 数据管理器
- 如果项目不存在，自动跳转到标注页面创建项目

### 2.3 作为标注员，我希望看到标注任务列表而非仪表盘
**验收标准**:
- 打开的 URL 指向 `/projects/{projectId}/data` 端点
- 页面显示任务列表，包含"Label All Tasks"按钮
- 用户可以点击单个任务进行标注
- 用户可以批量标注所有任务

## 3. 功能需求

### 3.1 URL 路由配置
**需求**: 使用正确的 Label Studio URL 端点

**详细说明**:
- **错误 URL**: `/projects/{projectId}` - 显示项目仪表盘
- **正确 URL**: `/projects/{projectId}/data` - 显示数据管理器（任务列表）

**实现位置**:
- `frontend/src/pages/Tasks/TaskDetail.tsx` - `handleOpenInNewWindow` 函数
- `frontend/src/pages/Tasks/TaskAnnotate.tsx` - 引导界面中的按钮

### 3.2 引导界面设计
**需求**: 在标注页面显示清晰的引导信息

**详细说明**:
- 使用 Ant Design `Result` 组件
- 显示信息图标（蓝色）
- 标题: "请在新窗口中进行标注"
- 说明文字:
  - Label Studio Community Edition 需要在独立窗口中使用
  - 列出用户可以执行的操作
  - 显示当前项目 ID 和任务进度
- 操作按钮:
  - 主按钮: "在新窗口中打开 Label Studio"
  - 次要按钮: "返回任务详情"

### 3.3 项目验证和创建
**需求**: 自动处理项目不存在的情况

**详细说明**:
- 检查任务是否有 `label_studio_project_id`
- 如果没有，提示用户"项目尚未创建，正在跳转到标注页面..."
- 跳转到标注页面，自动创建项目
- 创建成功后，用户可以使用"在新窗口中打开"功能

### 3.4 认证处理
**需求**: 使用 Personal Access Token 认证

**详细说明**:
- Label Studio Community Edition 使用 session-based 认证
- 用户需要先在 Label Studio 中登录
- 登录后，session cookie 会保存在浏览器中
- 新窗口会自动使用相同的 session

**配置**:
```env
LABEL_STUDIO_API_TOKEN=fdf4c143512bf61cc1a51ac7a2fa0f429131a7a8
LABEL_STUDIO_SSO_ENABLED=false
```

## 4. 非功能需求

### 4.1 性能
- 新窗口打开响应时间 < 1 秒
- Label Studio 页面加载时间 < 3 秒

### 4.2 可用性
- 引导界面清晰易懂
- 按钮位置明显
- 错误提示友好

### 4.3 兼容性
- 支持 Chrome、Firefox、Safari、Edge 最新版本
- 支持 Label Studio Community Edition 1.x

## 5. 约束条件

### 5.1 技术约束
- Label Studio Community Edition 不支持 iframe 集成
- 不支持 JWT 认证（仅 Enterprise Edition）
- 不支持 URL 参数传递 token
- 需要 session-based 认证（Cookie）

### 5.2 业务约束
- 用户必须先登录 Label Studio
- 无法在 SuperInsight 界面内嵌入标注功能
- 需要在新窗口中操作

## 6. 依赖关系

### 6.1 外部依赖
- Label Studio Community Edition 服务运行正常
- Docker 容器网络配置正确
- 浏览器支持 Cookie 和新窗口

### 6.2 内部依赖
- 任务管理系统
- 项目管理系统
- 认证系统

## 7. 风险和缓解措施

### 7.1 风险: Label Studio 服务不可用
**缓解措施**:
- 显示友好的错误提示
- 提供重试按钮
- 提供返回任务列表的选项

### 7.2 风险: 用户未登录 Label Studio
**缓解措施**:
- 在引导界面中说明需要先登录
- 提供 Label Studio 登录页面链接
- 显示登录步骤说明

### 7.3 风险: URL 配置错误
**缓解措施**:
- 使用环境变量配置 Label Studio URL
- 提供默认值 fallback
- 在开发环境中显示完整 URL 用于调试

## 8. 验收标准

### 8.1 功能验收
- [ ] 点击"开始标注"显示引导界面
- [ ] 点击"在新窗口中打开 Label Studio"打开正确的 URL
- [ ] 新窗口显示数据管理器（任务列表）
- [ ] 可以看到"Label All Tasks"按钮
- [ ] 可以点击单个任务进行标注
- [ ] 项目不存在时自动创建

### 8.2 用户体验验收
- [ ] 引导界面清晰易懂
- [ ] 按钮位置明显
- [ ] 错误提示友好
- [ ] 操作流程顺畅

### 8.3 技术验收
- [ ] URL 格式正确: `/projects/{projectId}/data`
- [ ] 环境变量配置正确
- [ ] Docker 容器运行正常
- [ ] 认证机制工作正常

## 9. 测试场景

### 9.1 正常流程测试
1. 用户登录 SuperInsight
2. 进入任务详情页
3. 点击"开始标注"
4. 看到引导界面
5. 点击"在新窗口中打开 Label Studio"
6. 新窗口显示数据管理器
7. 点击"Label All Tasks"开始标注

### 9.2 项目不存在测试
1. 用户登录 SuperInsight
2. 进入任务详情页（项目未创建）
3. 点击"在新窗口中打开"
4. 看到提示"项目尚未创建，正在跳转到标注页面..."
5. 跳转到标注页面
6. 自动创建项目
7. 可以使用"在新窗口中打开"功能

### 9.3 错误处理测试
1. Label Studio 服务停止
2. 点击"在新窗口中打开 Label Studio"
3. 看到友好的错误提示
4. 可以点击重试或返回

## 10. 文档需求

### 10.1 用户文档
- 如何使用 Label Studio 进行标注
- 如何登录 Label Studio
- 常见问题解答

### 10.2 开发文档
- Label Studio 集成架构
- URL 配置说明
- 认证机制说明
- 故障排查指南

## 11. 国际化（i18n）支持

### 11.1 前端国际化
**需求**: 前端界面支持中英文切换，默认中文

**详细说明**:
- 所有界面文本使用 i18n 翻译键
- 默认语言为中文（zh-CN）
- 支持语言切换（中文/English）
- 语言选择持久化到 localStorage
- 遵循 i18n 翻译规范

**实现位置**:
- `frontend/src/locales/zh/tasks.json` - 任务相关中文翻译
- `frontend/src/locales/en/tasks.json` - 任务相关英文翻译
- `frontend/src/pages/Tasks/index.tsx` - 使用翻译键

### 11.2 Label Studio 语言同步
**需求**: Label Studio 跟随前端语言切换

**详细说明**:
- 前端切换语言时，Label Studio 也切换语言
- 支持中文和英文标注界面
- 使用 Label Studio 的 Django i18n 机制
- 通过 URL 参数传递语言设置

**实现方式**:
```typescript
// 在打开 Label Studio 时传递语言参数
const labelStudioUrl = `http://localhost:8080/projects/${projectId}/data?lang=${language}`;
```

### 11.3 翻译键命名规范
**需求**: 遵循项目 i18n 翻译规范

**详细说明**:
- 使用 camelCase 命名
- 对象类型键用于模块分组
- 字符串类型键用于简单文本
- 避免重复键定义
- 保持中英文文件结构一致

**示例**:
```json
{
  "tasks": {
    "title": "标注任务",
    "list": {
      "refresh": "刷新",
      "export": "导出数据",
      "create": "创建任务",
      "sync": "同步所有任务"
    },
    "status": {
      "pending": "待处理",
      "inProgress": "进行中",
      "completed": "已完成",
      "cancelled": "已取消"
    }
  }
}
```

### 11.4 默认语言设置
**需求**: 系统默认使用中文界面

**详细说明**:
- i18n 配置默认语言为 zh-CN
- 首次访问显示中文界面
- 用户可以手动切换语言
- 语言选择保存到 localStorage

**配置**:
```typescript
// frontend/src/i18n/config.ts
i18n.use(initReactI18next).init({
  lng: 'zh', // 默认中文
  fallbackLng: 'zh',
  defaultNS: 'common',
  // ...
});
```

## 12. 任务列表页面功能增强

### 11.1 刷新功能增强
**需求**: 刷新按钮不仅同步"Annotation Project"，还要同步上级的"Projects"列表

**详细说明**:
- 当前刷新只更新任务列表数据
- 需要同时同步 Label Studio 项目状态
- 需要同步项目的标注进度
- 需要更新项目的任务数量

**实现位置**:
- `frontend/src/pages/Tasks/index.tsx` - 刷新按钮处理函数
- 需要调用 Label Studio API 获取项目列表
- 需要更新本地任务的 Label Studio 相关字段

### 11.2 导出数据功能
**需求**: 导出按钮能够导出任务数据和标注结果

**详细说明**:
- 支持导出选中的任务
- 支持导出所有任务
- 导出格式: CSV, JSON, Excel
- 包含任务基本信息和标注结果

### 11.3 创建任务功能
**需求**: 创建任务按钮能够创建新的标注任务

**详细说明**:
- 打开创建任务对话框
- 填写任务基本信息
- 自动创建 Label Studio 项目
- 导入初始数据

### 11.4 编辑功能
**需求**: 编辑按钮能够修改任务信息

**详细说明**:
- 修改任务名称、描述
- 修改任务状态、优先级
- 修改分配人员
- 修改截止日期

### 11.5 删除功能
**需求**: 删除按钮能够删除任务

**详细说明**:
- 单个删除
- 批量删除
- 删除确认对话框
- 同时删除 Label Studio 项目（可选）

## 12. 未来改进

### 12.1 升级到 Enterprise Edition
- 支持 iframe 集成
- 支持 JWT 认证
- 支持 Embed SDK

### 12.2 增强功能
- 实时进度同步
- 标注质量监控
- 自动保存和恢复

### 12.3 用户体验优化
- 减少窗口切换
- 提供快捷键支持
- 优化移动端体验
