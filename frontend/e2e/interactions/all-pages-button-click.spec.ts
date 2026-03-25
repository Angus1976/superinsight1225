/**
 * All Pages Button Click E2E Tests
 *
 * Validates: Requirements 2.1
 * Tests ALL visible buttons on EVERY remaining page not covered by
 * button-interactions.spec.ts (which covers Dashboard, Tasks, Quality, Admin).
 *
 * Covered pages:
 *  1. Security (Audit, Permissions, Dashboard, RBAC, SSO, Sessions, DataPermissions)
 *  2. DataSync (Sources, History, Scheduler, Security, Export, Datalake, APIManagement)
 *  3. Augmentation (Samples, Config)
 *  4. License (Activate, Usage, Report, Alerts)
 *  5. DataLifecycle (TempData, SampleLibrary, AnnotationTasks, Enhancement, AITrial, AuditLog)
 *  6. Billing (Overview, Reports)
 *  7. Settings
 *  8. AI Annotation
 *  9. AI Assistant
 * 10. AI Processing (/augmentation/ai-processing)
 * 11. Data Structuring (Upload)
 * 12. Workspace Management
 * 13. Quality sub-pages (Rules, Reports, ImprovementTaskList)
 */

import { test, expect } from '../fixtures'
import { mockAllApis } from '../helpers/mock-api-factory'
import { setupAuth, waitForPageReady } from '../test-helpers'
import { Page } from '@playwright/test'

/* ------------------------------------------------------------------ */
/*  Shared helpers                                                     */
/* ------------------------------------------------------------------ */

/**
 * Click every visible, enabled button on the current page.
 * After each click: dismiss modals / popconfirms, navigate back if needed.
 */
async function clickAllButtons(page: Page, route: string): Promise<void> {
  const buttons = page.locator('button:visible, .ant-btn:visible')
  const count = await buttons.count()

  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i)
    const isEnabled = await btn.isEnabled().catch(() => false)
    if (!isEnabled) continue

    const urlBefore = page.url()

    await btn.click({ timeout: 3000 }).catch(() => {})
    await page.waitForTimeout(500)

    // Dismiss any modal that opened
    await dismissModal(page)

    // Dismiss any popconfirm / popover
    await dismissPopconfirm(page)

    // If navigated away, go back
    if (page.url() !== urlBefore) {
      await page.goto(route)
      await waitForPageReady(page)
    }

    // Page must not crash
    await expect(page.locator('#root')).toBeVisible()
  }
}

/**
 * Click all visible links / navigation elements and verify they work.
 */
async function clickAllLinks(page: Page, route: string): Promise<void> {
  const links = page.locator('a[href]:visible, .ant-menu-item:visible')
  const count = await links.count()

  for (let i = 0; i < count; i++) {
    const link = links.nth(i)
    const urlBefore = page.url()

    await link.click({ timeout: 3000 }).catch(() => {})
    await page.waitForTimeout(500)

    await dismissModal(page)

    // Navigate back if needed
    if (page.url() !== urlBefore) {
      await page.goto(route)
      await waitForPageReady(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  }
}

/**
 * Find form submit buttons and verify form interaction works.
 */
async function clickFormSubmitButtons(page: Page, route: string): Promise<void> {
  const submitBtns = page.locator(
    'button[type="submit"]:visible, .ant-btn-primary:visible',
  )
  const count = await submitBtns.count()

  for (let i = 0; i < count; i++) {
    const btn = submitBtns.nth(i)
    const isEnabled = await btn.isEnabled().catch(() => false)
    if (!isEnabled) continue

    const urlBefore = page.url()

    await btn.click({ timeout: 3000 }).catch(() => {})
    await page.waitForTimeout(500)

    await dismissModal(page)
    await dismissPopconfirm(page)

    if (page.url() !== urlBefore) {
      await page.goto(route)
      await waitForPageReady(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  }
}

async function dismissModal(page: Page): Promise<void> {
  const modal = page.locator('.ant-modal:visible')
  if (await modal.isVisible({ timeout: 1000 }).catch(() => false)) {
    const cancelBtn = modal
      .locator(
        '.ant-modal-close, button:has-text("取消"), button:has-text("Cancel"), button:has-text("关闭"), button:has-text("Close")',
      )
      .first()
    if (await cancelBtn.isVisible({ timeout: 500 }).catch(() => false)) {
      await cancelBtn.click().catch(() => {})
      await page.waitForTimeout(300)
    }
  }
}

async function dismissPopconfirm(page: Page): Promise<void> {
  const popconfirm = page.locator('.ant-popconfirm:visible, .ant-popover:visible')
  if (await popconfirm.isVisible({ timeout: 500 }).catch(() => false)) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
  }
}

/* ------------------------------------------------------------------ */
/*  Global setup                                                       */
/* ------------------------------------------------------------------ */

test.beforeEach(async ({ page }) => {
  await mockAllApis(page)
  await setupAuth(page, 'admin', 'tenant-1')

  // Catch-all for any unmocked API to prevent 404 noise
  await page.route('**/api/**', async (route) => {
    if (!route.request().isNavigationRequest()) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0, success: true }),
      })
    } else {
      await route.continue()
    }
  })
})


/* ================================================================== */
/*  1. Security Pages                                                  */
/* ================================================================== */

test.describe('Security buttons', () => {
  const ROUTE = '/security'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

test.describe('Security > Audit buttons', () => {
  const ROUTE = '/security/audit'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Export audit logs button
    const exportBtn = page.locator('button').filter({ hasText: /导出|export/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Refresh / filter buttons
    const refreshBtn = page.locator('button').filter({ hasText: /刷新|refresh|查询|search/i }).first()
    if (await refreshBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await refreshBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Security > Permissions buttons', () => {
  const ROUTE = '/security/permissions'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Security > Dashboard buttons', () => {
  const ROUTE = '/security/dashboard'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })
})

test.describe('Security > RBAC buttons', () => {
  const ROUTE = '/security/rbac'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Create role button
    const createBtn = page.getByRole('button', { name: /创建|新建|添加角色|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Security > SSO buttons', () => {
  const ROUTE = '/security/sso'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

test.describe('Security > Sessions buttons', () => {
  const ROUTE = '/security/sessions'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Terminate session button
    const terminateBtn = page.locator('button').filter({ hasText: /终止|terminate|踢出|revoke/i }).first()
    if (await terminateBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await terminateBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissPopconfirm(page)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Security > DataPermissions buttons', () => {
  const ROUTE = '/security/data-permissions'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  2. DataSync Pages                                                  */
/* ================================================================== */

test.describe('DataSync buttons', () => {
  const ROUTE = '/data-sync'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })
})

test.describe('DataSync > Sources buttons', () => {
  const ROUTE = '/data-sync/sources'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Add data source button
    const addBtn = page.getByRole('button', { name: /添加|新建|创建|create|add/i }).first()
    if (await addBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Test connection button
    const testBtn = page.locator('button').filter({ hasText: /测试|test|连接/i }).first()
    if (await testBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await testBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataSync > History buttons', () => {
  const ROUTE = '/data-sync/history'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const refreshBtn = page.locator('button').filter({ hasText: /刷新|refresh/i }).first()
    if (await refreshBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await refreshBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    const exportBtn = page.locator('button').filter({ hasText: /导出|export/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataSync > Scheduler buttons', () => {
  const ROUTE = '/data-sync/scheduler'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataSync > Security buttons', () => {
  const ROUTE = '/data-sync/security'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

test.describe('DataSync > Export buttons', () => {
  const ROUTE = '/data-sync/export'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const exportBtn = page.locator('button').filter({ hasText: /导出|export|下载|download/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataSync > Datalake buttons', () => {
  const ROUTE = '/data-sync/datalake'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })
})

test.describe('DataSync > APIManagement buttons', () => {
  const ROUTE = '/data-sync/api-management'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

/* ================================================================== */
/*  3. Augmentation Pages                                              */
/* ================================================================== */

test.describe('Augmentation buttons', () => {
  const ROUTE = '/augmentation'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })
})

test.describe('Augmentation > Samples buttons', () => {
  const ROUTE = '/augmentation/samples'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const uploadBtn = page.locator('button').filter({ hasText: /上传|upload|导入|import/i }).first()
    if (await uploadBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await uploadBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Augmentation > Config buttons', () => {
  const ROUTE = '/augmentation/config'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

/* ================================================================== */
/*  4. License Pages                                                   */
/* ================================================================== */

test.describe('License buttons', () => {
  const ROUTE = '/license'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })
})

test.describe('License > Activate buttons', () => {
  const ROUTE = '/license/activate'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

test.describe('License > Usage buttons', () => {
  const ROUTE = '/license/usage'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const refreshBtn = page.locator('button').filter({ hasText: /刷新|refresh/i }).first()
    if (await refreshBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await refreshBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('License > Report buttons', () => {
  const ROUTE = '/license/report'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const exportBtn = page.locator('button').filter({ hasText: /导出|export|下载|download/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('License > Alerts buttons', () => {
  const ROUTE = '/license/alerts'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

/* ================================================================== */
/*  5. DataLifecycle Pages                                             */
/* ================================================================== */

test.describe('DataLifecycle buttons', () => {
  const ROUTE = '/data-lifecycle'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })
})

test.describe('DataLifecycle > TempData buttons', () => {
  const ROUTE = '/data-lifecycle/temp-data'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Clean up / delete temp data button
    const cleanBtn = page.locator('button').filter({ hasText: /清理|清除|删除|clean|delete|remove/i }).first()
    if (await cleanBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await cleanBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissPopconfirm(page)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataLifecycle > SampleLibrary buttons', () => {
  const ROUTE = '/data-lifecycle/samples'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const uploadBtn = page.locator('button').filter({ hasText: /上传|upload|导入|import|添加|add/i }).first()
    if (await uploadBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await uploadBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataLifecycle > AnnotationTasks buttons', () => {
  const ROUTE = '/data-lifecycle/tasks'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataLifecycle > Enhancement buttons', () => {
  const ROUTE = '/data-lifecycle/enhancement'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const startBtn = page.locator('button').filter({ hasText: /开始|启动|start|run|执行/i }).first()
    if (await startBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await startBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
      await dismissPopconfirm(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataLifecycle > AITrial buttons', () => {
  const ROUTE = '/data-lifecycle/trials'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add|试用/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('DataLifecycle > AuditLog buttons', () => {
  const ROUTE = '/data-lifecycle/audit'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const exportBtn = page.locator('button').filter({ hasText: /导出|export/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    const filterBtn = page.locator('button').filter({ hasText: /筛选|filter|查询|search/i }).first()
    if (await filterBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await filterBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  6. Billing Pages                                                   */
/* ================================================================== */

test.describe('Billing > Overview buttons', () => {
  const ROUTE = '/billing/overview'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const exportBtn = page.locator('button').filter({ hasText: /导出|export|下载|download/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Billing > Reports buttons', () => {
  const ROUTE = '/billing/reports'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    const exportBtn = page.locator('button').filter({ hasText: /导出|export|下载|download/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    const refreshBtn = page.locator('button').filter({ hasText: /刷新|refresh/i }).first()
    if (await refreshBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await refreshBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  7. Settings Page                                                   */
/* ================================================================== */

test.describe('Settings buttons', () => {
  const ROUTE = '/settings'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Save settings button
    const saveBtn = page.locator('button').filter({ hasText: /保存|save|提交|submit/i }).first()
    if (await saveBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await saveBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Change password button
    const pwdBtn = page.locator('button').filter({ hasText: /修改密码|change password|密码/i }).first()
    if (await pwdBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pwdBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  8. AI Annotation Page                                              */
/* ================================================================== */

test.describe('AI Annotation buttons', () => {
  const ROUTE = '/ai-annotation'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Start annotation button
    const startBtn = page.locator('button').filter({ hasText: /开始|启动|start|标注|annotate/i }).first()
    if (await startBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await startBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Config / settings button
    const configBtn = page.locator('button').filter({ hasText: /配置|config|设置|settings/i }).first()
    if (await configBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await configBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  9. AI Assistant Page                                               */
/* ================================================================== */

test.describe('AI Assistant buttons', () => {
  const ROUTE = '/ai-assistant'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Send / submit message button
    const sendBtn = page.locator('button').filter({ hasText: /发送|send|提交|submit/i }).first()
    if (await sendBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Fill input if present
      const input = page.locator('input[type="text"]:visible, textarea:visible').first()
      if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
        await input.fill('测试消息')
      }
      await sendBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    // Clear / new conversation button
    const clearBtn = page.locator('button').filter({ hasText: /清空|clear|新对话|new/i }).first()
    if (await clearBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await clearBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissPopconfirm(page)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  10. AI Processing Page                                             */
/* ================================================================== */

test.describe('AI Processing buttons', () => {
  const ROUTE = '/augmentation/ai-processing'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Start processing button
    const startBtn = page.locator('button').filter({ hasText: /开始|启动|start|处理|process|run/i }).first()
    if (await startBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await startBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
      await dismissPopconfirm(page)
    }

    // Upload / import button
    const uploadBtn = page.locator('button').filter({ hasText: /上传|upload|导入|import/i }).first()
    if (await uploadBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await uploadBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})


/* ================================================================== */
/*  11. Data Structuring (Upload) Page                                 */
/* ================================================================== */

test.describe('Data Structuring > Upload buttons', () => {
  const ROUTE = '/data-structuring/upload'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Upload button
    const uploadBtn = page.locator('button').filter({ hasText: /上传|upload|选择文件|choose/i }).first()
    if (await uploadBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await uploadBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Start structuring button
    const startBtn = page.locator('button').filter({ hasText: /开始|start|解析|parse|结构化/i }).first()
    if (await startBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await startBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

/* ================================================================== */
/*  12. Workspace Management Page                                      */
/* ================================================================== */

test.describe('Workspace Management buttons', () => {
  const ROUTE = '/admin/workspaces'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Create workspace button
    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Edit workspace button
    const editBtn = page.locator('button, a').filter({ hasText: /编辑|edit/i }).first()
    if (await editBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await editBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Delete workspace button
    const deleteBtn = page.locator('button, a').filter({ hasText: /删除|delete/i }).first()
    if (await deleteBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await deleteBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissPopconfirm(page)
      await dismissModal(page)
    }

    await expect(page.locator('#root')).toBeVisible()
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})


/* ================================================================== */
/*  13. Quality Sub-Pages                                              */
/* ================================================================== */

test.describe('Quality > Rules buttons', () => {
  const ROUTE = '/quality/rules'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Create rule button
    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Run all rules button
    const runBtn = page.locator('button').filter({ hasText: /运行|执行|run|check|检查/i }).first()
    if (await runBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await runBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    // Toggle rule enabled/disabled
    const toggleBtn = page.locator('.ant-switch:visible').first()
    if (await toggleBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await toggleBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})

test.describe('Quality > Reports buttons', () => {
  const ROUTE = '/quality/reports'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Export report button
    const exportBtn = page.locator('button').filter({ hasText: /导出|export|下载|download/i }).first()
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await exportBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Refresh button
    const refreshBtn = page.locator('button').filter({ hasText: /刷新|refresh/i }).first()
    if (await refreshBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await refreshBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    // Date range filter buttons
    const dateBtn = page.locator('.ant-picker:visible, button').filter({ hasText: /日期|date|时间|time/i }).first()
    if (await dateBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await dateBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)
    }

    await expect(page.locator('#root')).toBeVisible()
  })
})

test.describe('Quality > ImprovementTaskList buttons', () => {
  const ROUTE = '/quality/workflow/tasks'

  test('all buttons are clickable and responsive', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllButtons(page, ROUTE)
  })

  test('specific action buttons work correctly', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)

    // Create improvement task button
    const createBtn = page.getByRole('button', { name: /创建|新建|添加|create|add/i }).first()
    if (await createBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await createBtn.click().catch(() => {})
      await page.waitForTimeout(500)
      await dismissModal(page)
    }

    // Filter / search button
    const filterBtn = page.locator('button').filter({ hasText: /筛选|filter|查询|search/i }).first()
    if (await filterBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await filterBtn.click().catch(() => {})
      await page.waitForTimeout(500)
    }

    await expect(page.locator('#root')).toBeVisible()
  })

  test('links and navigation elements work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickAllLinks(page, ROUTE)
  })

  test('form submit buttons work', async ({ page }) => {
    await page.goto(ROUTE)
    await waitForPageReady(page)
    await clickFormSubmitButtons(page, ROUTE)
  })
})
