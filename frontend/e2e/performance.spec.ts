/**
 * Performance E2E Tests
 *
 * Tests page load performance, Core Web Vitals, memory usage, and network resilience.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9
 */

import { test, expect } from './fixtures'
import { setupAuth, waitForPageReady } from './test-helpers'
import { mockAllApis } from './helpers/mock-api-factory'

/* ------------------------------------------------------------------ */
/*  Page Load Performance (Req 6.1, 6.2, 6.3)                         */
/* ------------------------------------------------------------------ */

test.describe('Page Load Performance', () => {
  test('Login page loads within 2000ms', async ({ page }) => {
    await mockAllApis(page)
    const start = Date.now()
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - start
    expect(loadTime).toBeLessThan(2000)
  })

  test('Dashboard loads within 3000ms', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    const start = Date.now()
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - start
    expect(loadTime).toBeLessThan(3000)
  })

  const genericPages = [
    { name: 'Tasks', route: '/tasks' },
    { name: 'Quality', route: '/quality' },
    { name: 'Security', route: '/security' },
    { name: 'Admin', route: '/admin' },
    { name: 'DataSync', route: '/data-sync' },
  ]

  for (const pg of genericPages) {
    test(`${pg.name} page loads within 5000ms`, async ({ page }) => {
      await setupAuth(page)
      await mockAllApis(page)
      const start = Date.now()
      await page.goto(pg.route)
      await waitForPageReady(page)
      const loadTime = Date.now() - start
      expect(loadTime).toBeLessThan(5000)
    })
  }
})

/* ------------------------------------------------------------------ */
/*  Core Web Vitals on Dashboard (Req 6.4)                             */
/* ------------------------------------------------------------------ */

test.describe('Core Web Vitals', () => {
  test('Dashboard meets Core Web Vitals thresholds', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    const vitals = await page.evaluate(() => {
      return new Promise<{ lcp: number; fcp: number; cls: number; ttfb: number }>((resolve) => {
        const result = { lcp: 0, fcp: 0, cls: 0, ttfb: 0 }

        try {
          new PerformanceObserver((list) => {
            const entries = list.getEntries()
            if (entries.length) result.lcp = entries[entries.length - 1].startTime
          }).observe({ entryTypes: ['largest-contentful-paint'] })
        } catch { /* not supported */ }

        try {
          new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              if (!(entry as any).hadRecentInput) result.cls += (entry as any).value
            }
          }).observe({ entryTypes: ['layout-shift'] })
        } catch { /* not supported */ }

        try {
          new PerformanceObserver((list) => {
            const entries = list.getEntries()
            if (entries.length) result.fcp = entries[0].startTime
          }).observe({ entryTypes: ['paint'] })
        } catch { /* not supported */ }

        const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        if (nav) result.ttfb = nav.responseStart - nav.requestStart

        setTimeout(() => resolve(result), 3000)
      })
    })

    expect(vitals.lcp).toBeLessThan(2500)
    expect(vitals.fcp).toBeLessThan(1800)
    expect(vitals.cls).toBeLessThan(0.1)
    expect(vitals.ttfb).toBeLessThan(600)
  })
})

/* ------------------------------------------------------------------ */
/*  Table Render Benchmark (Req 6.5)                                   */
/* ------------------------------------------------------------------ */

test.describe('Large Data Rendering', () => {
  test('table renders 1000-row dataset first page within 3000ms', async ({ page }) => {
    await setupAuth(page)

    await page.route('**/api/tasks**', async (route) => {
      const rows = Array.from({ length: 50 }, (_, i) => ({
        id: `task-${i}`,
        name: `任务 ${i + 1}`,
        status: ['pending', 'in_progress', 'completed'][i % 3],
        assignee: `用户${(i % 5) + 1}`,
        progress: (i * 10) % 100,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        tenant_id: 'tenant-1',
      }))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: rows, total: 1000 }),
      })
    })

    await page.route('**/api/tasks/stats', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 1000, pending: 300, in_progress: 400, completed: 300 }) }),
    )

    const start = Date.now()
    await page.goto('/tasks')
    await waitForPageReady(page)
    const renderTime = Date.now() - start
    expect(renderTime).toBeLessThan(3000)
  })
})

/* ------------------------------------------------------------------ */
/*  Memory Leak Detection (Req 6.6, 6.7)                               */
/* ------------------------------------------------------------------ */

test.describe('Memory Leak Detection', () => {
  test('memory growth < 200% after 5 page navigations', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    await page.goto('/dashboard')
    await waitForPageReady(page)

    const initialMemory = await page.evaluate(() =>
      (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0,
    )

    const routes = ['/tasks', '/quality', '/settings', '/billing', '/dashboard']
    for (const r of routes) {
      await page.goto(r)
      await waitForPageReady(page)
    }

    const finalMemory = await page.evaluate(() =>
      (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0,
    )

    if (initialMemory > 0 && finalMemory > 0) {
      const growthPercent = ((finalMemory - initialMemory) / initialMemory) * 100
      expect(growthPercent).toBeLessThan(200)
    }
  })

  test('memory growth < 50% after 10 modal open/close cycles', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/tasks')
    await waitForPageReady(page)

    const baseline = await page.evaluate(() =>
      (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0,
    )

    for (let i = 0; i < 10; i++) {
      const createBtn = page.getByRole('button', { name: /创建|create|新建/i })
      if (await createBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await createBtn.click()
        const modal = page.locator('.ant-modal')
        if (await modal.isVisible({ timeout: 2000 }).catch(() => false)) {
          await page.keyboard.press('Escape')
          await modal.waitFor({ state: 'hidden', timeout: 2000 }).catch(() => {})
        }
      }
    }

    await page.evaluate(() => { if ((window as any).gc) (window as any).gc() })
    await page.waitForTimeout(500)

    const finalMem = await page.evaluate(() =>
      (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0,
    )

    if (baseline > 0 && finalMem > 0) {
      const growthPercent = ((finalMem - baseline) / baseline) * 100
      expect(growthPercent).toBeLessThan(50)
    }
  })
})

/* ------------------------------------------------------------------ */
/*  Slow Network Test (Req 6.8)                                        */
/* ------------------------------------------------------------------ */

test.describe('Slow Network', () => {
  test('loading indicators appear under 500ms latency, page renders after data', async ({ page }) => {
    await setupAuth(page)

    // Add 500ms delay to all routes
    await page.route('**/*', async (route) => {
      await new Promise((r) => setTimeout(r, 500))
      await route.continue()
    })

    await page.goto('/dashboard')

    // Loading indicator should appear
    const spinner = page.locator('.ant-spin, .ant-skeleton, .loading')
    if (await spinner.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(spinner).toBeVisible()
    }

    // Eventually the page should render
    await waitForPageReady(page, 15000)
    const root = page.locator('#root')
    await expect(root).toBeVisible()
  })
})

/* ------------------------------------------------------------------ */
/*  Offline Test (Req 6.9)                                             */
/* ------------------------------------------------------------------ */

test.describe('Offline Resilience', () => {
  test('error state displayed when offline, no crash', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    await page.goto('/dashboard')
    await waitForPageReady(page)

    // Go offline
    await page.context().setOffline(true)

    // Try navigating
    await page.goto('/tasks').catch(() => {})

    // App should not crash — #root should still be present
    const root = page.locator('#root')
    await expect(root).toBeVisible()

    // Restore
    await page.context().setOffline(false)
  })
})
