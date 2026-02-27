# Requirements Document

## Introduction

基于已批准的设计文档，定义问视间 (SuperInsight) 平台 UI/UX 升级的功能需求。涵盖 Logo SVG 系统、侧边栏分组导航、客户品牌白标、Header 增强、底部品牌栏、登录页重设计六大模块。技术栈保持 React 19 + TypeScript + Ant Design v5 + ProLayout + SCSS Modules + Zustand + i18next 不变。

## Glossary

- **Logo_SVG_System**: 内联 SVG Logo 组件集（LogoIcon / LogoIconSimple / LogoFull 三个变体）
- **Sidebar**: ProLayout 侧边栏区域，包含客户品牌区、分组导航、底部品牌
- **NavGroup**: 侧边栏菜单分组，包含 key、titleKey（i18n）、items 列表
- **ClientBranding**: 侧边栏顶部客户公司品牌组件（B2B 白标模式）
- **HeaderContent**: 顶部栏内容区，包含全局搜索、通知、帮助、语言切换、主题切换、用户头像
- **GlobalSearch**: 全局搜索组件，支持 ⌘K / Ctrl+K 快捷键触发
- **NotificationBell**: 通知铃铛组件，显示未读消息数 Badge
- **LayoutFooter**: 底部品牌栏，显示 "Powered by 问视间 SuperInsight"
- **LoginPage**: 登录页面，含动画背景和居中卡片布局
- **buildMenuRoutes**: 将 NavGroup[] 转换为 ProLayout 路由数组的核心函数

## Requirements

### Requirement 1: Logo SVG 组件渲染

**User Story:** As a developer, I want inline SVG logo components with theme support, so that logos render without extra network requests and adapt to light/dark themes.

#### Acceptance Criteria

1. WHEN LogoIcon is rendered, THE Logo_SVG_System SHALL display a circular gradient SVG with W-shape at the specified size (default 32px)
2. WHEN LogoIconSimple is rendered, THE Logo_SVG_System SHALL display a rounded-rectangle background SVG with W-shape
3. WHEN LogoFull is rendered with showText=true, THE Logo_SVG_System SHALL display the icon followed by "问视间 SuperInsight" text
4. WHEN the theme switches between light and dark, THE Logo_SVG_System SHALL adapt colors via CSS variables without re-mounting
5. IF LogoIcon rendering fails, THEN THE Logo_SVG_System SHALL fall back to a text Avatar displaying "问"

### Requirement 2: 侧边栏分组导航

**User Story:** As a user, I want sidebar menu items grouped by business category, so that I can find navigation items more efficiently.

#### Acceptance Criteria

1. THE buildMenuRoutes function SHALL transform NavGroup[] into a flat ProLayout route array with group divider entries
2. WHEN a NavGroup contains items with access='admin' and the current user role is not 'admin', THE buildMenuRoutes function SHALL exclude those items from the output
3. WHEN all items in a NavGroup are filtered out, THE buildMenuRoutes function SHALL omit that group divider entirely
4. WHEN a menu item is active, THE Sidebar SHALL display a left border accent (3px solid #1890FF) on that item
5. WHILE the sidebar is collapsed, THE Sidebar SHALL hide group title text and display only item icons
6. THE buildMenuRoutes function SHALL translate all name fields via the i18next translation function without mutating the input groups array

### Requirement 3: 客户公司品牌（白标）

**User Story:** As a B2B client, I want my company branding displayed at the sidebar top, so that the platform reflects my organization's identity.

#### Acceptance Criteria

1. WHEN clientCompany is configured with a logo URL, THE ClientBranding component SHALL render the logo image with the company name and optional label
2. WHEN clientCompany is configured without a logo URL, THE ClientBranding component SHALL render a gradient Avatar using the first character of the company name
3. WHEN clientCompany is null, THE ClientBranding component SHALL render the default SuperInsight LogoIcon with "问视间" text
4. WHILE the sidebar is collapsed, THE ClientBranding component SHALL display only the Avatar or Icon without text
5. IF the clientCompany logo URL fails to load, THEN THE ClientBranding component SHALL fall back to the gradient Avatar

### Requirement 4: Header 增强功能

**User Story:** As a user, I want global search, notifications, and help access in the header, so that I can quickly find content and stay informed.

#### Acceptance Criteria

1. WHEN the user presses ⌘K (Mac) or Ctrl+K (Windows/Linux), THE GlobalSearch component SHALL open the search modal
2. WHEN the GlobalSearch modal is closed, THE GlobalSearch component SHALL reset the query string to empty
3. WHEN the GlobalSearch component mounts, THE GlobalSearch component SHALL register the keyboard shortcut listener, and remove the listener on unmount
4. WHEN there are unread notifications, THE NotificationBell SHALL display a Badge with the unread count
5. WHEN the notification API request fails, THE NotificationBell SHALL display a count of zero and retry silently at 30-second intervals
6. WHEN the user clicks the HelpButton, THE HeaderContent SHALL open the help documentation link

### Requirement 5: 底部品牌栏

**User Story:** As a platform operator, I want "Powered by 问视间 SuperInsight" displayed at the bottom, so that platform branding is always visible.

#### Acceptance Criteria

1. THE LayoutFooter SHALL display LogoIconSimple followed by "Powered by 问视间 SuperInsight" and "© {currentYear} SuperInsight"
2. WHILE the sidebar is collapsed, THE LayoutFooter SHALL display only the small LogoIconSimple without text

### Requirement 6: 登录页重设计

**User Story:** As a user, I want a visually appealing login page, so that I have a professional first impression of the platform.

#### Acceptance Criteria

1. WHEN the login page loads, THE LoginPage SHALL render animated gradient background blobs using CSS animation
2. THE LoginPage SHALL display a centered card containing LogoFull and the existing LoginForm component
3. THE LoginPage SHALL include placeholder areas for social login options (Google, Enterprise SSO)

### Requirement 7: 安全与国际化

**User Story:** As a developer, I want all new UI components to follow security and i18n standards, so that the platform remains safe and multilingual.

#### Acceptance Criteria

1. WHEN rendering clientCompany logo URL, THE ClientBranding component SHALL validate the URL as a legitimate image source to prevent XSS
2. THE NotificationBell SHALL use i18n keys for notification content instead of raw HTML to prevent injection
3. WHEN submitting a global search query, THE GlobalSearch component SHALL sanitize the query string before sending to the backend
4. THE Sidebar SHALL render all user-facing text via i18next translation keys
