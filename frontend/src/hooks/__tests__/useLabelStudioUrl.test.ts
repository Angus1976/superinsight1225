/**
 * Tests for useLabelStudioUrl hook
 * 
 * **Validates: Requirements 11.2** - Label Studio 语言同步
 * **Validates: Requirements 2.1** - URL 路由配置
 * 
 * Tests the URL building logic for Label Studio integration,
 * including language parameter synchronization.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// Mock react-i18next
const mockI18n = {
  language: 'zh',
};

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: mockI18n,
  }),
}));

// Mock import.meta.env
const originalEnv = import.meta.env;

describe('useLabelStudioUrl', () => {
  beforeEach(() => {
    // Reset language to default
    mockI18n.language = 'zh';
    // Reset env
    vi.stubGlobal('import.meta', {
      env: {
        ...originalEnv,
        VITE_LABEL_STUDIO_URL: undefined,
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('buildLabelStudioUrl', () => {
    it('should build URL with default base URL when env not set', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).toContain('http://localhost:8080');
      expect(url).toContain('/projects/123/data');
    });

    it('should include /data endpoint for data manager', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(456);
      
      expect(url).toContain('/projects/456/data');
      expect(url).not.toMatch(/\/projects\/456(?!\/)$/);
    });

    it('should include language parameter for Chinese (zh)', async () => {
      mockI18n.language = 'zh';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).toContain('lang=zh-cn');
    });

    it('should include language parameter for Chinese (zh-CN)', async () => {
      mockI18n.language = 'zh-CN';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).toContain('lang=zh-cn');
    });

    it('should include language parameter for English (en)', async () => {
      mockI18n.language = 'en';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).toContain('lang=en');
    });

    it('should include language parameter for English (en-US)', async () => {
      mockI18n.language = 'en-US';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).toContain('lang=en');
    });

    it('should default to zh-cn for unknown language', async () => {
      mockI18n.language = 'unknown';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).toContain('lang=zh-cn');
    });

    it('should include task ID when provided', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123, 456);
      
      expect(url).toContain('task=456');
    });

    it('should not include task parameter when taskId is undefined', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      expect(url).not.toContain('task=');
    });

    it('should build correct full URL format', async () => {
      mockI18n.language = 'zh';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123, 456);
      
      // Expected format: http://localhost:8080/projects/123/data?lang=zh-cn&task=456
      expect(url).toBe('http://localhost:8080/projects/123/data?lang=zh-cn&task=456');
    });

    it('should handle zero project ID', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(0);
      
      expect(url).toContain('/projects/0/data');
    });

    it('should handle large project IDs', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(999999999);
      
      expect(url).toContain('/projects/999999999/data');
    });

    it('should handle zero task ID', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123, 0);
      
      // Zero task ID should still be included
      expect(url).toContain('task=0');
    });

    it('should not include task parameter when taskId is null', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123, null as unknown as number);
      
      expect(url).not.toContain('task=');
    });
  });

  describe('buildProjectSettingsUrl', () => {
    it('should build settings URL with language parameter', async () => {
      mockI18n.language = 'en';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildProjectSettingsUrl(123);
      
      expect(url).toContain('/projects/123/settings');
      expect(url).toContain('lang=en');
    });

    it('should build correct full settings URL format', async () => {
      mockI18n.language = 'zh';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildProjectSettingsUrl(123);
      
      expect(url).toBe('http://localhost:8080/projects/123/settings?lang=zh-cn');
    });
  });

  describe('buildLoginUrl', () => {
    it('should build login URL with language parameter', async () => {
      mockI18n.language = 'zh';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLoginUrl();
      
      expect(url).toContain('/user/login');
      expect(url).toContain('lang=zh-cn');
    });

    it('should build correct full login URL format', async () => {
      mockI18n.language = 'en';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLoginUrl();
      
      expect(url).toBe('http://localhost:8080/user/login?lang=en');
    });
  });

  describe('getLabelStudioLanguage', () => {
    it('should return zh-cn for Chinese', async () => {
      mockI18n.language = 'zh';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      expect(result.current.getLabelStudioLanguage()).toBe('zh-cn');
    });

    it('should return en for English', async () => {
      mockI18n.language = 'en';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      expect(result.current.getLabelStudioLanguage()).toBe('en');
    });

    it('should return zh-tw for Traditional Chinese', async () => {
      mockI18n.language = 'zh-TW';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      expect(result.current.getLabelStudioLanguage()).toBe('zh-tw');
    });

    it('should return en for en-GB', async () => {
      mockI18n.language = 'en-GB';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      expect(result.current.getLabelStudioLanguage()).toBe('en');
    });

    it('should return default zh-cn for empty language', async () => {
      mockI18n.language = '';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      expect(result.current.getLabelStudioLanguage()).toBe('zh-cn');
    });
  });

  describe('getBaseUrl', () => {
    it('should return default URL when env not set', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      expect(result.current.getBaseUrl()).toBe('http://localhost:8080');
    });
  });

  describe('URL format validation', () => {
    it('should produce valid URL format', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      
      // Should be a valid URL
      expect(() => new URL(url)).not.toThrow();
    });

    it('should have correct query parameter format', async () => {
      mockI18n.language = 'zh';
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123, 456);
      const urlObj = new URL(url);
      
      expect(urlObj.searchParams.get('lang')).toBe('zh-cn');
      expect(urlObj.searchParams.get('task')).toBe('456');
    });

    it('should have correct pathname format', async () => {
      const { useLabelStudioUrl } = await import('../useLabelStudioUrl');
      const { result } = renderHook(() => useLabelStudioUrl());
      
      const url = result.current.buildLabelStudioUrl(123);
      const urlObj = new URL(url);
      
      expect(urlObj.pathname).toBe('/projects/123/data');
    });
  });
});
