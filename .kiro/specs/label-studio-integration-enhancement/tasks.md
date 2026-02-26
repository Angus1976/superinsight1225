# 实施计划：Label Studio 集成增强

## 概述

按三层覆盖架构（Nginx → 容器启动 → 前端组件）逐层实现，每层独立可验证。

## 任务

- [x] 1. 翻译注入脚本与品牌样式
  - [x] 1.1 创建 `deploy/label-studio/i18n-inject.js`
    - 实现翻译词典、MutationObserver DOM 翻译、postMessage 语言切换监听
    - "Label Studio" → "问视间" 文本替换
    - 加载失败静默降级
    - _需求: 1.1, 1.2, 1.3, 1.5, 1.6, 4.4_
  - [x] 1.2 创建 `deploy/label-studio/branding.css`
    - 隐藏原始 Logo 替换为问视间 Logo，调整主题色
    - _需求: 5.1, 5.3, 5.5_
  - [x] 1.3 编写翻译函数属性测试
    - **属性 1: 翻译函数语言正确性**
    - **验证: 需求 1.1, 1.2, 4.4**

- [x] 2. 容器启动脚本扩展
  - [x] 2.1 扩展 `deploy/label-studio/entrypoint-sso.sh`
    - 复制 i18n-inject.js、branding.css、favicon 到 LS 静态目录
    - 修改 Django 模板注入 script/link 标签，替换 title
    - 标记检测防重复，失败输出错误日志
    - _需求: 1.4, 4.3, 5.2, 5.4, 6.1, 6.2, 6.4_
  - [x] 2.2 更新 `deploy/label-studio/Dockerfile` COPY 新文件
    - _需求: 1.4, 5.2_
  - [x] 2.3 编写补丁幂等性属性测试
    - **属性 5: 补丁脚本幂等性**
    - **验证: 需求 6.2**

- [x] 3. 检查点 - 部署层验证
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 4. Nginx 配置增强
  - [x] 4.1 修改 `deploy/tcb/config/nginx/nginx.conf` 添加 sub_filter
    - proxy_set_header Accept-Encoding ""、sub_filter 'Label Studio' '问视间'、sub_filter_types、sub_filter_once off
    - _需求: 4.1, 4.2, 4.5, 6.5_
  - [x] 4.2 修改 `deploy/private/nginx.conf` 同步 sub_filter 配置
    - _需求: 4.1, 4.2, 4.5, 6.5_

- [x] 5. 前端组件增强
  - [x] 5.1 增强 `LabelStudioEmbed.tsx`
    - 骨架屏替代 Spin、300ms 淡入动画、15 秒超时+重试、进度状态文本
    - _需求: 3.1, 3.2, 3.4, 3.5_
  - [x] 5.2 实现预热机制与语言缓存
    - 后台隐藏 iframe 预加载、pendingLanguage 缓存与同步
    - _需求: 2.3, 2.4, 3.3_
  - [x] 5.3 更新 `languageStore.ts` 添加 pendingLanguage 字段
    - _需求: 2.1, 2.2, 2.4_
  - [x] 5.4 编写语言切换消息属性测试
    - **属性 2: 语言切换消息发送**
    - **验证: 需求 2.1**
  - [x] 5.5 编写 URL 语言参数属性测试
    - **属性 3: URL 包含语言参数**
    - **验证: 需求 2.3**
  - [x] 5.6 编写语言缓存属性测试
    - **属性 4: 语言缓存与同步**
    - **验证: 需求 2.4**

- [x] 6. 翻译文件更新
  - [x] 6.1 更新前端 locale JSON 中 "Label Studio" 引用为 "问视间"，网站信息改为：www.wenshijian.com,其他信息一般更新为：问视间（上海）科技有限公司及相关英文WinsAI(Shanghai) Co.LTD
    - _需求: 4.4_

- [x] 7. 最终检查点
  - 确保所有测试通过，如有疑问请询问用户。

## 备注

- 标记 `*` 的子任务为可选，可跳过以加速 MVP
- 每个任务引用具体需求编号，确保可追溯
- 属性测试使用 fast-check 库
