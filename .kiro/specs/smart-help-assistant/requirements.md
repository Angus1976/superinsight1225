# 需求文档：智能帮助助手 (Smart Help Assistant)

## 需求 1: 快捷键触发帮助

### 验收标准

1.1 Given 用户在任意页面，When 按下 F1 键，Then 显示当前上下文的帮助浮层
1.2 Given 用户在任意页面，When 按下 ? 键且焦点不在输入框内，Then 显示当前上下文的帮助浮层
1.3 Given 焦点在 INPUT/TEXTAREA/SELECT/contentEditable 内，When 按下 ? 键，Then 不触发帮助（避免干扰输入）
1.4 Given 帮助浮层已显示，When 按下 Esc 键或点击浮层外部，Then 关闭帮助浮层
1.5 Given 帮助浮层已显示，When 再次按下 F1 或 ?，Then 关闭帮助浮层（toggle 行为）

### 正确性属性

```
属性 1.A: ∀ event(key='?'), target ∈ {INPUT, TEXTAREA, SELECT, contentEditable} ⟹ helpStore.visible 不变
属性 1.B: useHelpShortcut 卸载后，全局 keydown 监听器被移除（无内存泄漏）
```

---

## 需求 2: 上下文感知帮助

### 验收标准

2.1 Given 用户在某个页面，When 触发帮助，Then 系统自动检测当前路由并映射到页面标识（如 '/dashboard' → 'dashboard'）
2.2 Given 聚焦元素有 `data-help-key` 属性，When 触发帮助，Then 显示该元素对应的具体帮助内容
2.3 Given 聚焦元素无 `data-help-key` 属性，When 触发帮助，Then 回退到页面级帮助内容
2.4 Given 帮助键在 i18n 中不存在，When 触发帮助，Then 按优先级回退：element → component → page → 通用帮助

### 正确性属性

```
属性 2.A: ∀ context: HelpContext, resolveHelpKey(context) 返回非空字符串
属性 2.B: ∀ context: HelpContext, resolveHelpKey(context) 返回的键在 help namespace 中存在
属性 2.C: data-help-key 值只接受 [a-zA-Z0-9._] 格式
```

---

## 需求 3: 帮助内容展示

### 验收标准

3.1 Given 帮助被触发，When 帮助浮层显示，Then 展示标题（title）和描述（description），可选展示快捷键提示（shortcut）
3.2 Given 组件使用 HelpPopover 包裹，When 鼠标悬停在目标元素上，Then 显示对应帮助内容
3.3 Given 组件旁有 HelpIcon，When 点击帮助图标，Then 显示对应帮助内容
3.4 Given HelpPopover 包裹了按钮/输入框，When 用户正常操作该元素，Then 元素原有功能不受影响

### 正确性属性

```
属性 3.A: helpStore.visible === true ⟹ helpStore.currentHelpKey !== null
属性 3.B: helpStore.visible === false ⟹ helpStore.currentHelpKey === null
属性 3.C: ∀ helpEntry, title.length ≤ 20 ∧ description.length ≤ 100
```

---

## 需求 4: 国际化支持

### 验收标准

4.1 Given 帮助内容存储在 `locales/zh/help.json` 和 `locales/en/help.json`，When 系统加载，Then 帮助内容通过 i18n help namespace 提供
4.2 Given 用户切换语言（zh ↔ en），When 帮助浮层正在显示，Then 帮助内容实时更新为目标语言
4.3 Given 帮助内容在某语言下缺失，When 触发帮助，Then 回退到 fallback 语言（zh）的内容
4.4 Given i18n config 已注册 help namespace，When 应用启动，Then help 翻译资源正确加载

### 正确性属性

```
属性 4.A: ∀ helpKey, ∀ lang ∈ {'zh', 'en'}, languageStore.language === lang ⟹ 帮助内容显示 lang 下的翻译
```

---

## 需求 5: 帮助内容管理

### 验收标准

5.1 Given 开发者需要为新元素添加帮助，When 在元素上添加 `data-help-key` 属性并在 help.json 中添加对应翻译，Then 帮助系统自动识别并展示
5.2 Given help.json 中定义了帮助条目，When 条目包含 `related` 字段，Then 帮助浮层可展示关联帮助链接
5.3 Given 开发环境，When 某个 data-help-key 在 help.json 中不存在，Then 控制台输出警告信息

---

## 需求 6: 无障碍与键盘导航

### 验收标准

6.1 Given 帮助浮层显示，When 用户按 Tab 键，Then 可在帮助内容区域内导航
6.2 Given 帮助浮层显示，When 屏幕阅读器激活，Then 帮助内容通过 ARIA 属性正确朗读
6.3 Given HelpIcon 组件，When 键盘聚焦并按 Enter，Then 触发帮助显示

