/**
 * Label Studio Template Library
 * 
 * Provides pre-built annotation templates for various data types and use cases.
 * Templates are based on official Label Studio documentation: https://labelstud.io/guide/
 * 
 * @module TemplateLibrary
 */

export interface LabelConfig {
  value: string;
  background?: string;
  alias?: string;
  hotkey?: string;
}

export interface TemplateConfig {
  id: string;
  name: string;
  nameZh: string;
  category: TemplateCategory;
  description: string;
  descriptionZh: string;
  xml: string;
  sampleData: Record<string, unknown>;
  tags: string[];
  version: string;
}

export type TemplateCategory = 
  | 'computer_vision'
  | 'nlp'
  | 'audio'
  | 'video'
  | 'conversational_ai'
  | 'llm'
  | 'structured_data'
  | 'time_series'
  | 'ranking';

export interface TemplateLibraryConfig {
  enableCustomTemplates?: boolean;
  customTemplatesPath?: string;
  defaultCategory?: TemplateCategory;
}

/**
 * Template Library for Label Studio annotation configurations
 */
export class TemplateLibrary {
  private templates: Map<string, TemplateConfig> = new Map();
  private customTemplates: Map<string, TemplateConfig> = new Map();
  private config: TemplateLibraryConfig;

  constructor(config: TemplateLibraryConfig = {}) {
    this.config = {
      enableCustomTemplates: true,
      defaultCategory: 'nlp',
      ...config,
    };
    this.initializeBuiltInTemplates();
  }

  private initializeBuiltInTemplates(): void {
    // NLP Templates
    this.registerTemplate({
      id: 'ner-basic',
      name: 'Named Entity Recognition (NER)',
      nameZh: '命名实体识别 (NER)',
      category: 'nlp',
      description: 'Label named entities in text such as persons, organizations, locations',
      descriptionZh: '标注文本中的命名实体，如人名、组织、地点等',
      xml: `<View>
  <Labels name="label" toName="text">
    <Label value="PER" background="red"/>
    <Label value="ORG" background="darkorange"/>
    <Label value="LOC" background="orange"/>
    <Label value="MISC" background="green"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>`,
      sampleData: {
        text: 'Apple Inc. was founded by Steve Jobs in Cupertino, California.',
      },
      tags: ['ner', 'text', 'entity', 'nlp'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'text-classification',
      name: 'Text Classification',
      nameZh: '文本分类',
      category: 'nlp',
      description: 'Classify text into predefined categories',
      descriptionZh: '将文本分类到预定义的类别中',
      xml: `<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single-radio">
    <Choice value="Positive"/>
    <Choice value="Negative"/>
    <Choice value="Neutral"/>
  </Choices>
</View>`,
      sampleData: {
        text: 'This product is amazing! I love it.',
      },
      tags: ['classification', 'sentiment', 'text', 'nlp'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'relation-extraction',
      name: 'Relation Extraction',
      nameZh: '关系抽取',
      category: 'nlp',
      description: 'Extract relationships between entities in text',
      descriptionZh: '抽取文本中实体之间的关系',
      xml: `<View>
  <Labels name="label" toName="text">
    <Label value="Person" background="#FFA39E"/>
    <Label value="Organization" background="#D4380D"/>
    <Label value="Location" background="#FFC069"/>
  </Labels>
  <Text name="text" value="$text"/>
  <Relations>
    <Relation value="works_for"/>
    <Relation value="located_in"/>
    <Relation value="founded_by"/>
  </Relations>
</View>`,
      sampleData: {
        text: 'Elon Musk is the CEO of Tesla, which is headquartered in Austin.',
      },
      tags: ['relation', 'entity', 'text', 'nlp'],
      version: '1.0.0',
    });

    // Computer Vision Templates
    this.registerTemplate({
      id: 'image-bbox',
      name: 'Object Detection (Bounding Box)',
      nameZh: '目标检测 (边界框)',
      category: 'computer_vision',
      description: 'Draw bounding boxes around objects in images',
      descriptionZh: '在图像中的目标周围绘制边界框',
      xml: `<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="Car" background="green"/>
    <Label value="Person" background="blue"/>
    <Label value="Building" background="red"/>
  </RectangleLabels>
</View>`,
      sampleData: {
        image: 'https://example.com/sample-image.jpg',
      },
      tags: ['object-detection', 'bbox', 'image', 'cv'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'image-segmentation',
      name: 'Semantic Segmentation',
      nameZh: '语义分割',
      category: 'computer_vision',
      description: 'Pixel-level segmentation of images',
      descriptionZh: '图像的像素级分割',
      xml: `<View>
  <Image name="image" value="$image" zoom="true"/>
  <BrushLabels name="label" toName="image">
    <Label value="Road" background="#FF0000"/>
    <Label value="Sky" background="#0000FF"/>
    <Label value="Vegetation" background="#00FF00"/>
  </BrushLabels>
</View>`,
      sampleData: {
        image: 'https://example.com/sample-image.jpg',
      },
      tags: ['segmentation', 'brush', 'image', 'cv'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'image-classification',
      name: 'Image Classification',
      nameZh: '图像分类',
      category: 'computer_vision',
      description: 'Classify images into categories',
      descriptionZh: '将图像分类到不同类别',
      xml: `<View>
  <Image name="image" value="$image"/>
  <Choices name="choice" toName="image">
    <Choice value="Cat"/>
    <Choice value="Dog"/>
    <Choice value="Bird"/>
    <Choice value="Other"/>
  </Choices>
</View>`,
      sampleData: {
        image: 'https://example.com/sample-image.jpg',
      },
      tags: ['classification', 'image', 'cv'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'image-polygon',
      name: 'Polygon Annotation',
      nameZh: '多边形标注',
      category: 'computer_vision',
      description: 'Draw polygons around irregular objects',
      descriptionZh: '在不规则物体周围绘制多边形',
      xml: `<View>
  <Image name="image" value="$image" zoom="true"/>
  <PolygonLabels name="label" toName="image" strokeWidth="3" pointSize="small">
    <Label value="Building" background="#FF0000"/>
    <Label value="Road" background="#00FF00"/>
    <Label value="Water" background="#0000FF"/>
  </PolygonLabels>
</View>`,
      sampleData: {
        image: 'https://example.com/sample-image.jpg',
      },
      tags: ['polygon', 'image', 'cv'],
      version: '1.0.0',
    });

    // Audio Templates
    this.registerTemplate({
      id: 'audio-transcription',
      name: 'Audio Transcription',
      nameZh: '音频转录',
      category: 'audio',
      description: 'Transcribe audio recordings to text',
      descriptionZh: '将音频录音转录为文本',
      xml: `<View>
  <Audio name="audio" value="$audio"/>
  <TextArea name="transcription" toName="audio" 
            showSubmitButton="true" maxSubmissions="1" 
            editable="true" placeholder="Enter transcription here..."/>
</View>`,
      sampleData: {
        audio: 'https://example.com/sample-audio.mp3',
      },
      tags: ['transcription', 'audio', 'speech'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'audio-classification',
      name: 'Audio Classification',
      nameZh: '音频分类',
      category: 'audio',
      description: 'Classify audio clips into categories',
      descriptionZh: '将音频片段分类到不同类别',
      xml: `<View>
  <Audio name="audio" value="$audio"/>
  <Choices name="genre" toName="audio" choice="single">
    <Choice value="Speech"/>
    <Choice value="Music"/>
    <Choice value="Noise"/>
    <Choice value="Silence"/>
  </Choices>
</View>`,
      sampleData: {
        audio: 'https://example.com/sample-audio.mp3',
      },
      tags: ['classification', 'audio'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'speaker-diarization',
      name: 'Speaker Diarization',
      nameZh: '说话人分离',
      category: 'audio',
      description: 'Identify and label different speakers in audio',
      descriptionZh: '识别并标注音频中的不同说话人',
      xml: `<View>
  <AudioPlus name="audio" value="$audio"/>
  <Labels name="speaker" toName="audio">
    <Label value="Speaker 1" background="#FF0000"/>
    <Label value="Speaker 2" background="#00FF00"/>
    <Label value="Speaker 3" background="#0000FF"/>
  </Labels>
</View>`,
      sampleData: {
        audio: 'https://example.com/sample-audio.mp3',
      },
      tags: ['diarization', 'speaker', 'audio'],
      version: '1.0.0',
    });

    // Video Templates
    this.registerTemplate({
      id: 'video-classification',
      name: 'Video Classification',
      nameZh: '视频分类',
      category: 'video',
      description: 'Classify video content into categories',
      descriptionZh: '将视频内容分类到不同类别',
      xml: `<View>
  <Video name="video" value="$video"/>
  <Choices name="category" toName="video" choice="single">
    <Choice value="Sports"/>
    <Choice value="News"/>
    <Choice value="Entertainment"/>
    <Choice value="Education"/>
  </Choices>
</View>`,
      sampleData: {
        video: 'https://example.com/sample-video.mp4',
      },
      tags: ['classification', 'video'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'video-timeline',
      name: 'Video Timeline Segmentation',
      nameZh: '视频时间线分割',
      category: 'video',
      description: 'Segment video into labeled time ranges',
      descriptionZh: '将视频分割成带标签的时间段',
      xml: `<View>
  <Video name="video" value="$video"/>
  <VideoRectangle name="box" toName="video"/>
  <Labels name="label" toName="video">
    <Label value="Action" background="#FF0000"/>
    <Label value="Dialogue" background="#00FF00"/>
    <Label value="Transition" background="#0000FF"/>
  </Labels>
</View>`,
      sampleData: {
        video: 'https://example.com/sample-video.mp4',
      },
      tags: ['timeline', 'segmentation', 'video'],
      version: '1.0.0',
    });

    // LLM Templates
    this.registerTemplate({
      id: 'llm-response-ranking',
      name: 'LLM Response Ranking',
      nameZh: 'LLM 响应排序',
      category: 'llm',
      description: 'Rank multiple LLM responses for quality',
      descriptionZh: '对多个 LLM 响应进行质量排序',
      xml: `<View>
  <Style>
    .prompt { background: #f0f0f0; padding: 10px; border-radius: 5px; }
    .response { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
  </Style>
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
</View>`,
      sampleData: {
        prompt: 'Explain quantum computing in simple terms.',
        response_a: 'Quantum computing uses quantum bits...',
        response_b: 'Think of quantum computing like...',
      },
      tags: ['llm', 'ranking', 'rlhf'],
      version: '1.0.0',
    });

    this.registerTemplate({
      id: 'llm-quality-evaluation',
      name: 'LLM Quality Evaluation',
      nameZh: 'LLM 质量评估',
      category: 'llm',
      description: 'Evaluate LLM response quality on multiple dimensions',
      descriptionZh: '从多个维度评估 LLM 响应质量',
      xml: `<View>
  <Text name="prompt" value="$prompt"/>
  <Text name="response" value="$response"/>
  <Header value="Evaluation"/>
  <Rating name="relevance" toName="response" maxRating="5"/>
  <Header value="Relevance (1-5)"/>
  <Rating name="accuracy" toName="response" maxRating="5"/>
  <Header value="Accuracy (1-5)"/>
  <Rating name="fluency" toName="response" maxRating="5"/>
  <Header value="Fluency (1-5)"/>
  <TextArea name="feedback" toName="response" placeholder="Additional feedback..."/>
</View>`,
      sampleData: {
        prompt: 'What is machine learning?',
        response: 'Machine learning is a subset of AI...',
      },
      tags: ['llm', 'evaluation', 'quality'],
      version: '1.0.0',
    });

    // Conversational AI Templates
    this.registerTemplate({
      id: 'dialogue-annotation',
      name: 'Dialogue Annotation',
      nameZh: '对话标注',
      category: 'conversational_ai',
      description: 'Annotate multi-turn conversations',
      descriptionZh: '标注多轮对话',
      xml: `<View>
  <Paragraphs name="dialogue" value="$dialogue" layout="dialogue" 
              nameKey="author" textKey="text"/>
  <Choices name="intent" toName="dialogue" perRegion="true">
    <Choice value="Question"/>
    <Choice value="Answer"/>
    <Choice value="Greeting"/>
    <Choice value="Farewell"/>
  </Choices>
</View>`,
      sampleData: {
        dialogue: [
          { author: 'User', text: 'Hello, how can I reset my password?' },
          { author: 'Agent', text: 'I can help you with that. Please verify your email.' },
        ],
      },
      tags: ['dialogue', 'conversation', 'intent'],
      version: '1.0.0',
    });

    // Structured Data Templates
    this.registerTemplate({
      id: 'table-annotation',
      name: 'Table Data Annotation',
      nameZh: '表格数据标注',
      category: 'structured_data',
      description: 'Annotate tabular data',
      descriptionZh: '标注表格数据',
      xml: `<View>
  <Table name="table" value="$table"/>
  <Choices name="quality" toName="table">
    <Choice value="Complete"/>
    <Choice value="Incomplete"/>
    <Choice value="Invalid"/>
  </Choices>
</View>`,
      sampleData: {
        table: [
          { name: 'John', age: 30, city: 'New York' },
          { name: 'Jane', age: 25, city: 'Los Angeles' },
        ],
      },
      tags: ['table', 'structured', 'data'],
      version: '1.0.0',
    });

    // Time Series Templates
    this.registerTemplate({
      id: 'time-series-anomaly',
      name: 'Time Series Anomaly Detection',
      nameZh: '时间序列异常检测',
      category: 'time_series',
      description: 'Label anomalies in time series data',
      descriptionZh: '标注时间序列数据中的异常',
      xml: `<View>
  <TimeSeries name="ts" value="$timeseries" valueType="url">
    <Channel column="value"/>
  </TimeSeries>
  <TimeSeriesLabels name="label" toName="ts">
    <Label value="Normal" background="#00FF00"/>
    <Label value="Anomaly" background="#FF0000"/>
    <Label value="Uncertain" background="#FFFF00"/>
  </TimeSeriesLabels>
</View>`,
      sampleData: {
        timeseries: 'https://example.com/timeseries.csv',
      },
      tags: ['timeseries', 'anomaly', 'detection'],
      version: '1.0.0',
    });

    // Ranking Templates
    this.registerTemplate({
      id: 'pairwise-comparison',
      name: 'Pairwise Comparison',
      nameZh: '成对比较',
      category: 'ranking',
      description: 'Compare two items and select the better one',
      descriptionZh: '比较两个项目并选择更好的一个',
      xml: `<View>
  <View style="display: flex; gap: 20px;">
    <View style="flex: 1;">
      <Header value="Option A"/>
      <Text name="option_a" value="$option_a"/>
    </View>
    <View style="flex: 1;">
      <Header value="Option B"/>
      <Text name="option_b" value="$option_b"/>
    </View>
  </View>
  <Choices name="preference" toName="option_a" choice="single">
    <Choice value="A is better"/>
    <Choice value="B is better"/>
    <Choice value="Equal"/>
  </Choices>
</View>`,
      sampleData: {
        option_a: 'First option text...',
        option_b: 'Second option text...',
      },
      tags: ['ranking', 'comparison', 'pairwise'],
      version: '1.0.0',
    });
  }

  /**
   * Register a new template
   */
  registerTemplate(template: TemplateConfig): void {
    this.templates.set(template.id, template);
  }

  /**
   * Register a custom template
   */
  registerCustomTemplate(template: TemplateConfig): void {
    if (!this.config.enableCustomTemplates) {
      throw new Error('Custom templates are disabled');
    }
    this.customTemplates.set(template.id, template);
  }

  /**
   * Get a template by ID
   */
  getTemplate(id: string): TemplateConfig | undefined {
    return this.templates.get(id) || this.customTemplates.get(id);
  }

  /**
   * Get all templates
   */
  getAllTemplates(): TemplateConfig[] {
    return [
      ...Array.from(this.templates.values()),
      ...Array.from(this.customTemplates.values()),
    ];
  }

  /**
   * Get templates by category
   */
  getTemplatesByCategory(category: TemplateCategory): TemplateConfig[] {
    return this.getAllTemplates().filter(t => t.category === category);
  }

  /**
   * Search templates by tags or name
   */
  searchTemplates(query: string): TemplateConfig[] {
    const lowerQuery = query.toLowerCase();
    return this.getAllTemplates().filter(t => 
      t.name.toLowerCase().includes(lowerQuery) ||
      t.nameZh.includes(query) ||
      t.tags.some(tag => tag.toLowerCase().includes(lowerQuery)) ||
      t.description.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * Get template categories
   */
  getCategories(): { id: TemplateCategory; name: string; nameZh: string }[] {
    return [
      { id: 'computer_vision', name: 'Computer Vision', nameZh: '计算机视觉' },
      { id: 'nlp', name: 'Natural Language Processing', nameZh: '自然语言处理' },
      { id: 'audio', name: 'Audio/Speech Processing', nameZh: '音频/语音处理' },
      { id: 'video', name: 'Video', nameZh: '视频' },
      { id: 'conversational_ai', name: 'Conversational AI', nameZh: '对话式 AI' },
      { id: 'llm', name: 'LLM Fine-tuning & Evaluation', nameZh: 'LLM 微调与评估' },
      { id: 'structured_data', name: 'Structured Data', nameZh: '结构化数据' },
      { id: 'time_series', name: 'Time Series', nameZh: '时间序列' },
      { id: 'ranking', name: 'Ranking & Scoring', nameZh: '排序与评分' },
    ];
  }

  /**
   * Customize a template with new labels
   */
  customizeTemplate(
    templateId: string, 
    labels: LabelConfig[]
  ): string {
    const template = this.getTemplate(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }

    let xml = template.xml;
    
    // Replace labels in the XML
    const labelRegex = /<Label[^>]*\/>/g;
    const labelsXml = labels.map(l => 
      `<Label value="${l.value}"${l.background ? ` background="${l.background}"` : ''}${l.hotkey ? ` hotkey="${l.hotkey}"` : ''}/>`
    ).join('\n    ');

    // Find and replace the Labels content
    xml = xml.replace(
      /(<Labels[^>]*>)([\s\S]*?)(<\/Labels>)/,
      `$1\n    ${labelsXml}\n  $3`
    );

    return xml;
  }

  /**
   * Export template as JSON
   */
  exportTemplate(templateId: string): string {
    const template = this.getTemplate(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }
    return JSON.stringify(template, null, 2);
  }

  /**
   * Import template from JSON
   */
  importTemplate(json: string): TemplateConfig {
    const template = JSON.parse(json) as TemplateConfig;
    this.registerCustomTemplate(template);
    return template;
  }
}

export default TemplateLibrary;
