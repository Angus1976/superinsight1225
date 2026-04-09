/**
 * Task detail → annotation navigation (Label Studio entry points).
 * Uses `setupE2eSession` + shared API mocks (`mock-api-factory` task + auth-url).
 */

import { test, expect } from '@playwright/test'
import { setupE2eSession, waitForPageReady } from './test-helpers'

test.describe('Annotation Navigation E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh' })
  })

  test('navigates to annotation page when clicking start annotation', async ({ page }) => {
    await page.goto('/tasks/task-1')
    await waitForPageReady(page)
    await expect(page.getByText(/测试任务/).first()).toBeVisible({ timeout: 15000 })

    await page.getByRole('button', { name: /开始标注|Start Annotation/i }).click()
    await page.waitForURL('**/tasks/*/annotate', { timeout: 10000 })
    expect(page.url()).toContain('/annotate')
  })

  test('opens Label Studio URL in new window when clicking open in new window', async ({
    page,
    context,
  }) => {
    await page.goto('/tasks/task-1')
    await waitForPageReady(page)
    await expect(page.getByText(/测试任务/).first()).toBeVisible({ timeout: 15000 })

    const popupPromise = context.waitForEvent('page')
    await page.getByRole('button', { name: /在新窗口打开|Open in New Window/i }).click()
    const newPage = await popupPromise
    await newPage.waitForLoadState('domcontentloaded')
    const url = newPage.url()
    expect(url).toMatch(/token=|projects\/\d+\/data/)
    await newPage.close()
  })

  test('start annotation without Label Studio project still opens annotate route', async ({ page }) => {
    await page.goto('/tasks/test-task-no-project')
    await waitForPageReady(page)
    await expect(page.getByText(/测试任务|任务/).first()).toBeVisible({ timeout: 15000 })

    await page.getByRole('button', { name: /开始标注|Start Annotation/i }).click()
    await page.waitForURL('**/tasks/*/annotate', { timeout: 10000 })
    expect(page.url()).toContain('/annotate')
  })
})
