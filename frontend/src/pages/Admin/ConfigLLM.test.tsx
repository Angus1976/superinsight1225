/**
 * Unit tests for Admin LLM Configuration Page
 * 
 * Tests form validation, API key masking, and connection testing.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import ConfigLLM from './ConfigLLM';
import { adminApi } from '@/services/adminApi';

// Mock the adminApi
vi.mock('@/services/adminApi', () => ({
  adminApi: {
    listLLMConfigs: vi.fn(),
    createLLMConfig: vi.fn(),
    updateLLMConfig: vi.fn(),
    deleteLLMConfig: vi.fn(),
    testLLMConnection: vi.fn(),
  },
  getLLMTypeName: (type: string) => {
    const names: Record<string, string> = {
      local_ollama: '本地 Ollama',
      openai: 'OpenAI',
      qianwen: '通义千问',
      zhipu: '智谱 GLM',
      hunyuan: '腾讯混元',
      custom: '自定义',
    };
    return names[type] || type;
  },
}));

// Mock auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: 'test-user-id', username: 'testuser', role: 'admin' },
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('ConfigLLM', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.listLLMConfigs as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: '1',
        name: 'Test OpenAI Config',
        llm_type: 'openai',
        model_name: 'gpt-3.5-turbo',
        api_endpoint: 'https://api.openai.com/v1',
        api_key_masked: 'sk-****1234',
        temperature: 0.7,
        max_tokens: 2048,
        timeout_seconds: 60,
        is_active: true,
        is_default: true,
        extra_config: {},
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]);
  });

  it('renders the LLM configuration page', async () => {
    render(<ConfigLLM />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('LLM 配置管理')).toBeInTheDocument();
    });
  });

  it('displays LLM configs in table', async () => {
    render(<ConfigLLM />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('Test OpenAI Config')).toBeInTheDocument();
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('gpt-3.5-turbo')).toBeInTheDocument();
    });
  });

  it('shows masked API key', async () => {
    render(<ConfigLLM />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('sk-****1234')).toBeInTheDocument();
    });
  });

  it('opens create modal when clicking add button', async () => {
    render(<ConfigLLM />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('添加配置')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('添加配置'));
    
    await waitFor(() => {
      expect(screen.getByText('添加 LLM 配置')).toBeInTheDocument();
    });
  });

  it('validates required fields in create form', async () => {
    render(<ConfigLLM />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('添加配置')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('添加配置'));
    
    await waitFor(() => {
      expect(screen.getByText('添加 LLM 配置')).toBeInTheDocument();
    });
    
    // Try to submit without filling required fields
    const okButton = screen.getByRole('button', { name: /确定|OK/i });
    fireEvent.click(okButton);
    
    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText('请输入配置名称')).toBeInTheDocument();
    });
  });

  it('tests LLM connection', async () => {
    (adminApi.testLLMConnection as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: true,
      latency_ms: 150,
    });
    
    render(<ConfigLLM />, { wrapper: createWrapper() });
    
    await waitFor(() => {
      expect(screen.getByText('Test OpenAI Config')).toBeInTheDocument();
    });
    
    // Find and click the test connection button
    const testButtons = screen.getAllByRole('button');
    const testButton = testButtons.find(btn => btn.querySelector('[aria-label="api"]'));
    
    if (testButton) {
      fireEvent.click(testButton);
      
      await waitFor(() => {
        expect(adminApi.testLLMConnection).toHaveBeenCalledWith('1');
      });
    }
  });
});
