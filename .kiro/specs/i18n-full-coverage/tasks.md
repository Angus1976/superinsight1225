# Implementation Plan: i18n Full Coverage

## Overview

本实现计划将 SuperInsight 前端的国际化覆盖从部分支持扩展到全面覆盖。主要工作包括：更新翻译文件、修改硬编码文本的组件、添加 TypeScript 类型定义，以及编写测试用例。

## Tasks

- [x] 1. 更新翻译文件 - 添加缺失的翻译键
  - [x] 1.1 更新 billing.json 添加 WorkHoursReport 翻译键
    - 在 zh/billing.json 中添加 workHours.report 命名空间下的所有翻译键
    - 包括：columns（表格列）、stats（统计卡片）、charts（图表）、datePresets（日期预设）、modal（模态框）、actions（操作按钮）、messages（消息提示）
    - _Requirements: 4.1_
  
  - [x] 1.2 更新 en/billing.json 添加对应英文翻译
    - 添加与 zh/billing.json 相同结构的英文翻译
    - 确保所有键名一致
    - _Requirements: 4.1, 4.4, 4.5_
  
  - [x] 1.3 更新 common.json 添加错误页面翻译键
    - 在 zh/common.json 中添加 error.pages.notFound 和 error.pages.forbidden 翻译键
    - 包括：title、subtitle、backHome
    - _Requirements: 4.2_
  
  - [x] 1.4 更新 en/common.json 添加对应英文翻译
    - 添加与 zh/common.json 相同结构的英文翻译
    - _Requirements: 4.2, 4.4, 4.5_
  
  - [x] 1.5 更新 auth.json 添加登录页面翻译键
    - 在 zh/auth.json 中添加 login.appName 和 login.logoAlt 翻译键
    - _Requirements: 4.3_
  
  - [x] 1.6 更新 en/auth.json 添加对应英文翻译
    - 添加与 zh/auth.json 相同结构的英文翻译
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 2. 修改 Login 页面组件
  - [x] 2.1 更新 Login/index.tsx 使用翻译函数
    - 导入 useTranslation hook
    - 将 logo alt 文本 "问视间" 替换为 t('login.logoAlt')
    - 将标题 "问视间" 替换为 t('login.appName')
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 2.2 编写 Login 页面国际化单元测试
    - 验证 t() 函数被正确调用
    - 验证语言切换后文本更新
    - _Requirements: 1.4_

- [x] 3. 修改错误页面组件
  - [x] 3.1 更新 Error/404.tsx 使用翻译函数
    - 导入 useTranslation hook
    - 将 "抱歉，您访问的页面不存在。" 替换为 t('error.pages.notFound.subtitle')
    - 将 "返回首页" 替换为 t('error.pages.notFound.backHome')
    - _Requirements: 2.1, 2.3_
  
  - [x] 3.2 更新 Error/403.tsx 使用翻译函数
    - 导入 useTranslation hook
    - 将 "抱歉，您没有权限访问此页面。" 替换为 t('error.pages.forbidden.subtitle')
    - 将 "返回首页" 替换为 t('error.pages.forbidden.backHome')
    - _Requirements: 2.2, 2.3_
  
  - [x] 3.3 编写错误页面国际化单元测试
    - 验证 404 和 403 页面使用正确的翻译键
    - 验证语言切换后文本更新
    - _Requirements: 2.4, 2.5_

- [x] 4. Checkpoint - 验证基础页面国际化
  - 确保 Login、404、403 页面正确使用翻译函数
  - 验证翻译文件结构正确
  - 手动测试语言切换功能
  - 如有问题请提出

- [x] 5. 修改 WorkHoursReport 组件
  - [x] 5.1 更新 WorkHoursReport.tsx 表格列标题
    - 导入 useTranslation hook
    - 将所有列标题（排名、用户、总工时、计费工时、标注数、时效、效率评分、成本、操作）替换为翻译函数调用
    - 设置适当的列宽（width/minWidth）以适应中英文长度差异
    - _Requirements: 3.1, 10.1_
  
  - [x] 5.2 更新 WorkHoursReport.tsx 统计卡片标题
    - 将所有 Statistic 组件的 title 属性替换为翻译函数调用
    - 包括：统计人数、总工时、计费工时、总标注数、平均效率、总成本
    - 确保卡片布局在不同语言下保持一致
    - _Requirements: 3.2, 10.2_
  
  - [x] 5.3 更新 WorkHoursReport.tsx 按钮和操作文本
    - 将所有 Button 组件的文本替换为翻译函数调用
    - 包括：刷新、导出 Excel、详情、关闭、重试
    - 使用 minWidth 或 Space 组件确保按钮布局美观
    - _Requirements: 3.3, 10.1_
  
  - [x] 5.4 更新 WorkHoursReport.tsx 日期选择器预设
    - 将 RangePicker presets 的 label 替换为翻译函数调用
    - 包括：本周、本月、上月、本季度
    - _Requirements: 3.5_
  
  - [x] 5.5 更新 WorkHoursReport.tsx 图表和提示文本
    - 将图表标题、Legend、Tooltip 文本替换为翻译函数调用
    - 将 message.success/error 调用的文本替换为翻译函数调用
    - _Requirements: 3.4_
  
  - [x] 5.6 更新 UserDetailModal 组件
    - 将模态框标题、Descriptions.Item label 替换为翻译函数调用
    - 将所有单位文本（小时、条、条/小时）替换为翻译函数调用
    - _Requirements: 3.6_
  
  - [x] 5.7 编写 WorkHoursReport 国际化单元测试
    - 验证所有文本使用翻译函数
    - 验证语言切换后所有文本更新
    - _Requirements: 3.7_

- [x] 6. Checkpoint - 验证 WorkHoursReport 国际化
  - 确保 WorkHoursReport 组件所有文本使用翻译函数
  - 验证翻译文件包含所有必需的键
  - 手动测试语言切换功能
  - 验证中英文切换后 UI 布局保持美观
  - 如有问题请提出

- [x] 7. 添加 TypeScript 类型定义
  - [x] 7.1 创建 i18n 类型定义文件
    - 创建 frontend/src/types/i18n.d.ts
    - 定义 CustomTypeOptions 扩展 react-i18next 类型
    - 导入各命名空间的翻译文件类型
    - _Requirements: 8.5_
  
  - [x] 7.2 验证类型定义生效
    - 确保 IDE 提供翻译键自动补全
    - 确保拼写错误的翻译键产生 TypeScript 错误
    - _Requirements: 8.5_

- [x] 8. 编写属性测试
  - [x] 8.1 编写翻译文件双向完整性属性测试
    - **Property 3: Translation File Bidirectional Completeness**
    - 验证 zh 和 en 翻译文件的键完全一致
    - **Validates: Requirements 4.4, 4.5**
  
  - [x] 8.2 编写翻译键命名规范属性测试
    - **Property 5: Translation Key Naming Convention**
    - 验证所有键遵循点分隔和 camelCase 规范
    - **Validates: Requirements 5.1, 5.2**
  
  - [x] 8.3 编写语言偏好持久化往返属性测试
    - **Property 6: Language Preference Persistence Round-trip**
    - 验证语言设置保存到 localStorage 后能正确恢复
    - **Validates: Requirements 6.2, 6.3**

- [x] 9. 创建国际化开发指南文档
  - [x] 9.1 创建 i18n-guidelines.md 文档
    - 编写翻译键命名规范
    - 编写组件国际化最佳实践
    - 编写新增翻译键的流程
    - 编写测试国际化功能的方法
    - 编写 UI 布局适配指南（处理中英文长度差异）
    - _Requirements: 8.2, 10.2, 10.3, 10.4_

- [x] 10. Final Checkpoint - 完整验证
  - 运行所有单元测试确保通过
  - 运行属性测试确保通过
  - 手动测试所有修改的页面和组件
  - 验证语言切换在所有页面正常工作
  - 验证中英文切换后所有 UI 布局保持美观
  - 如有问题请提出

## Notes

- 所有任务均为必需任务，确保从一开始就有完整的测试覆盖
- 每个任务都引用了具体的需求条款以便追溯
- Checkpoint 任务用于阶段性验证，确保增量开发的正确性
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
