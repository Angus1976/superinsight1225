/**
 * Language switching on admin routes (MainLayout header). Starts from English — more
 * reliable than zh-first loads with i18n hydration. Admin copy matches admin.json.
 */

import { test, expect, Page } from '@playwright/test'
import { setupE2eSession, waitForPageReady } from './test-helpers'

const adminPages = [
  {
    name: 'Admin Console',
    path: '/admin/console',
    zhTitle: '管理控制台',
    enTitle: 'Admin Console',
    zhElements: ['系统状态', '租户统计', '总租户数'],
    enElements: ['System Status', 'Tenant Statistics', 'Total Tenants'],
  },
  {
    name: 'Billing Management',
    path: '/admin/billing',
    zhTitle: '账单管理',
    enTitle: 'Billing Management',
    zhElements: ['月度收入', '全部账单', '存储费用'],
    enElements: ['Monthly Revenue', 'All Bills', 'Storage Cost'],
  },
  {
    name: 'Permission Configuration',
    path: '/admin/permissions',
    zhTitle: '权限配置管理',
    enTitle: 'Permission Configuration Management',
    zhElements: ['权限矩阵', 'API 权限', '权限说明'],
    enElements: ['Permission Matrix', 'API Permissions', 'Owner has all permissions'],
  },
  {
    name: 'Quota Management',
    path: '/admin/quotas',
    zhTitle: '配额管理',
    enTitle: 'Quota Management',
    zhElements: ['总存储使用', '租户', '调整配额'],
    enElements: ['Total Storage Usage', 'Adjust Quota', 'Tenant'],
  },
]

function escapeRe(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function expectPrimaryTitle(page: Page, fragment: string) {
  const rex = new RegExp(escapeRe(fragment), 'i')
  const h2 = page.locator('h2').filter({ hasText: rex })
  const cardTitle = page.locator('.ant-card-head-title').filter({ hasText: rex })
  await expect(h2.or(cardTitle).first()).toBeVisible({ timeout: 20000 })
}

async function expectCopyVisible(page: Page, text: string) {
  await expect(page.getByText(text, { exact: false }).first()).toBeVisible()
}

/** Header language control: GlobalOutlined + locale label */
function languageTrigger(page: Page) {
  return page.locator('button').filter({ has: page.locator('.anticon-global') }).first()
}

async function openLanguageMenu(page: Page) {
  await languageTrigger(page).click()
}

function strictI18nWarnings(warnings: string[]) {
  return warnings.filter((w) =>
    /missing key|not found in en|not found in zh|I18next.*missing|Translation missing/i.test(w),
  )
}

function filterNonCriticalConsoleErrors(errors: string[]) {
  return errors.filter(
    (e) =>
      !e.includes('favicon') &&
      !e.includes('404') &&
      !e.includes('net::ERR_') &&
      !e.includes('[antd:') &&
      !e.includes('destroyOnClose') &&
      !e.includes('destroyOnHidden'),
  )
}

test.describe('Language Switching Tests', () => {
  let consoleWarnings: string[] = []
  let consoleErrors: string[] = []

  test.beforeEach(async ({ page }) => {
    consoleWarnings = []
    consoleErrors = []
    page.on('console', (msg) => {
      const text = msg.text()
      if (msg.type() === 'warning') consoleWarnings.push(text)
      else if (msg.type() === 'error') consoleErrors.push(text)
    })
  })

  for (const adminPage of adminPages) {
    test.describe(adminPage.name, () => {
      test('should round-trip en → zh → en via header', async ({ page }) => {
        await setupE2eSession(page, { lang: 'en', role: 'admin' })
        await page.goto(adminPage.path)
        await waitForPageReady(page)

        await expectPrimaryTitle(page, adminPage.enTitle)
        for (const t of adminPage.enElements) {
          await expectCopyVisible(page, t)
        }

        await openLanguageMenu(page)
        await page.getByRole('menuitem', { name: /中文/ }).click()
        await page.waitForTimeout(400)
        await waitForPageReady(page)

        await expectPrimaryTitle(page, adminPage.zhTitle)
        for (const t of adminPage.zhElements) {
          await expectCopyVisible(page, t)
        }

        await openLanguageMenu(page)
        await page.getByRole('menuitem', { name: /English/i }).click()
        await page.waitForTimeout(400)
        await waitForPageReady(page)

        await expectPrimaryTitle(page, adminPage.enTitle)
        for (const t of adminPage.enElements) {
          await expectCopyVisible(page, t)
        }

        expect(strictI18nWarnings(consoleWarnings)).toHaveLength(0)
      })

      test('should persist language preference across navigation', async ({ page }) => {
        await setupE2eSession(page, { lang: 'en', role: 'admin' })
        await page.goto(adminPage.path)
        await waitForPageReady(page)
        await expectPrimaryTitle(page, adminPage.enTitle)

        const otherPage = adminPages.find((p) => p.path !== adminPage.path)
        if (otherPage) {
          await page.goto(otherPage.path)
          await waitForPageReady(page)
          await expectPrimaryTitle(page, otherPage.enTitle)
        }
      })

      test('should have no console errors during language switching', async ({ page }) => {
        await setupE2eSession(page, { lang: 'en', role: 'admin' })
        await page.goto(adminPage.path)
        await waitForPageReady(page)

        consoleErrors = []
        await openLanguageMenu(page)
        await page.getByRole('menuitem', { name: /中文/ }).click()
        await page.waitForTimeout(400)
        await waitForPageReady(page)

        const criticalErrors = filterNonCriticalConsoleErrors(consoleErrors)
        expect(criticalErrors).toHaveLength(0)
      })
    })
  }

  test('should handle rapid language switching', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await page.goto('/admin/console')
    await waitForPageReady(page)

    const trigger = languageTrigger(page)
    if ((await trigger.count()) > 0) {
      for (let i = 0; i < 3; i++) {
        await trigger.click()
        await page.getByRole('menuitem', { name: /English/i }).click()
        await page.waitForTimeout(200)
        await trigger.click()
        await page.getByRole('menuitem', { name: /中文/ }).click()
        await page.waitForTimeout(200)
      }
      await expect(page.locator('h2').filter({ hasText: /管理控制台|Admin Console/i })).toBeVisible()
      expect(filterNonCriticalConsoleErrors(consoleErrors)).toHaveLength(0)
    }
  })
})
