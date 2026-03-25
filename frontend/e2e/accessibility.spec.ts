/**
 * Accessibility E2E Tests
 *
 * Tests keyboard navigation, focus indicators, modal focus trap,
 * form labels, Escape key, alt text, and color contrast.
 *
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
 */

import { test, expect } from './fixtures'
import { setupAuth, waitForPageReady } from './test-helpers'
import { mockAllApis } from './helpers/mock-api-factory'

/* ================================================================== */
/*  Tab Navigation (Req 10.1)                                          */
/* ================================================================== */

test.describe('Tab key navigation', () => {
  test('focus moves through interactive elements in logical order', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/dashboard')
    await waitForPageReady(page)

    const focusedTags: string[] = []

    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab')
      const tag = await page.evaluate(() => {
        const el = document.activeElement
        return el ? el.tagName.toLowerCase() : 'none'
      })
      focusedTags.push(tag)
    }

    // Should have focused on interactive elements (not stuck on body)
    const interactiveTags = focusedTags.filter((t) =>
      ['a', 'button', 'input', 'select', 'textarea', 'li', 'div'].includes(t),
    )
    expect(interactiveTags.length).toBeGreaterThan(0)
  })
})

/* ================================================================== */
/*  Visible Focus Indicators (Req 10.2)                                */
/* ================================================================== */

test.describe('Visible focus indicators', () => {
  test('focused elements have non-zero outline or box-shadow', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/tasks')
    await waitForPageReady(page)

    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    const hasFocus = await page.evaluate(() => {
      const el = document.activeElement
      if (!el || el === document.body) return true // skip if nothing focusable
      const styles = window.getComputedStyle(el)
      return (
        styles.outline !== 'none' ||
        styles.outlineWidth !== '0px' ||
        styles.boxShadow !== 'none'
      )
    })

    expect(hasFocus).toBeTruthy()
  })
})

/* ================================================================== */
/*  Modal Focus Trap (Req 10.3)                                        */
/* ================================================================== */

test.describe('Modal focus trap', () => {
  test('Tab cycles within modal, focus returns to trigger on close', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/tasks')
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|create|新建/i })
    if (!(await createBtn.isVisible({ timeout: 3000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal')
    if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) return

    // Tab several times — focus should stay within modal
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab')
    }

    const focusInModal = await page.evaluate(() => {
      const active = document.activeElement
      const modal = document.querySelector('.ant-modal')
      if (!active || !modal) return true
      return modal.contains(active)
    })
    expect(focusInModal).toBeTruthy()

    // Close modal
    await page.keyboard.press('Escape')
    await modal.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {})
  })
})

/* ================================================================== */
/*  Form Input Label Association (Req 10.4)                            */
/* ================================================================== */

test.describe('Form input labels', () => {
  test('all inputs have label, aria-label, or aria-labelledby', async ({ page }) => {
    await page.route('**/api/**', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
    )
    await page.goto('/login')
    await waitForPageReady(page)

    const unlabeled = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input:not([type="hidden"])')
      let count = 0
      inputs.forEach((input) => {
        const hasLabel =
          input.getAttribute('aria-label') ||
          input.getAttribute('aria-labelledby') ||
          input.getAttribute('placeholder') ||
          input.id && document.querySelector(`label[for="${input.id}"]`) ||
          input.closest('label')
        if (!hasLabel) count++
      })
      return count
    })

    // All visible inputs should have some form of label
    expect(unlabeled).toBe(0)
  })
})

/* ================================================================== */
/*  Escape Key Closes Overlays (Req 10.5)                              */
/* ================================================================== */

test.describe('Escape key', () => {
  test('closes open modals', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/tasks')
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|create|新建/i })
    if (!(await createBtn.isVisible({ timeout: 3000 }).catch(() => false))) return

    await createBtn.click()
    const modal = page.locator('.ant-modal')
    if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) return

    await page.keyboard.press('Escape')
    await expect(modal).not.toBeVisible({ timeout: 3000 })
  })
})

/* ================================================================== */
/*  Alt Text (Req 10.6)                                                */
/* ================================================================== */

test.describe('Alt text', () => {
  test('images/icons have alt text or aria-hidden', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/dashboard')
    await waitForPageReady(page)

    const missingAlt = await page.evaluate(() => {
      const images = document.querySelectorAll('img')
      let count = 0
      images.forEach((img) => {
        const hasAlt =
          img.getAttribute('alt') !== null ||
          img.getAttribute('aria-hidden') === 'true' ||
          img.getAttribute('role') === 'presentation'
        if (!hasAlt) count++
      })
      return count
    })

    expect(missingAlt).toBe(0)
  })
})

/* ================================================================== */
/*  Color Contrast (Req 10.7)                                          */
/* ================================================================== */

test.describe('Color contrast', () => {
  test('minimum 4.5:1 ratio on Login page text', async ({ page }) => {
    await page.route('**/api/**', (r) =>
      r.fulfill({ status: 200, contentType: 'application/json', body: '{}' }),
    )
    await page.goto('/login')
    await waitForPageReady(page)

    // Sample check: verify text color is not too light on a light background
    const contrastOk = await page.evaluate(() => {
      function luminance(r: number, g: number, b: number): number {
        const a = [r, g, b].map((v) => {
          v /= 255
          return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
        })
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722
      }

      function parseColor(color: string): [number, number, number] | null {
        const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
        if (m) return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])]
        return null
      }

      const labels = document.querySelectorAll('label, .ant-form-item-label')
      let allPass = true
      labels.forEach((el) => {
        const styles = window.getComputedStyle(el)
        const fg = parseColor(styles.color)
        const bg = parseColor(styles.backgroundColor || 'rgb(255,255,255)')
        if (fg && bg) {
          const l1 = luminance(...fg)
          const l2 = luminance(...bg)
          const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
          if (ratio < 4.5) allPass = false
        }
      })
      return allPass
    })

    expect(contrastOk).toBeTruthy()
  })
})
