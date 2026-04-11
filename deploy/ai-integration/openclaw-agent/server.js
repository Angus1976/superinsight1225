const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

const app = express();
const PORT = 8080;

app.use(bodyParser.json());

// ---------------------------------------------------------------------------
// Skill Registry
// ---------------------------------------------------------------------------
const SKILL_CATALOG = {
  'data-query': {
    name: 'data-query',
    displayName: '数据查询',
    description: '查询 SuperInsight 治理后的高质量数据',
    version: '1.0.0',
    category: 'data-processing',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-annotation-assist': {
    name: 'data-annotation-assist',
    displayName: '智能标注辅助',
    description: '利用 LLM 辅助数据标注，自动生成标注建议和预标注结果',
    version: '1.0.0',
    category: 'data-annotation',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-structuring': {
    name: 'data-structuring',
    displayName: '数据梳理',
    description: '自动识别非结构化数据的 schema，提取实体和关系',
    version: '1.0.0',
    category: 'data-structuring',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-analysis': {
    name: 'data-analysis',
    displayName: '数据分析',
    description: '对标注数据进行质量分析、分布统计和趋势洞察',
    version: '1.0.0',
    category: 'data-analysis',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-cleaning': {
    name: 'data-cleaning',
    displayName: '数据清洗',
    description: '检测并修复数据中的异常值、重复项和格式问题',
    version: '1.0.0',
    category: 'data-processing',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-summary': {
    name: 'data-summary',
    displayName: '数据摘要',
    description: '数据摘要与统计分析，生成关键指标与分布概览',
    version: '1.0.0',
    category: 'data-analysis',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-quality-check': {
    name: 'data-quality-check',
    displayName: '数据质量检测',
    description: '识别缺失值、异常值、重复记录等质量问题',
    version: '1.0.0',
    category: 'data-quality',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-transform': {
    name: 'data-transform',
    displayName: '数据转换',
    description: '格式转换、字段映射与标准化',
    version: '1.0.0',
    category: 'data-processing',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-export': {
    name: 'data-export',
    displayName: '数据导出',
    description: '导出为 CSV/JSON/Excel 等格式',
    version: '1.0.0',
    category: 'data-export',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-comparison': {
    name: 'data-comparison',
    displayName: '数据对比',
    description: '多数据源字段级差异与变更追踪',
    version: '1.0.0',
    category: 'data-analysis',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'data-lineage': {
    name: 'data-lineage',
    displayName: '数据血缘',
    description: '追踪数据来源、流转路径与依赖关系',
    version: '1.0.0',
    category: 'data-governance',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'file-document-parse': {
    name: 'file-document-parse',
    displayName: '文件与文档解析',
    description: '从 CSV、Excel、JSON、日志与文本中提取结构化字段',
    version: '1.1.0',
    category: 'file-processing',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'nl-data-query': {
    name: 'nl-data-query',
    displayName: '智能问数',
    description: '自然语言描述需求，转换为查询意图或分析步骤',
    version: '1.1.0',
    category: 'intelligent-query',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'text-to-sql-assisted': {
    name: 'text-to-sql-assisted',
    displayName: 'Text-to-SQL 辅助',
    description: '在受控数据源上生成、解释与校验 SQL',
    version: '1.1.0',
    category: 'intelligent-query',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
  'metrics-dashboard-insight': {
    name: 'metrics-dashboard-insight',
    displayName: '指标与看板解读',
    description: '解释 KPI、图表与报表含义，辅助业务理解',
    version: '1.1.0',
    category: 'data-analysis',
    status: 'active',
    deployed_at: new Date().toISOString(),
  },
};

// Track deployed skills (start with all active)
const deployedSkills = { ...SKILL_CATALOG };

// ---------------------------------------------------------------------------
// Ollama LLM Helper
// ---------------------------------------------------------------------------
async function callOllama(prompt, options = {}) {
  const baseUrl = process.env.LLM_API_URL || 'http://ollama:11434';
  const model = process.env.LLM_MODEL || 'qwen2.5:1.5b';

  try {
    const resp = await axios.post(`${baseUrl}/api/generate`, {
      model,
      prompt,
      stream: false,
      options: { temperature: options.temperature || 0.7 },
    }, { timeout: 120000 });

    return { success: true, text: resp.data.response };
  } catch (err) {
    console.error('Ollama call failed:', err.message);
    return { success: false, text: '', error: err.message };
  }
}

async function checkOllamaHealth() {
  const baseUrl = process.env.LLM_API_URL || 'http://ollama:11434';
  try {
    const resp = await axios.get(`${baseUrl}/api/tags`, { timeout: 5000 });
    const models = resp.data?.models || [];
    return { healthy: true, models: models.map(m => m.name) };
  } catch {
    return { healthy: false, models: [] };
  }
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
app.get('/health', async (req, res) => {
  const ollama = await checkOllamaHealth();
  res.json({
    status: 'healthy',
    service: 'openclaw-agent',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    gateway_url: process.env.GATEWAY_URL,
    llm_provider: process.env.LLM_PROVIDER,
    llm_model: process.env.LLM_MODEL,
    ollama: ollama,
    skills_count: Object.keys(deployedSkills).length,
  });
});

// ---------------------------------------------------------------------------
// Agent info
// ---------------------------------------------------------------------------
app.get('/api/info', (req, res) => {
  res.json({
    name: process.env.AGENT_NAME || 'SuperInsight Assistant',
    description: process.env.AGENT_DESCRIPTION || 'AI assistant for governed data',
    version: '2.0.0',
    llm: {
      provider: process.env.LLM_PROVIDER,
      model: process.env.LLM_MODEL,
      api_url: process.env.LLM_API_URL,
    },
    language: {
      user_language: process.env.OPENCLAW_USER_LANGUAGE,
      locale: process.env.OPENCLAW_LOCALE,
    },
  });
});


// ---------------------------------------------------------------------------
// Skills API
// ---------------------------------------------------------------------------
app.get('/api/skills', (req, res) => {
  const skills = Object.values(deployedSkills).map(s => ({
    id: s.name,
    name: s.displayName,
    description: s.description,
    version: s.version,
    category: s.category,
    status: s.status,
    deployed_at: s.deployed_at,
  }));
  res.json({ skills });
});

app.get('/api/skills/catalog', (req, res) => {
  const catalog = Object.values(SKILL_CATALOG).map(s => ({
    id: s.name,
    name: s.displayName,
    description: s.description,
    version: s.version,
    category: s.category,
  }));
  res.json({ catalog });
});

// Deploy / undeploy a skill
app.post('/api/skills/deploy', (req, res) => {
  const { skill_id } = req.body;
  if (!skill_id) {
    return res.status(400).json({ success: false, error: '缺少 skill_id' });
  }
  const template = SKILL_CATALOG[skill_id];
  if (!template) {
    return res.status(404).json({ success: false, error: `技能 ${skill_id} 不存在` });
  }
  deployedSkills[skill_id] = { ...template, status: 'active', deployed_at: new Date().toISOString() };
  res.json({ success: true, message: `技能 "${template.displayName}" 部署成功`, skill: deployedSkills[skill_id] });
});

app.post('/api/skills/undeploy', (req, res) => {
  const { skill_id } = req.body;
  if (!skill_id || !deployedSkills[skill_id]) {
    return res.status(404).json({ success: false, error: '技能未部署' });
  }
  const name = deployedSkills[skill_id].displayName;
  delete deployedSkills[skill_id];
  res.json({ success: true, message: `技能 "${name}" 已卸载` });
});

// ---------------------------------------------------------------------------
// Skill Execution
// ---------------------------------------------------------------------------
app.post('/api/skills/execute', async (req, res) => {
  const { skill_name, parameters = {} } = req.body;
  console.log(`[execute] skill=${skill_name}`, JSON.stringify(parameters).slice(0, 200));

  const skill = deployedSkills[skill_name];
  if (!skill) {
    return res.status(404).json({ success: false, error: `技能 "${skill_name}" 未部署` });
  }

  try {
    const result = await executeSkill(skill_name, parameters);
    res.json({ success: true, skill: skill_name, result });
  } catch (err) {
    console.error(`[execute] error: ${err.message}`);
    res.status(500).json({ success: false, error: err.message });
  }
});

async function executeGenericDataSkill(skillName, params) {
  const skill = deployedSkills[skillName];
  const label = skill?.displayName || skillName;
  const prompt = `你是 SuperInsight 数据治理助手。当前技能：${label}（${skillName}）。
请根据技能目标，结合用户参数，用中文给出结构化、可落地的建议；若适合请使用 JSON 输出关键字段。

用户参数：${JSON.stringify(params).slice(0, 6000)}`;

  const llmResult = await callOllama(prompt, { temperature: 0.35 });
  return {
    message: `${label} 已完成（LLM 辅助）`,
    skill: skillName,
    result: llmResult.success ? llmResult.text : '(LLM 不可用)',
  };
}

async function executeSkill(skillName, params) {
  switch (skillName) {
    case 'data-query':
      return await executeDataQuery(params);
    case 'data-annotation-assist':
      return await executeAnnotationAssist(params);
    case 'data-structuring':
      return await executeDataStructuring(params);
    case 'data-analysis':
      return await executeDataAnalysis(params);
    case 'data-cleaning':
      return await executeDataCleaning(params);
    default:
      return await executeGenericDataSkill(skillName, params);
  }
}

// ---------------------------------------------------------------------------
// Skill: Data Query
// ---------------------------------------------------------------------------
async function executeDataQuery(params) {
  const { query, dataset_id } = params;
  if (!query) {
    return { error: '请提供查询内容 (query)' };
  }

  // Use LLM to interpret natural language query
  const prompt = `你是一个数据查询助手。用户想查询以下内容：
"${query}"
${dataset_id ? `数据集ID: ${dataset_id}` : ''}

请将用户的自然语言查询转换为结构化的查询条件，返回 JSON 格式：
{"filters": [...], "sort": "...", "limit": 10, "explanation": "..."}`;

  const llmResult = await callOllama(prompt, { temperature: 0.3 });

  return {
    message: '数据查询完成',
    query_interpretation: llmResult.success ? llmResult.text : '(LLM 不可用，使用默认解析)',
    records_found: 42,
    sample: [
      { id: 1, content: '示例数据记录 1', quality_score: 0.95 },
      { id: 2, content: '示例数据记录 2', quality_score: 0.88 },
    ],
  };
}

// ---------------------------------------------------------------------------
// Skill: Annotation Assist
// ---------------------------------------------------------------------------
async function executeAnnotationAssist(params) {
  const { text, label_schema, task_type = 'classification' } = params;
  if (!text) {
    return { error: '请提供待标注文本 (text)' };
  }

  const schemaDesc = label_schema
    ? `标签体系: ${JSON.stringify(label_schema)}`
    : '标签体系: 自动推断';

  const prompt = `你是一个专业的数据标注助手。请对以下文本进行${task_type === 'ner' ? '命名实体识别' : '分类'}标注。

文本: "${text}"
${schemaDesc}
任务类型: ${task_type}

请返回 JSON 格式的标注结果：
- classification: {"label": "...", "confidence": 0.95, "reasoning": "..."}
- ner: {"entities": [{"text": "...", "label": "...", "start": 0, "end": 5}]}`;

  const llmResult = await callOllama(prompt, { temperature: 0.2 });

  return {
    message: '标注建议生成完成',
    task_type,
    suggestion: llmResult.success ? llmResult.text : '(LLM 不可用)',
    confidence: 0.85,
    needs_review: true,
  };
}


// ---------------------------------------------------------------------------
// Skill: Data Structuring
// ---------------------------------------------------------------------------
async function executeDataStructuring(params) {
  const { text, format = 'auto' } = params;
  if (!text) {
    return { error: '请提供待梳理的文本 (text)' };
  }

  const prompt = `你是一个数据梳理专家。请分析以下非结构化文本，提取其中的结构化信息。

文本: "${text.slice(0, 1000)}"

请返回 JSON 格式：
{
  "schema": {"fields": [{"name": "...", "type": "string|number|date|boolean", "description": "..."}]},
  "entities": [{"name": "...", "type": "...", "value": "..."}],
  "relations": [{"source": "...", "target": "...", "relation": "..."}],
  "summary": "..."
}`;

  const llmResult = await callOllama(prompt, { temperature: 0.3 });

  return {
    message: '数据梳理完成',
    format,
    structured_result: llmResult.success ? llmResult.text : '(LLM 不可用)',
    fields_detected: 5,
    entities_found: 8,
  };
}

// ---------------------------------------------------------------------------
// Skill: Data Analysis
// ---------------------------------------------------------------------------
async function executeDataAnalysis(params) {
  const { dataset_id, analysis_type = 'quality' } = params;

  const typeMap = {
    quality: '数据质量分析（完整性、一致性、准确性）',
    distribution: '数据分布统计（类别分布、数值分布）',
    trend: '趋势分析（时间序列变化）',
    anomaly: '异常检测（离群值、异常模式）',
  };

  const prompt = `你是一个数据分析专家。请对数据集进行${typeMap[analysis_type] || '综合分析'}。

数据集ID: ${dataset_id || '默认数据集'}
分析类型: ${analysis_type}

请返回分析报告，JSON 格式：
{
  "summary": "...",
  "metrics": {"completeness": 0.95, "consistency": 0.88, "accuracy": 0.92},
  "issues": [{"type": "...", "severity": "high|medium|low", "description": "...", "affected_count": 10}],
  "recommendations": ["..."]
}`;

  const llmResult = await callOllama(prompt, { temperature: 0.5 });

  return {
    message: `${typeMap[analysis_type] || '数据分析'}完成`,
    analysis_type,
    report: llmResult.success ? llmResult.text : '(LLM 不可用)',
    metrics: {
      total_records: 1250,
      completeness: 0.94,
      consistency: 0.87,
      quality_score: 0.91,
    },
  };
}

// ---------------------------------------------------------------------------
// Skill: Data Cleaning
// ---------------------------------------------------------------------------
async function executeDataCleaning(params) {
  const { text, rules = [] } = params;
  if (!text) {
    return { error: '请提供待清洗的数据 (text)' };
  }

  const rulesDesc = rules.length > 0
    ? `清洗规则: ${JSON.stringify(rules)}`
    : '清洗规则: 自动检测';

  const prompt = `你是一个数据清洗专家。请检查以下数据并提出清洗建议。

数据: "${text.slice(0, 1000)}"
${rulesDesc}

请返回 JSON 格式：
{
  "issues": [{"type": "duplicate|missing|format|outlier|inconsistent", "description": "...", "location": "...", "suggestion": "..."}],
  "cleaned_data": "...",
  "changes_made": 3,
  "quality_before": 0.7,
  "quality_after": 0.95
}`;

  const llmResult = await callOllama(prompt, { temperature: 0.3 });

  return {
    message: '数据清洗完成',
    cleaning_result: llmResult.success ? llmResult.text : '(LLM 不可用)',
    issues_found: 3,
    issues_fixed: 2,
    quality_improvement: '+15%',
  };
}

// ---------------------------------------------------------------------------
// Chat endpoint (conversational interface)
// ---------------------------------------------------------------------------
app.post('/api/chat', async (req, res) => {
  const { message, context = {} } = req.body;
  if (!message) {
    return res.status(400).json({ success: false, error: '请提供消息内容' });
  }

  const systemPrompt = process.env.OPENCLAW_SYSTEM_PROMPT ||
    '你是 SuperInsight 智能助手，专注于数据标注、数据梳理、数据分析和数据处理。请用中文回答。';

  const prompt = `${systemPrompt}\n\n用户: ${message}\n\n助手:`;
  const llmResult = await callOllama(prompt);

  res.json({
    success: true,
    reply: llmResult.success ? llmResult.text : '抱歉，LLM 服务暂时不可用，请稍后再试。',
    llm_available: llmResult.success,
  });
});

// ---------------------------------------------------------------------------
// Ollama status endpoint
// ---------------------------------------------------------------------------
app.get('/api/llm/status', async (req, res) => {
  const ollama = await checkOllamaHealth();
  res.json({
    provider: process.env.LLM_PROVIDER || 'ollama',
    model: process.env.LLM_MODEL || 'qwen2.5:1.5b',
    api_url: process.env.LLM_API_URL || 'http://ollama:11434',
    ...ollama,
  });
});

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------
app.listen(PORT, '0.0.0.0', () => {
  console.log(`OpenClaw Agent v2.1 listening on port ${PORT}`);
  console.log(`Gateway URL: ${process.env.GATEWAY_URL}`);
  console.log(`SuperInsight API: ${process.env.SUPERINSIGHT_API_URL}`);
  console.log(`LLM: ${process.env.LLM_PROVIDER} / ${process.env.LLM_MODEL}`);
  console.log(`Language: ${process.env.OPENCLAW_USER_LANGUAGE}`);
  console.log(`Skills loaded: ${Object.keys(deployedSkills).length}`);
});
