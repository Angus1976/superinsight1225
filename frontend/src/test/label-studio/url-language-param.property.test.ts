/**
 * Property 3: URL 包含语言参数
 *
 * Feature: label-studio-integration-enhancement
 * Property 3: URL 包含语言参数
 *
 * Validates: Requirements 2.3
 *
 * For any 支持的语言和任意 projectId，构建的 Label Studio URL
 * 应包含 `lang=` 参数且值与当前语言设置一致。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import fc from 'fast-check'
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '@/constants'
import { useLanguageStore, getLabelStudioUrl } from '@/stores/languageStore'

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generates a random supported language */
const supportedLanguageArb = fc.constantFrom<SupportedLanguage>(...SUPPORTED_LANGUAGES)

/** Generates a random positive integer projectId */
const projectIdIntArb = fc.integer({ min: 1, max: 999999 })

/** Generates a random string-number projectId */
const projectIdStrArb = fc.integer({ min: 1, max: 999999 }).map(String)

/** Generates either int or string projectId */
const projectIdArb = fc.oneof(projectIdIntArb, projectIdStrArb)

/** Generates a plausible base URL (no trailing slash) */
const baseUrlArb = fc.constantFrom(
  'http://localhost:8080',
  'https://label-studio.example.com',
  'http://10.0.0.1:8080',
  'https://ls.wenshijian.com',
)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function expectedLangParam(lang: SupportedLanguage): string {
  return lang === 'zh' ? 'zh' : 'en'
}

// ---------------------------------------------------------------------------
// Property tests
// ---------------------------------------------------------------------------

describe('Feature: label-studio-integration-enhancement, Property 3: URL 包含语言参数', () => {
  beforeEach(() => {
    // Reset store to a clean state before each test
    useLanguageStore.setState({ language: 'zh', pendingLanguage: null })
  })

  /**
   * **Validates: Requirements 2.3**
   *
   * For any supported language and any projectId, the built URL must
   * contain a `lang=` query parameter matching the current language.
   */
  it('对任意语言和 projectId，URL 应包含正确的 lang 参数', () => {
    fc.assert(
      fc.property(supportedLanguageArb, projectIdArb, baseUrlArb, (lang, projectId, baseUrl) => {
        useLanguageStore.setState({ language: lang })

        const url = getLabelStudioUrl(baseUrl, projectId)
        const parsed = new URL(url)

        expect(parsed.searchParams.get('lang')).toBe(expectedLangParam(lang))
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.3**
   *
   * The URL path must contain `/projects/{projectId}`.
   */
  it('URL 路径应包含 /projects/{projectId}', () => {
    fc.assert(
      fc.property(supportedLanguageArb, projectIdArb, baseUrlArb, (lang, projectId, baseUrl) => {
        useLanguageStore.setState({ language: lang })

        const url = getLabelStudioUrl(baseUrl, projectId)

        expect(url).toContain(`/projects/${projectId}`)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.3**
   *
   * The URL must start with the provided baseUrl.
   */
  it('URL 应以 baseUrl 开头', () => {
    fc.assert(
      fc.property(supportedLanguageArb, projectIdArb, baseUrlArb, (lang, projectId, baseUrl) => {
        useLanguageStore.setState({ language: lang })

        const url = getLabelStudioUrl(baseUrl, projectId)

        expect(url.startsWith(baseUrl)).toBe(true)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.3**
   *
   * The lang parameter value must only be 'zh' or 'en', never anything else.
   */
  it('lang 参数值只能是 zh 或 en', () => {
    fc.assert(
      fc.property(supportedLanguageArb, projectIdIntArb, (lang, projectId) => {
        useLanguageStore.setState({ language: lang })

        const url = getLabelStudioUrl('http://localhost:8080', projectId)
        const parsed = new URL(url)
        const langValue = parsed.searchParams.get('lang')

        expect(['zh', 'en']).toContain(langValue)
      }),
      { numRuns: 100 },
    )
  })
})
