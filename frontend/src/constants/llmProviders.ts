/**
 * LLM Providers and Models Configuration
 * 中国主流 LLM 提供商和模型配置
 */

export interface LLMModel {
  value: string;
  label: string;
  apiEndpoint?: string;
}

export interface LLMProvider {
  value: string;
  label: string;
  labelEn: string;
  models: LLMModel[];
  defaultEndpoint?: string;
}

export const CHINA_LLM_PROVIDERS: LLMProvider[] = [
  {
    value: 'deepseek',
    label: '深度求索 (DeepSeek)',
    labelEn: 'DeepSeek',
    defaultEndpoint: 'https://api.deepseek.com',
    models: [
      { value: 'deepseek-chat', label: 'DeepSeek Chat' },
      { value: 'deepseek-coder', label: 'DeepSeek Coder' },
      { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner (R1)' },
    ],
  },
  {
    value: 'zhipu',
    label: '智谱 AI (Zhipu AI)',
    labelEn: 'Zhipu AI',
    defaultEndpoint: 'https://open.bigmodel.cn/api/paas/v4',
    models: [
      { value: 'glm-4', label: 'GLM-4' },
      { value: 'glm-4-plus', label: 'GLM-4 Plus' },
      { value: 'glm-4-air', label: 'GLM-4 Air' },
      { value: 'glm-4-flash', label: 'GLM-4 Flash' },
      { value: 'glm-3-turbo', label: 'GLM-3 Turbo' },
    ],
  },
  {
    value: 'qwen',
    label: '通义千问 (Qwen)',
    labelEn: 'Qwen (Alibaba)',
    defaultEndpoint: 'https://dashscope.aliyuncs.com/api/v1',
    models: [
      { value: 'qwen-max', label: 'Qwen Max' },
      { value: 'qwen-plus', label: 'Qwen Plus' },
      { value: 'qwen-turbo', label: 'Qwen Turbo' },
      { value: 'qwen-long', label: 'Qwen Long' },
      { value: 'qwen2.5-72b-instruct', label: 'Qwen2.5 72B' },
      { value: 'qwen2.5-32b-instruct', label: 'Qwen2.5 32B' },
    ],
  },
  {
    value: 'baidu',
    label: '文心一言 · 旧版应用 (AK/SK + OAuth)',
    labelEn: 'ERNIE legacy (app AK/SK)',
    defaultEndpoint: 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1',
    models: [
      { value: 'ernie-4.0-8k', label: 'ERNIE 4.0 8K' },
      { value: 'ernie-4.0-turbo-8k', label: 'ERNIE 4.0 Turbo' },
      { value: 'ernie-3.5-8k', label: 'ERNIE 3.5 8K' },
      { value: 'ernie-speed-128k', label: 'ERNIE Speed 128K' },
      { value: 'ernie-lite-8k', label: 'ERNIE Lite 8K' },
    ],
  },
  /** 控制台「API Key」格式如 bce-v3/ALTAK-…，走 OpenAI 兼容 Chat Completions */
  {
    value: 'baidu_qianfan',
    label: '百度千帆 (Qianfan · OpenAI 兼容)',
    labelEn: 'Baidu Qianfan (OpenAI-compatible)',
    defaultEndpoint: 'https://qianfan.baidubce.com/v2',
    models: [
      { value: 'ernie-4.0-8k', label: 'ERNIE 4.0 8K（通用）' },
      { value: 'ernie-4.0-turbo-8k', label: 'ERNIE 4.0 Turbo 8K' },
      { value: 'ernie-speed-128k', label: 'ERNIE Speed 128K（长文本）' },
      { value: 'ernie-3.5-8k', label: 'ERNIE 3.5 8K' },
      { value: 'ernie-lite-8k', label: 'ERNIE Lite 8K（低成本）' },
    ],
  },
  {
    value: 'moonshot',
    label: '月之暗面 (Moonshot)',
    labelEn: 'Moonshot AI',
    defaultEndpoint: 'https://api.moonshot.cn/v1',
    models: [
      { value: 'moonshot-v1-8k', label: 'Moonshot v1 8K' },
      { value: 'moonshot-v1-32k', label: 'Moonshot v1 32K' },
      { value: 'moonshot-v1-128k', label: 'Moonshot v1 128K' },
    ],
  },
  {
    value: 'minimax',
    label: 'MiniMax',
    labelEn: 'MiniMax',
    defaultEndpoint: 'https://api.minimax.chat/v1',
    models: [
      { value: 'abab6.5-chat', label: 'abab6.5 Chat' },
      { value: 'abab6.5s-chat', label: 'abab6.5s Chat' },
      { value: 'abab5.5-chat', label: 'abab5.5 Chat' },
    ],
  },
  {
    value: 'doubao',
    label: '豆包 (Doubao)',
    labelEn: 'Doubao (ByteDance)',
    defaultEndpoint: 'https://ark.cn-beijing.volces.com/api/v3',
    models: [
      { value: 'doubao-pro-32k', label: 'Doubao Pro 32K' },
      { value: 'doubao-pro-128k', label: 'Doubao Pro 128K' },
      { value: 'doubao-lite-32k', label: 'Doubao Lite 32K' },
    ],
  },
  {
    value: 'yi',
    label: '零一万物 (Yi)',
    labelEn: 'Yi (01.AI)',
    defaultEndpoint: 'https://api.lingyiwanwu.com/v1',
    models: [
      { value: 'yi-large', label: 'Yi Large' },
      { value: 'yi-medium', label: 'Yi Medium' },
      { value: 'yi-spark', label: 'Yi Spark' },
    ],
  },
];

export const INTERNATIONAL_LLM_PROVIDERS: LLMProvider[] = [
  {
    value: 'openai',
    label: 'OpenAI',
    labelEn: 'OpenAI',
    defaultEndpoint: 'https://api.openai.com/v1',
    models: [
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    ],
  },
  {
    value: 'anthropic',
    label: 'Anthropic',
    labelEn: 'Anthropic',
    defaultEndpoint: 'https://api.anthropic.com',
    models: [
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
      { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
    ],
  },
  {
    value: 'azure',
    label: 'Azure OpenAI',
    labelEn: 'Azure OpenAI',
    models: [],
  },
  {
    value: 'ollama',
    label: 'Ollama (本地)',
    labelEn: 'Ollama (Local)',
    defaultEndpoint: 'http://localhost:11434',
    models: [
      { value: 'qwen2.5:1.5b', label: 'Qwen2.5 1.5B' },
      { value: 'qwen2.5:7b', label: 'Qwen2.5 7B' },
      { value: 'llama3.2:3b', label: 'Llama 3.2 3B' },
      { value: 'gemma2:2b', label: 'Gemma2 2B' },
    ],
  },
  {
    value: 'custom',
    label: '自定义',
    labelEn: 'Custom',
    models: [],
  },
];

export const ALL_LLM_PROVIDERS = [
  ...CHINA_LLM_PROVIDERS,
  ...INTERNATIONAL_LLM_PROVIDERS,
];
