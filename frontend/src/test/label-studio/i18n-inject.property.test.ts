/**
 * Property 1: 翻译函数语言正确性
 *
 * Feature: label-studio-integration-enhancement
 * Property 1: 翻译函数语言正确性
 *
 * Validates: Requirements 1.1, 1.2, 4.4
 *
 * For any 翻译词典中的条目和任意支持的语言设置:
 * - 当 lang=zh 时翻译函数应返回对应中文文本（包括 "Label Studio" → "问视间"）
 * - 当 lang=en 时应返回原始英文文本不变
 */
import { describe, it, expect, beforeEach } from 'vitest'
import fc from 'fast-check'

// eslint-disable-next-line @typescript-eslint/no-require-imports
const i18n = require('../../../../deploy/label-studio/i18n-inject.js')

const {
  translateText,
  TRANSLATIONS,
  REVERSE_TRANSLATIONS,
  _setLang,
} = i18n as {
  translateText: (text: string) => string
  TRANSLATIONS: Record<string, string>
  REVERSE_TRANSLATIONS: Record<string, string>
  _setLang: (lang: string) => void
}

// 所有英文 key 列表
const englishKeys = Object.keys(TRANSLATIONS)

// 生成随机词典条目索引的 arbitrary
const dictionaryEntryArb = fc.integer({ min: 0, max: englishKeys.length - 1 })

// 语言 arbitrary
const langArb = fc.constantFrom('zh' as const, 'en' as const)

describe('Feature: label-studio-integration-enhancement, Property 1: 翻译函数语言正确性', () => {
  beforeEach(() => {
    // 重置为默认语言
    _setLang('zh')
  })

  /**
   * **Validates: Requirements 1.1, 1.2**
   *
   * 对于词典中的任意条目，zh 模式返回中文，en 模式返回英文原文
   */
  it('对于任意词典条目和语言设置，翻译函数应返回正确语言的文本', () => {
    fc.assert(
      fc.property(dictionaryEntryArb, langArb, (index, lang) => {
        const englishText = englishKeys[index]
        const expectedChinese = TRANSLATIONS[englishText]

        _setLang(lang)

        const result = translateText(englishText)

        if (lang === 'zh') {
          expect(result).toBe(expectedChinese)
        } else {
          // en 模式：英文文本不在 REVERSE_TRANSLATIONS 中，应原样返回
          expect(result).toBe(englishText)
        }
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 4.4**
   *
   * "Label Studio" → "问视间" 品牌替换在 zh 模式下生效
   */
  it('"Label Studio" 在 zh 模式下应翻译为 "问视间"', () => {
    fc.assert(
      fc.property(langArb, (lang) => {
        _setLang(lang)
        const result = translateText('Label Studio')

        if (lang === 'zh') {
          expect(result).toBe('问视间')
        } else {
          expect(result).toBe('Label Studio')
        }
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 1.2**
   *
   * 不在词典中的文本应原样返回，不论语言设置
   */
  it('不在词典中的文本应原样返回', () => {
    // 所有词典中的文本（英文 key + 中文 value）
    const allValues = new Set([
      ...Object.keys(TRANSLATIONS),
      ...Object.values(TRANSLATIONS),
    ])

    // 使用字母数字字符串避免 JS 原型属性（__proto__ 等）干扰
    const safeCharArb = fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789 '.split(''))
    const nonDictTextArb = fc
      .array(safeCharArb, { minLength: 1, maxLength: 30 })
      .map((chars) => chars.join(''))
      .filter((s) => s.trim().length > 0 && !allValues.has(s.trim()))

    fc.assert(
      fc.property(nonDictTextArb, langArb, (text, lang) => {
        _setLang(lang)
        const result = translateText(text)
        expect(result).toBe(text)
      }),
      { numRuns: 100 },
    )
  })
})
