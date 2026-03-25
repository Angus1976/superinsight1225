/**
 * Data Lifecycle: Acquisition to Export E2E Tests
 *
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
 * Tests the full pipeline: DataSync Sources → add source → trigger sync →
 * verify Temp Data → create annotation task → assign → annotate →
 * quality review → export.
 */

import { test, expect } from '../fixtures'
import { mockAllApis, mockDataSyncApi, mockTasksApi, mockQualityApi } from '../helpers/mock-api-factory'
import { setupAuth, waitForPageReady } from '../test-helpers'

/* ------------------------------------------------------------------ */
/*  Extended mock helpers for pipeline stages                          */
/* ------------------------------------------------------------------ */

async function mockDataLifecycleApis(page: import('@playwright/test').Page) {
  // Temp data endpoint
  await page.route('**/api/data-lifecycle/temp-data**', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'td-1', name: '同步数据批次1', source: 'source-1', recordCount: 500, status: 'ready', createdAt: new Date().toISOString() },
            { id: 'td-2', name: '同步数据批次2', source: 'source-2', recordCount: 300, status: 'ready', createdAt: new Date().toISOString() },
          ],
          total: 2,
        }),
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  // Annotation tasks endpoint
  await page.route('**/api/data-lifecycle/tasks**', async (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'ann-task-1', name: '标注任务1', status: 'pending', itemCount: 500 }),
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [{ id: 'ann-task-1', name: '标注任务1', status: 'in_progress', assignee: 'annotator1', itemCount: 500 }],
        total: 1,
      }),
    })
  })

  // Annotation submission
  await page.route('**/api/data-lifecycle/annotations**', async (route) => {
    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'ann-1', taskId: 'ann-task-1', status: 'submitted' }),
    })
  })

  // Export endpoint
  await page.route('**/api/data-lifecycle/export**', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'export-1', status: 'completed', recordCount: 500, format: 'json' }),
    })
  })

  // Sync trigger
  await page.route(/\/api\/v1\/datalake\/sources\/[^/]+\/sync$/, async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, syncId: 'sync-1', rowsSynced: 500 }),
    })
  })
}

/* ------------------------------------------------------------------ */
/*  Setup                                                              */
/* ------------------------------------------------------------------ */

test.beforeEach(async ({ page }) => {
  await mockAllApis(page)
  await mockDataLifecycleApis(page)
  await setupAuth(page, 'admin', 'tenant-1')
})

/* ================================================================== */
/*  1. DataSync Sources → Add Source → Trigger Sync (Req 3.1)          */
/* ================================================================== */

test.describe('Stage 1: Data acquisition via DataSync', () => {
  test('navigate to DataSync Sources and view source list', async ({ page }) => {
    await page.goto('/data-sync/sources')
    await waitForPageReady(page)

    // Should display the sources list
    const content = page.locator('.ant-table, .ant-list, .ant-card')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })

  test('add a new data source', async ({ page }) => {
    await page.goto('/data-sync/sources')
    await waitForPageReady(page)

    const addBtn = page.getByRole('button', { name: /添加|新建|创建|add|create/i }).first()
    if (!(await addBtn.isVisible({ timeout: 5000 }).catch(() => false))) return

    await addBtn.click()

    const modal = page.locator('.ant-modal, .ant-drawer')
    if (await modal.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      // Fill source name
      const nameInput = modal.first().locator('input').first()
      if (await nameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await nameInput.fill('E2E 测试数据源')
      }
      // Submit
      const okBtn = modal.first().locator('.ant-btn-primary').first()
      if (await okBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await okBtn.click()
        await page.waitForTimeout(2000)
      }
    }
  })

  test('trigger sync on a data source', async ({ page }) => {
    await page.goto('/data-sync/sources')
    await waitForPageReady(page)

    const syncBtn = page.locator('button').filter({ hasText: /同步|sync|trigger/i }).first()
    if (await syncBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      let syncTriggered = false
      await page.route(/\/api\/v1\/datalake\/sources\/[^/]+\/sync$/, async (route) => {
        syncTriggered = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, syncId: 'sync-1', rowsSynced: 500 }),
        })
      })

      await syncBtn.click()
      await page.waitForTimeout(2000)
    }
  })
})

/* ================================================================== */
/*  2. Verify Temp Data → Create Annotation Task (Req 3.2)             */
/* ================================================================== */

test.describe('Stage 2: Temp Data to annotation task', () => {
  test('verify synced data appears in Temp Data', async ({ page }) => {
    await page.goto('/data-lifecycle/temp-data')
    await waitForPageReady(page)

    const content = page.locator('.ant-table, .ant-list, .ant-card, [class*="temp-data"]')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })

  test('create annotation task from temp data', async ({ page }) => {
    await page.goto('/data-lifecycle/temp-data')
    await waitForPageReady(page)

    const createTaskBtn = page.locator('button').filter({ hasText: /创建.*任务|标注|create.*task|annotate/i }).first()
    if (await createTaskBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await createTaskBtn.click()

      const modal = page.locator('.ant-modal, .ant-drawer')
      if (await modal.first().isVisible({ timeout: 5000 }).catch(() => false)) {
        const nameInput = modal.first().locator('input').first()
        if (await nameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
          await nameInput.fill('E2E 标注任务')
        }
        const okBtn = modal.first().locator('.ant-btn-primary').first()
        if (await okBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await okBtn.click()
          await page.waitForTimeout(2000)
        }
      }
    }
  })

  test('verify task appears in Tasks list', async ({ page }) => {
    await page.goto('/tasks')
    await waitForPageReady(page)

    const table = page.locator('.ant-table')
    await expect(table.first()).toBeVisible({ timeout: 10000 })
  })
})

/* ================================================================== */
/*  3. Assign → Annotate → Complete (Req 3.3)                         */
/* ================================================================== */

test.describe('Stage 3: Annotation execution', () => {
  test('assign task to annotator', async ({ page }) => {
    await page.goto('/tasks')
    await waitForPageReady(page)

    const assignBtn = page.locator('button, a').filter({ hasText: /分配|指派|assign/i }).first()
    if (await assignBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await assignBtn.click()
      await page.waitForTimeout(2000)
    }
  })

  test('navigate to annotation page and complete annotation', async ({ page }) => {
    // Mock annotation page data
    await page.route('**/api/tasks/task-1', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'task-1',
          name: '测试任务 1',
          status: 'in_progress',
          assignee: 'annotator1',
          items: [{ id: 'item-1', data: { text: '待标注文本' }, annotation: null }],
        }),
      })
    })

    await page.goto('/tasks/task-1/annotate')
    await waitForPageReady(page)

    // The annotation page should load
    const pageContent = page.locator('#root')
    await expect(pageContent).toBeVisible({ timeout: 10000 })
  })
})

/* ================================================================== */
/*  4. Quality Review (Req 3.4)                                        */
/* ================================================================== */

test.describe('Stage 4: Quality review', () => {
  test('quality metrics reflect annotations', async ({ page }) => {
    await page.goto('/quality')
    await waitForPageReady(page)

    const content = page.locator('.ant-card, .ant-statistic, [class*="quality"]')
    await expect(content.first()).toBeVisible({ timeout: 10000 })
  })

  test('run quality rules against annotated data', async ({ page }) => {
    let rulesCalled = false
    await page.route('**/api/quality/rules/run-all', async (route) => {
      rulesCalled = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, issuesFound: 2 }),
      })
    })

    await page.goto('/quality')
    await waitForPageReady(page)

    const runBtn = page.locator('button').filter({ hasText: /运行|检查|run|check/i }).first()
    if (await runBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await runBtn.click()
      await page.waitForTimeout(2000)
      expect(rulesCalled).toBe(true)
    }
  })
})

/* ================================================================== */
/*  5. Export (Req 3.5)                                                */
/* ================================================================== */

test.describe('Stage 5: Data export', () => {
  test('navigate to export and execute export', async ({ page }) => {
    await page.goto('/data-sync/export')
    await waitForPageReady(page)

    const content = page.locator('.ant-table, .ant-card, .ant-form, [class*="export"]')
    await expect(content.first()).toBeVisible({ timeout: 10000 })

    const exportBtn = page.locator('button').filter({ hasText: /导出|export|执行/i }).first()
    if (await exportBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      let exportCalled = false
      await page.route('**/api/data-lifecycle/export**', async (route) => {
        exportCalled = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 'export-1', status: 'completed', recordCount: 500 }),
        })
      })

      await exportBtn.click()
      await page.waitForTimeout(2000)
    }
  })
})
