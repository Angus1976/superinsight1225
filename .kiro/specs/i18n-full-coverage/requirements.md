# Requirements Document

## Introduction

SuperInsight 平台已有基础的 i18n 支持，但存在多处硬编码的中文文本未使用翻译函数。本需求旨在完成前端的全面国际化覆盖，确保所有用户界面文本都通过 i18n 系统管理，实现中英文的完整切换。

## Glossary

- **I18n_System**: 国际化系统，基于 react-i18next 实现的多语言翻译管理
- **Translation_Key**: 翻译键，用于标识特定文本的唯一标识符
- **Hardcoded_Text**: 硬编码文本，直接写在代码中的中文或英文字符串
- **Translation_Function**: 翻译函数，即 `t()` 函数，用于获取当前语言的翻译文本
- **Translation_File**: 翻译文件，存储翻译键值对的 JSON 文件
- **Language_Switcher**: 语言切换器，用户切换界面语言的 UI 组件

## Requirements

### Requirement 1: 登录页面国际化

**User Story:** 作为系统用户，我希望登录页面支持中英文切换，以便我能使用熟悉的语言进行登录操作。

#### Acceptance Criteria

1. WHEN the Login page renders, THE I18n_System SHALL display the application name using translation keys
2. WHEN the Login page renders, THE I18n_System SHALL display the logo alt text using translation keys
3. THE Login page SHALL use translation keys for all visible text including title, subtitle, and links
4. WHEN language is switched, THE Login page SHALL update all text content immediately

### Requirement 2: 错误页面国际化

**User Story:** 作为系统用户，我希望错误页面（404、403）支持中英文切换，以便我能理解错误信息并采取相应操作。

#### Acceptance Criteria

1. WHEN the 404 page renders, THE I18n_System SHALL display error message using translation keys
2. WHEN the 403 page renders, THE I18n_System SHALL display permission error message using translation keys
3. THE error pages SHALL use translation keys for all button text including "返回首页"
4. WHEN language is switched, THE error pages SHALL update all text content immediately
5. THE I18n_System SHALL provide consistent error page translations across both languages

### Requirement 3: 工时报表组件国际化

**User Story:** 作为账单管理员，我希望工时报表组件支持中英文切换，以便我能使用熟悉的语言查看和导出工时数据。

#### Acceptance Criteria

1. WHEN the WorkHoursReport component renders, THE I18n_System SHALL display all table column headers using translation keys
2. THE WorkHoursReport component SHALL use translation keys for all statistic card titles
3. THE WorkHoursReport component SHALL use translation keys for all button text (刷新、导出 Excel、详情、关闭、重试)
4. THE WorkHoursReport component SHALL use translation keys for all tooltip and message text
5. THE WorkHoursReport component SHALL use translation keys for date picker presets (本周、本月、上月、本季度)
6. THE WorkHoursReport component SHALL use translation keys for modal content and labels
7. WHEN language is switched, THE WorkHoursReport component SHALL update all text content immediately

### Requirement 4: 翻译文件完整性

**User Story:** 作为系统开发者，我希望翻译文件包含所有必要的翻译键，以确保国际化覆盖的完整性。

#### Acceptance Criteria

1. THE Translation_File for billing namespace SHALL include all WorkHoursReport related translation keys
2. THE Translation_File for common namespace SHALL include all error page related translation keys
3. THE Translation_File for auth namespace SHALL include all login page related translation keys
4. FOR ALL translation keys in Chinese Translation_File, THE English Translation_File SHALL contain corresponding translations
5. FOR ALL translation keys in English Translation_File, THE Chinese Translation_File SHALL contain corresponding translations

### Requirement 5: 翻译键命名规范

**User Story:** 作为系统开发者，我希望翻译键遵循统一的命名规范，以便于维护和扩展。

#### Acceptance Criteria

1. THE Translation_Key SHALL follow dot notation for nested structures (e.g., billing.workHours.columns.rank)
2. THE Translation_Key SHALL use camelCase for individual key names
3. THE Translation_Key SHALL be grouped by functional module in Translation_File
4. THE Translation_Key SHALL be descriptive and self-documenting
5. THE Translation_Key SHALL avoid abbreviations unless commonly understood

### Requirement 6: 语言切换同步

**User Story:** 作为系统用户，我希望切换语言后所有页面内容都能同步更新，以获得一致的用户体验。

#### Acceptance Criteria

1. WHEN language is switched, THE I18n_System SHALL update all rendered components immediately
2. WHEN language is switched, THE I18n_System SHALL persist the language preference to localStorage
3. WHEN the application reloads, THE I18n_System SHALL restore the previously selected language
4. THE I18n_System SHALL ensure no hardcoded text remains visible after language switch
5. WHEN language is switched, THE I18n_System SHALL update dynamic content including tooltips and messages

### Requirement 7: 测试文件国际化

**User Story:** 作为系统开发者，我希望测试文件中的中文文本也使用翻译键或英文，以保持代码一致性。

#### Acceptance Criteria

1. THE test files SHALL use English for test descriptions and assertions
2. THE test files SHALL mock translation functions when testing i18n-dependent components
3. THE test files SHALL verify that components correctly use translation keys
4. IF test files contain user-visible text assertions, THEN THE test files SHALL use translation keys or English equivalents

### Requirement 8: 新增页面国际化规范

**User Story:** 作为系统开发者，我希望有明确的国际化开发规范，以确保新增或修改的页面都能自动跟随语言选择。

#### Acceptance Criteria

1. WHEN a new page or component is created, THE developer SHALL use Translation_Function for all user-visible text
2. THE I18n_System SHALL provide a development guideline document for internationalization
3. WHEN a page is modified, THE developer SHALL ensure all new text uses Translation_Function
4. THE I18n_System SHALL support real-time language switching without page reload
5. THE I18n_System SHALL provide TypeScript type definitions for translation keys to prevent typos
6. WHEN new translation keys are added, THE developer SHALL add translations to both Chinese and English Translation_Files simultaneously

### Requirement 9: 动态内容国际化

**User Story:** 作为系统用户，我希望所有动态生成的内容（如消息提示、表单验证、日期格式）也能跟随语言切换。

#### Acceptance Criteria

1. WHEN displaying success/error messages, THE I18n_System SHALL use translation keys
2. WHEN displaying form validation messages, THE I18n_System SHALL use translation keys
3. WHEN displaying date/time, THE I18n_System SHALL format according to current language locale
4. WHEN displaying numbers and currency, THE I18n_System SHALL format according to current language locale
5. WHEN language is switched, THE I18n_System SHALL update all dynamic content immediately without requiring user interaction

### Requirement 10: UI 布局适配

**User Story:** 作为系统用户，我希望在不同语言下界面布局保持美观，按钮和文本不会因为翻译长度变化而破坏布局。

#### Acceptance Criteria

1. WHEN displaying buttons with translated text, THE UI SHALL maintain consistent button sizing and alignment
2. THE UI components SHALL use flexible layouts (flex, grid) to accommodate text length variations
3. WHEN text is longer in one language, THE UI SHALL handle overflow gracefully (truncation with tooltip, or responsive sizing)
4. THE Translation_File SHALL provide concise translations that fit within typical UI constraints
5. WHEN language is switched, THE UI layout SHALL remain visually consistent and aesthetically pleasing
