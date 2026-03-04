/**
 * LLM Config Translation Key Completeness Tests
 * 
 * **Validates: Requirements 10.11** - 验证翻译文件同步
 * 
 * Tests that translation keys are complete and synchronized between Chinese and English files
 * for the LLM configuration management feature.
 */

import { describe, it, expect } from 'vitest';
import zhLlmConfig from '../zh/llmConfig.json';
import enLlmConfig from '../en/llmConfig.json';

/**
 * Recursively get all keys from an object with dot notation
 * @param obj - The object to extract keys from
 * @param prefix - The prefix for nested keys
 * @returns Array of all keys in dot notation
 */
function getAllKeys(obj: Record<string, unknown>, prefix = ''): string[] {
  const keys: string[] = [];
  
  for (const key of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    const value = obj[key];
    
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      // Recursively get keys from nested objects
      keys.push(...getAllKeys(value as Record<string, unknown>, fullKey));
    } else {
      // Add leaf key
      keys.push(fullKey);
    }
  }
  
  return keys;
}

/**
 * Find keys that exist in source but not in target
 * @param sourceKeys - Keys from source object
 * @param targetKeys - Keys from target object
 * @returns Array of missing keys
 */
function findMissingKeys(sourceKeys: string[], targetKeys: string[]): string[] {
  const targetSet = new Set(targetKeys);
  return sourceKeys.filter(key => !targetSet.has(key));
}

describe('LLM Config Translation Key Completeness', () => {
  const zhKeys = getAllKeys(zhLlmConfig);
  const enKeys = getAllKeys(enLlmConfig);

  describe('Key Existence', () => {
    it('should have Chinese translation keys', () => {
      expect(zhKeys.length).toBeGreaterThan(0);
    });

    it('should have English translation keys', () => {
      expect(enKeys.length).toBeGreaterThan(0);
    });

    it('should have the same number of keys in both languages', () => {
      expect(zhKeys.length).toBe(enKeys.length);
    });
  });

  describe('Key Synchronization', () => {
    it('should have all Chinese keys in English file', () => {
      const missingInEn = findMissingKeys(zhKeys, enKeys);
      
      if (missingInEn.length > 0) {
        console.error('Keys missing in English file:', missingInEn);
      }
      
      expect(missingInEn).toHaveLength(0);
    });

    it('should have all English keys in Chinese file', () => {
      const missingInZh = findMissingKeys(enKeys, zhKeys);
      
      if (missingInZh.length > 0) {
        console.error('Keys missing in Chinese file:', missingInZh);
      }
      
      expect(missingInZh).toHaveLength(0);
    });
  });

  describe('Core Translation Keys', () => {
    // Test that essential keys exist in both languages
    const coreKeys = [
      'pageTitle',
      'pageDescription',
      'providers.openai',
      'providers.azure',
      'providers.anthropic',
      'providers.ollama',
      'providers.custom',
      'applications.structuring.name',
      'applications.knowledge_graph.name',
      'applications.ai_assistant.name',
      'configList.title',
      'configList.addButton',
      'configForm.createTitle',
      'configForm.editTitle',
      'configForm.fields.name.label',
      'configForm.fields.provider.label',
      'configForm.fields.apiKey.label',
      'configForm.fields.modelName.label',
      'testConnection.button',
      'testConnection.success',
      'testConnection.failed',
      'bindings.title',
      'bindings.addButton',
      'bindingForm.createTitle',
      'bindingForm.fields.application.label',
      'bindingForm.fields.llmConfig.label',
      'bindingForm.fields.priority.label',
      'bindingForm.fields.maxRetries.label',
      'bindingForm.fields.timeoutSeconds.label',
      'errors.loadConfigsFailed',
      'errors.networkError',
      'messages.loading',
      'tabs.configs',
      'tabs.bindings',
    ];

    coreKeys.forEach(key => {
      it(`should have core key "${key}" in Chinese`, () => {
        expect(zhKeys).toContain(key);
      });

      it(`should have core key "${key}" in English`, () => {
        expect(enKeys).toContain(key);
      });
    });
  });

  describe('Translation Values', () => {
    it('should have non-empty Chinese translations', () => {
      const testKeys = [
        'pageTitle',
        'configList.title',
        'configForm.fields.name.label',
        'testConnection.button',
        'bindings.title',
      ];
      
      testKeys.forEach(key => {
        const parts = key.split('.');
        let value: unknown = zhLlmConfig;
        
        for (const part of parts) {
          value = (value as Record<string, unknown>)?.[part];
        }
        
        expect(value).toBeTruthy();
        expect(typeof value).toBe('string');
        expect((value as string).length).toBeGreaterThan(0);
      });
    });

    it('should have non-empty English translations', () => {
      const testKeys = [
        'pageTitle',
        'configList.title',
        'configForm.fields.name.label',
        'testConnection.button',
        'bindings.title',
      ];
      
      testKeys.forEach(key => {
        const parts = key.split('.');
        let value: unknown = enLlmConfig;
        
        for (const part of parts) {
          value = (value as Record<string, unknown>)?.[part];
        }
        
        expect(value).toBeTruthy();
        expect(typeof value).toBe('string');
        expect((value as string).length).toBeGreaterThan(0);
      });
    });

    it('should have different values for Chinese and English translations', () => {
      // Verify that translations are actually different (not just copied)
      const testKeys = [
        'pageTitle',
        'configList.addButton',
        'testConnection.success',
        'bindings.title',
      ];
      
      testKeys.forEach(key => {
        const parts = key.split('.');
        
        let zhValue: unknown = zhLlmConfig;
        let enValue: unknown = enLlmConfig;
        
        for (const part of parts) {
          zhValue = (zhValue as Record<string, unknown>)?.[part];
          enValue = (enValue as Record<string, unknown>)?.[part];
        }
        
        expect(typeof zhValue).toBe('string');
        expect(typeof enValue).toBe('string');
        expect(zhValue).not.toBe(enValue);
      });
    });
  });

  describe('Interpolation Consistency', () => {
    it('should have consistent interpolation variables in both languages', () => {
      // Find keys with interpolation ({{variable}})
      const interpolationRegex = /\{\{(\w+)\}\}/g;
      
      const getInterpolationVars = (value: string): string[] => {
        const matches = value.match(interpolationRegex) || [];
        return matches.map(m => m.replace(/\{\{|\}\}/g, ''));
      };
      
      // Check keys with interpolation
      const keysWithInterpolation = [
        'configList.deleteConfirm.content',
        'testConnection.latency',
        'testConnection.error',
      ];
      
      keysWithInterpolation.forEach(key => {
        const parts = key.split('.');
        
        let zhValue: unknown = zhLlmConfig;
        let enValue: unknown = enLlmConfig;
        
        for (const part of parts) {
          zhValue = (zhValue as Record<string, unknown>)?.[part];
          enValue = (enValue as Record<string, unknown>)?.[part];
        }
        
        if (typeof zhValue === 'string' && typeof enValue === 'string') {
          const zhVars = getInterpolationVars(zhValue);
          const enVars = getInterpolationVars(enValue);
          
          // Both should have the same interpolation variables
          expect(zhVars.sort()).toEqual(enVars.sort());
        }
      });
    });
  });

  describe('No Missing Translations', () => {
    it('should not have any missing translations in Chinese file', () => {
      // All leaf values should be strings, not objects or undefined
      const checkForMissing = (obj: Record<string, unknown>, path = ''): string[] => {
        const missing: string[] = [];
        
        for (const [key, value] of Object.entries(obj)) {
          const fullPath = path ? `${path}.${key}` : key;
          
          if (value === null || value === undefined || value === '') {
            missing.push(fullPath);
          } else if (typeof value === 'object' && !Array.isArray(value)) {
            missing.push(...checkForMissing(value as Record<string, unknown>, fullPath));
          }
        }
        
        return missing;
      };
      
      const missingZh = checkForMissing(zhLlmConfig);
      
      if (missingZh.length > 0) {
        console.error('Missing translations in Chinese file:', missingZh);
      }
      
      expect(missingZh).toHaveLength(0);
    });

    it('should not have any missing translations in English file', () => {
      const checkForMissing = (obj: Record<string, unknown>, path = ''): string[] => {
        const missing: string[] = [];
        
        for (const [key, value] of Object.entries(obj)) {
          const fullPath = path ? `${path}.${key}` : key;
          
          if (value === null || value === undefined || value === '') {
            missing.push(fullPath);
          } else if (typeof value === 'object' && !Array.isArray(value)) {
            missing.push(...checkForMissing(value as Record<string, unknown>, fullPath));
          }
        }
        
        return missing;
      };
      
      const missingEn = checkForMissing(enLlmConfig);
      
      if (missingEn.length > 0) {
        console.error('Missing translations in English file:', missingEn);
      }
      
      expect(missingEn).toHaveLength(0);
    });
  });

  describe('Provider Names', () => {
    it('should have all provider translations', () => {
      const providers = ['openai', 'azure', 'anthropic', 'ollama', 'custom'];
      
      providers.forEach(provider => {
        expect(zhLlmConfig.providers).toHaveProperty(provider);
        expect(enLlmConfig.providers).toHaveProperty(provider);
        expect(typeof zhLlmConfig.providers[provider as keyof typeof zhLlmConfig.providers]).toBe('string');
        expect(typeof enLlmConfig.providers[provider as keyof typeof enLlmConfig.providers]).toBe('string');
      });
    });
  });

  describe('Application Names', () => {
    it('should have all application translations', () => {
      const applications = [
        'structuring',
        'knowledge_graph',
        'ai_assistant',
        'semantic_analysis',
        'rag_agent',
        'text_to_sql',
      ];
      
      applications.forEach(app => {
        expect(zhLlmConfig.applications).toHaveProperty(app);
        expect(enLlmConfig.applications).toHaveProperty(app);
        
        const zhApp = zhLlmConfig.applications[app as keyof typeof zhLlmConfig.applications];
        const enApp = enLlmConfig.applications[app as keyof typeof enLlmConfig.applications];
        
        expect(zhApp).toHaveProperty('name');
        expect(zhApp).toHaveProperty('description');
        expect(enApp).toHaveProperty('name');
        expect(enApp).toHaveProperty('description');
      });
    });
  });
});
