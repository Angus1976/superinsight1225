# 任务列表：AI 数据处理（扩展）

## 概述

在已完成的结构化功能基础上，扩展支持 PPT/音视频文件类型，新增向量化和语义化处理管道，以及对应的前端界面。

## 已完成任务

- [x] 1. 后端数据模型与基础设施
  - [x] 1.1 创建 StructuringJob 和 StructuredRecord 模型、迁移脚本
  - [x] 1.2 实现 TabularParser（CSV/Excel）
- [x] 2. AI 分析核心模块
  - [x] 2.1 实现 SchemaInferrer 和 EntityExtractor
  - [x] 2.2 实现 LLM 重试机制
- [x] 3. Pipeline 编排与 API
  - [x] 3.1 实现 Celery 结构化管道和状态机
  - [x] 3.2 实现 6 个结构化 API 端点
- [x] 4. 前端页面与状态管理
  - [x] 4.1 实现结构化相关 Store、API、页面和 i18n
- [x] 5. 属性测试（结构化）
  - [x] 5.1 表格解析、置信度、状态机、Schema 唯一性、文件路由属性测试

## 新增任务

- [x] 6. 数据模型扩展与新增提取器
  - [x] 6.1 扩展 FileType 枚举（加 PPT/VIDEO/AUDIO），新增 ProcessingType 枚举，扩展 StructuringJob 模型（processing_type, chunk_count 字段）
    - _需求: 1.1, 5.1_
  - [x] 6.2 创建 VectorRecord 和 SemanticRecord 模型，编写数据库迁移（含 pgvector 扩展）
    - _需求: 5.3, 5.4, 5.5_
  - [x] 6.3 创建 `src/extractors/ppt.py` PPTExtractor，用 python-pptx 按页提取文本
    - _需求: 1.4_
  - [x] 6.4 创建 `src/extractors/media.py` MediaTranscriber，用 Whisper API + ffmpeg 转录音视频
    - _需求: 1.5, 1.6_
  - [x] 6.5 更新 structuring_pipeline.py 文件类型路由，支持 PPT/Video/Audio
    - _需求: 1.1, 1.4, 1.5, 1.6, 1.7_

- [x] 7. 检查点 - 确保提取器和模型扩展正确
  - 确保所有测试通过，如有疑问请询问用户。

- [ ] 8. 向量化管道
  - [x] 8.1 实现 `chunk_text()` 函数（tiktoken 分词，token 级分块，overlap 重叠）
    - _需求: 2.3, 4.1, 4.2, 4.3, 4.4_
  - [ ]* 8.2 属性测试: 分块覆盖完整性
    - **Property 1: 分块覆盖完整性**
    - **Validates: 需求 4.1**
  - [ ]* 8.3 属性测试: 分块大小上限
    - **Property 2: 分块大小上限**
    - **Validates: 需求 2.3, 4.2**
  - [ ]* 8.4 属性测试: 分块重叠正确性
    - **Property 3: 分块重叠正确性**
    - **Validates: 需求 4.4**
  - [x] 8.5 创建 `src/services/vectorization_pipeline.py`，实现提取→分块→embed→批量写入 vector_records
    - _需求: 2.1, 2.2, 2.4_
  - [ ]* 8.6 属性测试: Embedding 维度一致性
    - **Property 4: Embedding 维度一致性**
    - **Validates: 需求 2.4, 5.5**

- [ ] 9. 语义化管道
  - [x] 9.1 创建 `src/services/semantic_pipeline.py`，实现提取→LLM 分析→存储实体/关系/摘要
    - _需求: 3.1, 3.2, 3.3_
  - [ ]* 9.2 属性测试: record_type 枚举约束
    - **Property 7: record_type 枚举约束**
    - **Validates: 需求 3.3**

- [ ] 10. API 端点
  - [x] 10.1 创建向量化 API（POST/GET /api/vectorization/jobs, GET .../records）
    - _需求: 2.1, 2.5_
  - [x] 10.2 创建语义化 API（POST/GET /api/semantic/jobs, GET .../records）
    - _需求: 3.1, 3.4_
  - [ ]* 10.3 属性测试: processing_type 枚举约束
    - **Property 6: processing_type 枚举约束**
    - **Validates: 需求 5.1**

- [x] 11. 检查点 - 确保后端管道和 API 正确
  - 确保所有测试通过，如有疑问请询问用户。

- [x] 12. 前端扩展
  - [x] 12.1 创建 vectorizationStore.ts 和 semanticStore.ts（Zustand）
    - _需求: 6.4_
  - [x] 12.2 创建 AIProcessingTab 组件，含结构化/向量化/语义化三个子 Tab
    - _需求: 6.1, 6.2_
  - [x] 12.3 实现向量化和语义化子 Tab（上传、任务列表、结果查看）
    - _需求: 6.3_
  - [x] 12.4 添加新增功能的 i18n 翻译 key（zh + en）
    - _需求: 6.1, 6.2, 6.3_

- [ ] 13. 补充属性测试
  - [ ]* 13.1 属性测试: 文件类型路由正确性（含 PPT/Video/Audio）
    - **Property 10: 文件类型路由正确性**
    - **Validates: 需求 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
  - [ ]* 13.2 属性测试: 向量记录数据完整性
    - **Property 8: 向量记录数据完整性**
    - **Validates: 需求 5.3**
  - [ ]* 13.3 属性测试: 语义记录数据完整性
    - **Property 9: 语义记录数据完整性**
    - **Validates: 需求 5.4**

- [x] 14. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有疑问请询问用户。

## 备注

- 带 `*` 的子任务为可选测试任务，可跳过以加速 MVP
- 后端使用 Python，前端使用 TypeScript
- 属性测试验证设计文档中的正确性属性
