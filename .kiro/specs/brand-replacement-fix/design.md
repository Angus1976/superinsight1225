# 品牌替换不完全 Bugfix Design

## Overview

Label Studio iframe 内部侧边栏仍显示原始品牌元素（logo、外部链接、版本号），前端 `IframeContainer.tsx` 和 `LabelStudioEmbed.tsx` 存在硬编码 "Label Studio" 字符串。修复策略：扩展现有 `branding.css` 隐藏/替换侧边栏品牌元素，扩展 `i18n-inject.js` 翻译侧边栏文本，将前端组件硬编码字符串替换为 i18n 翻译键。

## Glossary

- **Bug_Condition (C)**: iframe 内部侧边栏显示原始 Label Studio 品牌元素，或前端组件显示硬编码 "Label Studio" 字符串
- **Property (P)**: 侧边栏品牌被隐藏/替换为问视间品牌，前端组件使用 i18n 翻译键
- **Preservation**: 登录页、主导航、标注功能、Admin 页面品牌配置不受影响
- **branding.css**: `deploy/label-studio/branding.css`，通过 `entrypoint-sso.sh` 注入到 LS 静态目录的品牌覆盖样式
- **i18n-inject.js**: `deploy/label-studio/i18n-inject.js`，运行在 LS iframe 内部的 DOM 翻译脚本
- **IframeContainer**: `frontend/src/components/LabelStudio/IframeContainer.tsx`，iframe 容器组件
- **LabelStudioEmbed**: `frontend/src/components/LabelStudio/LabelStudioEmbed.tsx`，LS iframe 嵌入组件

## Bug Details

### Fault Condition

Bug 在三个层面同时存在：(1) CSS 未覆盖侧边栏 logo 区域和底部链接区域；(2) i18n 脚本未翻译侧边栏中的外部链接文本和版本号；(3) 前端组件硬编码 "Label Studio" 字符串未使用 i18n。

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type UIElement
  OUTPUT: boolean

  RETURN (input.location = "ls-iframe-sidebar-header" AND displaysOriginalLSBrand(input))
         OR (input.location = "ls-iframe-sidebar-footer" AND displaysExternalLinks(input))
         OR (input.location = "ls-iframe-sidebar-footer" AND displaysLSVersionNumber(input))
         OR (input.component IN ["IframeContainer", "LabelStudioEmbed"]
             AND containsHardcoded("Label Studio", input))
END FUNCTION
```

### Examples

- 侧边栏左上角显示 "Label Studio" logo 和文字 → 应显示 "问视间" 或隐藏
- 侧边栏底部显示 "API | Docs | GitHub | Slack Community" 链接 → 应移除或替换
- 侧边栏底部显示 "v1.22.0" 版本号 → 应隐藏或替换为 SuperInsight 版本
- `IframeContainer` Card 标题显示 "Label Studio" → 应使用 `t('labelStudio.title')`
- `LabelStudioEmbed` 错误消息显示 "Label Studio 加载错误" → 已有 i18n 键但 Card 标题仍硬编码

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- 登录页继续显示 `logo-wenshijian.svg`
- 主导航 ProLayout 继续显示 "问视间" 品牌
- LS 标注功能（提交、跳过、区域标注等）不受影响
- Admin/System 页面品牌配置继续正常工作
- `branding.css` 中已有的顶部导航栏 logo 替换和主题色覆盖继续生效
- `i18n-inject.js` 中已有的翻译词典继续正常工作
- Nginx `sub_filter` 文本替换继续生效

**Scope:**
不涉及侧边栏品牌元素和前端硬编码字符串的所有输入/交互不受影响。

## Hypothesized Root Cause

1. **branding.css 覆盖不完整**: 现有 CSS 只覆盖了顶部导航栏 `.ls-header` 的 logo，未覆盖侧边栏（LS 使用不同的 CSS 类名如 `.ls-sidebar`、`[class*="sidebar"]`）的 logo 区域和底部链接/版本号区域
2. **i18n-inject.js 词典缺失**: 翻译词典中没有侧边栏底部链接文本（"API"、"Docs"、"GitHub"、"Slack Community"）和版本号的条目，且这些元素可能需要 CSS 隐藏而非翻译
3. **前端组件未使用 i18n**: `IframeContainer.tsx` 的 Card `title="Label Studio"`、`Spin tip="Loading Label Studio..."`、`Alert message="Label Studio Error"` 均为硬编码字符串；`LabelStudioEmbed.tsx` 的 Card 标题 `<span>Label Studio</span>` 也是硬编码

## Correctness Properties

Property 1: Fault Condition - 侧边栏品牌元素被隐藏或替换

_For any_ LS iframe 页面加载后，侧边栏左上角 SHALL NOT 显示原始 "Label Studio" logo/文字，侧边栏底部 SHALL NOT 显示外部链接（API、Docs、GitHub、Slack Community）和原始版本号 v1.22.0。

**Validates: Requirements 2.1, 2.2**

Property 2: Fault Condition - 前端组件使用 i18n 翻译键

_For any_ `IframeContainer` 或 `LabelStudioEmbed` 组件渲染时，Card 标题、加载提示和错误消息 SHALL 使用 i18n 翻译键而非硬编码 "Label Studio" 字符串。

**Validates: Requirements 2.3**

Property 3: Preservation - 现有品牌替换和标注功能不受影响

_For any_ 不涉及侧边栏品牌元素的交互（登录页、主导航、标注操作、Admin 配置），修复后 SHALL 产生与修复前完全相同的行为。

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File 1**: `deploy/label-studio/branding.css`

1. **新增侧边栏 logo 隐藏规则**: 添加 CSS 选择器覆盖侧边栏左上角 logo 区域（`[class*="sidebar"] [class*="logo"]` 等），隐藏原始图片并用 `::after` 伪元素显示 "问视间"
2. **新增侧边栏底部链接隐藏规则**: 添加 CSS 选择器隐藏底部外部链接区域（`[class*="sidebar"] [class*="footer"]`、`[class*="sidebar"] a[href*="github"]` 等）
3. **新增版本号隐藏规则**: 隐藏侧边栏底部版本号显示

**File 2**: `deploy/label-studio/i18n-inject.js`

1. **扩展翻译词典**: 添加侧边栏可能残留的文本翻译条目（如 "API"、"Documentation" 等）
2. **添加 DOM 隐藏逻辑**: 对于外部链接和版本号，在 `translatePage()` 中添加选择器隐藏逻辑作为 CSS 的补充

**File 3**: `frontend/src/components/LabelStudio/IframeContainer.tsx`

1. **Card 标题**: `title="Label Studio"` → `title={t('labelStudio.title', '标注系统')}`
2. **加载提示**: `tip="Loading Label Studio..."` → `tip={t('labelStudio.loading', '正在加载标注系统...')}`
3. **错误标题**: `message="Label Studio Error"` → `message={t('labelStudio.loadErrorTitle', '标注系统加载错误')}`
4. **添加 i18n hook**: 引入 `useTranslation`

**File 4**: `frontend/src/components/LabelStudio/LabelStudioEmbed.tsx`

1. **Card 标题**: `<span>Label Studio</span>` → `<span>{t('labelStudio.title', '标注系统')}</span>`

## Testing Strategy

### Validation Approach

两阶段验证：先在未修复代码上确认 bug 存在，再验证修复后行为正确且不引入回归。

### Exploratory Fault Condition Checking

**Goal**: 在未修复代码上确认 bug 存在。

**Test Cases**:
1. **CSS 选择器测试**: 检查 `branding.css` 是否包含侧边栏相关选择器（当前不包含，确认缺失）
2. **i18n 词典测试**: 检查 `i18n-inject.js` 的 TRANSLATIONS 对象是否包含侧边栏链接文本（当前不包含）
3. **IframeContainer 硬编码测试**: 检查组件源码中是否存在硬编码 "Label Studio" 字符串（当前存在 3 处）
4. **LabelStudioEmbed 硬编码测试**: 检查 Card 标题是否硬编码（当前存在 1 处）

### Fix Checking

**Goal**: 验证修复后所有 bug 条件下行为正确。

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := renderWithFix(input)
  ASSERT NOT containsOriginalLSBrand(result)
  ASSERT usesI18nKeys(result)
END FOR
```

### Preservation Checking

**Goal**: 验证非 bug 条件下行为不变。

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT renderOriginal(input) = renderWithFix(input)
END FOR
```

### Unit Tests

- `IframeContainer` 渲染测试：验证 Card 标题、加载提示、错误消息使用 i18n 键
- `LabelStudioEmbed` 渲染测试：验证 Card 标题使用 i18n 键
- `branding.css` 选择器覆盖测试：验证新增选择器存在且语法正确

### Property-Based Tests

- 生成随机 i18n 语言配置，验证 IframeContainer 和 LabelStudioEmbed 不输出硬编码 "Label Studio"
- 验证 branding.css 补丁幂等性（与现有 patch-idempotency 测试模式一致）

### Integration Tests

- 完整 iframe 加载流程：验证侧边栏品牌元素被正确隐藏/替换
- 语言切换后：验证前端组件文本随语言变化
- 标注功能回归：验证标注提交、跳过等操作不受影响
