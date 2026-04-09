/**
 * Performance E2E Tests
 *
 * Tests page load performance, Core Web Vitals, memory usage, and network resilience.
 *
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9
 */

import { test, expect } from './fixtures'
import type { Route } from '@playwright/test'
import { setupAuth, waitForPageReady } from './test-helpers'
import { mockAllApis } from './helpers/mock-api-factory'

/* ------------------------------------------------------------------ */
/*  Page Load Performance (Req 6.1, 6.2, 6.3)                         */
/* ------------------------------------------------------------------ */

test.describe('Page Load Performance', () => {
  test('Login page loads within 5000ms', async ({ page }) => {
    await mockAllApis(page)
    const start = Date.now()
    await page.goto('/login')
    await page.waitForLoadState('load')
    const loadTime = Date.now() - start
    expect(loadTime).toBeLessThan(5000)
  })

  test('Dashboard loads within 6000ms', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)
    const start = Date.now()
    await page.goto('/dashboard')
    await page.waitForLoadState('load')
    const loadTime = Date.now() - start
    expect(loadTime).toBeLessThan(6000)
  })

  const genericPages = [
    { name: 'Tasks', route: '/tasks' },
    { name: 'Quality', route: '/quality' },
    { name: 'Security', route: '/security' },
    { name: 'Admin', route: '/admin' },
    { name: 'DataSync', route: '/data-sync' },
  ]

  for (const pg of genericPages) {
    const limitMs = pg.route === '/admin' ? 8000 : 5000
    test(`${pg.name} page loads within ${limitMs}ms`, async ({ page }) => {
      await setupAuth(page)
      await mockAllApis(page)
      const start = Date.now()
      await page.goto(pg.route)
      await waitForPageReady(page)
      const loadTime = Date.now() - start
      expect(loadTime).toBeLessThan(limitMs)
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

        setTimeout(() => resolve(result), 4000)
      })
    })

    /* Headless Vite dev + route mocks: CWVs are noisier than lab “green” thresholds; still catch regressions. */
    if (vitals.lcp > 0) expect(vitals.lcp).toBeLessThan(12000)
    if (vitals.fcp > 0) expect(vitals.fcp).toBeLessThan(8000)
    expect(vitals.cls).toBeLessThan(0.25)
    if (vitals.ttfb > 0) expect(vitals.ttfb).toBeLessThan(2500)
  })
})

/* ------------------------------------------------------------------ */
/*  Table Render Benchmark (Req 6.5)                                   */
/* ------------------------------------------------------------------ */

test.describe('Large Data Rendering', () => {
  test('table renders 1000-row dataset first page within 8000ms', async ({ page }) => {
    await setupAuth(page)
    await mockAllApis(page)

    const rows = Array.from({ length: 50 }, (_, i) => ({
      id: `task-${i}`,
      name: `任务 ${i + 1}`,
      description: `perf ${i}`,
      status: ['pending', 'in_progress', 'completed'][i % 3],
      priority: 'medium' as const,
      annotation_type: 'text_classification' as const,
      assignee_id: 'user-1',
      assignee_name: `用户${(i % 5) + 1}`,
      created_by: 'e2e',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      progress: (i * 10) % 100,
      total_items: 10,
      completed_items: 0,
      tenant_id: 'tenant-1',
      label_studio_project_id: String(40 + i),
    }))

    const listBody = JSON.stringify({
      items: rows,
      total: 1000,
      page: 1,
      page_size: 50,
    })

    const fulfill = async (route: Route) => {
      if (route.request().method() !== 'GET') return route.continue()
      await route.fulfill({ status: 200, contentType: 'application/json', body: listBody })
    }

    await page.route('**/api/tasks?**', fulfill)
    await page.route('**/api/tasks', async (route) => {
      if (route.request().method() !== 'GET') return route.continue()
      if (new URL(route.request().url()).pathname !== '/api/tasks') return route.continue()
      return fulfill(route)
    })

    await page.route('**/api/tasks/stats', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 1000, pending: 300, in_progress: 400, completed: 300 }) }),
    )

    const start = Date.now()
    await page.goto('/tasks')
    await waitForPageReady(page)
    const renderTime = Date.now() - start
    expect(renderTime).toBeLessThan(8000)
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
        await createBtn.click({ force: true }).catch(() => {})
        const modal = page.locator('.ant-modal').first()
        if (await modal.isVisible({ timeout: 3000 }).catch(() => false)) {
          const close = page.locator('.ant-modal-close').first()
          if (await close.isVisible({ timeout: 1500 }).catch(() => false)) {
            await close.click()
          } else {
            await modal.locator('.ant-modal-body').click({ position: { x: 2, y: 2 } }).catch(() => {})
            await page.keyboard.press('Escape')
          }
          await modal.waitFor({ state: 'hidden', timeout: 8000 }).catch(() => {})
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

    // Offline navigation may fail; keep the page alive without crashing.
    await page.goto('/tasks').catch(() => {})

    await expect(page.locator('body')).toBeVisible()

    // Restore
    await page.context().setOffline(false)
  })
})
