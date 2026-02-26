/**
 * Property 4: 语言缓存与同步
 *
 * Feature: label-studio-integration-enhancement
 * Property 4: 语言缓存与同步
 *
 * Validates: Requirements 2.4
 *
 * For any 语言设置，若在 iframe 未就绪时设置语言，该语言应被缓存为 pendingLanguage；
 * 当 iframe 就绪事件触发后，pendingLanguage 应被同步并清空。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import fc from 'fast-check'
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '@/constants'
import { useLanguageStore } from '@/stores/languageStore'

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generates a random supported language */
const supportedLanguageArb = fc.constantFrom<SupportedLanguage>(...SUPPORTED_LANGUAGES)

/** Generates a non-empty sequence of supported languages */
const languageSequenceArb = fc.array(supportedLanguageArb, { minLength: 1, maxLength: 20 })

// ---------------------------------------------------------------------------
// Property tests
// ---------------------------------------------------------------------------

describe('Feature: label-studio-integration-enhancement, Property 4: 语言缓存与同步', () => {
  beforeEach(() => {
    // Reset store to clean state before each test
    useLanguageStore.setState({
      pendingLanguage: null,
      language: 'zh',
      labelStudioSynced: false,
      isInitialized: false,
    })
  })

  /**
   * **Validates: Requirements 2.4**
   *
   * For any supported language, setPendingLanguage should cache it correctly.
   */
  it('对任意支持的语言，setPendingLanguage 应正确缓存语言', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        // Reset
        useLanguageStore.setState({ pendingLanguage: null })

        // Act
        useLanguageStore.getState().setPendingLanguage(lang)

        // Assert: pendingLanguage should be the set value
        expect(useLanguageStore.getState().pendingLanguage).toBe(lang)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.4**
   *
   * clearPendingLanguage should always reset pendingLanguage to null.
   */
  it('clearPendingLanguage 应始终将 pendingLanguage 清空为 null', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        // Set a pending language first
        useLanguageStore.setState({ pendingLanguage: lang })
        expect(useLanguageStore.getState().pendingLanguage).toBe(lang)

        // Act: clear
        useLanguageStore.getState().clearPendingLanguage()

        // Assert: should be null
        expect(useLanguageStore.getState().pendingLanguage).toBeNull()
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.4**
   *
   * Full cycle: set pending → verify cached → clear → verify null.
   * For any supported language, the cache-then-sync cycle should work correctly.
   */
  it('完整缓存同步周期：设置 → 验证缓存 → 清空 → 验证为 null', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        // 1. Start clean
        useLanguageStore.setState({ pendingLanguage: null })
        expect(useLanguageStore.getState().pendingLanguage).toBeNull()

        // 2. Set pending language (iframe not ready)
        useLanguageStore.getState().setPendingLanguage(lang)
        expect(useLanguageStore.getState().pendingLanguage).toBe(lang)

        // 3. Simulate iframe ready: sync and clear
        useLanguageStore.getState().clearPendingLanguage()
        expect(useLanguageStore.getState().pendingLanguage).toBeNull()
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.4**
   *
   * For any sequence of language changes before iframe is ready,
   * only the last language should be cached as pendingLanguage.
   */
  it('对任意语言变更序列，只有最后一个语言应被缓存为 pendingLanguage', () => {
    fc.assert(
      fc.property(languageSequenceArb, (languages) => {
        // Reset
        useLanguageStore.setState({ pendingLanguage: null })

        // Apply all language changes sequentially
        for (const lang of languages) {
          useLanguageStore.getState().setPendingLanguage(lang)
        }

        // Only the last language should be cached
        const lastLang = languages[languages.length - 1]
        expect(useLanguageStore.getState().pendingLanguage).toBe(lastLang)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.4**
   *
   * Setting pendingLanguage to null should also work via setPendingLanguage(null).
   */
  it('setPendingLanguage(null) 应将缓存清空', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        // Set a pending language
        useLanguageStore.getState().setPendingLanguage(lang)
        expect(useLanguageStore.getState().pendingLanguage).toBe(lang)

        // Clear via setPendingLanguage(null)
        useLanguageStore.getState().setPendingLanguage(null)
        expect(useLanguageStore.getState().pendingLanguage).toBeNull()
      }),
      { numRuns: 100 },
    )
  })
})
