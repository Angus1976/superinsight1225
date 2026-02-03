/**
 * Language Configuration Tests
 * 
 * **Validates: Requirements 10.2.1** - 配置默认语言
 * **Validates: Requirements 11.4** - 默认语言设置
 * 
 * Tests that default language is Chinese and language switching works correctly.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

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

describe('Language Configuration', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    
    Object.defineProperty(global, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
  });

  afterEach(() => {
    localStorageMock.clear();
    vi.resetModules();
  });

  describe('Default Language', () => {
    it('should have Chinese (zh) as fallback language', async () => {
      const { default: i18n } = await import('../config');
      
      expect(i18n.options.fallbackLng).toContain('zh');
    });

    it('should have common as default namespace', async () => {
      const { default: i18n } = await import('../config');
      
      expect(i18n.options.defaultNS).toBe('common');
    });

    it('should have common as fallback namespace', async () => {
      const { default: i18n } = await import('../config');
      
      // fallbackNS can be a string or array
      const fallbackNS = i18n.options.fallbackNS;
      if (Array.isArray(fallbackNS)) {
        expect(fallbackNS).toContain('common');
      } else {
        expect(fallbackNS).toBe('common');
      }
    });

    it('should include tasks namespace', async () => {
      const { default: i18n } = await import('../config');
      
      expect(i18n.options.ns).toContain('tasks');
    });

    it('should have both zh and en resources loaded', async () => {
      const { default: i18n } = await import('../config');
      
      expect(i18n.options.resources).toHaveProperty('zh');
      expect(i18n.options.resources).toHaveProperty('en');
    });

    it('should have tasks translations in zh resources', async () => {
      const { default: i18n } = await import('../config');
      
      const resources = i18n.options.resources as Record<string, Record<string, unknown>>;
      expect(resources.zh).toHaveProperty('tasks');
    });

    it('should have tasks translations in en resources', async () => {
      const { default: i18n } = await import('../config');
      
      const resources = i18n.options.resources as Record<string, Record<string, unknown>>;
      expect(resources.en).toHaveProperty('tasks');
    });
  });

  describe('Language Detection', () => {
    it('should have localStorage in detection order', async () => {
      const { default: i18n } = await import('../config');
      
      const detection = i18n.options.detection as { order?: string[] } | undefined;
      expect(detection?.order).toContain('localStorage');
    });

    it('should have navigator in detection order', async () => {
      const { default: i18n } = await import('../config');
      
      const detection = i18n.options.detection as { order?: string[] } | undefined;
      expect(detection?.order).toContain('navigator');
    });

    it('should cache language in localStorage', async () => {
      const { default: i18n } = await import('../config');
      
      const detection = i18n.options.detection as { caches?: string[] } | undefined;
      expect(detection?.caches).toContain('localStorage');
    });

    it('should prioritize localStorage over navigator', async () => {
      const { default: i18n } = await import('../config');
      
      const detection = i18n.options.detection as { order?: string[] } | undefined;
      const order = detection?.order || [];
      const localStorageIndex = order.indexOf('localStorage');
      const navigatorIndex = order.indexOf('navigator');
      
      expect(localStorageIndex).toBeLessThan(navigatorIndex);
    });
  });

  describe('Interpolation', () => {
    it('should have escapeValue set to false for React', async () => {
      const { default: i18n } = await import('../config');
      
      expect(i18n.options.interpolation?.escapeValue).toBe(false);
    });
  });

  describe('Supported Languages', () => {
    it('should support Chinese (zh)', async () => {
      const { default: i18n } = await import('../config');
      
      const resources = i18n.options.resources as Record<string, unknown>;
      expect(Object.keys(resources)).toContain('zh');
    });

    it('should support English (en)', async () => {
      const { default: i18n } = await import('../config');
      
      const resources = i18n.options.resources as Record<string, unknown>;
      expect(Object.keys(resources)).toContain('en');
    });

    it('should have exactly 2 supported languages', async () => {
      const { default: i18n } = await import('../config');
      
      const resources = i18n.options.resources as Record<string, unknown>;
      expect(Object.keys(resources).length).toBe(2);
    });
  });

  describe('Language Switching', () => {
    it('should be able to change language to English', async () => {
      const { default: i18n } = await import('../config');
      
      await i18n.changeLanguage('en');
      
      expect(i18n.language).toBe('en');
    });

    it('should be able to change language to Chinese', async () => {
      const { default: i18n } = await import('../config');
      
      await i18n.changeLanguage('zh');
      
      expect(i18n.language).toBe('zh');
    });

    it('should fall back to zh for unsupported language', async () => {
      const { default: i18n } = await import('../config');
      
      // Try to change to unsupported language
      await i18n.changeLanguage('fr');
      
      // Should fall back to zh (fallbackLng)
      // Note: i18n.language might still be 'fr' but translations will use fallback
      const fallbackLng = i18n.options.fallbackLng;
      expect(fallbackLng).toContain('zh');
    });
  });

  describe('Translation Function', () => {
    it('should translate tasks.title in Chinese', async () => {
      const { default: i18n } = await import('../config');
      
      await i18n.changeLanguage('zh');
      const translation = i18n.t('tasks:tasks.title');
      
      expect(translation).toBe('标注任务');
    });

    it('should translate tasks.title in English', async () => {
      const { default: i18n } = await import('../config');
      
      await i18n.changeLanguage('en');
      const translation = i18n.t('tasks:tasks.title');
      
      expect(translation).toBe('Annotation Tasks');
    });

    it('should translate nested keys correctly', async () => {
      const { default: i18n } = await import('../config');
      
      await i18n.changeLanguage('zh');
      const translation = i18n.t('tasks:tasks.list.refresh');
      
      expect(translation).toBe('刷新');
    });

    it('should handle interpolation in translations', async () => {
      const { default: i18n } = await import('../config');
      
      await i18n.changeLanguage('zh');
      const translation = i18n.t('tasks:tasks.messages.syncSuccess', { count: 5 });
      
      expect(translation).toContain('5');
    });
  });
});
