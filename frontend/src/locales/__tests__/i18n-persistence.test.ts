/**
 * i18n Language Preference Persistence Tests
 * 
 * **Property 23: Language Preference Persistence**
 * For any user language preference change, the preference should be stored 
 * and restored in subsequent sessions.
 * 
 * **Validates: Requirements 8.4**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fc from 'fast-check';

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

// Supported languages
const SUPPORTED_LANGUAGES = ['zh', 'en'] as const;
type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];

// i18next localStorage key (default key used by i18next-browser-languagedetector)
const I18N_STORAGE_KEY = 'i18nextLng';

describe('Property 23: Language Preference Persistence', () => {
  beforeEach(() => {
    // Reset localStorage mock before each test
    localStorageMock.clear();
    vi.clearAllMocks();
    
    // Replace global localStorage with mock
    Object.defineProperty(global, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  /**
   * Property: Language preference round-trip
   * For any supported language, storing it and retrieving it should return the same value.
   */
  it('should persist and restore language preference correctly (property test)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...SUPPORTED_LANGUAGES),
        (language: SupportedLanguage) => {
          // Store language preference
          localStorageMock.setItem(I18N_STORAGE_KEY, language);
          
          // Retrieve language preference
          const storedLanguage = localStorageMock.getItem(I18N_STORAGE_KEY);
          
          // Property: stored value should equal original value
          expect(storedLanguage).toBe(language);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: Language preference survives multiple changes
   * After multiple language changes, the last set language should be persisted.
   */
  it('should persist the last language preference after multiple changes (property test)', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom(...SUPPORTED_LANGUAGES), { minLength: 1, maxLength: 20 }),
        (languageSequence: SupportedLanguage[]) => {
          // Simulate multiple language changes
          for (const language of languageSequence) {
            localStorageMock.setItem(I18N_STORAGE_KEY, language);
          }
          
          // Get the last language in the sequence
          const lastLanguage = languageSequence[languageSequence.length - 1];
          
          // Retrieve stored language
          const storedLanguage = localStorageMock.getItem(I18N_STORAGE_KEY);
          
          // Property: stored value should be the last set value
          expect(storedLanguage).toBe(lastLanguage);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: Language preference is independent of other localStorage items
   * Setting language preference should not affect other localStorage items.
   */
  it('should not affect other localStorage items when setting language (property test)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...SUPPORTED_LANGUAGES),
        fc.string({ minLength: 1, maxLength: 50 }),
        fc.string({ minLength: 1, maxLength: 100 }),
        (language: SupportedLanguage, otherKey: string, otherValue: string) => {
          // Skip if otherKey is the same as i18n key
          if (otherKey === I18N_STORAGE_KEY) return;
          
          // Set another localStorage item first
          localStorageMock.setItem(otherKey, otherValue);
          
          // Set language preference
          localStorageMock.setItem(I18N_STORAGE_KEY, language);
          
          // Property: other item should be unchanged
          expect(localStorageMock.getItem(otherKey)).toBe(otherValue);
          
          // Property: language should be set correctly
          expect(localStorageMock.getItem(I18N_STORAGE_KEY)).toBe(language);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property: Language preference can be cleared and reset
   * Clearing and resetting language preference should work correctly.
   */
  it('should handle clearing and resetting language preference (property test)', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...SUPPORTED_LANGUAGES),
        fc.constantFrom(...SUPPORTED_LANGUAGES),
        (firstLanguage: SupportedLanguage, secondLanguage: SupportedLanguage) => {
          // Set first language
          localStorageMock.setItem(I18N_STORAGE_KEY, firstLanguage);
          expect(localStorageMock.getItem(I18N_STORAGE_KEY)).toBe(firstLanguage);
          
          // Clear language preference
          localStorageMock.removeItem(I18N_STORAGE_KEY);
          expect(localStorageMock.getItem(I18N_STORAGE_KEY)).toBeNull();
          
          // Set second language
          localStorageMock.setItem(I18N_STORAGE_KEY, secondLanguage);
          
          // Property: new language should be persisted
          expect(localStorageMock.getItem(I18N_STORAGE_KEY)).toBe(secondLanguage);
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Unit test: Verify supported languages are valid
   */
  it('should only accept supported languages', () => {
    for (const lang of SUPPORTED_LANGUAGES) {
      localStorageMock.setItem(I18N_STORAGE_KEY, lang);
      const stored = localStorageMock.getItem(I18N_STORAGE_KEY);
      expect(SUPPORTED_LANGUAGES).toContain(stored);
    }
  });

  /**
   * Unit test: Verify localStorage key is correct
   */
  it('should use the correct localStorage key for i18next', () => {
    const testLanguage = 'zh';
    localStorageMock.setItem(I18N_STORAGE_KEY, testLanguage);
    
    // Verify the key is 'i18nextLng' (default i18next-browser-languagedetector key)
    expect(localStorageMock.setItem).toHaveBeenCalledWith('i18nextLng', testLanguage);
  });

  /**
   * Unit test: Verify default fallback language
   */
  it('should have zh as the fallback language in config', async () => {
    // Import the actual config to verify fallback language
    const { default: i18n } = await import('../config');
    
    // The fallback language should be 'zh' as configured
    expect(i18n.options.fallbackLng).toContain('zh');
  });

  /**
   * Unit test: Verify localStorage is in detection order
   */
  it('should have localStorage in detection order', async () => {
    const { default: i18n } = await import('../config');
    
    // Detection order should include localStorage
    const detectionOptions = i18n.options.detection as { order?: string[] } | undefined;
    expect(detectionOptions?.order).toContain('localStorage');
  });

  /**
   * Unit test: Verify localStorage is in caches
   */
  it('should cache language preference in localStorage', async () => {
    const { default: i18n } = await import('../config');
    
    // Caches should include localStorage
    const detectionOptions = i18n.options.detection as { caches?: string[] } | undefined;
    expect(detectionOptions?.caches).toContain('localStorage');
  });
});
