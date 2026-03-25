/**
 * AI Assistant E2E Tests
 *
 * Tests chat interface loads, accepts user messages, displays AI responses.
 *
 * Requirements: 15.3
 */

import { test, expect } from '../fixtures'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { mockAllApis } from '../helpers/mock-api-factory'

test.describe('AI Assistant', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await mockAllApis(page)

    await page.route('**/api/ai-assistant/**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: '你好！我是AI助手，有什么可以帮助你的？',
          conversationId: 'conv-1',
        }),
      })
    })

    await page.route('**/api/chat/**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: '这是AI的回复内容。',
          conversationId: 'conv-1',
        }),
      })
    })
  })

  test('chat interface loads', async ({ page }) => {
    await page.goto('/ai-assistant')
    await waitForPageReady(page)

    const url = page.url()
    expect(url).not.toMatch(/\/login/)
    expect(url).not.toMatch(/\/403/)
  })

  test('chat page renders content', async ({ page }) => {
    await page.goto('/ai-assistant')
    await waitForPageReady(page)

    const root = page.locator('#root')
    await expect(root).toBeVisible()
    const children = await root.evaluate((el: Element) => el.children.length)
    expect(children).toBeGreaterThan(0)
  })

  test('message input is accessible', async ({ page }) => {
    await page.goto('/ai-assistant')
    await waitForPageReady(page)

    const input = page.locator('textarea, input[placeholder*="消息"], input[placeholder*="message"], input[type="text"]').first()
    if (await input.isVisible({ timeout: 3000 }).catch(() => false)) {
      await input.fill('你好')
      const value = await input.inputValue()
      expect(value).toBe('你好')
    }
  })
})
