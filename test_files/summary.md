# 文件格式支持状态总结

## 已完成的工作

### 1. 后端支持的文件格式

#### 文本类格式（_TEXT_TYPES）
- ✅ **PDF** - 使用 pypdf 库提取
- ✅ **DOCX** - 使用 python-docx 库提取
- ✅ **TXT** - 直接读取文本
- ✅ **HTML** - 使用 BeautifulSoup 解析
- ✅ **Markdown (.md)** - 作为纯文本处理（新增）
- ✅ **JSON (.json)** - 作为纯文本处理（新增）

#### 表格类格式（_TABULAR_TYPES）
- ✅ **CSV** - 使用 TabularParser
- ✅ **Excel (.xlsx, .xls)** - 使用 TabularParser

#### 演示文稿格式（_PPT_TYPES）
- ✅ **PPT/PPTX** - 使用 PPTExtractor

#### 媒体格式（_MEDIA_TYPES）
- ✅ **Video** - 使用 MediaTranscriber
- ✅ **Audio** - 使用 MediaTranscriber

### 2. 前端支持的文件格式

在 `DataStructuring/Upload.tsx` 中：
```typescript
const ACCEPTED_EXTENSIONS = [
  '.pdf', '.csv', '.xlsx', '.xls', 
  '.docx', '.html', '.htm', '.txt', 
  '.md', '.json'
];
```

### 3. 代码修改清单

#### src/extractors/file.py
```python
def extract_data(self, **kwargs) -> ExtractionResult:
    if self.config.file_type == FileType.PDF:
        return self._extract_pdf()
    elif self.config.file_type == FileType.DOCX:
        return self._extract_docx()
    elif self.config.file_type == FileType.TXT:
        return self._extract_text()
    elif self.config.file_type == FileType.HTML:
        return self._extract_html()
    elif self.config.file_type == FileType.MARKDOWN:
        return self._extract_text()  # 新增
    elif self.config.file_type == FileType.JSON:
        return self._extract_text()  # 新增
```

#### src/services/structuring_pipeline.py
```python
_TEXT_TYPES = {
    StructuringFileType.PDF.value,
    StructuringFileType.DOCX.value,
    StructuringFileType.TXT.value,
    StructuringFileType.HTML.value,
    StructuringFileType.MARKDOWN.value,  # 新增
    StructuringFileType.JSON.value,      # 新增
}
```

#### docker-compose.yml
```yaml
# app 服务
volumes:
  - ./src:/app/src
  - ./logs:/var/log/superinsight
  - ./uploads:/app/uploads  # 新增

# celery-worker 服务
volumes:
  - ./src:/app/src
  - ./logs:/var/log/superinsight
  - ./uploads:/app/uploads  # 新增
```

### 4. 测试文件已创建

- ✅ test_markdown.md - Markdown 格式测试
- ✅ test_json.json - JSON 格式测试
- ✅ test_files/test.txt - 纯文本测试
- ✅ test_files/test.html - HTML 格式测试
- ✅ test_files/test.csv - CSV 格式测试

## 测试方法

1. 访问前端页面：http://localhost:5173
2. 进入"数据结构化"页面
3. 上传任意支持格式的文件
4. 点击"查看处理进度"验证处理流程

## 技术说明

### Markdown 和 JSON 处理方式
- 两种格式都作为纯文本处理
- 复用 `_extract_text()` 方法
- 提取后的文本用于 Schema 推断和实体提取
- 适合包含结构化信息的文本内容

### 容器配置
- app 和 celery-worker 容器都已挂载 uploads 目录
- 确保文件在两个容器间共享
- 支持本地开发和生产环境

## 状态总结

✅ 所有前端声明的格式都已在后端实现支持
✅ 容器配置已更新，uploads 目录正确挂载
✅ 代码无语法错误，已通过 getDiagnostics 检查
✅ 测试文件已准备就绪
