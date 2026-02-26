# 需求文档

## 简介

AI 数据处理系统，对 PDF、PPT、Word、Excel、CSV、HTML、TXT、视频、音频等非结构化/半结构化数据提供三种处理能力：结构化（已实现）、向量化（新增）、语义化（新增）。在 DataSync 页面新增"AI 数据处理"Tab，统一管理三种处理流程。

## 术语表

- **处理系统 (Processing_System)**: AI 数据处理后端服务，包含结构化、向量化、语义化管道
- **前端界面 (Frontend_UI)**: DataSync 页面中的"AI 数据处理"Tab 及其子 Tab
- **PPT提取器 (PPT_Extractor)**: 基于 python-pptx 的 PPT/PPTX 文本提取组件
- **音视频转录器 (Media_Transcriber)**: 基于 Whisper API 的音视频转文本组件
- **向量化管道 (Vectorization_Pipeline)**: 文本分块 → Embedding → pgvector 存储的处理流程
- **语义化管道 (Semantic_Pipeline)**: LLM 提取实体、关系、摘要的处理流程
- **分块函数 (Chunker)**: 按 token 数将文本切分为重叠块的函数
- **状态机 (Job_State_Machine)**: 控制任务状态合法转换的组件

## 需求

### 需求 1: 文件类型支持与内容提取

**用户故事:** 作为数据工程师，我希望上传多种格式的文件进行 AI 处理，以便处理各类非结构化数据。

#### 验收标准

1. THE Processing_System SHALL 支持以下文件类型: PDF, DOCX, HTML, TXT, CSV, Excel, PPT/PPTX, Video, Audio
2. WHEN 用户上传 PDF/DOCX/HTML/TXT 文件时, THE Processing_System SHALL 使用 FileExtractor 提取文本内容
3. WHEN 用户上传 CSV/Excel 文件时, THE Processing_System SHALL 使用 TabularParser 解析为表头和行数据
4. WHEN 用户上传 .pptx 文件时, THE PPT_Extractor SHALL 按幻灯片顺序提取全部文本内容并返回拼接结果
5. WHEN 用户上传视频文件时, THE Media_Transcriber SHALL 先用 ffmpeg 提取音轨，再调用 Whisper API 转录为文本
6. WHEN 用户上传音频文件时, THE Media_Transcriber SHALL 直接调用 Whisper API 转录为文本
7. IF 文件提取或转录失败, THEN THE Processing_System SHALL 将任务状态设为 failed 并记录 error_message

### 需求 2: 向量化处理

**用户故事:** 作为数据工程师，我希望将文档内容向量化存储，以便后续进行语义检索和相似度匹配。

#### 验收标准

1. WHEN 用户提交向量化任务时, THE Processing_System SHALL 通过 POST /api/vectorization/jobs 创建任务并提交 Celery 管道
2. WHEN 向量化管道执行时, THE Vectorization_Pipeline SHALL 按顺序执行: 内容提取 → 文本分块 → Embedding → 批量写入 vector_records
3. THE Chunker SHALL 按 512 token 大小分块，相邻块保留 50 token 重叠
4. WHEN 分块完成后, THE Vectorization_Pipeline SHALL 调用 LLMSwitcher.embed() 生成 1536 维向量
5. WHEN 用户查询向量化任务状态时, THE Processing_System SHALL 通过 GET /api/vectorization/jobs/:id 返回任务状态和向量记录数

### 需求 3: 语义化处理

**用户故事:** 作为数据工程师，我希望对文档进行语义分析，以便自动提取实体、关系和摘要。

#### 验收标准

1. WHEN 用户提交语义化任务时, THE Processing_System SHALL 通过 POST /api/semantic/jobs 创建任务并提交 Celery 管道
2. WHEN 语义化管道执行时, THE Semantic_Pipeline SHALL 调用 LLM 提取实体和关系，并生成文档摘要
3. THE Semantic_Pipeline SHALL 将结果存入 semantic_records 表，record_type 为 entity、relationship 或 summary
4. WHEN 用户查询语义化任务状态时, THE Processing_System SHALL 通过 GET /api/semantic/jobs/:id 返回任务状态和语义记录

### 需求 4: 文本分块正确性

**用户故事:** 作为数据工程师，我希望文本分块覆盖原文全部内容且无遗漏，以便向量化结果完整可靠。

#### 验收标准

1. THE Chunker SHALL 保证所有分块拼接后覆盖原始文本的全部内容
2. THE Chunker SHALL 保证每个分块的 token 数不超过指定的 chunk_size
3. WHEN 输入文本非空时, THE Chunker SHALL 返回至少一个分块
4. WHEN chunk_size 大于 overlap 且 overlap 大于 0 时, THE Chunker SHALL 保证相邻分块有指定数量的 token 重叠

### 需求 5: 数据模型与状态管理

**用户故事:** 作为开发者，我希望处理任务有清晰的状态管理和数据模型，以便系统可靠运行。

#### 验收标准

1. THE Processing_System SHALL 为每个任务记录 processing_type，值为 structuring、vectorization 或 semantic 之一
2. THE Job_State_Machine SHALL 验证所有状态转换的合法性，拒绝非法转换
3. THE Processing_System SHALL 将向量记录存入 vector_records 表，每条记录包含 job_id、chunk_index、chunk_text、embedding 和 metadata
4. THE Processing_System SHALL 将语义记录存入 semantic_records 表，每条记录包含 job_id、record_type、content 和 confidence
5. WHEN 向量记录写入时, THE Processing_System SHALL 保证 embedding 维度为 1536

### 需求 6: 前端界面

**用户故事:** 作为数据工程师，我希望在 DataSync 页面统一管理三种数据处理流程，以便高效操作。

#### 验收标准

1. WHEN 用户访问 DataSync 页面时, THE Frontend_UI SHALL 显示"AI 数据处理"Tab
2. WHEN 用户进入"AI 数据处理"Tab 时, THE Frontend_UI SHALL 显示结构化、向量化、语义化三个子 Tab
3. WHEN 用户在任一子 Tab 中操作时, THE Frontend_UI SHALL 提供文件上传、任务列表和结果查看功能
4. WHEN 任务状态变更时, THE Frontend_UI SHALL 实时更新任务列表中的状态显示
