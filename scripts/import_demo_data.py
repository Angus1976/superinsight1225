#!/usr/bin/env python3
"""
导入演示数据到 Label Studio
"""
import json
import requests
import sys

# Label Studio 配置
LS_URL = "http://localhost:8080"
LS_TOKEN = "f6d8ca85d2289294ca8b68ab4e24210d9a0a9c17"

headers = {
    "Authorization": f"Token {LS_TOKEN}",
    "Content-Type": "application/json"
}

def create_project(title, description, label_config):
    """创建项目"""
    data = {
        "title": title,
        "description": description,
        "label_config": label_config
    }
    response = requests.post(f"{LS_URL}/api/projects", headers=headers, json=data)
    if response.status_code == 201:
        project = response.json()
        print(f"✓ 创建项目: {title} (ID: {project['id']})")
        return project['id']
    else:
        print(f"✗ 创建项目失败: {response.status_code}")
        print(response.text[:200])
        return None

def import_tasks(project_id, tasks):
    """导入任务"""
    for task in tasks:
        response = requests.post(
            f"{LS_URL}/api/projects/{project_id}/tasks",
            headers=headers,
            json=task
        )
        if response.status_code != 201:
            print(f"✗ 导入任务失败: {response.status_code}")
            return False
    print(f"✓ 导入 {len(tasks)} 个任务")
    return True

# 1. 文本分类项目
print("\n=== 1. 电商评论情感分类 ===")
label_config_1 = """<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single" showInLine="true">
    <Choice value="正面"/>
    <Choice value="负面"/>
    <Choice value="中性"/>
  </Choices>
  <Choices name="category" toName="text" choice="single" showInLine="true">
    <Choice value="产品质量"/>
    <Choice value="物流服务"/>
    <Choice value="客户服务"/>
    <Choice value="价格"/>
    <Choice value="其他"/>
  </Choices>
</View>"""

project_id_1 = create_project(
    "电商评论情感分类",
    "对电商评论进行情感分类（正面/负面/中性）和类别标注",
    label_config_1
)

if project_id_1:
    with open("data/demo_datasets/text_classification.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_1, tasks)

# 2. 命名实体识别项目
print("\n=== 2. 命名实体识别 (NER) ===")
label_config_2 = """<View>
  <Labels name="label" toName="text">
    <Label value="人名" background="red"/>
    <Label value="公司" background="blue"/>
    <Label value="地点" background="green"/>
    <Label value="时间" background="orange"/>
    <Label value="产品" background="purple"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>"""

project_id_2 = create_project(
    "命名实体识别 (NER)",
    "识别文本中的人名、公司、地点、时间等实体",
    label_config_2
)

if project_id_2:
    with open("data/demo_datasets/ner_dataset.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_2, tasks)

# 3. 问答系统项目
print("\n=== 3. 问答系统 (QA) ===")
label_config_3 = """<View>
  <Header value="上下文"/>
  <Text name="context" value="$context"/>
  <Header value="问题"/>
  <Text name="question" value="$question"/>
  <Header value="答案"/>
  <TextArea name="answer" toName="context" editable="true" 
            placeholder="请输入答案..." maxSubmissions="1"/>
</View>"""

project_id_3 = create_project(
    "问答系统 (QA)",
    "基于上下文回答问题",
    label_config_3
)

if project_id_3:
    with open("data/demo_datasets/qa_dataset.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_3, tasks)

# 4. 文本摘要项目
print("\n=== 4. 文本摘要 ===")
label_config_4 = """<View>
  <Text name="text" value="$text"/>
  <Header value="摘要"/>
  <TextArea name="summary" toName="text" editable="true" 
            placeholder="请输入摘要..." maxSubmissions="1" rows="3"/>
  <Choices name="quality" toName="text" choice="single" showInLine="true">
    <Choice value="优秀"/>
    <Choice value="良好"/>
    <Choice value="一般"/>
  </Choices>
</View>"""

project_id_4 = create_project(
    "文本摘要",
    "为长文本生成简洁的摘要",
    label_config_4
)

if project_id_4:
    with open("data/demo_datasets/text_summarization.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_4, tasks)

# 5. 对话系统项目
print("\n=== 5. 对话系统标注 ===")
label_config_5 = """<View>
  <Text name="dialogue" value="$dialogue"/>
  <Choices name="intent" toName="dialogue" choice="single" showInLine="true">
    <Choice value="咨询"/>
    <Choice value="投诉"/>
    <Choice value="建议"/>
    <Choice value="其他"/>
  </Choices>
  <Choices name="sentiment" toName="dialogue" choice="single" showInLine="true">
    <Choice value="满意"/>
    <Choice value="不满"/>
    <Choice value="中性"/>
  </Choices>
</View>"""

project_id_5 = create_project(
    "对话系统标注",
    "标注对话的意图和情感",
    label_config_5
)

if project_id_5:
    with open("data/demo_datasets/dialogue_dataset.json", "r", encoding="utf-8") as f:
        dialogues = json.load(f)
    # 转换对话格式
    tasks = []
    for item in dialogues:
        dialogue_text = "\n".join([f"{turn['role']}: {turn['text']}" for turn in item['dialogue']])
        tasks.append({"dialogue": dialogue_text})
    import_tasks(project_id_5, tasks)

# 6. 关系抽取项目
print("\n=== 6. 关系抽取 ===")
label_config_6 = """<View>
  <Labels name="label" toName="text">
    <Label value="人物" background="red"/>
    <Label value="组织" background="blue"/>
    <Label value="地点" background="green"/>
    <Label value="时间" background="orange"/>
  </Labels>
  <Text name="text" value="$text"/>
  <Relations>
    <Relation value="创始人"/>
    <Relation value="位于"/>
    <Relation value="成立于"/>
    <Relation value="CEO"/>
  </Relations>
</View>"""

project_id_6 = create_project(
    "关系抽取",
    "识别实体之间的关系（创始人、位于、成立于等）",
    label_config_6
)

if project_id_6:
    with open("data/demo_datasets/relation_extraction.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_6, tasks)

# 7. 图像分类项目
print("\n=== 7. 图像分类 ===")
label_config_7 = """<View>
  <Image name="image" value="$image"/>
  <Choices name="category" toName="image" choice="single" showInLine="true">
    <Choice value="自然风光"/>
    <Choice value="城市建筑"/>
    <Choice value="动物"/>
    <Choice value="食物"/>
    <Choice value="交通工具"/>
    <Choice value="其他"/>
  </Choices>
</View>"""

project_id_7 = create_project(
    "图像分类",
    "对图像进行分类标注",
    label_config_7
)

if project_id_7:
    with open("data/demo_datasets/image_classification.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_7, tasks)

# 8. 目标检测项目
print("\n=== 8. 目标检测 ===")
label_config_8 = """<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="car" background="red"/>
    <Label value="person" background="blue"/>
    <Label value="chair" background="green"/>
    <Label value="table" background="orange"/>
    <Label value="laptop" background="purple"/>
    <Label value="phone" background="pink"/>
    <Label value="dog" background="brown"/>
    <Label value="cat" background="yellow"/>
  </RectangleLabels>
</View>"""

project_id_8 = create_project(
    "目标检测",
    "在图像中标注物体的边界框",
    label_config_8
)

if project_id_8:
    with open("data/demo_datasets/object_detection.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_8, tasks)

# 9. 语义分割项目
print("\n=== 9. 语义分割 ===")
label_config_9 = """<View>
  <Image name="image" value="$image"/>
  <BrushLabels name="label" toName="image">
    <Label value="sky" background="#87CEEB"/>
    <Label value="mountain" background="#8B4513"/>
    <Label value="forest" background="#228B22"/>
    <Label value="water" background="#4169E1"/>
    <Label value="building" background="#808080"/>
    <Label value="road" background="#696969"/>
    <Label value="vehicle" background="#FF0000"/>
  </BrushLabels>
</View>"""

project_id_9 = create_project(
    "语义分割",
    "对图像进行像素级分割标注",
    label_config_9
)

if project_id_9:
    with open("data/demo_datasets/semantic_segmentation.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_9, tasks)

# 10. 音频分类项目
print("\n=== 10. 音频分类 ===")
label_config_10 = """<View>
  <Audio name="audio" value="$audio"/>
  <Choices name="category" toName="audio" choice="single" showInLine="true">
    <Choice value="音乐"/>
    <Choice value="语音"/>
    <Choice value="噪音"/>
    <Choice value="自然声音"/>
    <Choice value="其他"/>
  </Choices>
  <Choices name="quality" toName="audio" choice="single" showInLine="true">
    <Choice value="清晰"/>
    <Choice value="一般"/>
    <Choice value="模糊"/>
  </Choices>
</View>"""

project_id_10 = create_project(
    "音频分类",
    "对音频进行分类和质量评估",
    label_config_10
)

if project_id_10:
    with open("data/demo_datasets/audio_classification.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_10, tasks)

# 11. 视频标注项目
print("\n=== 11. 视频标注 ===")
label_config_11 = """<View>
  <Video name="video" value="$video"/>
  <VideoRectangle name="box" toName="video"/>
  <Labels name="videoLabels" toName="video">
    <Label value="人物" background="red"/>
    <Label value="车辆" background="blue"/>
    <Label value="动物" background="green"/>
    <Label value="物体" background="orange"/>
  </Labels>
  <Choices name="action" toName="video" choice="single" showInLine="true">
    <Choice value="行走"/>
    <Choice value="跑步"/>
    <Choice value="站立"/>
    <Choice value="坐下"/>
    <Choice value="其他"/>
  </Choices>
</View>"""

project_id_11 = create_project(
    "视频标注",
    "对视频中的物体和动作进行标注",
    label_config_11
)

if project_id_11:
    with open("data/demo_datasets/video_annotation.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_11, tasks)

# 12. HTML 标注项目
print("\n=== 12. HTML 内容标注 ===")
label_config_12 = """<View>
  <HyperText name="html" value="$html"/>
  <Labels name="label" toName="html">
    <Label value="标题" background="red"/>
    <Label value="正文" background="blue"/>
    <Label value="关键词" background="green"/>
    <Label value="日期" background="orange"/>
    <Label value="作者" background="purple"/>
  </Labels>
</View>"""

project_id_12 = create_project(
    "HTML 内容标注",
    "标注 HTML 内容中的关键信息",
    label_config_12
)

if project_id_12:
    with open("data/demo_datasets/html_annotation.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_12, tasks)

# 13. OCR 标注项目
print("\n=== 13. OCR 文字识别 ===")
label_config_13 = """<View>
  <Image name="image" value="$image"/>
  <Rectangle name="bbox" toName="image"/>
  <TextArea name="transcription" toName="image" 
            editable="true" perRegion="true" 
            placeholder="输入识别的文字..."/>
</View>"""

project_id_13 = create_project(
    "OCR 文字识别",
    "标注图像中的文字区域并转录内容",
    label_config_13
)

if project_id_13:
    with open("data/demo_datasets/ocr_annotation.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_13, tasks)

# 14. 时间序列标注项目
print("\n=== 14. 时间序列标注 ===")
label_config_14 = """<View>
  <TimeSeries name="ts" value="$timeseries" valueType="url">
    <Channel column="value" strokeColor="#1f77b4" legend="数值"/>
  </TimeSeries>
  <TimeSeriesLabels name="label" toName="ts">
    <Label value="异常" background="red"/>
    <Label value="趋势上升" background="green"/>
    <Label value="趋势下降" background="blue"/>
    <Label value="平稳" background="gray"/>
  </TimeSeriesLabels>
</View>"""

project_id_14 = create_project(
    "时间序列标注",
    "标注时间序列数据中的模式和异常",
    label_config_14
)

if project_id_14:
    with open("data/demo_datasets/time_series.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)
    import_tasks(project_id_14, tasks)

print("\n=== 导入完成 ===")
print(f"访问 Label Studio: {LS_URL}")
print(f"用户名: admin@example.com")
print(f"密码: admin")
print(f"\n已创建 14 个不同类型的演示项目：")
print("1. 电商评论情感分类 (文本)")
print("2. 命名实体识别 (文本)")
print("3. 问答系统 (文本)")
print("4. 文本摘要 (文本)")
print("5. 对话系统标注 (文本)")
print("6. 关系抽取 (文本)")
print("7. 图像分类 (图像)")
print("8. 目标检测 (图像)")
print("9. 语义分割 (图像)")
print("10. 音频分类 (音频)")
print("11. 视频标注 (视频)")
print("12. HTML 内容标注 (HTML)")
print("13. OCR 文字识别 (图像+文本)")
print("14. 时间序列标注 (时间序列)")
