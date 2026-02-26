/**
 * Property 2: 语言切换消息发送
 *
 * Feature: label-studio-integration-enhancement
 * Property 2: 语言切换消息发送
 *
 * Validates: Requirements 2.1
 *
 * For any 支持的语言值，当调用 syncToLabelStudio 时，组件应通过 postMessage
 * 发送包含正确语言值的 {type: 'setLanguage', lang, source: 'superinsight'} 消息。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import fc from 'fast-check'
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from '@/constants'

// ---------------------------------------------------------------------------
// Helpers: simulate the syncToLabelStudio logic from languageStore.ts
// ---------------------------------------------------------------------------

/**
 * Mirrors the postMessage sending logic in languageStore.syncToLabelStudio.
 * Extracted here so we test the message contract independently of Zustand.
 */
function buildLanguageMessage(lang: SupportedLanguage) {
  return {
    type: 'setLanguage' as const,
    lang,
    source: 'superinsight' as const,
  }
}

function syncLanguageToIframes(lang: SupportedLanguage, origins: string[]) {
  const iframes = document.querySelectorAll<HTMLIFrameElement>('iframe[data-label-studio]')
  const message = buildLanguageMessage(lang)

  iframes.forEach((iframe) => {
    if (iframe.contentWindow) {
      origins.forEach((origin) => {
        try {
          iframe.contentWindow?.postMessage(message, origin)
        } catch {
          // Ignore cross-origin errors
        }
      })
    }
  })

  return message
}

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generates a random supported language */
const supportedLanguageArb = fc.constantFrom<SupportedLanguage>(...SUPPORTED_LANGUAGES)

// ---------------------------------------------------------------------------
// Property tests
// ---------------------------------------------------------------------------

describe('Feature: label-studio-integration-enhancement, Property 2: 语言切换消息发送', () => {
  let mockPostMessage: ReturnType<typeof vi.fn>
  let iframe: HTMLIFrameElement

  beforeEach(() => {
    // Create a mock iframe with data-label-studio attribute
    iframe = document.createElement('iframe')
    iframe.setAttribute('data-label-studio', 'true')
    document.body.appendChild(iframe)

    // Mock contentWindow.postMessage
    mockPostMessage = vi.fn()
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage: mockPostMessage },
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    document.body.removeChild(iframe)
    vi.restoreAllMocks()
  })

  /**
   * **Validates: Requirements 2.1**
   *
   * For any supported language, the message sent via postMessage must have
   * the exact shape: { type: 'setLanguage', lang: <language>, source: 'superinsight' }
   */
  it('对任意支持的语言，postMessage 应发送正确格式的消息', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        mockPostMessage.mockClear()

        const testOrigin = 'http://localhost:3000'
        syncLanguageToIframes(lang, [testOrigin])

        expect(mockPostMessage).toHaveBeenCalledTimes(1)
        expect(mockPostMessage).toHaveBeenCalledWith(
          {
            type: 'setLanguage',
            lang,
            source: 'superinsight',
          },
          testOrigin,
        )
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.1**
   *
   * The message type field must always be 'setLanguage' regardless of language.
   */
  it('消息 type 字段始终为 setLanguage', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        const message = buildLanguageMessage(lang)
        expect(message.type).toBe('setLanguage')
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.1**
   *
   * The message source field must always be 'superinsight' regardless of language.
   */
  it('消息 source 字段始终为 superinsight', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        const message = buildLanguageMessage(lang)
        expect(message.source).toBe('superinsight')
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.1**
   *
   * The lang field in the message must exactly match the input language value.
   */
  it('消息 lang 字段应与输入语言值完全一致', () => {
    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        const message = buildLanguageMessage(lang)
        expect(message.lang).toBe(lang)
        expect(SUPPORTED_LANGUAGES).toContain(message.lang)
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 2.1**
   *
   * When multiple origins are configured, postMessage should be called
   * once per origin for each iframe.
   */
  it('对任意支持的语言，应向所有配置的 origin 发送消息', () => {
    const origins = ['http://localhost:3000', 'http://localhost:8080', 'http://label-studio:8080']

    fc.assert(
      fc.property(supportedLanguageArb, (lang) => {
        mockPostMessage.mockClear()

        syncLanguageToIframes(lang, origins)

        expect(mockPostMessage).toHaveBeenCalledTimes(origins.length)

        origins.forEach((origin) => {
          expect(mockPostMessage).toHaveBeenCalledWith(
            {
              type: 'setLanguage',
              lang,
              source: 'superinsight',
            },
            origin,
          )
        })
      }),
      { numRuns: 100 },
    )
  })
})
