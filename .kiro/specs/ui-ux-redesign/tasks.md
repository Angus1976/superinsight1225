# Implementation Plan: UI/UX Redesign

## Overview

按设计文档分 6 个模块渐进实现，每步构建在前一步基础上，最终在 MainLayout 中集成。

## Tasks

- [x] 1. Logo SVG 系统
  - [x] 1.1 Create LogoIcon, LogoIconSimple, LogoFull SVG components in `src/components/Brand/`
    - Inline SVG with CSS variable theming (light/dark)
    - LogoIcon: circular gradient + W, default size=32
    - LogoIconSimple: rounded-rect background + W
    - LogoFull: icon + "问视间 SuperInsight" text, showText prop
    - Fallback to "问" Avatar on render error
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 1.2 Write property test: LogoIcon renders at specified size
    - **Property 1: LogoIcon renders at specified size**
    - **Validates: Requirement 1.1**

- [x] 2. Sidebar navigation grouping
  - [x] 2.1 Define NavGroup config and implement `buildMenuRoutes()` in `src/config/navGroups.ts`
    - Define NAV_GROUPS constant (workbench, dataManage, aiCapability, qualitySec, system)
    - Implement buildMenuRoutes: group dividers, role filtering, i18n translation, no mutation
    - _Requirements: 2.1, 2.2, 2.3, 2.6_
  - [x] 2.2 Write property tests for buildMenuRoutes
    - **Property 2: buildMenuRoutes produces correct structure with role-based filtering**
    - **Property 3: buildMenuRoutes does not mutate input**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.6**
  - [x] 2.3 Implement sidebar group header rendering and active item accent style
    - menuItemRender: detect itemType='group' → render section header
    - Active item left border accent (3px solid #1890FF)
    - Collapsed mode: hide group titles, show icons only
    - _Requirements: 2.4, 2.5_

- [x] 3. ClientBranding component
  - [x] 3.1 Extend uiStore with clientCompany state and implement ClientBranding in `src/components/Layout/`
    - Add clientCompany + setClientCompany to uiStore
    - Render logo image or gradient Avatar (first char) based on logo presence
    - Null state: default LogoIcon + "问视间"
    - Collapsed mode: Avatar/Icon only, no text
    - Logo URL validation (reject non-http/https image URLs)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1_
  - [x] 3.2 Write property tests for ClientBranding
    - **Property 4: ClientBranding renders correct visual based on logo presence**
    - **Property 5: Collapsed mode hides text across branding components**
    - **Property 8: Client logo URL validation rejects malicious inputs**
    - **Validates: Requirements 3.1, 3.2, 3.4, 7.1**

- [x] 4. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Header enhancements
  - [x] 5.1 Implement GlobalSearch component with useGlobalSearch hook
    - Search input with ⌘K / Ctrl+K shortcut registration/cleanup
    - Modal open/close, query reset on close
    - Query sanitization before backend submission
    - _Requirements: 4.1, 4.2, 4.3, 7.3_
  - [x] 5.2 Write property tests for GlobalSearch
    - **Property 6: GlobalSearch close resets query state**
    - **Property 9: Global search query sanitization**
    - **Validates: Requirements 4.2, 7.3**
  - [x] 5.3 Implement NotificationBell and HelpButton components
    - NotificationBell: Badge with unread count, zero on API failure, 30s silent retry
    - HelpButton: opens help documentation link
    - All notification content via i18n keys
    - _Requirements: 4.4, 4.5, 4.6, 7.2_
  - [x] 5.4 Write property test for NotificationBell
    - **Property 7: NotificationBell displays correct badge count**
    - **Validates: Requirement 4.4**

- [x] 6. LayoutFooter and i18n
  - [x] 6.1 Implement LayoutFooter in `src/components/Layout/`
    - LogoIconSimple + "Powered by 问视间 SuperInsight" + © year
    - Collapsed mode: small logo only
    - _Requirements: 5.1, 5.2_
  - [x] 6.2 Add all i18n keys for navGroups, header, footer to translation files
    - All sidebar text via i18next translation keys
    - _Requirements: 7.4_

- [x] 7. Login page redesign
  - [x] 7.1 Redesign LoginPage with animated background and centered card
    - CSS animation gradient blobs background
    - Centered card with LogoFull + existing LoginForm
    - Social login placeholders (Google, Enterprise SSO)
    - _Requirements: 6.1, 6.2, 6.3_

- [x] 8. Integration and wiring
  - [x] 8.1 Wire all components into MainLayout (ProLayout)
    - menuHeaderRender → ClientBranding
    - route → buildMenuRoutes output (useMemo cached)
    - menuItemRender → group header + nav items
    - headerContentRender → GlobalSearch + NotificationBell + HelpButton + existing toggles
    - footerRender → LayoutFooter
    - _Requirements: 2.1, 3.1, 4.1, 5.1_
  - [x] 8.2 Write integration tests for MainLayout rendering
    - Verify sidebar grouping, header components, footer render together
    - Test theme switch and collapsed mode across all new components
    - _Requirements: 2.4, 2.5, 3.4, 5.2_

- [x] 9. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use fast-check library per design document
- All components use existing tech stack (Ant Design v5 + ProLayout + SCSS Modules)
