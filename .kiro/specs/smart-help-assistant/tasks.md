# 任务清单：智能帮助助手 (Smart Help Assistant)

## 任务 1: 基础设施搭建
- [x] 1.1 创建 `frontend/src/stores/helpStore.ts`（Zustand store：visible, currentHelpKey, position, showHelp, hideHelp, toggleHelp）
- [x] 1.2 创建 `frontend/src/locales/zh/help.json` 和 `frontend/src/locales/en/help.json`（初始帮助内容：通用帮助、快捷键一览、主要页面帮助）
- [x] 1.3 在 `frontend/src/locales/config.ts` 中注册 help namespace（import help.json 并添加到 resources 和 ns 数组）
- [x] 1.4 创建 `frontend/src/types/help.ts`（HelpEntry, HelpContext, HelpState 类型定义）

## 任务 2: 核心 Hooks
- [x] 2.1 创建 `frontend/src/hooks/useHelpShortcut.ts`（全局键盘监听：F1 和 ? 触发，输入框内屏蔽 ?，组件卸载清理）
- [x] 2.2 创建 `frontend/src/hooks/useHelpContext.ts`（上下文解析：路由→page，data-help-key→component/element，回退逻辑）
- [x] 2.3 创建 `frontend/src/utils/helpUtils.ts`（resolveHelpKey、extractPageFromRoute、validateHelpKey 工具函数）

## 任务 3: UI 组件
- [x] 3.1 创建 `frontend/src/components/SmartHelp/HelpPopover.tsx`（基于 Ant Design Popover，读取 help namespace i18n 内容）
- [x] 3.2 创建 `frontend/src/components/SmartHelp/HelpIcon.tsx`（QuestionCircleOutlined 图标按钮，点击触发帮助）
- [x] 3.3 创建 `frontend/src/components/SmartHelp/HelpOverlay.tsx`（全局帮助浮层，从 helpStore 读取状态，支持 Esc 关闭和键盘导航）
- [x] 3.4 创建 `frontend/src/components/SmartHelp/index.ts`（统一导出）

## 任务 4: 集成
- [x] 4.1 在 App 根组件中挂载 useHelpShortcut 和 HelpOverlay
- [x] 4.2 在 1-2 个现有页面（如 Dashboard、Tasks）添加 data-help-key 属性和 HelpPopover/HelpIcon 示例

## 任务 5: 测试
- [x] 5.1 helpStore 单元测试（状态一致性：showHelp/hideHelp/toggleHelp）
- [x] 5.2 helpUtils 单元测试（resolveHelpKey 各种上下文组合、validateHelpKey 白名单校验）
- [x] 5.3 fast-check 属性测试（任意 HelpContext 解析到非空字符串、helpStore 状态不变量）
- [x] 5.4 useHelpShortcut 测试（快捷键触发、输入框屏蔽、卸载清理）
