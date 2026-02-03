/**
 * Tests for Label Studio constants
 * **Validates: Requirements 2.1** - URL 路由配置
 */

import { describe, it, expect } from 'vitest';
import {
  LABEL_STUDIO_LANGUAGE_MAP,
  LABEL_STUDIO_DEFAULT_LANGUAGE,
  LABEL_STUDIO_DEFAULT_URL,
  LABEL_STUDIO_ENDPOINTS,
  LABEL_STUDIO_ERROR_TYPES,
  LABEL_STUDIO_SYNC_STATUS,
  LABEL_STUDIO_WINDOW_OPTIONS,
  LABEL_STUDIO_API_PATHS,
  ANNOTATION_TYPES,
} from '../labelStudio';

describe('Label Studio Constants', () => {
  describe('LABEL_STUDIO_LANGUAGE_MAP', () => {
    it('should map zh to zh-cn', () => {
      expect(LABEL_STUDIO_LANGUAGE_MAP['zh']).toBe('zh-cn');
    });

    it('should map en to en', () => {
      expect(LABEL_STUDIO_LANGUAGE_MAP['en']).toBe('en');
    });

    it('should return undefined for unknown language', () => {
      expect(LABEL_STUDIO_LANGUAGE_MAP['unknown']).toBeUndefined();
    });
  });

  describe('LABEL_STUDIO_DEFAULT_LANGUAGE', () => {
    it('should be zh-cn', () => {
      expect(LABEL_STUDIO_DEFAULT_LANGUAGE).toBe('zh-cn');
    });
  });

  describe('LABEL_STUDIO_DEFAULT_URL', () => {
    it('should be http://localhost:8080', () => {
      expect(LABEL_STUDIO_DEFAULT_URL).toBe('http://localhost:8080');
    });
  });

  describe('LABEL_STUDIO_ENDPOINTS', () => {
    it('should have DATA_MANAGER endpoint as /data', () => {
      expect(LABEL_STUDIO_ENDPOINTS.DATA_MANAGER).toBe('/data');
    });

    it('should have SETTINGS endpoint as /settings', () => {
      expect(LABEL_STUDIO_ENDPOINTS.SETTINGS).toBe('/settings');
    });

    it('should have LOGIN endpoint as /user/login', () => {
      expect(LABEL_STUDIO_ENDPOINTS.LOGIN).toBe('/user/login');
    });
  });

  describe('LABEL_STUDIO_ERROR_TYPES', () => {
    it('should have NOT_FOUND error type', () => {
      expect(LABEL_STUDIO_ERROR_TYPES.NOT_FOUND).toBe('not_found');
    });

    it('should have AUTH error type', () => {
      expect(LABEL_STUDIO_ERROR_TYPES.AUTH).toBe('auth');
    });

    it('should have NETWORK error type', () => {
      expect(LABEL_STUDIO_ERROR_TYPES.NETWORK).toBe('network');
    });

    it('should have SERVICE error type', () => {
      expect(LABEL_STUDIO_ERROR_TYPES.SERVICE).toBe('service');
    });

    it('should have UNKNOWN error type', () => {
      expect(LABEL_STUDIO_ERROR_TYPES.UNKNOWN).toBe('unknown');
    });
  });

  describe('LABEL_STUDIO_SYNC_STATUS', () => {
    it('should have SYNCED status', () => {
      expect(LABEL_STUDIO_SYNC_STATUS.SYNCED).toBe('synced');
    });

    it('should have PENDING status', () => {
      expect(LABEL_STUDIO_SYNC_STATUS.PENDING).toBe('pending');
    });

    it('should have FAILED status', () => {
      expect(LABEL_STUDIO_SYNC_STATUS.FAILED).toBe('failed');
    });
  });

  describe('LABEL_STUDIO_WINDOW_OPTIONS', () => {
    it('should be noopener,noreferrer', () => {
      expect(LABEL_STUDIO_WINDOW_OPTIONS).toBe('noopener,noreferrer');
    });
  });

  describe('LABEL_STUDIO_API_PATHS', () => {
    it('should have PROJECTS path', () => {
      expect(LABEL_STUDIO_API_PATHS.PROJECTS).toBe('/api/label-studio/projects');
    });

    it('should generate correct PROJECT path', () => {
      expect(LABEL_STUDIO_API_PATHS.PROJECT(123)).toBe('/api/label-studio/projects/123');
    });

    it('should generate correct PROJECT_TASKS path', () => {
      expect(LABEL_STUDIO_API_PATHS.PROJECT_TASKS(123)).toBe('/api/label-studio/projects/123/tasks');
    });
  });

  describe('ANNOTATION_TYPES', () => {
    it('should have TEXT_CLASSIFICATION type', () => {
      expect(ANNOTATION_TYPES.TEXT_CLASSIFICATION).toBe('text_classification');
    });

    it('should have NER type', () => {
      expect(ANNOTATION_TYPES.NER).toBe('ner');
    });
  });
});
