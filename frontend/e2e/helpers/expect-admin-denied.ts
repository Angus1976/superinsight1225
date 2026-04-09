/**
 * Admin shell (`/admin`, `/admin/*`) blocks non-admin users with an in-page Alert
 * (see `Admin/index.tsx`). The URL is not rewritten to /403 or /dashboard.
 */
import type { Page } from '@playwright/test'
import { expect } from '@playwright/test'
import { waitForPageReady } from '../test-helpers'

export function isAdminPath(route: string): boolean {
  const r = route.split('?')[0].replace(/\/$/, '') || '/'
  return r === '/admin' || r.startsWith('/admin/')
}

export async function expectNonAdminBlockedOnAdminRoute(page: Page, route: string): Promise<void> {
  await page.goto(route)
  await waitForPageReady(page)
  const url = page.url()
  expect(url).not.toMatch(/\/login/)

  await expect(
    page
      .locator('.ant-alert')
      .filter({ hasText: /Access Denied|don't have permission|admin console|管理|权限/i }),
  ).toBeVisible({ timeout: 15000 })
}
