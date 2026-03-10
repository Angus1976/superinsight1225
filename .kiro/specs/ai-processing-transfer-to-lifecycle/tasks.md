# Implementation Plan: AI 数据处理结果转存到数据生命周期

## Overview

本实现计划将 AI 数据处理结果转存功能集成到 4 个处理方法页面（结构化、向量化、语义化、AI 智能标注）。实现采用共享组件模式，通过 TransferToLifecycleModal 组件和 useTransferToLifecycle Hook 提供统一的转存体验。所有用户可见文本使用 i18n 国际化，支持中英文切换。

## Tasks

- [x] 1. 创建共享组件和 Hook
  - [x] 1.1 创建 TransferToLifecycleModal 组件
    - 创建 `frontend/src/components/DataLifecycle/TransferToLifecycleModal.tsx`
    - 实现模态框基础结构（标题、表单、按钮）
    - 实现目标阶段选择（根据 sourceType 动态显示可选阶段）
    - 实现可选配置项（数据类型、标签、备注、质量阈值）
    - 实现已选择数据的数量显示和预览
    - 使用 Ant Design 的 Modal、Form、Select、Input、Tag 组件
    - _Requirements: 1.2, 1.3, 1.7, 1.8, 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 11.1-11.8_
  
  - [x] 1.2 为 TransferToLifecycleModal 编写单元测试
    - 测试模态框打开/关闭
    - 测试表单验证
    - 测试目标阶段根据 sourceType 动态显示
    - 测试用户交互（选择阶段、输入配置）
    - _Requirements: 1.2, 1.3, 2.2, 3.2, 4.2_

  - [x] 1.3 创建 useTransferToLifecycle Hook
    - 创建 `frontend/src/hooks/useTransferToLifecycle.ts`
    - 实现 transferData 函数（批量转存逻辑）
    - 实现进度跟踪（total、completed、failed、percentage）
    - 实现错误处理和重试逻辑
    - 实现批量分批处理（每批最多 100 条，最多 3 个并发请求）
    - 返回 loading、progress、error 状态
    - _Requirements: 2.4, 3.4, 9.1-9.8, 10.1-10.8, 12.1-12.8_
  
  - [x] 1.4 为 useTransferToLifecycle Hook 编写单元测试
    - 测试单条数据转存
    - 测试批量数据转存
    - 测试进度跟踪准确性
    - 测试错误处理和重试
    - 测试批量分批逻辑
    - _Requirements: 2.4, 9.2, 10.5, 12.2, 12.3_

- [x] 2. 创建转存服务和数据映射
  - [x] 2.1 创建 Transfer Service
    - 创建 `frontend/src/services/transferService.ts`
    - 实现 validateData 函数（验证必需字段、数据大小、格式兼容性）
    - 实现 mapToLifecycleData 函数（根据 sourceType 映射数据格式）
    - 实现 checkPermissions 函数（检查用户权限）
    - 实现 batchTransfer 函数（批量转存协调）
    - _Requirements: 7.1-7.6, 8.1-8.8, 12.1-12.8_
  
  - [x] 2.2 为 Transfer Service 编写单元测试
    - 测试数据验证（缺少必需字段、数据大小超限、格式不兼容）
    - 测试数据映射（4 种 sourceType 的映射逻辑）
    - 测试权限检查
    - 测试批量转存协调
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 2.3 编写数据映射属性测试
    - **Property 10: Source Metadata Preservation**
    - **Validates: Requirements 6.2, 6.3**
    - 验证所有转存数据都包含 source、sourceType、sourceId 元数据
    - _Requirements: 6.2, 6.3_

- [x] 3. 添加国际化翻译
  - [x] 3.1 添加中文翻译
    - 在 `frontend/src/locales/zh/aiProcessing.json` 中添加 transfer 相关翻译 key
    - 包含：标题、按钮、模态框标签、阶段名称、数据类型、提示消息、进度文本、结果文本
    - 确保所有翻译 key 与设计文档中的结构一致
    - _Requirements: 5.1, 5.2, 5.5_
  
  - [x] 3.2 添加英文翻译
    - 在 `frontend/src/locales/en/aiProcessing.json` 中添加 transfer 相关翻译 key
    - 确保 key 结构与中文翻译文件完全一致
    - _Requirements: 5.1, 5.3, 5.5_
  
  - [x] 3.3 编写 i18n 合规性属性测试
    - **Property 8: i18n Text Wrapping**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
    - 验证所有用户可见文本都使用 t() 函数
    - 验证中英文翻译文件的 key 结构一致
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 4. 在结构化处理页面集成转存功能
  - [x] 4.1 在结构化处理页面添加转存按钮
    - 找到结构化处理结果展示页面组件
    - 添加"转存至数据生命周期"按钮
    - 按钮点击时打开 TransferToLifecycleModal，传入 sourceType='structuring' 和选中的数据
    - 使用 useTranslation('aiProcessing') 获取按钮文本
    - _Requirements: 1.1, 1.2_
  
  - [x] 4.2 实现结构化数据的转存逻辑
    - 在 TransferToLifecycleModal 中处理 sourceType='structuring' 的情况
    - 显示可选目标阶段：临时数据、样本库
    - 调用 useTransferToLifecycle Hook 执行转存
    - 转存成功后显示成功提示，包含目标阶段名称
    - 转存失败后显示错误提示，包含失败原因
    - _Requirements: 1.3, 1.4, 1.5, 1.6_
  
  - [x] 4.3 编写结构化转存集成测试
    - 测试按钮点击打开模态框
    - 测试选择目标阶段并确认转存
    - 测试成功提示消息显示
    - 测试错误提示消息显示
    - _Requirements: 1.2, 1.4, 1.5, 1.6_

- [x] 5. 在向量化处理页面集成转存功能
  - [x] 5.1 在向量化记录列表添加批量转存按钮
    - 找到向量化记录列表组件
    - 添加批量选择功能（如果不存在）
    - 添加"转存至数据生命周期"批量操作按钮
    - 按钮在选中记录时启用，未选中时禁用
    - 按钮点击时打开 TransferToLifecycleModal，传入 sourceType='vectorization' 和选中的记录
    - _Requirements: 2.1, 2.2_
  
  - [x] 5.2 实现向量化数据的批量转存逻辑
    - 在 TransferToLifecycleModal 中处理 sourceType='vectorization' 的情况
    - 显示已选择的记录数量
    - 显示可选目标阶段：临时数据、样本库、已增强
    - 调用 useTransferToLifecycle Hook 执行批量转存
    - 显示转存进度（进度条、已完成数量、预计剩余时间）
    - 转存完成后显示结果摘要（成功数量、失败数量）
    - 部分失败时显示失败记录列表和失败原因
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 9.1-9.8_
  
  - [x] 5.3 编写向量化批量转存属性测试
    - **Property 5: Batch Selection Count Display**
    - **Validates: Requirements 2.2, 3.2**
    - 验证模态框显示的选中数量与实际选中数量一致
    - **Property 6: Batch Transfer Result Summary**
    - **Validates: Requirements 2.5, 3.5**
    - 验证结果摘要中成功数 + 失败数 + 跳过数 = 总数
    - _Requirements: 2.2, 2.5, 3.2, 3.5_

- [x] 6. 在语义化处理页面集成转存功能
  - [x] 6.1 在语义化记录列表添加批量转存按钮
    - 找到语义化记录列表组件
    - 添加批量选择功能（如果不存在）
    - 添加"转存至数据生命周期"批量操作按钮
    - 按钮点击时打开 TransferToLifecycleModal，传入 sourceType='semantic' 和选中的记录
    - _Requirements: 3.1, 3.2_
  
  - [x] 6.2 实现语义化数据的批量转存逻辑
    - 在 TransferToLifecycleModal 中处理 sourceType='semantic' 的情况
    - 显示已选择的记录数量和类型筛选信息
    - 显示可选目标阶段：临时数据、样本库、已增强
    - 支持按语义类型（实体、关系、事件等）分组显示记录
    - 调用 useTransferToLifecycle Hook 执行批量转存
    - 转存包含关系的语义记录时，同时转存关联的实体记录
    - 显示转存结果摘要（成功数量、失败数量、按类型分组）
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [x] 6.3 编写语义化转存集成测试
    - 测试按语义类型分组显示
    - 测试关系记录转存时同时转存关联实体
    - 测试按类型分组的结果摘要
    - _Requirements: 3.6, 3.7, 3.8_

- [x] 7. 在 AI 智能标注页面集成转存功能
  - [x] 7.1 在 AI 标注任务详情添加转存按钮
    - 找到 AI 标注任务详情组件
    - 在已完成任务的详情中添加"转存至数据生命周期"按钮
    - 按钮点击时打开 TransferToLifecycleModal，传入 sourceType='ai_annotation' 和任务数据
    - _Requirements: 4.1, 4.2_
  
  - [x] 7.2 实现 AI 标注结果的转存逻辑
    - 在 TransferToLifecycleModal 中处理 sourceType='ai_annotation' 的情况
    - 显示任务名称和标注数据数量
    - 显示可选目标阶段：已标注、样本库
    - 支持选择标注质量阈值，只转存高于阈值的标注结果
    - 显示标注结果的质量分布图表（置信度分布）
    - 调用 useTransferToLifecycle Hook 执行转存
    - 转存成功后在任务详情中显示转存状态和目标阶段链接
    - _Requirements: 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_
  
  - [x] 7.3 编写 AI 标注转存集成测试
    - 测试质量阈值筛选
    - 测试质量分布图表显示
    - 测试转存状态和目标阶段链接显示
    - _Requirements: 4.7, 4.8, 4.6_

- [x] 8. 实现进度反馈和错误处理
  - [x] 8.1 实现转存进度显示
    - 在 TransferToLifecycleModal 中添加进度条组件
    - 实时更新进度百分比和已完成数量
    - 显示预计剩余时间
    - 转存进行中时禁用关闭按钮
    - 提供"取消转存"按钮
    - 用户取消时停止后续转存，已完成的转存保持有效
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [x] 8.2 实现转存结果显示
    - 批量转存完成后显示详细结果报告（成功数量、失败数量、跳过数量）
    - 支持下载转存结果报告为 CSV 文件
    - 显示失败记录列表，包含失败原因和建议操作
    - _Requirements: 9.7, 9.8, 10.8_
  
  - [x] 8.3 实现错误处理和重试
    - 网络错误：显示"网络连接失败，请检查网络后重试"
    - 服务器错误：显示"服务器错误，请稍后重试或联系管理员"
    - 权限错误：显示"权限不足，请联系管理员申请权限"
    - 数据验证失败：显示具体的验证错误信息和修复建议
    - 所有错误提示中提供"重试"按钮
    - 在审计日志中记录所有失败的转存操作和错误原因
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_
  
  - [x] 8.4 编写错误处理属性测试
    - **Property 19: Network Error Handling**
    - **Validates: Requirements 10.1**
    - 验证网络错误时显示正确的错误消息
    - **Property 20: Retry Functionality**
    - **Validates: Requirements 10.5, 10.6**
    - 验证重试按钮重新执行转存操作
    - _Requirements: 10.1, 10.5, 10.6_

- [x] 9. 实现权限控制和数据验证
  - [x] 9.1 实现权限检查
    - 在 Transfer Service 中实现 checkPermissions 函数
    - 检查用户是否具有"数据转存"权限
    - 没有权限时隐藏或禁用转存按钮
    - 尝试转存但没有权限时返回 403 错误
    - 检查用户是否具有目标阶段的写入权限
    - 没有目标阶段写入权限时禁用该选项并显示权限提示
    - 在审计日志中记录所有转存操作（用户、时间、来源、目标、结果）
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [x] 9.2 实现数据验证
    - 验证数据是否包含必需字段（ID、内容、元数据）
    - 数据缺少必需字段时拒绝转存并显示缺失字段列表
    - 验证数据大小是否超过目标阶段的限制
    - 数据大小超过限制时显示错误提示并建议分批转存
    - 验证数据格式是否与目标阶段兼容
    - 数据格式不兼容时提供格式转换选项或拒绝转存
    - 检查目标阶段是否已存在相同 ID 的数据
    - 目标阶段已存在相同 ID 的数据时提供覆盖或跳过选项
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 9.3 编写权限和验证属性测试
    - **Property 11: Permission Check Before Transfer**
    - **Validates: Requirements 7.1, 7.2, 7.3**
    - 验证转存前检查用户权限
    - **Property 13: Required Fields Validation**
    - **Validates: Requirements 8.1, 8.2**
    - 验证数据包含必需字段
    - **Property 15: Duplicate ID Handling**
    - **Validates: Requirements 8.7, 8.8**
    - 验证重复 ID 时提供覆盖或跳过选项
    - _Requirements: 7.1, 7.2, 7.3, 8.1, 8.2, 8.7, 8.8_

- [x] 10. 实现数据生命周期集成
  - [x] 10.1 实现 API 调用
    - 实现调用 POST /api/data-lifecycle/temp-data 创建临时数据
    - 实现调用 POST /api/data-lifecycle/samples 创建样本库数据
    - 实现调用 POST /api/data-lifecycle/annotated 创建已标注数据
    - 实现调用 POST /api/data-lifecycle/enhanced 创建已增强数据
    - 实现调用 POST /api/data-lifecycle/batch-transfer 批量转存
    - 所有 API 调用使用异步方式，避免阻塞 UI 线程
    - _Requirements: 1.4, 2.4, 3.4, 4.4, 4.5, 12.1_
  
  - [x] 10.2 实现转存后的数据可见性
    - 转存成功后，在数据记录的元数据中保留来源信息（source、sourceType、sourceId）
    - 确保转存的数据在目标阶段的数据列表中可见
    - 在数据记录中显示来源标签（如"来自向量化处理"）
    - 支持按来源筛选数据（结构化、向量化、语义化、AI 标注）
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [x] 10.3 编写数据可见性集成测试
    - **Property 9: Transferred Data Visibility**
    - **Validates: Requirements 6.1**
    - 验证转存成功后数据在目标阶段可见
    - 测试来源标签显示
    - 测试按来源筛选功能
    - _Requirements: 6.1, 6.3, 6.4_

- [x] 11. 性能优化和最终集成
  - [x] 11.1 实现性能优化
    - 批量 API 调用每批最多 100 条记录
    - 并发处理最多 3 个并行请求
    - 进度更新使用防抖（每 100ms 更新一次）
    - 使用 React.memo 优化 TransferToLifecycleModal 组件
    - 懒加载转存模态框组件（按钮点击时才加载）
    - 缓存权限检查结果 5 分钟
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_
  
  - [x] 11.2 最终集成测试和验证
    - 在 4 个处理方法页面分别测试转存功能
    - 验证所有用户可见文本都使用 i18n
    - 验证中英文切换正常工作
    - 验证权限控制正常工作
    - 验证数据验证正常工作
    - 验证错误处理和重试正常工作
    - 验证进度反馈正常工作
    - 验证转存后的数据在数据生命周期页面可见
    - _Requirements: 所有需求_
  
  - [x] 11.3 编写端到端属性测试
    - **Property 1: Modal Opening on Button Click**
    - **Validates: Requirements 1.2, 2.2, 3.2, 4.2**
    - **Property 2: API Call on Transfer Confirmation**
    - **Validates: Requirements 1.4, 2.4, 3.4, 4.4**
    - **Property 3: Success Message Display**
    - **Validates: Requirements 1.5, 2.5, 3.5, 4.5**
    - **Property 4: Error Message Display**
    - **Validates: Requirements 1.6, 2.6, 3.6, 4.6**
    - _Requirements: 1.2, 1.4, 1.5, 1.6, 2.2, 2.4, 2.5, 2.6, 3.2, 3.4, 3.5, 3.6, 4.2, 4.4, 4.5, 4.6_

- [x] 12. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，询问用户是否有问题。

## Notes

- 任务标记 `*` 的为可选测试任务，可以跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号，确保可追溯性
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
- 所有用户可见文本必须使用 t() 函数包裹，支持中英文国际化
- 转存操作使用异步 API 调用，避免阻塞 UI 线程
- 批量转存使用分批处理和并发控制，确保性能和稳定性
- 权限检查在前端和后端都要执行，确保安全性
- 所有转存操作记录审计日志，确保可追溯性
