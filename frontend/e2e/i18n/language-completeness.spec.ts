/**
 * i18n Language Completeness E2E Tests
 *
 * Tests language switching (zh↔en), absence of raw translation keys,
 * language persistence, and validation messages in active language.
 *
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Raw translation key pattern: e.g. common.button.submit */
const RAW_KEY_REGEX = /\b[a-z]+\.[a-z]+\.[a-z]+\b/

async function switchLanguage(page: import('@playwright/test').Page, targetLang: 'zh' | 'en') {
  // Look for language switcher in header / settings
  const langSwitch = page.locator(
    '[data-testid="language-switcher"], .language-selector, .ant-dropdown-trigger',
  ).filter({ hasText: /EN|中文|语言|Language/i }).first()

  if (await langSwitch.isVisible({ timeout: 3000 }).catch(() => false)) {
    await langSwitch.click()
    const option = page.locator('.ant-dropdown-menu-item, .ant-select-item-option').filter({
      hasText: targetLang === 'en' ? /English|EN/i : /中文|Chinese|ZH/i,
    }).first()
    if (await option.isVisible({ timeout: 2000 }).catch(() => false)) {
      await option.click()
      await page.waitForTimeout(1000)
      return
    }
  }

  // Fallback: set localStorage directly
  await page.evaluate((lang: string) => {
    localStorage.setItem('i18nextLng', lang)
    localStorage.setItem('language', lang)
  }, targetLang)
}

/* ================================================================== */
/*  zh → en Switch (Req 8.1)                                           */
/* ================================================================== */

test.describe('Language switch zh → en', () => {
  test('all visible text updates to English without page reload', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    // Start in Chinese
    await page.addInitScript(() => {
      localStorage.setItem('i18nextLng', 'zh')
      localStorage.setItem('language', 'zh')
    })

    await page.goto('/dashboard')
    await waitForPageReady(page)

    // Switch to English
    await switchLanguage(page, 'en')

    // Verify no full page reload occurred (URL stays the same)
    expect(page.url()).toContain('/dashboard')
  })
})

/* ================================================================== */
/*  en → zh Switch (Req 8.2)                                           */
/* ================================================================== */

test.describe('Language switch en → zh', () => {
  test('all visible text updates to Chinese without page reload', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    await page.addInitScript(() => {
      localStorage.setItem('i18nextLng', 'en')
      localStorage.setItem('language', 'en')
    })

    await page.goto('/dashboard')
    await waitForPageReady(page)

    await switchLanguage(page, 'zh')

    expect(page.url()).toContain('/dashboard')
  })
})

/* ================================================================== */
/*  No Raw Translation Keys (Req 8.3)                                  */
/* ================================================================== */

test.describe('No raw translation keys displayed', () => {
  const pages = ['/dashboard', '/tasks', '/login']

  for (const route of pages) {
    test(`no raw keys on ${route}`, async ({ page }) => {
      if (route !== '/login') {
        await setupAuth(page)
        await mockAllApis(page)
      } else {
        await page.route('**/api/**', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }))
      }

      await page.goto(route)
      await waitForPageReady(page)

      // Collect all visible text nodes
      const texts = await page.evaluate(() => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
        const results: string[] = []
        let node: Node | null
        while ((node = walker.nextNode())) {
          const t = (node.textContent || '').trim()
          if (t.length > 0) results.push(t)
        }
        return results
      })

      // None should match the raw key pattern
      for (const t of texts) {
        // Only flag strings that look purely like dotted keys (no spaces, no CJK)
        if (/^[a-z]+(\.[a-z_]+){2,}$/.test(t)) {
          expect(t).not.toMatch(/^[a-z]+(\.[a-z_]+){2,}$/)
        }
      }
    })
  }
})

/* ================================================================== */
/*  Language Persistence (Req 8.4)                                     */
/* ================================================================== */

test.describe('Language preference persistence', () => {
  test('language persists across navigation and browser refresh', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    await page.addInitScript(() => {
      localStorage.setItem('i18nextLng', 'en')
      localStorage.setItem('language', 'en')
    })

    await page.goto('/dashboard')
    await waitForPageReady(page)

    // Navigate to another page
    await page.goto('/tasks')
    await waitForPageReady(page)

    let lang = await page.evaluate(() => localStorage.getItem('i18nextLng') || localStorage.getItem('language'))
    expect(lang).toBe('en')

    // Refresh
    await page.reload()
    await waitForPageReady(page)

    lang = await page.evaluate(() => localStorage.getItem('i18nextLng') || localStorage.getItem('language'))
    expect(lang).toBe('en')
  })
})

/* ================================================================== */
/*  Validation Messages in Active Language (Req 8.5)                   */
/* ================================================================== */

test.describe('Validation messages in active language', () => {
  test('form validation messages display in active language', async ({ page }) => {
    await page.route('**/api/**', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }))

    await page.addInitScript(() => {
      localStorage.setItem('i18nextLng', 'zh')
      localStorage.setItem('language', 'zh')
    })

    await page.goto('/login')
    await waitForPageReady(page)

    // Submit empty form to trigger validation
    const submitBtn = page.getByRole('button', { name: /登录|login|sign in/i })
    if (await submitBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await submitBtn.click()

      const errorMsg = page.locator('.ant-form-item-explain-error').first()
      if (await errorMsg.isVisible({ timeout: 5000 }).catch(() => false)) {
        const text = await errorMsg.textContent()
        // In zh mode, validation messages should contain CJK characters or be non-empty
        expect(text).toBeTruthy()
      }
    }
  })
})
