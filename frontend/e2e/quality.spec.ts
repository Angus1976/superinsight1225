/**
 * Quality module E2E — aligned with `/quality` (Quality/index.tsx), sub-routes, and i18n.
 * Assertions use zh|en patterns: navigator + store hydration can still surface EN in CI.
 */

import { test, expect } from './fixtures'
import { setupE2eSession, waitForPageReady } from './test-helpers'

test.use({ locale: 'zh-CN' })

test.beforeEach(async ({ page }) => {
  await setupE2eSession(page, { lang: 'zh' })
})

test.describe('质量管理主页', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality')
    await waitForPageReady(page)
  })

  test('应展示概览统计卡片', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /质量管理|Quality Management/ })).toBeVisible()
    await expect(page.getByText(/活跃规则|Active Rules/)).toBeVisible()
    await expect(page.getByText(/总违规数|Total Violations/)).toBeVisible()
    await expect(page.getByText(/待处理问题|Open Issues/)).toBeVisible()
    await expect(page.getByText(/质量评分|Quality Score/)).toBeVisible()
  })

  test('应在主要 Tab 间切换', async ({ page }) => {
    await page.getByRole('tab', { name: /质量规则|Quality Rules/ }).click()
    await expect(page.getByRole('button', { name: /创建规则|Create Rule/ })).toBeVisible()

    await page.getByRole('tab', { name: /质量问题|Quality Issues/ }).click()
    await expect(page.getByRole('columnheader', { name: /描述|Description/ })).toBeVisible()

    await page.getByRole('tab', { name: /质量报表|Quality Reports/ }).click()
    await expect(page.getByText(/导出报表|Export Report/).first()).toBeVisible()
  })

  test('质量报表 Tab 中应展示考核排名数据', async ({ page }) => {
    await page.getByRole('tab', { name: /质量报表|Quality Reports/ }).click()
    await expect(page.getByText('John Doe').first()).toBeVisible()
  })
})

test.describe('质量规则', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality')
    await waitForPageReady(page)
  })

  test('应展示规则表格列', async ({ page }) => {
    await expect(page.getByRole('columnheader', { name: /规则名称|Rule Name/ })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /严重程度|Severity/ })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /规则类型|Rule Type/ })).toBeVisible()
  })

  test('应打开创建规则对话框', async ({ page }) => {
    await page.getByRole('button', { name: /创建规则|Create Rule/ }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByLabel(/规则名称|Rule Name/)).toBeVisible()
    await expect(page.getByLabel(/规则类型|Rule Type/)).toBeVisible()
  })

  test('应通过表单创建规则并关闭对话框', async ({ page }) => {
    await page.getByRole('button', { name: /创建规则|Create Rule/ }).click()
    await page.getByLabel(/规则名称|Rule Name/).fill('E2E 测试规则')
    await page.getByLabel(/规则类型|Rule Type/).click()
    await page.locator('.ant-select-item-option').filter({ hasText: /格式|Format/ }).click()
    // Ant Design zh_CN: modal OK is often "确 定" (spaced)
    await page.locator('.ant-modal-wrap').getByRole('button', { name: /确\s*定|OK/i }).click()
    await expect(page.getByRole('dialog', { name: /创建规则|Create Rule/ })).toBeHidden({ timeout: 8000 })
  })

  test('应切换规则启用状态', async ({ page }) => {
    const sw = page.locator('.ant-switch').first()
    const before = await sw.getAttribute('aria-checked')
    await sw.click()
    await expect(sw).toHaveAttribute('aria-checked', before === 'true' ? 'false' : 'true', { timeout: 5000 })
  })
})

test.describe('质量问题列表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality')
    await waitForPageReady(page)
    await page.getByRole('tab', { name: /质量问题|Quality Issues/ }).click()
  })

  test('应展示问题表格', async ({ page }) => {
    await expect(page.getByRole('table')).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /描述|Description/ })).toBeVisible()
  })
})

test.describe('质量报表（独立页）', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality/reports')
    await waitForPageReady(page)
  })

  test('应展示报表与指标区域', async ({ page }) => {
    await expect(page.getByText(/总体质量评分|Overall Quality Score/).first()).toBeVisible()
    await expect(page.getByText(/导出报告|Export Report/).first()).toBeVisible()
  })

  test('应展示导出与刷新控件', async ({ page }) => {
    await expect(page.getByRole('button', { name: /导出报告|Export Report/ })).toBeVisible()
    await expect(page.getByRole('button', { name: /刷新|Refresh/ })).toBeVisible()
  })
})

test.describe('改进任务列表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality/workflow/tasks')
    await waitForPageReady(page)
  })

  test('应展示任务表格与列', async ({ page }) => {
    await expect(page.getByText(/改进任务列表|Improvement Task List/).first()).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /任务ID|Task ID/ })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /优先级|Priority/ })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: /状态|Status/ })).toBeVisible()
  })

  test('应用状态筛选', async ({ page }) => {
    const statusFilter = page.locator('.ant-card-extra .ant-select').first()
    await statusFilter.click()
    await page.locator('.ant-select-item-option').filter({ hasText: /待处理|Pending/ }).first().click()
    await expect(page.getByRole('table')).toBeVisible()
  })

  test('应进入任务详情', async ({ page }) => {
    await page.getByRole('button', { name: /查看详情|View Details/ }).first().click()
    await expect(page).toHaveURL(/\/quality\/workflow\/tasks\//)
    await expect(page.getByText(/任务详情|Task Details/).first()).toBeVisible()
  })
})

test.describe('改进任务详情', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality/workflow/tasks/task_001')
    await waitForPageReady(page)
  })

  test('应展示任务与问题区块', async ({ page }) => {
    await expect(page.getByText(/任务详情|Task Details/).first()).toBeVisible()
    await expect(page.getByText(/质量问题|Quality Issues/).first()).toBeVisible()
    await expect(page.getByText(/改进数据|Improved Data/).first()).toBeVisible()
  })

  test('应进入编辑改进数据并提交', async ({ page }) => {
    await page.getByRole('button', { name: /编\s*辑|Edit/i }).first().click()
    await page.locator('textarea').fill('{"field": "corrected_value"}')
    await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes('/api/v1/quality-workflow/tasks/') &&
          r.url().includes('/submit') &&
          r.request().method() === 'POST' &&
          r.ok(),
      ),
      page.getByRole('button', { name: /提\s*交\s*改\s*进|Submit Improvement/i }).click(),
    ])
  })
})

test.describe('工作流配置', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality/workflow/config')
    await waitForPageReady(page)
  })

  test('应展示工作流配置表单', async ({ page }) => {
    await expect(page.getByText(/工作流配置|Workflow Configuration/).first()).toBeVisible()
    await expect(page.getByText(/工作流阶段|Workflow Stages/).first()).toBeVisible()
    await expect(page.getByText(/自动化设置|Automation Settings/).first()).toBeVisible()
  })

  test('应保存工作流配置（POST 成功）', async ({ page }) => {
    await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes('/api/v1/quality-workflow/configure') &&
          r.request().method() === 'POST' &&
          r.ok(),
      ),
      page.getByRole('button', { name: /保\s*存\s*配\s*置|Save Configuration/i }).click(),
    ])
  })

  test('应展示改进效果统计', async ({ page }) => {
    await expect(page.getByText(/改进效果统计|Improvement Effect Statistics/).first()).toBeVisible()
    await expect(page.getByText(/总任务数|Total Tasks/).first()).toBeVisible()
    await expect(page.getByText(/完成任务|Completed Tasks/).first()).toBeVisible()
  })
})

test.describe('质量模块完整浏览', () => {
  test('应在关键页面间连贯跳转', async ({ page }) => {
    await page.goto('/quality')
    await waitForPageReady(page)
    await expect(page.getByRole('heading', { name: /质量管理|Quality Management/ })).toBeVisible()

    await page.getByRole('tab', { name: /质量规则|Quality Rules/ }).click()
    await expect(page.getByRole('table')).toBeVisible()

    await page.getByRole('tab', { name: /质量问题|Quality Issues/ }).click()
    await expect(page.getByRole('table')).toBeVisible()

    await page.goto('/quality/workflow/tasks')
    await waitForPageReady(page)
    await expect(page.getByText(/改进任务列表|Improvement Task List/).first()).toBeVisible()
  })
})
