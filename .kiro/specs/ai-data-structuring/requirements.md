# 需求文档：AI 驱动的结构化数据分析

## 简介

对上传的非结构化文件（PDF/CSV/Excel/Word/HTML）进行 AI 结构化分析，包括 Schema 推断、字段提取、实体识别，将结构化结果存入数据库，并自动创建标注任务。

**复用原则**：FileExtractor（PDF/DOCX/TXT/HTML 提取）、Document Model、Task Model、LLMConfiguration、Celery/Redis 基础设施均已存在，本次只新增 AI 结构化分析管道和对应的前端页面。

## 术语表

- **StructuringJob**: 结构化分析任务，跟踪从文件上传到结构化完成的全流程
- **InferredSchema**: LLM 推断的数据 Schema，包含字段名、类型、描述、是否必填
- **StructuredRecord**: 按 Schema 从原始内容中提取的结构化记录
- **TabularParser**: CSV/Excel 表格解析器，输出统一的 TabularData
- **SchemaInferrer**: LLM 驱动的 Schema 推断器
- **EntityExtractor**: LLM 驱动的实体/字段提取器

## 需求

### 需求 1：文件上传与内容提取

**用户故事：** 作为数据管理员，我希望上传各种格式的文件并自动提取内容，以便后续进行 AI 结构化分析。

#### 验收标准

1. WHEN 用户上传文件，THE Structuring API SHALL 支持 PDF、CSV、Excel、DOCX、HTML、TXT 格式，文件大小上限 100MB
2. WHEN 文件类型为 PDF/DOCX/TXT/HTML，THE Pipeline SHALL 调用现有 FileExtractor 提取文本内容
3. WHEN 文件类型为 CSV/Excel，THE TabularParser SHALL 使用 pandas 解析表格数据，返回 headers + rows 结构
4. WHEN 文件上传成功，THE API SHALL 创建 StructuringJob（status=pending）并返回 job_id
5. IF 文件格式不支持或文件损坏，THEN THE API SHALL 返回 400 错误并提示具体原因

### 需求 2：AI Schema 推断

**用户故事：** 作为数据管理员，我希望系统自动推断上传数据的结构化 Schema，以便快速了解数据包含哪些字段和实体。

#### 验收标准

1. WHEN 文本内容提取完成，THE SchemaInferrer SHALL 通过 LLM（instructor + OpenAI）推断数据 Schema，包含字段名、字段类型（string/integer/float/boolean/date/entity/list）、描述和是否必填
2. WHEN Schema 推断完成，THE SchemaInferrer SHALL 返回 InferredSchema，其中所有字段名唯一，置信度在 0.0-1.0 范围内
3. WHEN 推断的 Schema 置信度 < 0.3，THE 前端 SHALL 显示低置信度警告并建议用户手动编辑
4. THE 前端 SHALL 提供 Schema 编辑器，允许用户修改字段名、类型、是否必填，并确认最终 Schema
5. IF LLM 调用失败，THEN THE Pipeline SHALL 重试 3 次（指数退避），仍失败则 Job 标记为 failed

### 需求 3：结构化数据提取

**用户故事：** 作为数据管理员，我希望系统按确认的 Schema 从原始内容中提取结构化数据，以便存入数据库供后续使用。

#### 验收标准

1. WHEN 用户确认 Schema 后，THE EntityExtractor SHALL 按 Schema 定义从原始内容中提取结构化记录
2. WHEN 提取完成，THE 每条 StructuredRecord 的 fields 中 SHALL 包含所有 required=true 的字段
3. WHEN 提取完成，THE ExtractionResult SHALL 包含 records 列表、total_extracted 数量和 avg_confidence 平均置信度
4. THE Pipeline SHALL 将结构化记录批量存入 structured_records 表（JSONB 格式）
5. IF 部分记录提取失败，THEN THE Pipeline SHALL 跳过失败记录并记录到 Job.metadata.skipped_records

### 需求 4：自动创建标注任务

**用户故事：** 作为项目管理员，我希望结构化完成后自动创建标注任务，以便标注团队可以立即开始工作。

#### 验收标准

1. WHEN StructuringJob 状态变为 completed，THE Pipeline SHALL 自动创建关联的标注 Task
2. THE 创建的 Task SHALL 包含 job_id 引用、结构化 Schema 信息和记录数量
3. WHEN 用户在结果页面点击"创建标注任务"按钮，THE API SHALL 支持手动触发标注任务创建
4. THE 前端结果页 SHALL 展示结构化记录列表、Schema 信息和标注任务创建状态

### 需求 5：Job 状态管理与监控

**用户故事：** 作为数据管理员，我希望实时了解结构化任务的进度和状态，以便及时处理异常。

#### 验收标准

1. THE StructuringJob 状态 SHALL 按 pending → extracting → inferring → confirming → extracting_entities → completed 顺序转换，或从任意状态转为 failed
2. WHEN 用户查询 Job 状态，THE API SHALL 返回当前状态、已提取记录数、Schema 信息和错误信息（如有）
3. THE 前端 SHALL 提供 Job 列表页，展示所有结构化任务的状态、文件名、创建时间和记录数
4. WHEN Job 失败，THE 前端 SHALL 显示错误详情并提供重试按钮

### 需求 6：前端结构化工作流

**用户故事：** 作为数据管理员，我希望通过直观的前端界面完成文件上传、内容预览、Schema 确认和结果查看的完整流程。

#### 验收标准

1. THE 前端 SHALL 提供文件上传页面，支持拖拽上传和文件选择，显示上传进度
2. WHEN 文件内容提取完成，THE 前端 SHALL 展示内容预览（文本前 500 字符或表格前 20 行）
3. WHEN Schema 推断完成，THE 前端 SHALL 展示 Schema 编辑器，支持字段增删改和类型选择
4. THE 前端 SHALL 提供结构化结果页面，以表格形式展示提取的记录，支持分页和搜索
5. THE 前端状态管理 SHALL 使用 Zustand store，API 调用使用 apiClient
