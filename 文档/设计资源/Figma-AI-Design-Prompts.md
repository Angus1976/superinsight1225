# 问视间 (SuperInsight) — Figma AI 设计提示词

> 共 6 段提示词，按顺序使用。Prompt 1 建立设计系统基础，后续 Prompt 引用该基础。
> 风格定位：时尚商务风（Modern Business Elegance）
> 双主题：明亮模式 (Light) + 睿黑模式 (Dark)
> 双语言：中文 (zh) + English (en)

---

## Prompt 1 — 设计系统基础 (Design System Foundation)

```
Design a comprehensive design system for "SuperInsight" (问视间), an enterprise AI data annotation and management platform. Style: Modern Business Elegance — clean, sophisticated, professional yet approachable with subtle tech-forward accents.

BRAND IDENTITY:
- Product name: 问视间 (Chinese) / SuperInsight (English)
- Logo variants: Standard (120×120), Simple (64×64), Full (280×80), Favicon (32×32)
- Brand personality: Intelligent, Trustworthy, Efficient, Modern

COLOR TOKENS — LIGHT MODE ("明亮"):
- Primary: #1890FF (hover: #40A9FF, active: #096DD9, light: #E6F7FF)
- Success: #52C41A (hover: #73D13D, active: #389E0D, light: #F6FFED)
- Warning: #FAAD14 (hover: #FFC53D, active: #D48806, light: #FFFBE6)
- Error: #FF4D4F (hover: #FF7875, active: #D9363E, light: #FFF2F0)
- Accent: #722ED1
- Background: #FFFFFF, Secondary BG: #FAFAFA, Tertiary BG: #F5F5F5
- Text: rgba(0,0,0,0.88), Secondary: rgba(0,0,0,0.65), Tertiary: rgba(0,0,0,0.45), Disabled: rgba(0,0,0,0.25)
- Border: #D9D9D9, Secondary border: #F0F0F0
- Surface/Card: #FFFFFF with shadow 0 1px 2px rgba(0,0,0,0.03)

COLOR TOKENS — DARK MODE ("睿黑"):
- Same primary/success/warning/error hues, adjusted for dark backgrounds
- Background: #141414, Secondary BG: #1F1F1F, Tertiary BG: #262626
- Text: rgba(255,255,255,0.88), Secondary: rgba(255,255,255,0.65), Tertiary: rgba(255,255,255,0.45)
- Border: rgba(255,255,255,0.12)
- Surface/Card: #1F1F1F with shadow 0 2px 8px rgba(0,0,0,0.36)

TYPOGRAPHY:
- Font family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC" (for Chinese)
- Code font: "SF Mono", Consolas, "Liberation Mono", Menlo, monospace
- Scale: H1=38px, H2=30px, H3=24px, H4=20px, H5=16px, Body=14px, Caption=12px
- Line height: 1.5714 (body), 1.5 (large), 1.667 (small)
- Weights: Regular=400, Medium=500, Semibold=600, Bold=700

SPACING SCALE: 4 / 8 / 12 / 16 / 24 / 32 / 48 px

BORDER RADIUS: XS=2, SM=4, Base=6, LG=8, XL=12, Full=9999 px

SHADOWS:
- SM: 0 1px 2px rgba(0,0,0,0.03), 0 1px 6px -1px rgba(0,0,0,0.02)
- Base: 0 6px 16px rgba(0,0,0,0.08), 0 3px 6px -4px rgba(0,0,0,0.12)
- Card: 0 1px 2px -2px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.12), 0 5px 12px 4px rgba(0,0,0,0.09)

ANIMATION: Duration fast=0.1s, base=0.2s, slow=0.3s. Easing: cubic-bezier(0.645, 0.045, 0.355, 1)

BREAKPOINTS: Mobile <576px, Tablet 576-991px, Desktop ≥992px, Wide ≥1200px, Ultra ≥1600px

Create a token reference sheet showing all values side-by-side for Light and Dark modes. Include a color palette swatch grid, typography specimen, spacing ruler, and icon style guide (outlined, 1.5px stroke, rounded caps, matching Ant Design 5 icon style).
```

---

## Prompt 2 — 核心组件库 (Core Component Library)

```
Using the SuperInsight design system (Primary: #1890FF, Modern Business Elegance style), design a component library page showing BOTH Light and Dark theme variants side by side.

BUTTONS:
- Primary (filled #1890FF), Default (outlined), Dashed, Text, Link
- States: default, hover, active, disabled, loading
- Sizes: Large (40px height), Medium (32px), Small (24px)
- Icon buttons: with left icon, right icon, icon-only (circle)
- Danger variant for destructive actions

FORM CONTROLS:
- Input: text, password (with toggle), number, textarea
- Select: single, multi-select with tags, searchable dropdown
- DatePicker: single date, date range
- Checkbox, Radio, Switch (toggle)
- Upload: drag-and-drop zone, file list
- States: default, focus (blue glow), error (red border + message), disabled
- Labels in both Chinese and English examples

CARDS:
- Basic card with title, subtitle, body, footer actions
- Statistic card (number + trend arrow + sparkline)
- Task card (status badge, progress bar, assignee avatar)
- Hover effect: translateY(-2px) + elevated shadow

TABLES (ProTable style):
- Header with search bar, filter chips, column settings gear icon
- Row with checkbox, avatar, text columns, status tag, action buttons
- Pagination bar at bottom
- Expandable row variant
- Sortable column headers with arrow indicators
- Empty state illustration

TAGS & BADGES:
- Status tags: Processing (blue), Success (green), Warning (orange), Error (red), Default (gray)
- Notification badge (red dot, number badge)
- User role badge

NAVIGATION:
- Breadcrumb with separator
- Tabs: line style, card style
- Steps: horizontal progress stepper
- Pagination

FEEDBACK:
- Alert: info, success, warning, error (with icon, closable)
- Message: toast notification (top center)
- Modal: confirmation dialog with icon, title, description, two buttons
- Drawer: right-side panel with header and close button
- Tooltip: dark bg with arrow (light mode), light bg (dark mode)
- Popover: rich content popup with title

Show each component in both 明亮 (Light) and 睿黑 (Dark) themes. Use Chinese text for labels where appropriate (e.g., "搜索", "确定", "取消", "提交").
```

---


## Prompt 3 — 应用外壳与导航 (App Shell & Navigation Layout)

```
Design the main application shell for SuperInsight (问视间), an enterprise AI platform. Modern Business Elegance style. Show BOTH Light and Dark themes, BOTH Chinese and English language versions (4 combinations total).

SIDEBAR NAVIGATION (left, collapsible):
- Width: expanded 256px, collapsed 64px
- Logo area at top: "问视间" wordmark (expanded) / icon mark (collapsed)
- Navigation groups with section headers:
  · 工作台: Dashboard (仪表盘), AI Assistant (AI 助手)
  · 数据管理: Tasks (标注任务), Data Structuring (数据结构化), Data Sync (数据同步)
  · AI 能力: AI Annotation (AI 标注), Augmentation (数据增强)
  · 质量与安全: Quality (质量管理), Security (安全中心)
  · 系统管理: Admin (管理后台), Settings (系统设置), Billing (计费管理), License (许可证)
- Each item: icon (Ant Design outlined style) + label
- Active state: primary color left border + light primary background
- Hover: subtle background tint
- Collapse toggle button at bottom
- Dark mode sidebar: #141414 bg, lighter text

HEADER BAR (top, 56px height):
- Left: Breadcrumb (e.g., 工作台 / 仪表盘)
- Center: Global search input (expandable, with ⌘K shortcut hint)
- Right actions row:
  · Language switcher: "中" / "EN" toggle pill
  · Theme switcher: sun/moon icon toggle
  · Notification bell with red badge count
  · Help button (? icon, triggers SmartHelp)
  · User avatar dropdown (name, role, settings, logout)
- Subtle bottom border or shadow separator

CONTENT AREA:
- Page title zone: H3 title + optional subtitle + action buttons (right-aligned)
- Content padding: 24px
- Max content width: 1600px centered on ultra-wide screens
- Background: #F5F5F5 (light) / #141414 (dark)

RESPONSIVE BEHAVIOR:
- Desktop (≥992px): sidebar + header + content
- Tablet (576-991px): collapsed sidebar, hamburger menu in header
- Mobile (<576px): hidden sidebar, full-width content, bottom tab bar for key nav items

Show a complete frame for each of the 4 combinations:
1. Light + Chinese
2. Light + English
3. Dark + Chinese
4. Dark + English
```

---

## Prompt 4 — 核心业务页面 Part 1 (Dashboard, Tasks, AI Features)

```
Design key business pages for SuperInsight (问视间) using the established design system (Primary #1890FF, Modern Business Elegance). Show Light and Dark variants for each page. Use Chinese labels with English shown in parentheses where helpful.

PAGE 1 — DASHBOARD (仪表盘):
- Welcome banner: "欢迎回来, [用户名]" with date/time, subtle gradient accent
- Row of 4 statistic cards: 总任务数, 进行中, 已完成, 待审核 — each with icon, number, trend percentage arrow, mini sparkline
- Chart section (2 columns):
  · Left: Area chart — "标注进度趋势" (7-day annotation progress)
  · Right: Donut chart — "任务状态分布" (task status distribution)
- Recent activity feed: timeline list with avatar, action description, timestamp
- Quick actions bar: "新建任务", "导入数据", "查看报告" buttons

PAGE 2 — TASKS LIST (标注任务列表):
- ProTable layout with toolbar:
  · Search input, status filter dropdown, date range picker, "新建任务" primary button
  · Column settings gear, density toggle, refresh button
- Table columns: checkbox, task name, type tag, status tag (color-coded), progress bar (%), assignee avatars (stacked), created date, actions (view/edit/delete icons)
- Batch action bar (appears when rows selected): "批量导出", "批量删除", "批量分配"
- Empty state: illustration + "暂无任务，点击新建开始" message

PAGE 3 — TASK DETAIL (任务详情):
- Header: task name (H3), status badge, edit/delete/export action buttons
- Tab navigation: 概览, 标注, 统计, 设置
- Overview tab content:
  · Info card: type, created by, created date, deadline, description
  · Progress section: circular progress ring + milestone timeline
  · Team section: assignee list with avatar, name, role, annotation count

PAGE 4 — AI ASSISTANT (AI 助手):
- Chat interface layout:
  · Left panel (280px): conversation history list with search
  · Main area: chat messages (user right-aligned blue bubble, AI left-aligned gray bubble)
  · Input area at bottom: textarea + send button + attachment icon + model selector dropdown
- AI response formatting: markdown rendering, code blocks with syntax highlighting, data tables
- Suggested prompts: pill-shaped quick action buttons above input

PAGE 5 — DATA STRUCTURING (数据结构化):
- Step wizard header: Upload → Preview → Schema → Results (4 steps, current step highlighted)
- Upload page: large drag-and-drop zone with file type icons (PDF, Excel, CSV, Word), file list below with progress bars
- Schema editor: split view — left: source data preview, right: schema tree editor with field mapping lines
- Results page: structured data table with export options (JSON, CSV, Excel)

For each page, show both Light and Dark theme. Maintain consistent spacing, card styles, and typography from the design system.
```

---


## Prompt 5 — 核心业务页面 Part 2 (Admin, Security, Quality, Data Sync)

```
Continue designing pages for SuperInsight (问视间). Same design system (Primary #1890FF, Modern Business Elegance). Show Light and Dark variants. Chinese labels.

PAGE 6 — ADMIN CONSOLE (管理控制台):
- Overview dashboard with system health cards: CPU, Memory, Storage, Active Users — each with gauge or progress ring
- Quick stats row: total tenants, total users, active tasks, API calls today
- System alerts list: severity icon (info/warning/error) + message + timestamp
- Navigation tabs: 控制台, 租户管理, 用户管理, 权限配置, 配额管理, 计费管理, LLM 配置, 系统设置

PAGE 7 — ADMIN LLM CONFIG (LLM 配置):
- Provider cards grid: each card shows provider logo, name, status badge (active/inactive), model count
- Selected provider detail panel:
  · Connection settings form: API endpoint, API key (masked), timeout, max tokens
  · Model list table: model name, type, status toggle, priority, test button
  · Test result panel: latency, token usage, sample output

PAGE 8 — SECURITY CENTER (安全中心):
- Security score card: large circular score (0-100) with color gradient, breakdown categories
- Tab navigation: 审计日志, 权限管理, RBAC, SSO, 会话管理, 数据权限
- Audit log tab: filterable table with timestamp, user, action, resource, IP, status (success/denied)
- RBAC tab: role hierarchy tree view (left) + permission matrix grid (right, checkboxes)
- SSO tab: provider cards (SAML, OAuth, LDAP) with enable toggle and config form

PAGE 9 — QUALITY MANAGEMENT (质量管理):
- Quality overview dashboard:
  · Score trend line chart (30 days)
  · Quality distribution bar chart by task type
  · Top issues list with severity badges
- Rules tab: rule cards with name, description, severity, enabled toggle, edit button
- Reports tab: report cards with date range, score summary, download PDF button
- Improvement workflow: Kanban board with columns (待处理, 进行中, 已完成, 已验证)

PAGE 10 — DATA SYNC (数据同步):
- Sync overview: connection status cards showing source name, type icon, last sync time, status indicator (green dot = connected)
- Sources tab: table with source name, type (PostgreSQL/Redis/API), connection status, sync frequency, actions
- History tab: timeline view with sync events, duration, records synced, error count
- Scheduler tab: calendar/timeline view showing scheduled sync jobs with drag-to-reschedule
- Export tab: export configuration form with format selector, field picker, preview

PAGE 11 — BILLING (计费管理):
- Usage overview: area chart showing daily API calls / storage / compute usage
- Current plan card: plan name, price, usage meters (used/total), upgrade button
- Invoice table: date, amount, status (paid/pending/overdue), download button
- Cost breakdown: horizontal stacked bar chart by category

PAGE 12 — LICENSE (许可证管理):
- License status card: license type, expiry date, days remaining (with color warning if <30 days)
- Usage meters: users (used/max), storage (used/max), API calls (used/max) — progress bars
- Activation wizard: step form (Enter Key → Verify → Activate → Done)
- Alert configuration: threshold sliders + notification channel checkboxes (email, in-app, webhook)

For each page, show both 明亮 (Light) and 睿黑 (Dark) themes. Keep consistent with the design system tokens.
```

---

## Prompt 6 — 认证页面与特殊组件 (Auth Pages, SmartHelp, Error Pages)

```
Design authentication pages and special UI components for SuperInsight (问视间). Modern Business Elegance style. Show Light and Dark variants, Chinese and English versions.

PAGE 13 — LOGIN (登录):
- Centered card layout on subtle gradient background (light: white-to-blue-tint, dark: #141414-to-#1a1a2e)
- Logo at top center: "问视间" wordmark + icon
- Form fields: email/username input, password input with show/hide toggle
- "记住我" checkbox + "忘记密码?" link
- Primary login button (full width, #1890FF)
- Divider: "或" / "OR"
- Social login buttons: SSO provider icons
- Bottom: "没有账号？立即注册" link
- Language switcher (top right corner): 中文 / English pill toggle

PAGE 14 — REGISTER (注册):
- Similar centered card layout
- Form: username, email, password, confirm password, organization name
- Password strength indicator bar (weak=red, medium=orange, strong=green)
- Terms checkbox: "我已阅读并同意《服务条款》"
- Register button + "已有账号？立即登录" link

PAGE 15 — FORGOT PASSWORD / RESET PASSWORD:
- Forgot: email input + "发送重置链接" button + back to login link
- Reset: new password + confirm password + strength indicator + "重置密码" button
- Success state: checkmark animation + "密码已重置，正在跳转..." message

SMART HELP SYSTEM (智能帮助):
- HelpIcon: small "?" circle button (24px), subtle border, hover shows blue tint
- HelpPopover: Ant Design Popover with title, description text, optional "了解更多" link, close X button. Max width 320px.
- HelpOverlay: floating panel (right side, 360px wide):
  · Header: "帮助" title + close button
  · Search input at top
  · Context-aware help content area with markdown rendering
  · Related topics links at bottom
  · Keyboard shortcut hint: "按 F1 或 ? 打开帮助"
- Show HelpIcon placement examples: next to form labels, next to page titles, in table column headers

ERROR PAGES:
- 404: large illustrated graphic (abstract/geometric style matching brand), "页面未找到" title, "您访问的页面不存在" subtitle, "返回首页" button
- 403: lock/shield illustration, "无权访问" title, "您没有权限访问此页面" subtitle, "返回首页" + "联系管理员" buttons
- 500: broken gear illustration, "服务器错误" title, "系统出现问题，请稍后重试" subtitle, "刷新页面" + "返回首页" buttons
- All error pages: centered layout, brand logo at top, consistent illustration style

LOADING STATES:
- Page skeleton: animated shimmer blocks matching page layout structure
- Spinner: primary color circular spinner with "加载中..." text
- Progress bar: thin top-of-page loading bar (like NProgress)

EMPTY STATES:
- No data: friendly illustration + "暂无数据" + action button
- No search results: search illustration + "未找到匹配结果" + "清除筛选" link
- First time: welcome illustration + "开始使用" guide steps

Show all components in both Light and Dark themes. Include Chinese and English text variants.
```

---

## 使用说明

| 顺序 | Prompt | 用途 | 建议 Figma 页面 |
|------|--------|------|----------------|
| 1 | Design System Foundation | 建立设计令牌和规范 | `🎨 Design System` |
| 2 | Core Component Library | 通用组件库 | `🧩 Components` |
| 3 | App Shell & Navigation | 应用外壳和导航 | `📐 Layout` |
| 4 | Business Pages Part 1 | Dashboard、Tasks、AI | `📄 Pages - Core` |
| 5 | Business Pages Part 2 | Admin、Security、Quality | `📄 Pages - Admin` |
| 6 | Auth & Special | 登录、帮助、错误页 | `📄 Pages - Auth & Special` |

### 使用建议

1. 按顺序执行 Prompt 1→6，每个 Prompt 在 Figma 中创建独立页面
2. Prompt 1 生成的设计令牌作为 Figma Variables / Styles 保存，后续页面引用
3. 每个 Prompt 都要求同时生成 Light + Dark 两套，确保主题一致性
4. 新增页面时，只需参考 Prompt 1-2 的设计系统即可保持风格统一
5. 如果单个 Prompt 输出过长，可以将页面拆分（如 Prompt 5 拆成 Admin 和 Non-Admin 两次）
