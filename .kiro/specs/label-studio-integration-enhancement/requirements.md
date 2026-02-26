# 需求文档：Label Studio 集成增强

## 简介

本功能旨在增强问视间平台与 Label Studio 的集成体验，在不修改 Label Studio 核心代码的前提下，通过外部覆盖方案（nginx sub_filter、容器启动脚本注入、CSS/JS 覆盖）实现三大目标：国际化中文支持、平滑跳转体验、统一品牌展示。所有定制均为外部层叠式，确保 Label Studio 升级时可快速重新集成。

## 术语表

- **问视间平台**：本项目的主应用系统（SuperInsight），包含前端和后端
- **标注系统**：嵌入在问视间平台中的 Label Studio 实例，通过 iframe 加载
- **Nginx_代理**：负责将 `/label-studio/` 路径请求转发至标注系统容器的反向代理
- **启动脚本**：容器启动时执行的 `entrypoint-sso.sh` 脚本，用于运行时补丁
- **翻译注入脚本**：通过启动脚本注入到标注系统中的自定义 JavaScript 文件，负责运行时 DOM 文本翻译
- **品牌覆盖样式**：通过启动脚本注入到标注系统中的自定义 CSS 文件，负责替换品牌视觉元素
- **iframe_嵌入组件**：问视间前端中负责加载和管理标注系统 iframe 的 React 组件（LabelStudioEmbed）

## 需求

### 需求 1：标注系统前端界面中文翻译

**用户故事：** 作为标注人员，我希望标注系统的界面显示中文，以便我能更高效地理解和操作标注工具。

#### 验收标准

1. WHEN 问视间平台语言设置为中文时，THE 翻译注入脚本 SHALL 将标注系统 React 界面中的英文 UI 文本替换为对应的中文翻译
2. WHEN 问视间平台语言设置为英文时，THE 翻译注入脚本 SHALL 保持标注系统界面显示原始英文文本
3. THE 翻译注入脚本 SHALL 覆盖标注系统中以下核心界面元素的翻译：导航菜单、按钮标签、表单标签、提示信息、数据管理表头、标注工具栏
4. THE 启动脚本 SHALL 在容器启动时将翻译注入脚本复制到标注系统的静态资源目录中
5. IF 翻译注入脚本加载失败，THEN THE 标注系统 SHALL 回退显示原始英文界面，且不影响标注功能的正常使用
6. THE 翻译注入脚本 SHALL 使用 MutationObserver 监听 DOM 变化，确保动态加载的内容也能被翻译

### 需求 2：语言切换同步机制

**用户故事：** 作为标注人员，我希望在问视间平台切换语言后，标注系统能同步切换语言，无需手动操作。

#### 验收标准

1. WHEN 用户在问视间平台切换语言时，THE iframe_嵌入组件 SHALL 通过 postMessage 将新的语言设置发送给标注系统
2. WHEN 翻译注入脚本接收到语言切换消息时，THE 翻译注入脚本 SHALL 在 500 毫秒内完成界面文本的切换，无需重新加载 iframe
3. THE iframe_嵌入组件 SHALL 在构建标注系统 URL 时包含当前语言参数
4. WHILE 标注系统 iframe 尚未加载完成时，THE iframe_嵌入组件 SHALL 缓存语言设置，并在加载完成后立即同步

### 需求 3：平滑跳转体验

**用户故事：** 作为标注人员，我希望从任务列表跳转到标注界面时有流畅的过渡效果，而不是看到空白加载页面。

#### 验收标准

1. WHEN 用户从任务列表导航至标注界面时，THE iframe_嵌入组件 SHALL 显示与标注系统布局匹配的骨架屏加载动画
2. WHEN 标注系统 iframe 加载完成时，THE iframe_嵌入组件 SHALL 使用淡入动画（持续时间 300 毫秒）过渡到实际内容
3. THE iframe_嵌入组件 SHALL 在用户可能导航至标注界面之前预加载 iframe（后台预热），以减少实际导航时的加载等待时间
4. IF 标注系统 iframe 在 15 秒内未加载完成，THEN THE iframe_嵌入组件 SHALL 显示友好的超时提示，并提供重试按钮
5. THE iframe_嵌入组件 SHALL 在加载过程中显示进度指示器，包含"正在连接标注系统"等状态文本

### 需求 4：品牌白标化 — 文本替换

**用户故事：** 作为产品负责人，我希望标注系统中所有 "Label Studio" 文字都替换为 "问视间"，以保持品牌一致性。

#### 验收标准

1. THE Nginx_代理 SHALL 使用 sub_filter 指令将标注系统 HTML 响应中的 "Label Studio" 文本替换为 "问视间"
2. THE Nginx_代理 SHALL 将 sub_filter 应用于 text/html 和 application/javascript 类型的响应
3. THE 启动脚本 SHALL 修改标注系统的 Django 模板，将页面 title 标签中的 "Label Studio" 替换为 "问视间"
4. THE 翻译注入脚本 SHALL 在运行时将 DOM 中残留的 "Label Studio" 文本节点替换为 "问视间"
5. THE Nginx_代理 SHALL 配置 proxy_set_header Accept-Encoding "" 以确保 sub_filter 能正确处理未压缩的响应内容

### 需求 5：品牌白标化 — 视觉元素替换

**用户故事：** 作为产品负责人，我希望标注系统的 Logo、Favicon 和视觉风格与问视间品牌保持一致。

#### 验收标准

1. THE 品牌覆盖样式 SHALL 隐藏标注系统原始 Logo 并替换为问视间 Logo
2. THE 启动脚本 SHALL 将问视间的 Favicon 文件复制到标注系统的静态资源目录，替换原始 Favicon
3. THE 品牌覆盖样式 SHALL 将标注系统的主题色调整为与问视间品牌色一致
4. THE 启动脚本 SHALL 在容器启动时将品牌覆盖样式文件注入到标注系统的 HTML 模板中
5. IF 品牌覆盖样式加载失败，THEN THE 标注系统 SHALL 正常显示原始界面，不影响标注功能

### 需求 6：升级兼容性保障

**用户故事：** 作为开发人员，我希望所有定制方案都不修改 Label Studio 核心代码，以便未来升级时能快速重新集成。

#### 验收标准

1. THE 启动脚本 SHALL 在每次容器启动时重新应用所有补丁，确保容器镜像更新后补丁自动生效
2. THE 启动脚本 SHALL 使用标记检测机制（grep 检查标记字符串），避免重复应用补丁
3. THE 翻译注入脚本 SHALL 独立于标注系统的代码结构，仅通过 DOM 操作和 CSS 选择器实现功能
4. IF 启动脚本中的补丁目标文件路径发生变化（因标注系统升级），THEN THE 启动脚本 SHALL 输出明确的错误日志，指明哪个补丁未能成功应用
5. THE Nginx_代理 中的 sub_filter 配置 SHALL 独立于标注系统版本，仅依赖 HTTP 响应内容进行文本替换
