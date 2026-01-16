/**
 * Language Store Property-Based Tests for Label Studio Integration
 * 
 * Property-based tests for universal correctness properties:
 * - Property 24: Label Studio Language Sync
 * - Property 25: Cross-Origin Message Security
 * - Property 26: Language State Consistency
 * 
 * **Feature: i18n-support**
 * **Testing Framework: fast-check**
 * **Minimum Iterations: 100 per property**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fc from 'fast-check';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '@/constants';

// Mock i18n - must be hoisted before imports
vi.mock('@/locales/config', () => ({
  default: {
    changeLanguage: vi.fn(),
    language: 'zh',
  },
}));

import { useLanguageStore, setupLabelStudioLanguageListener, type LabelStudioLanguageMessage } from '../languageStore';
import i18n from '@/locales/config';

const mockChangeLanguage = i18n.changeLanguage as ReturnType<typeof vi.fn>;

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
  } as Response)
);

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Mock document
const mockIframes: HTMLIFrameElement[] = [];
const mockDocument = {
  querySelectorAll: vi.fn((selector: string) => {
    if (selector === 'iframe[data-label-studio]') {
      return mockIframes;
    }
    return [];
  }),
  documentElement: {
    lang: 'zh-CN',
  },
};

Object.defineProperty(global, 'document', {
  value: mockDocument,
  writable: true,
});

// Mock window
const mockWindow = {
  location: {
    origin: 'http://localhost:3000',
  },
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
};

Object.defineProperty(global, 'window', {
  value: mockWindow,
  writable: true,
});

// Property-based test generators
const arbitraryLanguage = (): fc.Arbitrary<SupportedLanguage> =>
  fc.constantFrom(...SUPPORTED_LANGUAGES);

const arbitraryInvalidLanguage = (): fc.Arbitrary<string> =>
  fc.string({ minLength: 1, maxLength: 10 }).filter(
    (lang) => !SUPPORTED_LANGUAGES.includes(lang as SupportedLanguage)
  );

const arbitraryOrigin = (): fc.Arbitrary<string> =>
  fc.oneof(
    fc.constant('http://localhost:3000'),
    fc.constant('http://localhost:8080'),
    fc.constant('http://label-studio:8080'),
    fc.webUrl()
  );

const arbitraryMessageType = (): fc.Arbitrary<string> =>
  fc.oneof(
    fc.constant('setLanguage'),
    fc.constant('languageChanged'),
    fc.string({ minLength: 1, maxLength: 20 })
  );

describe('Language Store - Label Studio Integration Property Tests', () => {
  beforeEach(() => {
    // Reset store
    useLanguageStore.setState({
      language: 'zh',
      isInitialized: false,
      labelStudioSynced: false,
    });

    // Clear mocks
    vi.clearAllMocks();
    mockLocalStorage.clear();
    mockIframes.length = 0;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Property 24: Label Studio Language Sync', () => {
    /**
     * **Property 24: Label Studio Language Sync**
     * 
     * *For any* language change in SuperInsight, the system should synchronize 
     * the language setting to Label Studio iframe via postMessage.
     * 
     * **Validates: Requirements 12.1**
     */
    it('should sync language to all Label Studio iframes when language changes', () => {
      fc.assert(
        fc.property(
          arbitraryLanguage(),
          fc.integer({ min: 1, max: 5 }), // Number of iframes
          (language, iframeCount) => {
            // Setup: Create mock iframes
            mockIframes.length = 0;
            const postMessageMocks: Array<ReturnType<typeof vi.fn>> = [];
            
            for (let i = 0; i < iframeCount; i++) {
              const postMessageMock = vi.fn();
              postMessageMocks.push(postMessageMock);
              
              const mockIframe = {
                contentWindow: {
                  postMessage: postMessageMock,
                },
                dataset: {
                  labelStudio: 'true',
                },
              } as unknown as HTMLIFrameElement;
              
              mockIframes.push(mockIframe);
            }

            // Action: Change language
            useLanguageStore.getState().setLanguage(language);

            // Assertion: All iframes should receive postMessage
            postMessageMocks.forEach((postMessageMock) => {
              expect(postMessageMock).toHaveBeenCalled();
              
              // Check that at least one call contains the correct message
              const calls = postMessageMock.mock.calls;
              const hasCorrectMessage = calls.some((call) => {
                const message = call[0] as LabelStudioLanguageMessage;
                return (
                  message.type === 'setLanguage' &&
                  message.lang === language &&
                  message.source === 'superinsight'
                );
              });
              
              expect(hasCorrectMessage).toBe(true);
            });

            // Verify labelStudioSynced flag is set
            expect(useLanguageStore.getState().labelStudioSynced).toBe(true);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should handle missing iframes gracefully', () => {
      fc.assert(
        fc.property(arbitraryLanguage(), (language) => {
          // Setup: No iframes
          mockIframes.length = 0;

          // Action: Change language
          useLanguageStore.getState().setLanguage(language);

          // Assertion: Should still mark as synced
          expect(useLanguageStore.getState().labelStudioSynced).toBe(true);
          expect(useLanguageStore.getState().language).toBe(language);
        }),
        { numRuns: 100 }
      );
    });

    it('should sync language immediately when syncToLabelStudio is called', () => {
      fc.assert(
        fc.property(
          arbitraryLanguage(),
          fc.integer({ min: 1, max: 3 }),
          (language, iframeCount) => {
            // Setup: Set language first
            useLanguageStore.setState({ language, labelStudioSynced: false });

            // Create mock iframes
            mockIframes.length = 0;
            const postMessageMocks: Array<ReturnType<typeof vi.fn>> = [];
            
            for (let i = 0; i < iframeCount; i++) {
              const postMessageMock = vi.fn();
              postMessageMocks.push(postMessageMock);
              
              const mockIframe = {
                contentWindow: {
                  postMessage: postMessageMock,
                },
                dataset: {
                  labelStudio: 'true',
                },
              } as unknown as HTMLIFrameElement;
              
              mockIframes.push(mockIframe);
            }

            // Action: Sync to Label Studio
            useLanguageStore.getState().syncToLabelStudio();

            // Assertion: All iframes should receive the message
            postMessageMocks.forEach((postMessageMock) => {
              expect(postMessageMock).toHaveBeenCalled();
            });

            expect(useLanguageStore.getState().labelStudioSynced).toBe(true);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 25: Cross-Origin Message Security', () => {
    /**
     * **Property 25: Cross-Origin Message Security**
     * 
     * *For any* postMessage communication with Label Studio, the system should 
     * validate message origin and type before processing.
     * 
     * **Validates: Requirements 12.2**
     */
    it('should only process messages from allowed origins', () => {
      fc.assert(
        fc.property(
          arbitraryOrigin(),
          arbitraryLanguage(),
          (origin, language) => {
            // Setup: Create message event
            const allowedOrigins = [
              'http://localhost:3000',
              'http://localhost:8080',
              'http://label-studio:8080',
            ];

            const message: LabelStudioLanguageMessage = {
              type: 'languageChanged',
              lang: language,
              source: 'label-studio',
            };

            const event = {
              origin,
              data: message,
            } as MessageEvent;

            const initialLanguage = useLanguageStore.getState().language;

            // Action: Handle message
            useLanguageStore.getState().handleLabelStudioMessage(event);

            // Assertion: Language should only change if origin is allowed
            const isAllowedOrigin = allowedOrigins.includes(origin);
            const finalLanguage = useLanguageStore.getState().language;

            if (isAllowedOrigin && language !== initialLanguage) {
              expect(finalLanguage).toBe(language);
            } else if (!isAllowedOrigin) {
              expect(finalLanguage).toBe(initialLanguage);
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should validate message type before processing', () => {
      fc.assert(
        fc.property(
          arbitraryMessageType(),
          arbitraryLanguage(),
          (messageType, language) => {
            // Setup: Create message with various types
            const message = {
              type: messageType,
              lang: language,
              source: 'label-studio',
            };

            const event = {
              origin: 'http://localhost:8080',
              data: message,
            } as MessageEvent;

            const initialLanguage = useLanguageStore.getState().language;

            // Action: Handle message
            useLanguageStore.getState().handleLabelStudioMessage(event);

            // Assertion: Language should only change for valid message type
            const finalLanguage = useLanguageStore.getState().language;

            if (messageType === 'languageChanged' && language !== initialLanguage) {
              expect(finalLanguage).toBe(language);
            } else if (messageType !== 'languageChanged') {
              expect(finalLanguage).toBe(initialLanguage);
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should validate language code in incoming messages', () => {
      fc.assert(
        fc.property(
          fc.oneof(arbitraryLanguage(), arbitraryInvalidLanguage()),
          (language) => {
            // Setup: Create message with potentially invalid language
            const message = {
              type: 'languageChanged',
              lang: language,
              source: 'label-studio',
            };

            const event = {
              origin: 'http://localhost:8080',
              data: message,
            } as MessageEvent;

            const initialLanguage = useLanguageStore.getState().language;

            // Action: Handle message
            useLanguageStore.getState().handleLabelStudioMessage(event);

            // Assertion: Language should only change if valid
            const finalLanguage = useLanguageStore.getState().language;
            const isValidLanguage = SUPPORTED_LANGUAGES.includes(language as SupportedLanguage);

            if (isValidLanguage && language !== initialLanguage) {
              expect(finalLanguage).toBe(language);
            } else if (!isValidLanguage) {
              expect(finalLanguage).toBe(initialLanguage);
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should ignore messages without proper source field', () => {
      fc.assert(
        fc.property(arbitraryLanguage(), (language) => {
          // Setup: Create message without source field
          const message = {
            type: 'languageChanged',
            lang: language,
            // Missing source field
          };

          const event = {
            origin: 'http://localhost:8080',
            data: message,
          } as MessageEvent;

          const initialLanguage = useLanguageStore.getState().language;

          // Action: Handle message
          useLanguageStore.getState().handleLabelStudioMessage(event);

          // Assertion: Language should not change without proper source
          const finalLanguage = useLanguageStore.getState().language;
          expect(finalLanguage).toBe(initialLanguage);
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 26: Language State Consistency', () => {
    /**
     * **Property 26: Language State Consistency**
     * 
     * *For any* language change, the language state should be consistent across 
     * Zustand store, localStorage, react-i18next, and Label Studio.
     * 
     * **Validates: Requirements 12.3**
     */
    it('should maintain consistency across all language storage mechanisms', () => {
      fc.assert(
        fc.property(arbitraryLanguage(), (language) => {
          // Action: Change language
          useLanguageStore.getState().setLanguage(language);

          // Assertion 1: Zustand store should be updated
          expect(useLanguageStore.getState().language).toBe(language);

          // Assertion 2: localStorage should be updated
          const storedData = mockLocalStorage.getItem('language-storage');
          if (storedData) {
            const parsed = JSON.parse(storedData);
            expect(parsed.state.language).toBe(language);
          }

          // Assertion 3: react-i18next should be updated
          expect(mockChangeLanguage).toHaveBeenCalledWith(language);

          // Assertion 4: document.documentElement.lang should be updated
          const expectedLang = language === 'zh' ? 'zh-CN' : 'en';
          expect(document.documentElement.lang).toBe(expectedLang);

          // Assertion 5: Backend API should be notified
          expect(global.fetch).toHaveBeenCalledWith(
            '/api/settings/language',
            expect.objectContaining({
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ language }),
            })
          );
        }),
        { numRuns: 100 }
      );
    });

    it('should handle invalid languages by falling back to default', () => {
      fc.assert(
        fc.property(arbitraryInvalidLanguage(), (invalidLanguage) => {
          // Setup: Start with a known language
          useLanguageStore.setState({ language: 'en' });

          // Action: Try to set invalid language
          useLanguageStore.getState().setLanguage(invalidLanguage as SupportedLanguage);

          // Assertion: Should fallback to default language (zh)
          expect(useLanguageStore.getState().language).toBe('zh');
        }),
        { numRuns: 100 }
      );
    });

    it('should prevent infinite loops when receiving language changes from Label Studio', () => {
      fc.assert(
        fc.property(arbitraryLanguage(), (language) => {
          // Setup: Set initial language
          useLanguageStore.setState({ language });

          // Create message with same language
          const message: LabelStudioLanguageMessage = {
            type: 'languageChanged',
            lang: language,
            source: 'label-studio',
          };

          const event = {
            origin: 'http://localhost:8080',
            data: message,
          } as MessageEvent;

          // Clear previous calls
          mockChangeLanguage.mockClear();

          // Action: Handle message with same language
          useLanguageStore.getState().handleLabelStudioMessage(event);

          // Assertion: Should not trigger language change if already set
          expect(mockChangeLanguage).not.toHaveBeenCalled();
        }),
        { numRuns: 100 }
      );
    });

    it('should maintain state consistency during rapid language switches', () => {
      fc.assert(
        fc.property(
          fc.array(arbitraryLanguage(), { minLength: 2, maxLength: 10 }),
          (languages) => {
            // Clear mock before each property test iteration
            mockChangeLanguage.mockClear();
            
            // Action: Rapidly switch languages
            languages.forEach((language) => {
              useLanguageStore.getState().setLanguage(language);
            });

            // Assertion: Final state should match last language
            const lastLanguage = languages[languages.length - 1];
            expect(useLanguageStore.getState().language).toBe(lastLanguage);

            // Assertion: react-i18next should have been called for each change
            expect(mockChangeLanguage).toHaveBeenCalledTimes(languages.length);
            expect(mockChangeLanguage).toHaveBeenLastCalledWith(lastLanguage);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should initialize language correctly on app startup', () => {
      fc.assert(
        fc.property(arbitraryLanguage(), (language) => {
          // Setup: Store language in localStorage
          mockLocalStorage.setItem(
            'language-storage',
            JSON.stringify({
              state: { language },
              version: 0,
            })
          );

          // Reset store to simulate app restart
          useLanguageStore.setState({
            language: 'zh',
            isInitialized: false,
            labelStudioSynced: false,
          });

          // Action: Initialize language
          useLanguageStore.getState().initializeLanguage();

          // Assertion: Should be marked as initialized
          expect(useLanguageStore.getState().isInitialized).toBe(true);

          // Assertion: document.documentElement.lang should be set
          const expectedLang = useLanguageStore.getState().language === 'zh' ? 'zh-CN' : 'en';
          expect(document.documentElement.lang).toBe(expectedLang);
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('Integration: setupLabelStudioLanguageListener', () => {
    it('should setup and cleanup message listener correctly', () => {
      fc.assert(
        fc.property(fc.constant(null), () => {
          // Action: Setup listener
          const cleanup = setupLabelStudioLanguageListener();

          // Assertion: addEventListener should be called
          expect(mockWindow.addEventListener).toHaveBeenCalledWith(
            'message',
            expect.any(Function)
          );

          // Action: Cleanup
          cleanup();

          // Assertion: removeEventListener should be called
          expect(mockWindow.removeEventListener).toHaveBeenCalledWith(
            'message',
            expect.any(Function)
          );
        }),
        { numRuns: 100 }
      );
    });
  });
});
