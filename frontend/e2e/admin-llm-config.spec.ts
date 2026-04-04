/**
 * Admin LLM Configuration E2E Tests
 *
 * Aligns with `/admin/config/llm` → `LLMApplicationBinding` and `/api/llm-configs` APIs.
 */

import { test, expect } from '@playwright/test'
import { setupAuth, waitForPageReady, seedLanguageStores } from './test-helpers'
import { mockAllApis } from './helpers/mock-api-factory'

function sampleLlmConfigs() {
  const now = new Date().toISOString()
  return [
    {
      id: 'llm-1',
      name: 'OpenAI GPT-4',
      provider: 'openai',
      base_url: 'https://api.openai.com/v1',
      model_name: 'gpt-4o',
      parameters: {},
      is_active: true,
      created_at: now,
      updated_at: now,
    },
    {
      id: 'llm-2',
      name: '通义千问',
      provider: 'qwen',
      base_url: 'https://dashscope.aliyuncs.com/api/v1',
      model_name: 'qwen-turbo',
      parameters: {},
      is_active: true,
      created_at: now,
      updated_at: now,
    },
  ]
}

async function goToConfigsTab(page: import('@playwright/test').Page) {
  await page.getByRole('tab', { name: /配置管理|Configuration Management/i }).click()
}

test.describe('Admin LLM Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await seedLanguageStores(page, 'zh')
    await mockAllApis(page, { llmConfigs: sampleLlmConfigs() })

    await page.goto('/admin/config/llm')
    await waitForPageReady(page)
    await goToConfigsTab(page)
  })

  test('displays LLM configuration list', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /LLM 配置管理|LLM Configuration Management/i })).toBeVisible({
      timeout: 10000,
    })
    await expect(page.getByText('OpenAI GPT-4')).toBeVisible()
    await expect(page.getByText('通义千问')).toBeVisible()
  })

  test('opens create configuration modal', async ({ page }) => {
    await page.getByRole('button', { name: /添加配置|Add configuration/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    await expect(page.getByLabel(/配置名称|Configuration name/i)).toBeVisible()
  })

  test('creates new LLM configuration', async ({ page }) => {
    await page.getByRole('button', { name: /添加配置|Add configuration/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await page.getByLabel(/配置名称|Configuration name/i).fill('Test LLM Config')

    await page.getByLabel(/提供商|Provider/i).click()
    await page
      .locator('.ant-select-dropdown')
      .locator('.ant-select-item-option-content')
      .filter({ hasText: /^DeepSeek$/ })
      .click()

    await page.getByLabel(/API 密钥|API Key/i).fill('sk-test-key-12345')

    await page.locator('.ant-modal .ant-select').nth(1).click()
    await page
      .locator('.ant-select-dropdown')
      .locator('.ant-select-item-option-content')
      .filter({ hasText: /^DeepSeek Chat$/ })
      .click()

    const created = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/llm-configs\/?(\?|$)/.test(new URL(r.url()).pathname),
    )
    await page.locator('.ant-modal').getByRole('button', { name: /提交|Submit/i }).click()
    expect((await created).status()).toBe(201)

    await expect(page.locator('.ant-modal')).toBeHidden({ timeout: 15000 })
    await expect(page.getByText('Test LLM Config')).toBeVisible()
  })

  test('validates required fields', async ({ page }) => {
    await page.getByRole('button', { name: /添加配置|Add configuration/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await page.locator('.ant-modal').getByRole('button', { name: /提交|Submit/i }).click()

    await expect(page.locator('.ant-modal .ant-form-item-explain-error').first()).toBeVisible({ timeout: 5000 })
  })

  test('tests LLM connection', async ({ page }) => {
    const respPromise = page.waitForResponse(
      (r) =>
        /\/api\/llm-configs\/[^/]+\/test\/?(\?|$)/.test(r.url()) && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: /测试连接|Test connection/i }).first().click()
    const resp = await respPromise
    expect(resp.ok()).toBeTruthy()
    const body = (await resp.json()) as { status?: string }
    expect(body.status).toBe('success')
  })

  test('edits existing configuration', async ({ page }) => {
    await page.getByRole('button', { name: /编辑|Edit/i }).first().click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await page.getByLabel(/配置名称|Configuration name/i).clear()
    await page.getByLabel(/配置名称|Configuration name/i).fill('Updated LLM Config')

    await page.locator('.ant-modal').getByRole('button', { name: /提交|Submit/i }).click()

    await expect(page.locator('.ant-modal')).toBeHidden({ timeout: 10000 })
    await expect(page.getByText('Updated LLM Config')).toBeVisible()
  })

  test('deletes configuration with confirmation', async ({ page }) => {
    const delResp = page.waitForResponse(
      (r) => r.request().method() === 'DELETE' && r.url().includes('/api/llm-configs/'),
    )
    // LLMConfigList cards live under .ant-row; the page also wraps content in an outer ant-card,
    // so `.ant-card` + hasText would match the wrapper and .first() hit the wrong Delete.
    await page
      .locator('.ant-row .ant-card')
      .filter({ has: page.getByText('通义千问', { exact: true }) })
      .getByRole('button', { name: /^delete Delete$/i })
      .click()
    await expect(page.locator('.ant-modal-wrap').last()).toBeVisible({ timeout: 10000 })
    // antd 按钮文案在 a11y 树里可能是「确 定」等带字间距的形式，避免只匹配「确定」
    await page
      .locator('.ant-modal-wrap')
      .last()
      .getByRole('button', { name: /^OK$|^确定$|^确\s*定$/i })
      .click()
    expect((await delResp).status()).toBe(204)
    await expect(page.getByText('通义千问')).toHaveCount(0)
  })

  test('displays provider-specific fields when switching provider', async ({ page }) => {
    await page.getByRole('button', { name: /添加配置|Add configuration/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    await page.locator('.ant-modal .ant-select-selector').first().click()
    await page
      .locator('.ant-select-dropdown')
      .locator('.ant-select-item-option-content')
      .filter({ hasText: /^DeepSeek$/ })
      .click()
    await expect(page.getByLabel(/API 密钥|API Key/i)).toBeVisible()
  })

  test('handles connection test failure gracefully', async ({ page }) => {
    await page.unroute(/\/api\/llm-configs\/[^/]+\/test\/?$/)
    await page.route(/\/api\/llm-configs\/[^/]+\/test\/?$/, async (route) => {
      if (route.request().method() !== 'POST') return route.continue()
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          'Access-Control-Allow-Origin': '*',
        },
        body: JSON.stringify({
          status: 'failed',
          error: 'Connection timeout: Unable to reach API endpoint',
        }),
      })
    })

    await page.reload()
    await waitForPageReady(page)
    await goToConfigsTab(page)

    const failResp = page.waitForResponse(
      (r) =>
        /\/api\/llm-configs\/[^/]+\/test\/?(\?|$)/.test(r.url()) && r.request().method() === 'POST',
    )
    await page.getByRole('button', { name: /测试连接|Test connection/i }).first().click()
    const fr = await failResp
    expect(fr.ok()).toBeTruthy()
    const body = (await fr.json()) as { status: string }
    expect(body.status).toBe('failed')
  })

  test('search filters configuration cards', async ({ page }) => {
    const search = page.getByPlaceholder(/搜索配置名称或模型|Search configuration name or model/i)
    await search.fill('OpenAI')
    await expect(page.getByText('OpenAI GPT-4')).toBeVisible()
    await expect(page.getByText('Test LLM Config')).toHaveCount(0)
  })

  test('toggles active status when editing', async ({ page }) => {
    await page.getByRole('button', { name: /编辑|Edit/i }).first().click()
    await expect(page.locator('.ant-modal')).toBeVisible()

    const activeSwitch = page.locator('.ant-modal .ant-switch').first()
    if (await activeSwitch.isVisible()) {
      await activeSwitch.click()
    }

    const put = page.waitForResponse(
      (r) => r.request().method() === 'PUT' && r.url().includes('/api/llm-configs/'),
    )
    await page.locator('.ant-modal').getByRole('button', { name: /提交|Submit/i }).click()
    expect((await put).status()).toBe(200)
    await expect(page.locator('.ant-modal')).toBeHidden({ timeout: 15000 })
  })
})

test.describe('LLM Configuration - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1')
    await seedLanguageStores(page, 'zh')
    await mockAllApis(page)
  })

  test('displays correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/admin/config/llm')
    await waitForPageReady(page)
    await goToConfigsTab(page)

    await expect(page.getByRole('button', { name: /添加配置|Add configuration/i })).toBeVisible()
  })

  test('displays correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/admin/config/llm')
    await waitForPageReady(page)
    await goToConfigsTab(page)

    await expect(page.getByRole('button', { name: /添加配置|Add configuration/i })).toBeVisible()
  })
})

test.describe('LLM Configuration - Access Control', () => {
  test('denies access for non-admin users', async ({ page }) => {
    await setupAuth(page, 'user', 'tenant-1')
    await seedLanguageStores(page, 'zh')
    await mockAllApis(page)

    await page.goto('/admin/config/llm')
    await waitForPageReady(page)

    await expect(page.getByText(/Access Denied|权限|permission/i).first()).toBeVisible({ timeout: 10000 })
  })
})
