# Label Studio 模板库使用指南

## 概述

SuperInsight 集成了丰富的 Label Studio 标注模板库，支持多种数据类型和标注场景。模板基于 [Label Studio 官方文档](https://labelstud.io/guide/) 设计，并针对企业级应用进行了优化。

## 模板分类

### 1. 自然语言处理 (NLP)

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `ner-basic` | 命名实体识别 | 标注人名、组织、地点等实体 |
| `text-classification` | 文本分类 | 情感分析、主题分类 |
| `relation-extraction` | 关系抽取 | 实体间关系标注 |

#### NER 模板示例

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="PER" background="red"/>
    <Label value="ORG" background="darkorange"/>
    <Label value="LOC" background="orange"/>
    <Label value="MISC" background="green"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

### 2. 计算机视觉

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `image-bbox` | 目标检测 | 边界框标注 |
| `image-segmentation` | 语义分割 | 像素级分割 |
| `image-classification` | 图像分类 | 图像类别标注 |
| `image-polygon` | 多边形标注 | 不规则形状标注 |

#### 目标检测模板示例

```xml
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="Car" background="green"/>
    <Label value="Person" background="blue"/>
    <Label value="Building" background="red"/>
  </RectangleLabels>
</View>
```

### 3. 音频/语音处理

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `audio-transcription` | 音频转录 | 语音转文字 |
| `audio-classification` | 音频分类 | 音频类型识别 |
| `speaker-diarization` | 说话人分离 | 多说话人识别 |

### 4. 视频处理

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `video-classification` | 视频分类 | 视频内容分类 |
| `video-timeline` | 时间线分割 | 视频片段标注 |

### 5. LLM 微调与评估

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `llm-response-ranking` | 响应排序 | RLHF 数据准备 |
| `llm-quality-evaluation` | 质量评估 | 多维度评分 |

#### LLM 响应排序模板示例

```xml
<View>
  <View className="prompt">
    <Header value="Prompt"/>
    <Text name="prompt" value="$prompt"/>
  </View>
  <View className="response">
    <Header value="Response A"/>
    <Text name="response_a" value="$response_a"/>
  </View>
  <View className="response">
    <Header value="Response B"/>
    <Text name="response_b" value="$response_b"/>
  </View>
  <Choices name="preference" toName="prompt" choice="single">
    <Choice value="Response A is better"/>
    <Choice value="Response B is better"/>
    <Choice value="Both are equal"/>
  </Choices>
</View>
```

### 6. 对话式 AI

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `dialogue-annotation` | 对话标注 | 多轮对话意图标注 |

### 7. 结构化数据

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `table-annotation` | 表格标注 | 表格数据质量标注 |

### 8. 时间序列

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `time-series-anomaly` | 异常检测 | 时序数据异常标注 |

### 9. 排序与评分

| 模板 ID | 名称 | 用途 |
|---------|------|------|
| `pairwise-comparison` | 成对比较 | A/B 测试数据标注 |

## 使用方法

### 获取模板

```typescript
import { TemplateLibrary } from '@/services/iframe';

const library = new TemplateLibrary();

// 获取单个模板
const nerTemplate = library.getTemplate('ner-basic');

// 获取所有模板
const allTemplates = library.getAllTemplates();

// 按分类获取
const nlpTemplates = library.getTemplatesByCategory('nlp');

// 搜索模板
const results = library.searchTemplates('classification');
```

### 自定义标签

```typescript
// 自定义 NER 标签
const customXml = library.customizeTemplate('ner-basic', [
  { value: '人物', background: '#FF0000', hotkey: '1' },
  { value: '公司', background: '#00FF00', hotkey: '2' },
  { value: '产品', background: '#0000FF', hotkey: '3' },
]);
```

### 注册自定义模板

```typescript
library.registerCustomTemplate({
  id: 'my-custom-template',
  name: 'My Custom Template',
  nameZh: '我的自定义模板',
  category: 'nlp',
  description: 'Custom template for specific use case',
  descriptionZh: '特定场景的自定义模板',
  xml: '<View>...</View>',
  sampleData: { text: 'Sample text' },
  tags: ['custom', 'nlp'],
  version: '1.0.0',
});
```

### 导出/导入模板

```typescript
// 导出
const json = library.exportTemplate('ner-basic');

// 导入
const imported = library.importTemplate(jsonString);
```

## 最佳实践

### 1. 选择合适的模板

- 根据数据类型选择基础模板
- 考虑标注人员的使用习惯
- 评估标注效率和质量需求

### 2. 自定义标签设计

- 使用清晰、简洁的标签名称
- 选择对比度高的颜色
- 设置常用标签的快捷键

### 3. 数据格式准备

- 确保数据字段与模板变量匹配
- 预处理数据以提高加载速度
- 验证数据格式的正确性

## 参考资源

- [Label Studio 官方模板库](https://labelstud.io/templates)
- [Label Studio 标签配置指南](https://labelstud.io/guide/setup)
- [Label Studio 标签参考](https://labelstud.io/tags/)

## 版本信息

- 模板库版本: 1.0.0
- 更新日期: 2026年1月
- 兼容 Label Studio: 1.12.0+
