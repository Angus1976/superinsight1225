# Bugfix Requirements Document

## Introduction

品牌替换工作不完全。虽然 SuperInsight 平台自身的布局（登录页、主导航等）已完成品牌替换，但嵌入的 Label Studio iframe 内部仍然显示原始 Label Studio 品牌元素：

1. **侧边栏左上角** — 显示 "Label Studio" logo 和文字
2. **侧边栏底部** — 显示 Label Studio 的外部链接（API、Docs、GitHub、Slack Community）和版本号 v1.22.0

此外，前端 `IframeContainer.tsx` 组件中也存在硬编码的 "Label Studio" 字符串（Card 标题、加载提示、错误消息）。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN 用户在 SuperInsight 平台中打开包含 Label Studio iframe 的页面 THEN iframe 内部侧边栏左上角显示 "Label Studio" 原始 logo 和品牌文字

1.2 WHEN 用户在 SuperInsight 平台中打开包含 Label Studio iframe 的页面 THEN iframe 内部侧边栏底部显示 Label Studio 的外部链接（API、Docs、GitHub、Slack Community）和版本号 v1.22.0

1.3 WHEN IframeContainer 组件渲染时 THEN Card 标题显示硬编码的 "Label Studio" 文字，加载提示显示 "Loading Label Studio..."，错误消息显示 "Label Studio Error"

### Expected Behavior (Correct)

2.1 WHEN 用户在 SuperInsight 平台中打开包含 Label Studio iframe 的页面 THEN iframe 内部侧边栏左上角应显示 SuperInsight/问视间品牌 logo 和名称，或通过 CSS 注入/Django 模板覆盖隐藏原始 LS 品牌

2.2 WHEN 用户在 SuperInsight 平台中打开包含 Label Studio iframe 的页面 THEN iframe 内部侧边栏底部的外部链接（GitHub、Slack Community 等）应被移除或替换为公司自己的链接，版本号应反映 SuperInsight 版本

2.3 WHEN IframeContainer 组件渲染时 THEN Card 标题、加载提示和错误消息应使用 i18n 翻译键显示平台品牌名称（如"标注系统"或从系统配置读取品牌名），而非硬编码 "Label Studio"

### Unchanged Behavior (Regression Prevention)

3.1 WHEN 用户在登录页面时 THEN 系统 SHALL CONTINUE TO 显示 logo-wenshijian.svg 公司 logo

3.2 WHEN 用户在 SuperInsight 主导航（ProLayout 侧边栏）中时 THEN 系统 SHALL CONTINUE TO 显示 "问视间" 品牌名和 logo-wenshijian-simple.svg logo

3.3 WHEN Label Studio iframe 加载标注界面时 THEN 系统 SHALL CONTINUE TO 正常加载标注功能，不影响标注工作流

3.4 WHEN 系统管理员在 Admin/System 页面配置品牌信息时 THEN 系统 SHALL CONTINUE TO 支持自定义平台名称和品牌标识
