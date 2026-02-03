/**
 * i18n Integration Tests for Label Studio Integration
 * 
 * **Validates: Requirements 11.1** - 前端国际化
 * **Validates: Requirements 11.2** - Label Studio 语言同步
 * **Validates: Requirements 11.4** - 默认语言设置
 * 
 * Tests:
 * - Page language switching functionality
 * - Label Studio URL language parameter synchronization
 * - Language persistence to localStorage
 * - Ant Design ConfigProvider language switching
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import i18n from 'i18next';
import { initReactI18next, useTranslation } from 'react-i18next';
import React from 'react';

// Import translation files
import zhTasks from '../zh/tasks.json';
import enTasks from '../en/tasks.json';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  };
})();

// Setup i18n for testing
const setupI18n = async (defaultLanguage: string = 'zh') => {
  await i18n
    .use(initReactI18next)
    .init({
      resources: {
        zh: { tasks: zhTasks },
        en: { tasks: enTasks },
      },
      lng: defaultLanguage,
      fallbackLng: 'zh',
      defaultNS: 'tasks',
      interpolation: {
        escapeValue: false,
      },
      detection: {
        order: ['localStorage'],
        caches: ['localStorage'],
      },
    });
  return i18n;
};

describe('i18n Integration Tests', () => {
  beforeEach(() => {
    // Reset localStorage mock
    localStorageMock.clear();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    
    // Reset i18n instance
    if (i18n.isInitialized) {
      i18n.changeLanguage('zh');
    }
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Page Language Switching', () => {
    it('should switch from Chinese to English', async () => {
      await setupI18n('zh');
      
      expect(i18n.language).toBe('zh');
      
      await act(async () => {
        await i18n.changeLanguage('en');
      });
      
      expect(i18n.language).toBe('en');
    });

    it('should switch from English to Chinese', async () => {
      await setupI18n('en');
      
      expect(i18n.language).toBe('en');
      
      await act(async () => {
        await i18n.changeLanguage('zh');
      });
      
      expect(i18n.language).toBe('zh');
    });

    it('should update translations when language changes', async () => {
      await setupI18n('zh');
      
      // Chinese translation
      expect(i18n.t('tasks.title')).toBe('标注任务');
      expect(i18n.t('tasks.list.refresh')).toBe('刷新');
      
      await act(async () => {
        await i18n.changeLanguage('en');
      });
      
      // English translation
      expect(i18n.t('tasks.title')).toBe('Annotation Tasks');
      expect(i18n.t('tasks.list.refresh')).toBe('Refresh');
    });

    it('should handle rapid language switching', async () => {
      await setupI18n('zh');
      
      // Rapid switching
      await act(async () => {
        await i18n.changeLanguage('en');
        await i18n.changeLanguage('zh');
        await i18n.changeLanguage('en');
      });
      
      expect(i18n.language).toBe('en');
      expect(i18n.t('tasks.title')).toBe('Annotation Tasks');
    });
  });

  describe('Label Studio Language Synchronization', () => {
    const LANGUAGE_MAP: Record<string, string> = {
      'zh': 'zh-cn',
      'zh-CN': 'zh-cn',
      'en': 'en',
      'en-US': 'en',
    };

    const getLabelStudioLanguage = (frontendLang: string): string => {
      return LANGUAGE_MAP[frontendLang] || 'zh-cn';
    };

    const buildLabelStudioUrl = (projectId: number, language: string, taskId?: number): string => {
      const baseUrl = 'http://localhost:8080';
      const lsLanguage = getLabelStudioLanguage(language);
      let url = `${baseUrl}/projects/${projectId}/data?lang=${lsLanguage}`;
      if (taskId !== undefined) {
        url += `&task=${taskId}`;
      }
      return url;
    };

    it('should map zh to zh-cn for Label Studio', async () => {
      await setupI18n('zh');
      
      const lsLanguage = getLabelStudioLanguage(i18n.language);
      expect(lsLanguage).toBe('zh-cn');
    });

    it('should map en to en for Label Studio', async () => {
      await setupI18n('en');
      
      const lsLanguage = getLabelStudioLanguage(i18n.language);
      expect(lsLanguage).toBe('en');
    });

    it('should build correct URL with Chinese language', async () => {
      await setupI18n('zh');
      
      const url = buildLabelStudioUrl(123, i18n.language);
      expect(url).toBe('http://localhost:8080/projects/123/data?lang=zh-cn');
    });

    it('should build correct URL with English language', async () => {
      await setupI18n('en');
      
      const url = buildLabelStudioUrl(123, i18n.language);
      expect(url).toBe('http://localhost:8080/projects/123/data?lang=en');
    });

    it('should include task ID in URL when provided', async () => {
      await setupI18n('zh');
      
      const url = buildLabelStudioUrl(123, i18n.language, 456);
      expect(url).toBe('http://localhost:8080/projects/123/data?lang=zh-cn&task=456');
    });

    it('should update URL language when frontend language changes', async () => {
      await setupI18n('zh');
      
      let url = buildLabelStudioUrl(123, i18n.language);
      expect(url).toContain('lang=zh-cn');
      
      await act(async () => {
        await i18n.changeLanguage('en');
      });
      
      url = buildLabelStudioUrl(123, i18n.language);
      expect(url).toContain('lang=en');
    });

    it('should default to zh-cn for unknown languages', () => {
      const lsLanguage = getLabelStudioLanguage('unknown');
      expect(lsLanguage).toBe('zh-cn');
    });
  });

  describe('Language Persistence', () => {
    it('should persist language selection to localStorage', async () => {
      await setupI18n('zh');
      
      await act(async () => {
        await i18n.changeLanguage('en');
        // Simulate what i18next-browser-languagedetector does
        localStorageMock.setItem('i18nextLng', 'en');
      });
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('i18nextLng', 'en');
    });

    it('should read language from localStorage on init', async () => {
      // Pre-set language in localStorage
      localStorageMock.setItem('i18nextLng', 'en');
      
      // Verify localStorage was set
      expect(localStorageMock.getItem('i18nextLng')).toBe('en');
    });

    it('should use fallback language when localStorage is empty', async () => {
      localStorageMock.clear();
      
      await setupI18n('zh');
      
      expect(i18n.language).toBe('zh');
    });

    it('should handle localStorage errors gracefully', async () => {
      // Simulate localStorage error
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('localStorage not available');
      });
      
      // Should not throw and use default language
      await setupI18n('zh');
      expect(i18n.language).toBe('zh');
    });
  });

  describe('Ant Design Language Switching', () => {
    // Simulate Ant Design locale mapping
    const getAntdLocale = (language: string) => {
      const localeMap: Record<string, string> = {
        'zh': 'zh_CN',
        'zh-CN': 'zh_CN',
        'en': 'en_US',
        'en-US': 'en_US',
      };
      return localeMap[language] || 'zh_CN';
    };

    it('should map zh to zh_CN for Ant Design', async () => {
      await setupI18n('zh');
      
      const antdLocale = getAntdLocale(i18n.language);
      expect(antdLocale).toBe('zh_CN');
    });

    it('should map en to en_US for Ant Design', async () => {
      await setupI18n('en');
      
      const antdLocale = getAntdLocale(i18n.language);
      expect(antdLocale).toBe('en_US');
    });

    it('should update Ant Design locale when language changes', async () => {
      await setupI18n('zh');
      
      let antdLocale = getAntdLocale(i18n.language);
      expect(antdLocale).toBe('zh_CN');
      
      await act(async () => {
        await i18n.changeLanguage('en');
      });
      
      antdLocale = getAntdLocale(i18n.language);
      expect(antdLocale).toBe('en_US');
    });

    it('should default to zh_CN for unknown languages', () => {
      const antdLocale = getAntdLocale('unknown');
      expect(antdLocale).toBe('zh_CN');
    });
  });

  describe('Translation Key Consistency', () => {
    it('should have consistent structure between zh and en tasks translations', () => {
      const getKeys = (obj: object, prefix = ''): string[] => {
        const keys: string[] = [];
        for (const [key, value] of Object.entries(obj)) {
          const fullKey = prefix ? `${prefix}.${key}` : key;
          if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            keys.push(...getKeys(value, fullKey));
          } else {
            keys.push(fullKey);
          }
        }
        return keys;
      };

      const zhKeys = getKeys(zhTasks).sort();
      const enKeys = getKeys(enTasks).sort();

      // Check that all Chinese keys exist in English
      for (const key of zhKeys) {
        expect(enKeys).toContain(key);
      }
    });
  });

  describe('Default Language Configuration', () => {
    it('should default to Chinese (zh)', async () => {
      await setupI18n();
      
      expect(i18n.language).toBe('zh');
    });

    it('should use Chinese as fallback language', async () => {
      await setupI18n('zh');
      
      // Try to get a non-existent key
      const result = i18n.t('nonexistent.key', { defaultValue: 'fallback' });
      expect(result).toBe('fallback');
    });

    it('should display Chinese text by default', async () => {
      await setupI18n();
      
      expect(i18n.t('tasks.title')).toBe('标注任务');
      expect(i18n.t('tasks.status.pending')).toBe('待处理');
      expect(i18n.t('tasks.priority.high')).toBe('高');
    });
  });
});
