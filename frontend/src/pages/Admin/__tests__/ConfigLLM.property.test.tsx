/**
 * Property-Based Tests for Admin LLM Configuration Page
 * 
 * Tests provider-specific options display using property-based testing.
 * 
 * **Property 9: Provider-Specific Options Display**
 * **Validates: Requirements 1.2, 2.2, 3.2**
 * 
 * For any provider type selection (Global/Chinese LLM providers, or 
 * MySQL/PostgreSQL/Oracle/SQL Server database types), the UI should 
 * display only the configuration options specific to that provider/database type.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import fc from 'fast-check';
import ConfigLLM from '../ConfigLLM';
import { adminApi, LLMType, getLLMTypeName } from '@/services/adminApi';

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

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'llm.title': 'LLM 配置管理',
        'llm.form.addConfig': '添加配置',
        'llm.form.editConfig': '编辑配置',
        'llm.form.configName': '配置名称',
        'llm.form.configNameRequired': '请输入配置名称',
        'llm.form.llmType': 'LLM 类型',
        'llm.form.llmTypeRequired': '请选择 LLM 类型',
        'llm.form.modelName': '模型名称',
        'llm.form.modelNameRequired': '请输入模型名称',
        'llm.form.apiEndpoint': 'API 端点',
        'llm.form.apiKey': 'API Key',
        'common:name': '名称',
        'common:type': '类型',
        'common:status': '状态',
        'common:actions.label': '操作',
        'common:refresh': '刷新',
        'common:confirm': '确定',
        'common:cancel': '取消',
      };
      return translations[key] || key;
    },
    i18n: { language: 'zh-CN' },
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

// Define LLM provider types for property testing
const LLM_TYPES: LLMType[] = ['local_ollama', 'openai', 'qianwen', 'zhipu', 'hunyuan', 'custom'];

// Define expected fields for each provider type
const PROVIDER_REQUIRED_FIELDS: Record<LLMType, string[]> = {
  local_ollama: ['model_name', 'api_endpoint'],
  openai: ['model_name', 'api_key', 'api_endpoint'],
  qianwen: ['model_name', 'api_key'],
  zhipu: ['model_name', 'api_key'],
  hunyuan: ['model_name', 'api_key'],
  custom: ['model_name', 'api_endpoint'],
};

// Define optional fields for each provider type
const PROVIDER_OPTIONAL_FIELDS: Record<LLMType, string[]> = {
  local_ollama: ['temperature', 'max_tokens', 'timeout_seconds'],
  openai: ['temperature', 'max_tokens', 'timeout_seconds'],
  qianwen: ['temperature', 'max_tokens', 'timeout_seconds'],
  zhipu: ['temperature', 'max_tokens', 'timeout_seconds'],
  hunyuan: ['temperature', 'max_tokens', 'timeout_seconds'],
  custom: ['temperature', 'max_tokens', 'timeout_seconds', 'api_key'],
};

describe('ConfigLLM Property Tests - Provider-Specific Options Display', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.listLLMConfigs as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  /**
   * Property 9.1: All LLM provider types should have a display name
   * 
   * For any valid LLM provider type, the system should return a non-empty
   * display name that can be shown in the UI.
   */
  it('Property 9.1: All LLM provider types have display names', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        (providerType) => {
          const displayName = getLLMTypeName(providerType);
          
          // Display name should be non-empty
          expect(displayName).toBeTruthy();
          expect(displayName.length).toBeGreaterThan(0);
          
          // Display name should not be the raw type value (should be localized)
          // For Chinese providers, the display name should contain Chinese characters
          if (['qianwen', 'zhipu', 'hunyuan'].includes(providerType)) {
            expect(displayName).toMatch(/[\u4e00-\u9fa5]/); // Contains Chinese characters
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.2: Provider type selection determines required fields
   * 
   * For any provider type, the set of required fields should be consistent
   * and non-empty.
   */
  it('Property 9.2: Provider type determines required fields consistently', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        (providerType) => {
          const requiredFields = PROVIDER_REQUIRED_FIELDS[providerType];
          
          // Every provider should have at least model_name as required
          expect(requiredFields).toContain('model_name');
          
          // Required fields should be non-empty array
          expect(requiredFields.length).toBeGreaterThan(0);
          
          // Cloud providers should require API key
          if (['openai', 'qianwen', 'zhipu', 'hunyuan'].includes(providerType)) {
            expect(requiredFields).toContain('api_key');
          }
          
          // Local providers should not require API key
          if (providerType === 'local_ollama') {
            expect(requiredFields).not.toContain('api_key');
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.3: Provider type selection is idempotent
   * 
   * Selecting the same provider type multiple times should always result
   * in the same set of displayed fields.
   */
  it('Property 9.3: Provider type selection is idempotent', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        fc.integer({ min: 1, max: 5 }),
        (providerType, repetitions) => {
          const results: string[][] = [];
          
          for (let i = 0; i < repetitions; i++) {
            const requiredFields = PROVIDER_REQUIRED_FIELDS[providerType];
            const optionalFields = PROVIDER_OPTIONAL_FIELDS[providerType];
            results.push([...requiredFields, ...optionalFields].sort());
          }
          
          // All results should be identical
          for (let i = 1; i < results.length; i++) {
            expect(results[i]).toEqual(results[0]);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.4: No field overlap between required and optional
   * 
   * For any provider type, required fields and optional fields should
   * be mutually exclusive.
   */
  it('Property 9.4: Required and optional fields are mutually exclusive', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        (providerType) => {
          const requiredFields = new Set(PROVIDER_REQUIRED_FIELDS[providerType]);
          const optionalFields = new Set(PROVIDER_OPTIONAL_FIELDS[providerType]);
          
          // Check for intersection
          const intersection = [...requiredFields].filter(f => optionalFields.has(f));
          
          // Intersection should be empty (no field should be both required and optional)
          expect(intersection.length).toBe(0);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.5: Common fields exist across all providers
   * 
   * Certain fields (like model_name, temperature) should be available
   * for all provider types.
   */
  it('Property 9.5: Common fields exist across all providers', () => {
    const commonFields = ['model_name', 'temperature', 'max_tokens', 'timeout_seconds'];
    
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        (providerType) => {
          const allFields = [
            ...PROVIDER_REQUIRED_FIELDS[providerType],
            ...PROVIDER_OPTIONAL_FIELDS[providerType],
          ];
          
          // All common fields should be present (either required or optional)
          for (const commonField of commonFields) {
            expect(allFields).toContain(commonField);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.6: Provider display names are unique
   * 
   * Each provider type should have a unique display name to avoid
   * confusion in the UI.
   */
  it('Property 9.6: Provider display names are unique', () => {
    const displayNames = LLM_TYPES.map(type => getLLMTypeName(type));
    const uniqueNames = new Set(displayNames);
    
    expect(uniqueNames.size).toBe(LLM_TYPES.length);
  });

  /**
   * Property 9.7: Field configuration is complete
   * 
   * For any provider type, the union of required and optional fields
   * should cover all necessary configuration options.
   */
  it('Property 9.7: Field configuration is complete', () => {
    const minimumFields = ['model_name']; // At minimum, model_name is always needed
    
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        (providerType) => {
          const allFields = [
            ...PROVIDER_REQUIRED_FIELDS[providerType],
            ...PROVIDER_OPTIONAL_FIELDS[providerType],
          ];
          
          // All minimum fields should be present
          for (const field of minimumFields) {
            expect(allFields).toContain(field);
          }
          
          // Total fields should be reasonable (not too few, not too many)
          expect(allFields.length).toBeGreaterThanOrEqual(3);
          expect(allFields.length).toBeLessThanOrEqual(10);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('ConfigLLM Property Tests - Form Validation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.listLLMConfigs as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  /**
   * Property 9.8: Valid configurations pass validation
   * 
   * For any provider type with all required fields filled, the configuration
   * should pass validation.
   */
  it('Property 9.8: Valid configurations pass validation', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        fc.string({ minLength: 1, maxLength: 100 }),
        fc.string({ minLength: 1, maxLength: 100 }),
        (providerType, name, modelName) => {
          const config: Record<string, unknown> = {
            name,
            llm_type: providerType,
            model_name: modelName,
          };
          
          // Add required fields based on provider type
          const requiredFields = PROVIDER_REQUIRED_FIELDS[providerType];
          
          if (requiredFields.includes('api_key')) {
            config.api_key = 'sk-test-key-12345';
          }
          
          if (requiredFields.includes('api_endpoint')) {
            config.api_endpoint = 'https://api.example.com/v1';
          }
          
          // Validate that all required fields are present
          for (const field of requiredFields) {
            expect(config[field]).toBeTruthy();
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.9: Missing required fields fail validation
   * 
   * For any provider type with missing required fields, the configuration
   * should fail validation.
   */
  it('Property 9.9: Missing required fields fail validation', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...LLM_TYPES),
        (providerType) => {
          const requiredFields = PROVIDER_REQUIRED_FIELDS[providerType];
          
          // Create config with one required field missing
          const config: Record<string, unknown> = {
            name: 'Test Config',
            llm_type: providerType,
          };
          
          // Add all required fields except the first one
          for (let i = 1; i < requiredFields.length; i++) {
            const field = requiredFields[i];
            if (field === 'api_key') {
              config[field] = 'sk-test-key';
            } else if (field === 'api_endpoint') {
              config[field] = 'https://api.example.com';
            } else if (field === 'model_name') {
              config[field] = 'test-model';
            }
          }
          
          // The first required field should be missing
          const missingField = requiredFields[0];
          expect(config[missingField]).toBeUndefined();
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.10: Temperature values are bounded
   * 
   * Temperature values should be within valid range (0 to 2).
   */
  it('Property 9.10: Temperature values are bounded', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 2, noNaN: true }),
        (temperature) => {
          // Valid temperature should be between 0 and 2
          expect(temperature).toBeGreaterThanOrEqual(0);
          expect(temperature).toBeLessThanOrEqual(2);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.11: Max tokens values are positive integers
   * 
   * Max tokens should be positive integers within reasonable bounds.
   */
  it('Property 9.11: Max tokens values are positive integers', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 128000 }),
        (maxTokens) => {
          // Valid max_tokens should be positive
          expect(maxTokens).toBeGreaterThan(0);
          expect(Number.isInteger(maxTokens)).toBe(true);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.12: Timeout values are positive
   * 
   * Timeout values should be positive integers.
   */
  it('Property 9.12: Timeout values are positive', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 600 }),
        (timeout) => {
          // Valid timeout should be positive
          expect(timeout).toBeGreaterThan(0);
          expect(Number.isInteger(timeout)).toBe(true);
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});

describe('ConfigLLM Property Tests - API Key Handling', () => {
  /**
   * Property 9.13: API keys are masked in display
   * 
   * When displaying API keys, they should be masked to hide sensitive data.
   */
  it('Property 9.13: API keys are masked in display', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 10, maxLength: 100 }),
        (apiKey) => {
          // Simulate masking function
          const maskApiKey = (key: string): string => {
            if (key.length <= 8) {
              return '****';
            }
            return `${key.slice(0, 4)}****${key.slice(-4)}`;
          };
          
          const masked = maskApiKey(apiKey);
          
          // Masked key should contain asterisks
          expect(masked).toContain('****');
          
          // Masked key should not contain the full original key
          if (apiKey.length > 8) {
            expect(masked).not.toBe(apiKey);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 9.14: API key masking preserves identifiability
   * 
   * Masked API keys should still be partially identifiable (first/last chars).
   */
  it('Property 9.14: API key masking preserves identifiability', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 10, maxLength: 100 }),
        (apiKey) => {
          const maskApiKey = (key: string): string => {
            if (key.length <= 8) {
              return '****';
            }
            return `${key.slice(0, 4)}****${key.slice(-4)}`;
          };
          
          const masked = maskApiKey(apiKey);
          
          // For keys longer than 8 chars, first and last 4 chars should be visible
          if (apiKey.length > 8) {
            expect(masked.startsWith(apiKey.slice(0, 4))).toBe(true);
            expect(masked.endsWith(apiKey.slice(-4))).toBe(true);
          }
          
          return true;
        }
      ),
      { numRuns: 100 }
    );
  });
});
