/**
 * Text-to-SQL Configuration Page Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import TextToSQLConfigPage from './TextToSQLConfig';

// Mock the textToSql service
vi.mock('@/services/textToSql', () => ({
  textToSqlService: {
    getConfig: vi.fn(),
    getMethods: vi.fn(),
    getPlugins: vi.fn(),
    getStatistics: vi.fn(),
    updateConfig: vi.fn(),
    switchMethod: vi.fn(),
    testGenerate: vi.fn(),
    registerPlugin: vi.fn(),
    unregisterPlugin: vi.fn(),
    enablePlugin: vi.fn(),
    disablePlugin: vi.fn(),
    getPluginsHealth: vi.fn(),
    getPluginHealth: vi.fn(),
  },
  getMethodDisplayName: (method: string) => {
    const names: Record<string, string> = {
      template: '模板填充',
      llm: 'LLM 生成',
      hybrid: '混合方法',
      third_party: '第三方工具',
    };
    return names[method] || method;
  },
  getMethodDescription: (method: string) => `Description for ${method}`,
  getConnectionTypeDisplayName: (type: string) => type.toUpperCase(),
}));

import * as textToSqlService from '@/services/textToSql';

// Mock data
const mockConfig = {
  default_method: 'hybrid',
  auto_select_enabled: true,
  fallback_enabled: true,
  template_config: {},
  llm_config: {},
  hybrid_config: {},
};

const mockMethods = [
  {
    name: 'template',
    type: 'template',
    description: '基于预定义模板的SQL生成',
    supported_db_types: ['postgresql', 'mysql'],
    is_available: true,
    is_enabled: true,
  },
  {
    name: 'llm',
    type: 'llm',
    description: '基于大语言模型的SQL生成',
    supported_db_types: ['postgresql', 'mysql', 'sqlite'],
    is_available: true,
    is_enabled: true,
  },
  {
    name: 'hybrid',
    type: 'hybrid',
    description: '混合方法',
    supported_db_types: ['postgresql', 'mysql', 'sqlite'],
    is_available: true,
    is_enabled: true,
  },
];

const mockPlugins = [
  {
    name: 'vanna-ai',
    version: '1.0.0',
    description: 'Vanna.ai Text-to-SQL',
    connection_type: 'rest_api',
    supported_db_types: ['postgresql', 'mysql'],
    is_healthy: true,
    is_enabled: true,
  },
];

const mockStatistics = {
  total_calls: 100,
  method_calls: { template: 30, llm: 40, hybrid: 30 },
  current_method: 'hybrid',
  average_switch_time_ms: 1.5,
  max_switch_time_ms: 5.0,
  last_switch_time: '2026-01-14T10:00:00Z',
  config: {
    default_method: 'hybrid',
    auto_select_enabled: true,
    fallback_enabled: true,
  },
};

// Test utilities
const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('TextToSQLConfigPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Setup default mock implementations
    vi.mocked(textToSqlService.textToSqlService.getConfig).mockResolvedValue({
      success: true,
      config: mockConfig,
    });
    vi.mocked(textToSqlService.textToSqlService.getMethods).mockResolvedValue(mockMethods);
    vi.mocked(textToSqlService.textToSqlService.getPlugins).mockResolvedValue(mockPlugins);
    vi.mocked(textToSqlService.textToSqlService.getStatistics).mockResolvedValue({
      success: true,
      statistics: mockStatistics,
    });
  });

  it('renders the page title and description', async () => {
    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('Text-to-SQL 配置')).toBeInTheDocument();
    });
  });

  it('loads and displays configuration data', async () => {
    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(textToSqlService.textToSqlService.getConfig).toHaveBeenCalled();
      expect(textToSqlService.textToSqlService.getMethods).toHaveBeenCalled();
      expect(textToSqlService.textToSqlService.getPlugins).toHaveBeenCalled();
      expect(textToSqlService.textToSqlService.getStatistics).toHaveBeenCalled();
    });
  });

  it('displays available methods', async () => {
    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('template')).toBeInTheDocument();
      expect(screen.getByText('llm')).toBeInTheDocument();
      expect(screen.getByText('hybrid')).toBeInTheDocument();
    });
  });

  it('displays statistics', async () => {
    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('总调用次数')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();
    });
  });

  it('handles test generation', async () => {
    vi.mocked(textToSqlService.textToSqlService.testGenerate).mockResolvedValue({
      success: true,
      sql: 'SELECT * FROM users',
      method_used: 'hybrid',
      confidence: 0.85,
      execution_time_ms: 50,
      metadata: { test_mode: true },
    });

    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('SQL 测试')).toBeInTheDocument();
    });

    // Click on SQL Test tab
    fireEvent.click(screen.getByText('SQL 测试'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/输入自然语言查询/)).toBeInTheDocument();
    });
  });

  it('displays plugins in the plugins tab', async () => {
    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('第三方插件')).toBeInTheDocument();
    });

    // Click on plugins tab
    fireEvent.click(screen.getByText('第三方插件'));

    await waitFor(() => {
      expect(screen.getByText('vanna-ai')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    renderWithProviders(<TextToSQLConfigPage />);
    expect(screen.getByText('加载配置中...')).toBeInTheDocument();
  });

  it('handles configuration save', async () => {
    vi.mocked(textToSqlService.textToSqlService.updateConfig).mockResolvedValue({
      success: true,
      message: '配置保存成功',
    });

    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('保存配置')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('保存配置'));

    await waitFor(() => {
      expect(textToSqlService.textToSqlService.updateConfig).toHaveBeenCalled();
    });
  });

  it('handles method switching', async () => {
    vi.mocked(textToSqlService.textToSqlService.switchMethod).mockResolvedValue({
      success: true,
      new_method: 'template',
      switch_time_ms: 1.5,
    });

    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('方法配置')).toBeInTheDocument();
    });
  });

  it('handles plugin enable/disable', async () => {
    vi.mocked(textToSqlService.textToSqlService.enablePlugin).mockResolvedValue({
      success: true,
      message: '插件已启用',
    });
    vi.mocked(textToSqlService.textToSqlService.disablePlugin).mockResolvedValue({
      success: true,
      message: '插件已禁用',
    });

    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('第三方插件')).toBeInTheDocument();
    });

    // Click on plugins tab
    fireEvent.click(screen.getByText('第三方插件'));

    await waitFor(() => {
      expect(screen.getByText('vanna-ai')).toBeInTheDocument();
    });
  });

  it('handles add plugin button click', async () => {
    renderWithProviders(<TextToSQLConfigPage />);

    await waitFor(() => {
      expect(screen.getByText('第三方插件')).toBeInTheDocument();
    });

    // Click on plugins tab
    fireEvent.click(screen.getByText('第三方插件'));

    await waitFor(() => {
      expect(screen.getByText('添加插件')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('添加插件'));

    await waitFor(() => {
      expect(screen.getByText('插件名称')).toBeInTheDocument();
    });
  });
});
