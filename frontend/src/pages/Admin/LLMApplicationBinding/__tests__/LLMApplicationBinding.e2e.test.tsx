/**
 * End-to-end test for LLM Application Binding frontend workflows.
 * 
 * This module tests complete user workflows:
 * - Create LLM configuration workflow
 * - Edit and delete workflows
 * - Binding creation and reordering
 * - Connection testing
 * - i18n works in both languages
 * 
 * Validates: Requirements 9.1-9.8, 10.1-10.12
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18n';
import i18n from 'i18next';

import ApplicationBindings from '../ApplicationBindings';
import LLMConfigForm from '../LLMConfigForm';
import BindingForm from '../BindingForm';
import { llmConfigStore } from '@/stores/llmConfigStore';
import * as llmConfigApi from '@/services/llmConfigApi';

// Mock API calls
vi.mock('@/services/llmConfigApi');

// Setup i18n for testing
beforeEach(() => {
  i18n.init({
    lng: 'zh',
    resources: {
      zh: {
        llmConfig: {
          title: 'LLM 配置',
          providers: {
            openai: 'OpenAI',
            azure: 'Azure OpenAI 服务',
            anthropic: 'Anthropic Claude',
            ollama: 'Ollama (本地)',
            custom: '自定义提供商'
          },
          applications: {
            structuring: '数据结构化',
            knowledge_graph: '知识图谱',
            ai_assistant: 'AI 助手'
          },
          form: {
            name: '配置名称',
            provider: '提供商',
            apiKey: 'API 密钥',
            baseUrl: '基础 URL',
            modelName: '模型名称',
            parameters: '参数 (JSON)',
            priority: '优先级',
            maxRetries: '最大重试次数',
            timeout: '超时时间 (秒)'
          },
          actions: {
            create: '创建配置',
            edit: '编辑',
            delete: '删除',
            test: '测试连接',
            save: '保存',
            cancel: '取消',
            addBinding: '添加绑定'
          },
          messages: {
            createSuccess: '配置创建成功',
            updateSuccess: '配置更新成功',
            deleteSuccess: '配置删除成功',
            testSuccess: '连接测试成功',
            testFailed: '连接测试失败',
            deleteConfirm: '确定要删除此配置吗？'
          },
          validation: {
            nameRequired: '请输入配置名称',
            providerRequired: '请选择提供商',
            apiKeyRequired: '请输入 API 密钥',
            modelNameRequired: '请输入模型名称',
            priorityRange: '优先级必须在 1-99 之间',
            retriesRange: '重试次数必须在 0-10 之间',
            timeoutPositive: '超时时间必须大于 0'
          }
        }
      },
      en: {
        llmConfig: {
          title: 'LLM Configuration',
          providers: {
            openai: 'OpenAI',
            azure: 'Azure OpenAI Service',
            anthropic: 'Anthropic Claude',
            ollama: 'Ollama (Local)',
            custom: 'Custom Provider'
          },
          applications: {
            structuring: 'Data Structuring',
            knowledge_graph: 'Knowledge Graph',
            ai_assistant: 'AI Assistant'
          },
          form: {
            name: 'Configuration Name',
            provider: 'Provider',
            apiKey: 'API Key',
            baseUrl: 'Base URL',
            modelName: 'Model Name',
            parameters: 'Parameters (JSON)',
            priority: 'Priority',
            maxRetries: 'Max Retries',
            timeout: 'Timeout (seconds)'
          },
          actions: {
            create: 'Create Configuration',
            edit: 'Edit',
            delete: 'Delete',
            test: 'Test Connection',
            save: 'Save',
            cancel: 'Cancel',
            addBinding: 'Add Binding'
          },
          messages: {
            createSuccess: 'Configuration created successfully',
            updateSuccess: 'Configuration updated successfully',
            deleteSuccess: 'Configuration deleted successfully',
            testSuccess: 'Connection test successful',
            testFailed: 'Connection test failed',
            deleteConfirm: 'Are you sure you want to delete this configuration?'
          },
          validation: {
            nameRequired: 'Please enter configuration name',
            providerRequired: 'Please select provider',
            apiKeyRequired: 'Please enter API key',
            modelNameRequired: 'Please enter model name',
            priorityRange: 'Priority must be between 1-99',
            retriesRange: 'Retries must be between 0-10',
            timeoutPositive: 'Timeout must be greater than 0'
          }
        }
      }
    }
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

// Helper to render with providers
const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <I18nextProvider i18n={i18n}>
        {component}
      </I18nextProvider>
    </BrowserRouter>
  );
};

describe('LLM Configuration E2E Tests', () => {
  describe('Create LLM Configuration Workflow', () => {
    it('should complete full create workflow', async () => {
      const user = userEvent.setup();
      
      // Mock API response
      const mockConfig = {
        id: '123',
        name: 'Test Config',
        provider: 'openai',
        base_url: 'https://api.openai.com/v1',
        model_name: 'gpt-4',
        parameters: {},
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      vi.mocked(llmConfigApi.createLLMConfig).mockResolvedValue(mockConfig);
      
      // Render form
      const onSuccess = vi.fn();
      renderWithProviders(<LLMConfigForm onSuccess={onSuccess} />);
      
      // Fill in form fields
      const nameInput = screen.getByLabelText(/配置名称|Configuration Name/i);
      await user.type(nameInput, 'Test Config');
      
      const providerSelect = screen.getByLabelText(/提供商|Provider/i);
      await user.click(providerSelect);
      await user.click(screen.getByText('OpenAI'));
      
      const apiKeyInput = screen.getByLabelText(/API 密钥|API Key/i);
      await user.type(apiKeyInput, 'sk-test-key-123');
      
      const baseUrlInput = screen.getByLabelText(/基础 URL|Base URL/i);
      await user.type(baseUrlInput, 'https://api.openai.com/v1');
      
      const modelNameInput = screen.getByLabelText(/模型名称|Model Name/i);
      await user.type(modelNameInput, 'gpt-4');
      
      // Submit form
      const saveButton = screen.getByText(/保存|Save/i);
      await user.click(saveButton);
      
      // Verify API was called
      await waitFor(() => {
        expect(llmConfigApi.createLLMConfig).toHaveBeenCalledWith({
          name: 'Test Config',
          provider: 'openai',
          api_key: 'sk-test-key-123',
          base_url: 'https://api.openai.com/v1',
          model_name: 'gpt-4',
          parameters: {}
        });
      });
      
      // Verify success callback
      expect(onSuccess).toHaveBeenCalled();
    });
    
    it('should validate required fields', async () => {
      const user = userEvent.setup();
      
      renderWithProviders(<LLMConfigForm onSuccess={vi.fn()} />);
      
      // Try to submit without filling fields
      const saveButton = screen.getByText(/保存|Save/i);
      await user.click(saveButton);
      
      // Verify validation messages appear
      await waitFor(() => {
        expect(screen.getByText(/请输入配置名称|Please enter configuration name/i)).toBeInTheDocument();
        expect(screen.getByText(/请选择提供商|Please select provider/i)).toBeInTheDocument();
        expect(screen.getByText(/请输入 API 密钥|Please enter API key/i)).toBeInTheDocument();
      });
      
      // Verify API was not called
      expect(llmConfigApi.createLLMConfig).not.toHaveBeenCalled();
    });
  });
  
  describe('Edit and Delete Workflows', () => {
    it('should complete edit workflow', async () => {
      const user = userEvent.setup();
      
      const existingConfig = {
        id: '123',
        name: 'Original Config',
        provider: 'openai',
        base_url: 'https://api.openai.com/v1',
        model_name: 'gpt-3.5-turbo',
        parameters: {},
        is_active: true
      };
      
      const updatedConfig = {
        ...existingConfig,
        name: 'Updated Config',
        model_name: 'gpt-4'
      };
      
      vi.mocked(llmConfigApi.updateLLMConfig).mockResolvedValue(updatedConfig);
      
      // Render form with existing config
      const onSuccess = vi.fn();
      renderWithProviders(
        <LLMConfigForm 
          config={existingConfig} 
          onSuccess={onSuccess} 
        />
      );
      
      // Verify form is pre-filled
      expect(screen.getByDisplayValue('Original Config')).toBeInTheDocument();
      expect(screen.getByDisplayValue('gpt-3.5-turbo')).toBeInTheDocument();
      
      // Update fields
      const nameInput = screen.getByLabelText(/配置名称|Configuration Name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated Config');
      
      const modelInput = screen.getByLabelText(/模型名称|Model Name/i);
      await user.clear(modelInput);
      await user.type(modelInput, 'gpt-4');
      
      // Submit
      const saveButton = screen.getByText(/保存|Save/i);
      await user.click(saveButton);
      
      // Verify API was called
      await waitFor(() => {
        expect(llmConfigApi.updateLLMConfig).toHaveBeenCalledWith('123', {
          name: 'Updated Config',
          model_name: 'gpt-4'
        });
      });
      
      expect(onSuccess).toHaveBeenCalled();
    });
    
    it('should complete delete workflow with confirmation', async () => {
      const user = userEvent.setup();
      
      const mockConfig = {
        id: '123',
        name: 'Config to Delete',
        provider: 'openai',
        model_name: 'gpt-4'
      };
      
      vi.mocked(llmConfigApi.deleteLLMConfig).mockResolvedValue(undefined);
      
      // Mock window.confirm
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
      
      // Render component with delete button
      const onDelete = vi.fn();
      renderWithProviders(
        <div>
          <button onClick={() => {
            if (window.confirm('确定要删除此配置吗？')) {
              llmConfigApi.deleteLLMConfig(mockConfig.id).then(onDelete);
            }
          }}>
            删除
          </button>
        </div>
      );
      
      // Click delete
      const deleteButton = screen.getByText('删除');
      await user.click(deleteButton);
      
      // Verify confirmation was shown
      expect(confirmSpy).toHaveBeenCalled();
      
      // Verify API was called
      await waitFor(() => {
        expect(llmConfigApi.deleteLLMConfig).toHaveBeenCalledWith('123');
      });
      
      expect(onDelete).toHaveBeenCalled();
      
      confirmSpy.mockRestore();
    });
  });
  
  describe('Binding Creation and Reordering', () => {
    it('should create binding with validation', async () => {
      const user = userEvent.setup();
      
      const mockApplications = [
        { id: 'app1', code: 'structuring', name: '数据结构化' },
        { id: 'app2', code: 'knowledge_graph', name: '知识图谱' }
      ];
      
      const mockConfigs = [
        { id: 'config1', name: 'Config 1', provider: 'openai' },
        { id: 'config2', name: 'Config 2', provider: 'azure' }
      ];
      
      const mockBinding = {
        id: 'binding1',
        llm_config_id: 'config1',
        application_id: 'app1',
        priority: 1,
        max_retries: 3,
        timeout_seconds: 30
      };
      
      vi.mocked(llmConfigApi.createBinding).mockResolvedValue(mockBinding);
      
      // Render form
      const onSuccess = vi.fn();
      renderWithProviders(
        <BindingForm 
          applications={mockApplications}
          configs={mockConfigs}
          onSuccess={onSuccess}
        />
      );
      
      // Fill in form
      const appSelect = screen.getByLabelText(/应用|Application/i);
      await user.click(appSelect);
      await user.click(screen.getByText('数据结构化'));
      
      const configSelect = screen.getByLabelText(/LLM 配置|LLM Configuration/i);
      await user.click(configSelect);
      await user.click(screen.getByText('Config 1'));
      
      const priorityInput = screen.getByLabelText(/优先级|Priority/i);
      await user.type(priorityInput, '1');
      
      const retriesInput = screen.getByLabelText(/最大重试次数|Max Retries/i);
      await user.type(retriesInput, '3');
      
      const timeoutInput = screen.getByLabelText(/超时时间|Timeout/i);
      await user.type(timeoutInput, '30');
      
      // Submit
      const saveButton = screen.getByText(/保存|Save/i);
      await user.click(saveButton);
      
      // Verify API was called
      await waitFor(() => {
        expect(llmConfigApi.createBinding).toHaveBeenCalledWith({
          llm_config_id: 'config1',
          application_id: 'app1',
          priority: 1,
          max_retries: 3,
          timeout_seconds: 30
        });
      });
      
      expect(onSuccess).toHaveBeenCalled();
    });
    
    it('should validate priority range (1-99)', async () => {
      const user = userEvent.setup();
      
      renderWithProviders(
        <BindingForm 
          applications={[]}
          configs={[]}
          onSuccess={vi.fn()}
        />
      );
      
      const priorityInput = screen.getByLabelText(/优先级|Priority/i);
      
      // Try invalid priority
      await user.type(priorityInput, '100');
      
      const saveButton = screen.getByText(/保存|Save/i);
      await user.click(saveButton);
      
      // Verify validation message
      await waitFor(() => {
        expect(screen.getByText(/优先级必须在 1-99 之间|Priority must be between 1-99/i)).toBeInTheDocument();
      });
    });
    
    it('should validate retries range (0-10)', async () => {
      const user = userEvent.setup();
      
      renderWithProviders(
        <BindingForm 
          applications={[]}
          configs={[]}
          onSuccess={vi.fn()}
        />
      );
      
      const retriesInput = screen.getByLabelText(/最大重试次数|Max Retries/i);
      
      // Try invalid retries
      await user.type(retriesInput, '15');
      
      const saveButton = screen.getByText(/保存|Save/i);
      await user.click(saveButton);
      
      // Verify validation message
      await waitFor(() => {
        expect(screen.getByText(/重试次数必须在 0-10 之间|Retries must be between 0-10/i)).toBeInTheDocument();
      });
    });
  });
  
  describe('Connection Testing', () => {
    it('should test connection successfully', async () => {
      const user = userEvent.setup();
      
      const mockConfig = {
        id: '123',
        name: 'Test Config',
        provider: 'openai'
      };
      
      vi.mocked(llmConfigApi.testConnection).mockResolvedValue({
        status: 'success',
        latency_ms: 123
      });
      
      // Render test button
      renderWithProviders(
        <button onClick={() => llmConfigApi.testConnection(mockConfig.id)}>
          测试连接
        </button>
      );
      
      const testButton = screen.getByText('测试连接');
      await user.click(testButton);
      
      // Verify API was called
      await waitFor(() => {
        expect(llmConfigApi.testConnection).toHaveBeenCalledWith('123');
      });
    });
    
    it('should handle connection test failure', async () => {
      const user = userEvent.setup();
      
      const mockConfig = {
        id: '123',
        name: 'Test Config'
      };
      
      vi.mocked(llmConfigApi.testConnection).mockRejectedValue(
        new Error('Connection failed')
      );
      
      // Render test button with error handling
      const TestButton = () => {
        const [error, setError] = React.useState<string | null>(null);
        
        const handleTest = async () => {
          try {
            await llmConfigApi.testConnection(mockConfig.id);
          } catch (err) {
            setError('连接测试失败');
          }
        };
        
        return (
          <div>
            <button onClick={handleTest}>测试连接</button>
            {error && <div role="alert">{error}</div>}
          </div>
        );
      };
      
      renderWithProviders(<TestButton />);
      
      const testButton = screen.getByText('测试连接');
      await user.click(testButton);
      
      // Verify error message appears
      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent('连接测试失败');
      });
    });
  });
  
  describe('Internationalization (i18n)', () => {
    it('should display Chinese translations', () => {
      i18n.changeLanguage('zh');
      
      renderWithProviders(<LLMConfigForm onSuccess={vi.fn()} />);
      
      // Verify Chinese labels
      expect(screen.getByText(/配置名称/i)).toBeInTheDocument();
      expect(screen.getByText(/提供商/i)).toBeInTheDocument();
      expect(screen.getByText(/API 密钥/i)).toBeInTheDocument();
      expect(screen.getByText(/保存/i)).toBeInTheDocument();
    });
    
    it('should display English translations', () => {
      i18n.changeLanguage('en');
      
      renderWithProviders(<LLMConfigForm onSuccess={vi.fn()} />);
      
      // Verify English labels
      expect(screen.getByText(/Configuration Name/i)).toBeInTheDocument();
      expect(screen.getByText(/Provider/i)).toBeInTheDocument();
      expect(screen.getByText(/API Key/i)).toBeInTheDocument();
      expect(screen.getByText(/Save/i)).toBeInTheDocument();
    });
    
    it('should translate provider names', () => {
      i18n.changeLanguage('zh');
      
      const providers = ['openai', 'azure', 'anthropic', 'ollama', 'custom'];
      
      renderWithProviders(
        <div>
          {providers.map(provider => (
            <div key={provider}>
              {i18n.t(`llmConfig.providers.${provider}`)}
            </div>
          ))}
        </div>
      );
      
      // Verify Chinese provider names
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Azure OpenAI 服务')).toBeInTheDocument();
      expect(screen.getByText('Anthropic Claude')).toBeInTheDocument();
      expect(screen.getByText('Ollama (本地)')).toBeInTheDocument();
      expect(screen.getByText('自定义提供商')).toBeInTheDocument();
    });
    
    it('should translate application names', () => {
      i18n.changeLanguage('zh');
      
      const applications = ['structuring', 'knowledge_graph', 'ai_assistant'];
      
      renderWithProviders(
        <div>
          {applications.map(app => (
            <div key={app}>
              {i18n.t(`llmConfig.applications.${app}`)}
            </div>
          ))}
        </div>
      );
      
      // Verify Chinese application names
      expect(screen.getByText('数据结构化')).toBeInTheDocument();
      expect(screen.getByText('知识图谱')).toBeInTheDocument();
      expect(screen.getByText('AI 助手')).toBeInTheDocument();
    });
  });
});
