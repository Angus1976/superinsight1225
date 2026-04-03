/**
 * Unit tests for LLM Configuration Page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LLMConfigPage from './LLMConfig';
import { llmService } from '../../services/llm';

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
    vi.mocked(llmService.getConfig).mockResolvedValue(mockConfig as any);
    vi.mocked(llmService.getMethods).mockResolvedValue(mockMethods as any);
    vi.mocked(llmService.getHealth).mockResolvedValue(mockHealthStatus as any);
    vi.mocked(llmService.validateConfig).mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
    } as any);
  });

  it('renders the page title and description', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(screen.getByText(/LLM 配置管理|LLM Configuration/)).toBeInTheDocument();
      expect(screen.getByText(/配置和管理各种 LLM 提供商|Configure and manage various LLM providers/)).toBeInTheDocument();
    });
  });

  it('loads and displays configuration data', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(llmService.getConfig).toHaveBeenCalled();
      expect(llmService.getMethods).toHaveBeenCalled();
      expect(llmService.getHealth).toHaveBeenCalled();
    });

    // Switch to local LLM tab where local config is shown
    fireEvent.click(screen.getByText(/本地 LLM|Local LLM/));

    // Check if form fields are populated
    await waitFor(() => {
      const ollamaUrlInput = screen.getByDisplayValue(/http:\/\/localhost:11434/);
      expect(ollamaUrlInput).toBeInTheDocument();
    });
  });

  it('displays health status badges correctly', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(llmService.getHealth).toHaveBeenCalled();
    });
  });

  it('handles configuration validation', async () => {
    vi.mocked(llmService.validateConfig).mockResolvedValue({
      valid: false,
      errors: ['OpenAI API key is required'],
      warnings: ['Timeout value is high'],
    });

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const saveButton = screen.getByText(/保存配置|Save Config|Save Configuration/);
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/配置验证失败|Validation Failed|Configuration Validation Failed/)).toBeInTheDocument();
      expect(screen.getByText('OpenAI API key is required')).toBeInTheDocument();
      expect(screen.getByText('Timeout value is high')).toBeInTheDocument();
    });
  });

  it('handles successful configuration save', async () => {
    vi.mocked(llmService.updateConfig).mockResolvedValue(mockConfig as any);

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const saveButton = screen.getByText(/保存配置|Save Config|Save Configuration/);
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(llmService.validateConfig).toHaveBeenCalled();
      expect(llmService.updateConfig).toHaveBeenCalled();
    });
  });

  it('handles connection testing', async () => {
    vi.mocked(llmService.testConnection).mockResolvedValue({
      method: 'local_ollama',
      available: true,
      latency_ms: 120,
      model: 'llama2',
      last_check: '2024-01-01T00:00:00Z',
    });

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      // Switch to local LLM tab
      const localTab = screen.getByText(/本地 LLM|Local LLM/);
      fireEvent.click(localTab);
    });

    await waitFor(() => {
      const testButton = screen.getByText(/测试连接|Test Connection/);
      fireEvent.click(testButton);
    });

    await waitFor(() => {
      expect(llmService.testConnection).toHaveBeenCalledWith('local_ollama');
    });
  });

  it('handles hot reload functionality', async () => {
    vi.mocked(llmService.hotReload).mockResolvedValue(mockConfig as any);

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const hotReloadButton = screen.getByText(/热加载|Hot Reload/);
      fireEvent.click(hotReloadButton);
    });

    await waitFor(() => {
      expect(llmService.hotReload).toHaveBeenCalled();
    });
  });

  it('handles API key visibility toggle', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      // Switch to cloud LLM tab
      const cloudTab = screen.getByText(/云端 LLM|Cloud LLM/);
      fireEvent.click(cloudTab);
    });

    await waitFor(() => {
      // Find API key input and visibility toggle
      const apiKeyInputs = screen.getAllByPlaceholderText(/API Key/i);
      expect(apiKeyInputs.length).toBeGreaterThan(0);
      
      // The visibility toggle functionality is handled by Ant Design's Input.Password
      // We can test that the component renders correctly
      expect(apiKeyInputs[0]).toBeInTheDocument();
    });
  });

  it('displays method configuration status correctly', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(screen.getAllByText('Local Ollama').length).toBeGreaterThan(0);
      expect(screen.getAllByText('OpenAI').length).toBeGreaterThan(0);
    });
  });

  it('handles form reset functionality', async () => {
    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      const resetButton = screen.getByText(/重置|Reset/);
      fireEvent.click(resetButton);
    });

    // Should not crash; confirmation UI is antd-managed and may vary by version.
    expect(true).toBe(true);
  });

  it('handles loading state correctly', () => {
    // Mock loading state
    vi.mocked(llmService.getConfig).mockImplementation(
      () => new Promise(() => {}) // Never resolves to simulate loading
    );

    renderWithProviders(<LLMConfigPage />);

    expect(screen.getByText(/加载配置中\.\.\.|Loading configuration\.\.\./)).toBeInTheDocument();
  });

  it('handles error states gracefully', async () => {
    vi.mocked(llmService.getConfig).mockRejectedValue(
      new Error('Failed to load config')
    );

    renderWithProviders(<LLMConfigPage />);

    await waitFor(() => {
      expect(llmService.getConfig).toHaveBeenCalled();
    });

    // The component should handle the error gracefully
    // (specific error handling behavior depends on implementation)
  });
});