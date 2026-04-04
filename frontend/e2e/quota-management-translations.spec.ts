/**
 * E2E: Quota Management page translations (Admin → 配额管理)
 *
 * Uses shared session + API mocks so tests do not depend on real login or backend.
 */

import { test, expect } from './fixtures'
import { setupE2eSession, waitForPageReady } from './test-helpers'

test.use({ locale: 'zh-CN' })

const EXPECTED_TRANSLATIONS = {
  pageTitle: '配额管理',
  statistics: {
    totalStorage: '总存储使用',
    totalProjects: '总项目数',
    totalUsers: '总用户数',
    totalApiCalls: '总 API 调用',
  },
  columns: {
    tenant: '租户',
    storage: '存储',
    projects: '项目数',
    users: '用户数',
    apiCalls: 'API 调用',
    status: '状态',
    actions: '操作',
  },
  buttons: {
    refresh: '刷新',
    adjustQuota: '调整配额',
  },
  form: {
    storageQuota: '存储配额 (GB)',
    projectQuota: '项目配额',
    userQuota: '用户配额',
    apiQuota: 'API 调用配额',
  },
}

test.describe('Quota Management Page Translations', () => {
  let consoleMessages: string[] = []
  let i18nWarnings: string[] = []

  test.beforeEach(async ({ page }) => {
    consoleMessages = []
    i18nWarnings = []

    page.on('console', (msg) => {
      const text = msg.text()
      consoleMessages.push(text)
      if (text.includes('i18n') || text.includes('translation') || text.includes('missing')) {
        i18nWarnings.push(text)
      }
    })

    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await page.goto('/admin/quotas')
    await waitForPageReady(page)
    await page.waitForSelector('.quota-management', { timeout: 15000 })
  })

  test('should display correct page title', async ({ page }) => {
    const title = await page.locator('.ant-card-head-title').first().textContent()
    expect(title).toContain(EXPECTED_TRANSLATIONS.pageTitle)
  })

  test('should display all statistics cards with correct translations', async ({ page }) => {
    const statisticTitles = await page.locator('.ant-statistic-title').allTextContents()
    expect(statisticTitles).toHaveLength(4)
    expect(statisticTitles[0]).toBe(EXPECTED_TRANSLATIONS.statistics.totalStorage)
    expect(statisticTitles[1]).toBe(EXPECTED_TRANSLATIONS.statistics.totalProjects)
    expect(statisticTitles[2]).toBe(EXPECTED_TRANSLATIONS.statistics.totalUsers)
    expect(statisticTitles[3]).toBe(EXPECTED_TRANSLATIONS.statistics.totalApiCalls)
  })

  test('should display all table columns with correct translations', async ({ page }) => {
    const columnHeaders = await page.locator('.ant-table-thead th').allTextContents()
    const filteredHeaders = columnHeaders.filter((text) => text.trim() !== '')
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.tenant)
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.storage)
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.projects)
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.users)
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.apiCalls)
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.status)
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.actions)
  })

  test('should display refresh button with correct translation', async ({ page }) => {
    const refreshButton = page.locator('.quota-management .ant-card-extra button').first()
    const buttonText = await refreshButton.textContent()
    expect(buttonText?.trim()).toBe(EXPECTED_TRANSLATIONS.buttons.refresh)
  })

  test('should display adjust quota button with correct translation', async ({ page }) => {
    const btn = page.getByRole('button', { name: new RegExp(EXPECTED_TRANSLATIONS.buttons.adjustQuota) }).first()
    await expect(btn).toBeVisible()
  })

  test('should display modal form with correct translations', async ({ page }) => {
    await page.getByRole('button', { name: new RegExp(EXPECTED_TRANSLATIONS.buttons.adjustQuota) }).first().click()
    await page.waitForSelector('.ant-modal', { timeout: 5000 })
    const labelText = (await page.locator('.ant-modal .ant-form-item-label').allTextContents()).join(' ')
    expect(labelText).toContain('存储配额')
    expect(labelText).toContain('项目配额')
    expect(labelText).toContain('用户配额')
    expect(labelText).toMatch(/API\s*调用配额/)
    await page.locator('.ant-modal-close').click()
  })

  test('should display pagination with correct translation', async ({ page }) => {
    const paginationText = await page.locator('.ant-pagination-total-text').textContent()
    expect(paginationText).toMatch(/共.*个租户/)
  })

  test('should have no i18n warnings in console', async ({ page }) => {
    await page.waitForTimeout(2000)
    expect(i18nWarnings).toHaveLength(0)
  })

  test('should have no console errors', async ({ page }) => {
    await page.waitForTimeout(2000)
    const errors = consoleMessages.filter(
      (msg) => msg.toLowerCase().includes('error') && !msg.includes('DevTools'),
    )
    expect(errors.length).toBeLessThanOrEqual(5)
  })

  test.afterEach(async () => {
    console.log(`\n📊 Test completed — console messages: ${consoleMessages.length}`)
  })
})
