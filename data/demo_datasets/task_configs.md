# 综合标注任务配置

## 任务 1: 图文多模态标注任务

### 任务描述
这是一个综合性的图文标注任务，结合了图像分类、目标检测、文本分类、命名实体识别等多种标注类型。

### 数据文件
`comprehensive_task_1.json`

### Label Studio 配置

```xml
<View>
  <!-- 图像显示 -->
  <Header value="图像内容"/>
  <Image name="image" value="$image" zoom="true" zoomControl="true"/>
  
  <!-- 目标检测 -->
  <Header value="1. 目标检测 - 标注图像中的物体"/>
  <RectangleLabels name="objects" toName="image" strokeWidth="3">
    <Label value="人物" background="#FF0000"/>
    <Label value="动物" background="#00FF00"/>
    <Label value="食物" background="#0000FF"/>
    <Label value="建筑" background="#FFFF00"/>
    <Label value="自然景观" background="#FF00FF"/>
    <Label value="电子设备" background="#00FFFF"/>
    <Label value="家具" background="#FFA500"/>
    <Label value="交通工具" background="#800080"/>
  </RectangleLabels>
  
  <!-- 图像分类 -->
  <Header value="2. 图像分类 - 选择图像的主要类别"/>
  <Choices name="image_category" toName="image" choice="single" showInLine="true">
    <Choice value="办公场景"/>
    <Choice value="美食"/>
    <Choice value="宠物"/>
    <Choice value="自然风光"/>
    <Choice value="城市建筑"/>
    <Choice value="其他"/>
  </Choices>
  
  <!-- 图像质量评估 -->
  <Header value="3. 图像质量评估"/>
  <Rating name="image_quality" toName="image" maxRating="5" icon="star" size="medium"/>
  
  <!-- 文本显示 -->
  <Header value="文本内容"/>
  <Text name="text" value="$text"/>
  
  <!-- 文本分类 -->
  <Header value="4. 文本情感分析"/>
  <Choices name="sentiment" toName="text" choice="single" showInLine="true">
    <Choice value="积极"/>
    <Choice value="中性"/>
    <Choice value="消极"/>
  </Choices>
  
  <!-- 命名实体识别 -->
  <Header value="5. 命名实体识别 - 标注文本中的实体"/>
  <Labels name="entities" toName="text">
    <Label value="地点" background="#FFD700"/>
    <Label value="时间" background="#90EE90"/>
    <Label value="产品" background="#87CEEB"/>
    <Label value="品牌" background="#DDA0DD"/>
    <Label value="人名" background="#F08080"/>
  </Labels>
  
  <!-- 关键词提取 -->
  <Header value="6. 关键词标注"/>
  <Choices name="keywords" toName="text" choice="multiple" showInLine="true">
    <Choice value="科技"/>
    <Choice value="美食"/>
    <Choice value="旅游"/>
    <Choice value="宠物"/>
    <Choice value="办公"/>
    <Choice value="自然"/>
    <Choice value="城市"/>
  </Choices>
  
  <!-- 文本摘要 -->
  <Header value="7. 生成摘要"/>
  <TextArea name="summary" toName="text" 
            placeholder="请用一句话概括这段内容..."
            maxSubmissions="1" editable="true" rows="2"/>
  
  <!-- 元数据显示 -->
  <Header value="元数据信息"/>
  <Text name="metadata" value="来源: $metadata.source | 日期: $metadata.date | 地点: $metadata.location"/>
  
  <!-- 整体评价 -->
  <Header value="8. 整体质量评价"/>
  <Choices name="overall_quality" toName="image" choice="single" showInLine="true">
    <Choice value="优秀"/>
    <Choice value="良好"/>
    <Choice value="一般"/>
    <Choice value="较差"/>
  </Choices>
  
  <!-- 备注 -->
  <Header value="9. 备注说明"/>
  <TextArea name="notes" toName="image" 
            placeholder="请添加任何额外的备注或说明..."
            maxSubmissions="1" editable="true" rows="3"/>
</View>
```

### 标注指南

1. **目标检测**: 用矩形框标注图像中的所有可识别物体
2. **图像分类**: 选择最能代表图像主题的类别
3. **图像质量**: 根据清晰度、构图、光线等因素评分
4. **情感分析**: 判断文本描述的整体情感倾向
5. **实体识别**: 标注文本中的地点、时间、产品等实体
6. **关键词**: 选择与内容相关的所有关键词
7. **摘要**: 用简洁的语言概括图文内容
8. **整体评价**: 综合评估数据质量
9. **备注**: 记录任何特殊情况或需要说明的内容

---

## 任务 2: 多媒体综合标注任务

### 任务描述
这是一个包含音频、视频、文本、HTML 的全方位多媒体标注任务，展示 Label Studio 对各种数据类型的支持。

### 数据文件
`comprehensive_task_2.json`

### Label Studio 配置

```xml
<View>
  <!-- 视频标注 -->
  <Header value="视频内容"/>
  <Video name="video" value="$video" sync="audio"/>
  
  <!-- 视频中的目标检测 -->
  <Header value="1. 视频目标检测 - 标注视频中的物体"/>
  <VideoRectangle name="video_objects" toName="video" strokeWidth="2"/>
  <Labels name="video_labels" toName="video">
    <Label value="人物" background="#FF0000"/>
    <Label value="动物" background="#00FF00"/>
    <Label value="车辆" background="#0000FF"/>
    <Label value="建筑" background="#FFFF00"/>
    <Label value="产品" background="#FF00FF"/>
  </Labels>
  
  <!-- 视频分类 -->
  <Header value="2. 视频类别"/>
  <Choices name="video_category" toName="video" choice="single" showInLine="true">
    <Choice value="广告"/>
    <Choice value="旅游"/>
    <Choice value="娱乐"/>
    <Choice value="动画"/>
    <Choice value="科幻"/>
    <Choice value="教育"/>
  </Choices>
  
  <!-- 音频标注 -->
  <Header value="音频内容"/>
  <Audio name="audio" value="$audio" sync="video"/>
  
  <!-- 音频分类 -->
  <Header value="3. 音频类型"/>
  <Choices name="audio_type" toName="audio" choice="multiple" showInLine="true">
    <Choice value="音乐"/>
    <Choice value="语音"/>
    <Choice value="音效"/>
    <Choice value="环境音"/>
    <Choice value="背景音乐"/>
  </Choices>
  
  <!-- 音频质量 -->
  <Header value="4. 音频质量"/>
  <Rating name="audio_quality" toName="audio" maxRating="5" icon="star" size="medium"/>
  
  <!-- 音频情感 -->
  <Header value="5. 音频情感/氛围"/>
  <Choices name="audio_mood" toName="audio" choice="multiple" showInLine="true">
    <Choice value="欢快"/>
    <Choice value="平静"/>
    <Choice value="紧张"/>
    <Choice value="悲伤"/>
    <Choice value="激动"/>
    <Choice value="神秘"/>
  </Choices>
  
  <!-- 文本描述 -->
  <Header value="文本描述"/>
  <Text name="text" value="$text"/>
  
  <!-- 文本分类 -->
  <Header value="6. 内容主题"/>
  <Choices name="text_theme" toName="text" choice="multiple" showInLine="true">
    <Choice value="科技"/>
    <Choice value="旅游"/>
    <Choice value="娱乐"/>
    <Choice value="艺术"/>
    <Choice value="体育"/>
    <Choice value="教育"/>
  </Choices>
  
  <!-- HTML 内容 -->
  <Header value="HTML 内容"/>
  <HyperText name="html" value="$html"/>
  
  <!-- HTML 元素标注 -->
  <Header value="7. HTML 元素标注"/>
  <Labels name="html_elements" toName="html">
    <Label value="标题" background="#FF6B6B"/>
    <Label value="正文" background="#4ECDC4"/>
    <Label value="关键信息" background="#FFE66D"/>
    <Label value="日期时间" background="#95E1D3"/>
    <Label value="作者" background="#F38181"/>
    <Label value="评分" background="#AA96DA"/>
    <Label value="链接" background="#FCBAD3"/>
  </Labels>
  
  <!-- 内容完整性 -->
  <Header value="8. 内容完整性检查"/>
  <Choices name="completeness" toName="video" choice="multiple" showInLine="true">
    <Choice value="视频完整"/>
    <Choice value="音频完整"/>
    <Choice value="文本完整"/>
    <Choice value="HTML完整"/>
    <Choice value="元数据完整"/>
  </Choices>
  
  <!-- 内容一致性 -->
  <Header value="9. 多模态内容一致性"/>
  <Choices name="consistency" toName="video" choice="single" showInLine="true">
    <Choice value="完全一致"/>
    <Choice value="基本一致"/>
    <Choice value="部分一致"/>
    <Choice value="不一致"/>
  </Choices>
  
  <!-- 语言识别 -->
  <Header value="10. 语言识别"/>
  <Choices name="language" toName="text" choice="single" showInLine="true">
    <Choice value="中文"/>
    <Choice value="英文"/>
    <Choice value="中英混合"/>
    <Choice value="其他"/>
  </Choices>
  
  <!-- 适用年龄 -->
  <Header value="11. 内容分级"/>
  <Choices name="age_rating" toName="video" choice="single" showInLine="true">
    <Choice value="全年龄"/>
    <Choice value="12+"/>
    <Choice value="16+"/>
    <Choice value="18+"/>
  </Choices>
  
  <!-- 转录/翻译 -->
  <Header value="12. 音频转录或翻译"/>
  <TextArea name="transcription" toName="audio" 
            placeholder="请转录音频内容或提供翻译..."
            maxSubmissions="1" editable="true" rows="4"/>
  
  <!-- 综合评价 -->
  <Header value="13. 综合质量评分"/>
  <Rating name="overall_rating" toName="video" maxRating="10" icon="star" size="large"/>
  
  <!-- 标签 -->
  <Header value="14. 内容标签"/>
  <Taxonomy name="tags" toName="video">
    <Choice value="内容类型">
      <Choice value="教育"/>
      <Choice value="娱乐"/>
      <Choice value="商业"/>
      <Choice value="艺术"/>
    </Choice>
    <Choice value="风格">
      <Choice value="现代"/>
      <Choice value="传统"/>
      <Choice value="抽象"/>
      <Choice value="写实"/>
    </Choice>
    <Choice value="情感">
      <Choice value="积极"/>
      <Choice value="中性"/>
      <Choice value="消极"/>
    </Choice>
  </Taxonomy>
  
  <!-- 备注 -->
  <Header value="15. 详细备注"/>
  <TextArea name="detailed_notes" toName="video" 
            placeholder="请记录任何重要的观察、问题或建议..."
            maxSubmissions="1" editable="true" rows="5"/>
</View>
```

### 标注指南

1. **视频目标检测**: 在关键帧标注出现的物体
2. **视频分类**: 选择视频的主要类别
3. **音频类型**: 识别音频中包含的所有声音类型
4. **音频质量**: 评估音频的清晰度和质量
5. **音频情感**: 判断音频传达的情感或氛围
6. **内容主题**: 选择文本描述的主题
7. **HTML 元素**: 标注 HTML 中的关键信息
8. **完整性检查**: 确认各部分内容是否完整
9. **一致性**: 评估多模态内容之间的一致性
10. **语言识别**: 识别内容使用的语言
11. **内容分级**: 根据内容适合的年龄段分级
12. **转录/翻译**: 转录音频或翻译外语内容
13. **综合评分**: 对整体质量打分
14. **内容标签**: 使用层级标签分类内容
15. **详细备注**: 记录详细的观察和建议

---

## 使用说明

### 导入步骤

1. 登录 Label Studio (http://localhost:8080)
2. 创建新项目
3. 在 "Labeling Setup" 中选择 "Code" 模式
4. 复制上述对应的 XML 配置
5. 点击 "Save"
6. 在项目页面点击 "Import"
7. 上传对应的 JSON 文件

### 标注流程

1. **任务 1** 适合练习图文标注，包含 5 个样本
2. **任务 2** 适合练习多媒体标注，包含 5 个样本
3. 每个任务都包含多个标注步骤，建议按顺序完成
4. 可以保存草稿，随时继续标注
5. 完成后提交，可以查看标注结果

### 导出结果

标注完成后，可以导出为多种格式：
- JSON - 完整的标注数据
- CSV - 表格格式
- COCO - 目标检测格式
- YOLO - 目标检测格式

### 团队协作

- 可以邀请团队成员共同标注
- 支持标注任务分配
- 支持标注质量审核
- 支持标注一致性检查

## 功能展示清单

### 任务 1 展示的功能
- ✅ 图像显示和缩放
- ✅ 目标检测（矩形框）
- ✅ 图像分类
- ✅ 评分系统
- ✅ 文本显示
- ✅ 文本分类
- ✅ 命名实体识别
- ✅ 多选分类
- ✅ 文本输入
- ✅ 元数据显示

### 任务 2 展示的功能
- ✅ 视频播放和标注
- ✅ 视频目标检测
- ✅ 音频播放和标注
- ✅ 音视频同步
- ✅ HTML 内容显示和标注
- ✅ 多模态数据关联
- ✅ 层级分类（Taxonomy）
- ✅ 复杂的多步骤标注流程
- ✅ 内容质量评估
- ✅ 详细备注记录

## 扩展建议

1. **添加预标注**: 使用 ML 模型生成预标注结果
2. **自定义快捷键**: 提高标注效率
3. **标注指南**: 为团队成员提供详细的标注规范
4. **质量控制**: 设置标注审核流程
5. **数据增强**: 对标注数据进行增强处理
