/**
 * Unit tests for LLM Configuration Page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LLMConfigPage from './LLMConfig';

// Mock the LLM service
vi.mock('../../services/llm', () => ({
  llmService: {
    getConfig: vi.fn(),
    getMethods: vi.fn(),
    getHealth: vi.fn(),
    updateConfig: vi.fn(),
    validateConfig: vi.fn(),
    testConnection: vi.fn(),
    hotReload: vi.fn(),
  },
  getMethodName: vi.fn((method: string) => {
    const names: Record<string, string> = {
      local_ollama: 'Local Ollama',
      cloud_openai: 'OpenAI',
      cloud_azure: 'Azure OpenAI',
      china_qwen: '通义千问 (Qwen)',
      china_zhipu: '智谱 GLM',
      china_baidu: '文心一言',
      china_hunyuan: '腾讯混元',
    };
    return names[method] || method;
  }),
  getMethodCategory: vi.fn(),
  isApiKeyMasked: vi.fn(),
}));

// Mock Ant Design message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
    },
  };
});

const mockConfig = {
  default_method: 'local_ollama' as const,
  enabled_methods: ['local_ollama', 'cloud_openai'] as const,
  local_config: {
    ollama_url: 'http://localhost:11434',
    default_model: 'llama2',
    timeout: 30,
    max_retries: 3,
  },
  cloud_config: {
    openai_api_key: 'sk-****',
    openai_base_url: 'https://api.openai.com/v1',
    openai_model: 'gpt-3.5-turbo',
    azure_endpoint: '',
    azure_api_key: '',
    azure_deployment: '',
    azure_api_version: '2023-12-01-preview',
    timeout: 60,
    max_retries: 3,
  },
  china_config: {
    qwen_api_key: '',
    qwen_model: 'qwen-turbo',
    zhipu_api_key: '',
    zhipu_model: 'glm-4',
    baidu_api_key: '',
    baidu_secret_key: '',
    baidu_model: 'ernie-bot-turbo',
    hunyuan_secret_id: '',
    hunyuan_secret_key: '',
    hunyuan_model: 'hunyuan-lite',
    timeout: 60,
    max_retries: 3,
  },
};

const mockMethods = [
  {
    method: 'local_ollama' as const,
    name: 'Local Ollama',
    description: 'Local Ollama service',
    enabled: true,
    configured: true,
    models: ['llama2', 'codellama'],
  },
  {
    method: 'cloud_openai' as const,
    name: 'OpenAI',
    description: 'OpenAI API service',
    enabled: true,
    configured: false,
    models: ['gpt-3.5-turbo', 'gpt-4'],
  },
];

const mockHealthStatus = {
  local_ollama: {
    method: 'local_ollama' as const,
    available: true,
    latency_ms: 150,
    model: 'llama2',
    last_check: '2024-01-01T00:00:00Z',
  },
  cloud_openai: {
    method: 'cloud_openai' as const,
    available: false,
    error: 'API key not configured',
    last_check: '2024-01-01T00:00:00Z',
  },
};

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('LLMConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Setup default mocks
    const llmService = await import('../../services/llm');
    vi.mocked(llmService.llmService.getConfig).mockResolvedValue(mockConfig);
    vi.mocked(llmService.llmService.getMethods).mockResolvedValue(mockMethods);
    vi.mocked(llmService.llmService.getHealth).mockResolvedValue(mockHealthStatus);
    vi.mocked(llmService.llmService.validateConfig).mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
    });
  });

  it('renders the page title and description', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('LLM 配置管理')).toBeInTheDocument();
      expect(screen.getByText(/配置和管理各种 LLM 提供商/)).toBeInTheDocument();
    });
  });

  it('loads and displays configuration data', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const llmService = require('../../services/llm');
      expect(llmService.llmService.getConfig).toHaveBeenCalled();
      expect(llmService.llmService.getMethods).toHaveBeenCalled();
      expect(llmService.llmService.getHealth).toHaveBeenCalled();
    });

    // Check if form fields are populated
    await waitFor(() => {
      const ollamaUrlInput = screen.getByDisplayValue('http://localhost:11434');
      expect(ollamaUrlInput).toBeInTheDocument();
    });
  });

  it('displays health status badges correctly', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      // Should show success badge for local_ollama
      expect(screen.getByText(/在线 \(150ms\)/)).toBeInTheDocument();
      
      // Should show error badge for cloud_openai
      expect(screen.getByText('API key not configured')).toBeInTheDocument();
    });
  });

  it('handles configuration validation', async () => {
    vi.mocked(llmService.llmService.validateConfig).mockResolvedValue({
      valid: false,
      errors: ['OpenAI API key is required'],
      warnings: ['Timeout value is high'],
    });

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(screen.getByText('配置验证失败')).toBeInTheDocument();
      expect(screen.getByText('OpenAI API key is required')).toBeInTheDocument();
      expect(screen.getByText('Timeout value is high')).toBeInTheDocument();
    });
  });

  it('handles successful configuration save', async () => {
    vi.mocked(llmService.llmService.updateConfig).mockResolvedValue(mockConfig);

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const saveButton = screen.getByText('保存配置');
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(llmService.llmService.validateConfig).toHaveBeenCalled();
      expect(llmService.llmService.updateConfig).toHaveBeenCalled();
    });
  });

  it('handles connection testing', async () => {
    vi.mocked(llmService.llmService.testConnection).mockResolvedValue({
      method: 'local_ollama',
      available: true,
      latency_ms: 120,
      model: 'llama2',
      last_check: '2024-01-01T00:00:00Z',
    });

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      // Switch to local LLM tab
      const localTab = screen.getByText('本地 LLM');
      fireEvent.click(localTab);
    });

    await waitFor(() => {
      const testButton = screen.getByText('测试连接');
      fireEvent.click(testButton);
    });

    await waitFor(() => {
      expect(llmService.llmService.testConnection).toHaveBeenCalledWith('local_ollama');
    });
  });

  it('handles hot reload functionality', async () => {
    vi.mocked(llmService.llmService.hotReload).mockResolvedValue(mockConfig);

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const hotReloadButton = screen.getByText('热加载');
      fireEvent.click(hotReloadButton);
    });

    await waitFor(() => {
      expect(llmService.llmService.hotReload).toHaveBeenCalled();
    });
  });

  it('handles API key visibility toggle', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      // Switch to cloud LLM tab
      const cloudTab = screen.getByText('云端 LLM');
      fireEvent.click(cloudTab);
    });

    await waitFor(() => {
      // Find API key input and visibility toggle
      const apiKeyInputs = screen.getAllByPlaceholderText(/请输入.*API Key/);
      expect(apiKeyInputs.length).toBeGreaterThan(0);
      
      // The visibility toggle functionality is handled by Ant Design's Input.Password
      // We can test that the component renders correctly
      expect(apiKeyInputs[0]).toBeInTheDocument();
    });
  });

  it('displays method configuration status correctly', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      // Should show configured method without warning tag
      expect(screen.getByText('Local Ollama')).toBeInTheDocument();
      
      // Should show unconfigured method with warning tag
      expect(screen.getByText('未配置')).toBeInTheDocument();
    });
  });

  it('handles form reset functionality', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const resetButton = screen.getByText('重置');
      fireEvent.click(resetButton);
    });

    // Should show confirmation modal
    await waitFor(() => {
      expect(screen.getByText('重置配置')).toBeInTheDocument();
      expect(screen.getByText('确定要重置所有配置吗？')).toBeInTheDocument();
    });
  });

  it('handles loading state correctly', () => {
    // Mock loading state
    vi.mocked(llmService.llmService.getConfig).mockImplementation(
      () => new Promise(() => {}) // Never resolves to simulate loading
    );

    renderWithProviders(<LLMConfigPage />);

    expect(screen.getByText('加载配置中...')).toBeInTheDocument();
  });

  it('handles error states gracefully', async () => {
    vi.mocked(llmService.llmService.getConfig).mockRejectedValue(
      new Error('Failed to load config')
    );

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(llmService.llmService.getConfig).toHaveBeenCalled();
    });

    // The component should handle the error gracefully
    // (specific error handling behavior depends on implementation)
  });
});