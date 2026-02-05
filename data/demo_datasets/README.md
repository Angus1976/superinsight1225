# Label Studio 演示数据集

本目录包含多种类型的演示数据集，用于展示 Label Studio 的标注能力。

## 数据集列表

### 文本类型
1. **text_classification.json** - 电商评论情感分类（10条）
2. **ner_dataset.json** - 命名实体识别（10条）
3. **qa_dataset.json** - 问答系统（5条）
4. **text_summarization.json** - 文本摘要（5条）
5. **dialogue_dataset.json** - 对话系统（3条）
6. **relation_extraction.json** - 关系抽取（8条）

### 图像类型
7. **image_classification.json** - 图像分类（10张）
8. **object_detection.json** - 目标检测（5张）
9. **semantic_segmentation.json** - 语义分割（3张）
10. **ocr_annotation.json** - OCR 文字识别（3张）

### 多媒体类型
11. **audio_classification.json** - 音频分类（5个）
12. **video_annotation.json** - 视频标注（5个）

### 其他类型
13. **html_annotation.json** - HTML 内容标注（5个）
14. **time_series.json** - 时间序列标注（3个）

## 手动导入步骤

### 方法 1: 通过 UI 导入

1. 访问 Label Studio: http://localhost:8080
2. 登录（用户名: admin@example.com, 密码: admin）
3. 点击 "Create Project"
4. 输入项目名称和描述
5. 在 "Labeling Setup" 中选择模板或自定义配置
6. 点击 "Save"
7. 在项目页面点击 "Import"
8. 选择对应的 JSON 文件上传

### 方法 2: 使用 Python 脚本

```bash
# 安装依赖
pip install requests

# 运行导入脚本（需要先获取有效的 API Token）
python3 scripts/import_demo_data.py
```

## 标注配置示例

### 1. 文本分类
```xml
<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single">
    <Choice value="正面"/>
    <Choice value="负面"/>
    <Choice value="中性"/>
  </Choices>
</View>
```

### 2. 命名实体识别 (NER)
```xml
<View>
  <Labels name="label" toName="text">
    <Label value="人名" background="red"/>
    <Label value="公司" background="blue"/>
    <Label value="地点" background="green"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

### 3. 图像分类
```xml
<View>
  <Image name="image" value="$image"/>
  <Choices name="category" toName="image" choice="single">
    <Choice value="自然风光"/>
    <Choice value="城市建筑"/>
    <Choice value="动物"/>
  </Choices>
</View>
```

### 4. 目标检测
```xml
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="car" background="red"/>
    <Label value="person" background="blue"/>
  </RectangleLabels>
</View>
```

### 5. 音频分类
```xml
<View>
  <Audio name="audio" value="$audio"/>
  <Choices name="category" toName="audio" choice="single">
    <Choice value="音乐"/>
    <Choice value="语音"/>
    <Choice value="噪音"/>
  </Choices>
</View>
```

### 6. 视频标注
```xml
<View>
  <Video name="video" value="$video"/>
  <VideoRectangle name="box" toName="video"/>
  <Labels name="videoLabels" toName="video">
    <Label value="人物" background="red"/>
    <Label value="车辆" background="blue"/>
  </Labels>
</View>
```

### 7. HTML 标注
```xml
<View>
  <HyperText name="html" value="$html"/>
  <Labels name="label" toName="html">
    <Label value="标题" background="red"/>
    <Label value="正文" background="blue"/>
  </Labels>
</View>
```

### 8. OCR 标注
```xml
<View>
  <Image name="image" value="$image"/>
  <Rectangle name="bbox" toName="image"/>
  <TextArea name="transcription" toName="image" 
            editable="true" perRegion="true"/>
</View>
```

## 数据格式说明

### 基本格式
```json
[
  {
    "field_name": "value",
    "another_field": "another_value"
  }
]
```

### 文本数据
```json
{
  "text": "这是要标注的文本内容"
}
```

### 图像数据
```json
{
  "image": "https://example.com/image.jpg"
}
```

### 音频数据
```json
{
  "audio": "https://example.com/audio.mp3"
}
```

### 视频数据
```json
{
  "video": "https://example.com/video.mp4"
}
```

### HTML 数据
```json
{
  "html": "<div><h1>标题</h1><p>内容</p></div>"
}
```

## 注意事项

1. **URL 访问**: 确保图像、音频、视频的 URL 可以从 Label Studio 容器访问
2. **CORS 问题**: 如果使用外部 URL，可能需要配置 CORS
3. **文件大小**: 大文件建议使用云存储（S3、MinIO 等）
4. **编码格式**: JSON 文件使用 UTF-8 编码
5. **数据隐私**: 演示数据使用公开资源，生产环境请注意数据安全

## 扩展资源

- [Label Studio 官方文档](https://labelstud.io/guide/)
- [标注配置模板](https://labelstud.io/templates/)
- [API 文档](https://labelstud.io/api/)
- [GitHub 仓库](https://github.com/HumanSignal/label-studio)

## 常见问题

### Q: 如何获取 API Token?
A: 登录 Label Studio 后，访问 Account & Settings > Access Token

### Q: 导入失败怎么办?
A: 检查 JSON 格式是否正确，URL 是否可访问，Token 是否有效

### Q: 如何批量导入?
A: 可以使用 Python SDK 或 REST API 进行批量导入

### Q: 支持哪些文件格式?
A: JSON, CSV, TSV, TXT 等，具体参考官方文档
