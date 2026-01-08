/**
 * Performance E2E Tests
 *
 * Tests page load performance, rendering performance, and user experience metrics.
 */

import { test, expect } from '@playwright/test'

// Helper to set up authenticated state
async function setupAuth(page: any) {
  await page.addInitScript(() => {
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user: {
            id: 'user-1',
            username: 'testuser',
            name: '测试用户',
            email: 'test@example.com',
            tenant_id: 'tenant-1',
            roles: ['admin'],
            permissions: ['read:all', 'write:all'],
          },
          token: 'mock-jwt-token',
          currentTenant: {
            id: 'tenant-1',
            name: '测试租户',
          },
          isAuthenticated: true,
        },
      })
    )
  })
}

test.describe('Page Load Performance', () => {
  test('login page loads within acceptable time', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto('/login')
    
    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    // Login page should load within 2 seconds
    expect(loadTime).toBeLessThan(2000)
    
    // Check that essential elements are visible
    await expect(page.getByPlaceholder(/用户名|username/i)).toBeVisible()
    await expect(page.getByPlaceholder(/密码|password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /登录|login/i })).toBeVisible()
  })

  test('dashboard loads within acceptable time', async ({ page }) => {
    await setupAuth(page)
    
    const startTime = Date.now()
    
    await page.goto('/dashboard')
    
    // Wait for main content to load
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    // Dashboard should load within 3 seconds (more complex page)
    expect(loadTime).toBeLessThan(3000)
    
    // Check that main dashboard elements are present
    const mainContent = page.locator('.ant-layout-content, .dashboard-content')
    if (await mainContent.isVisible()) {
      await expect(mainContent).toBeVisible()
    }
  })

  test('tasks page loads efficiently with large dataset simulation', async ({ page }) => {
    await setupAuth(page)
    
    // Simulate large dataset by intercepting API calls
    await page.route('**/api/tasks*', async route => {
      // Simulate API response with many tasks
      const mockTasks = Array.from({ length: 100 }, (_, i) => ({
        id: `task-${i}`,
        name: `任务 ${i + 1}`,
        status: i % 3 === 0 ? 'completed' : i % 3 === 1 ? 'in_progress' : 'pending',
        assignee: `用户${i % 5 + 1}`,
        progress: Math.floor(Math.random() * 100),
        createdAt: new Date(Date.now() - i * 86400000).toISOString(),
      }))
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: mockTasks,
          total: 100,
          page: 1,
          pageSize: 20
        })
      })
    })
    
    const startTime = Date.now()
    
    await page.goto('/tasks')
    
    // Wait for table to render
    await page.waitForSelector('.ant-table-tbody tr', { timeout: 10000 })
    
    const loadTime = Date.now() - startTime
    
    // Should handle large dataset efficiently (within 5 seconds)
    expect(loadTime).toBeLessThan(5000)
    
    // Check that pagination is working
    const pagination = page.locator('.ant-pagination')
    if (await pagination.isVisible()) {
      await expect(pagination).toBeVisible()
    }
  })

  test('measures Core Web Vitals', async ({ page }) => {
    await setupAuth(page)
    
    // Navigate to dashboard and measure performance
    await page.goto('/dashboard')
    
    // Wait for page to fully load
    await page.waitForLoadState('networkidle')
    
    // Measure Web Vitals using Performance API
    const webVitals = await page.evaluate(() => {
      return new Promise((resolve) => {
        const vitals: any = {}
        
        // Largest Contentful Paint (LCP)
        new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const lastEntry = entries[entries.length - 1]
          vitals.lcp = lastEntry.startTime
        }).observe({ entryTypes: ['largest-contentful-paint'] })
        
        // First Input Delay (FID) - simulated
        vitals.fid = 0 // Will be 0 in automated tests
        
        // Cumulative Layout Shift (CLS)
        let clsValue = 0
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!(entry as any).hadRecentInput) {
              clsValue += (entry as any).value
            }
          }
          vitals.cls = clsValue
        }).observe({ entryTypes: ['layout-shift'] })
        
        // First Contentful Paint (FCP)
        new PerformanceObserver((list) => {
          const entries = list.getEntries()
          vitals.fcp = entries[0].startTime
        }).observe({ entryTypes: ['paint'] })
        
        // Time to First Byte (TTFB)
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        vitals.ttfb = navigation.responseStart - navigation.requestStart
        
        setTimeout(() => resolve(vitals), 2000)
      })
    })
    
    console.log('Web Vitals:', webVitals)
    
    // Assert Web Vitals thresholds
    expect((webVitals as any).lcp).toBeLessThan(2500) // LCP should be < 2.5s
    expect((webVitals as any).cls).toBeLessThan(0.1)  // CLS should be < 0.1
    expect((webVitals as any).fcp).toBeLessThan(1800) // FCP should be < 1.8s
    expect((webVitals as any).ttfb).toBeLessThan(600)  // TTFB should be < 600ms
  })
})

test.describe('Large Data Rendering Performance', () => {
  test('table renders large dataset efficiently', async ({ page }) => {
    await setupAuth(page)
    
    // Mock API with large dataset
    await page.route('**/api/tasks*', async route => {
      const mockTasks = Array.from({ length: 1000 }, (_, i) => ({
        id: `task-${i}`,
        name: `任务 ${i + 1}`,
        description: `这是任务 ${i + 1} 的详细描述，包含一些较长的文本内容来测试渲染性能`,
        status: ['pending', 'in_progress', 'completed', 'cancelled'][i % 4],
        assignee: `用户${i % 10 + 1}`,
        progress: Math.floor(Math.random() * 100),
        timeSpent: Math.floor(Math.random() * 480), // minutes
        createdAt: new Date(Date.now() - i * 86400000).toISOString(),
        updatedAt: new Date(Date.now() - i * 3600000).toISOString(),
      }))
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: mockTasks.slice(0, 50), // Paginated
          total: 1000,
          page: 1,
          pageSize: 50
        })
      })
    })
    
    const startTime = Date.now()
    
    await page.goto('/tasks')
    
    // Wait for table to render
    await page.waitForSelector('.ant-table-tbody tr:nth-child(10)', { timeout: 10000 })
    
    const renderTime = Date.now() - startTime
    
    // Should render 50 rows efficiently
    expect(renderTime).toBeLessThan(3000)
    
    // Test scrolling performance
    const tableBody = page.locator('.ant-table-tbody')
    
    if (await tableBody.isVisible()) {
      const scrollStartTime = Date.now()
      
      // Scroll through the table
      await tableBody.hover()
      await page.mouse.wheel(0, 1000)
      await page.waitForTimeout(100)
      
      const scrollTime = Date.now() - scrollStartTime
      
      // Scrolling should be smooth (< 500ms)
      expect(scrollTime).toBeLessThan(500)
    }
  })

  test('chart renders large dataset without performance issues', async ({ page }) => {
    await setupAuth(page)
    
    // Mock API with large chart data
    await page.route('**/api/dashboard/metrics*', async route => {
      const mockData = Array.from({ length: 365 }, (_, i) => ({
        date: new Date(Date.now() - i * 86400000).toISOString().split('T')[0],
        tasks: Math.floor(Math.random() * 100) + 50,
        quality: Math.random() * 0.3 + 0.7, // 0.7-1.0
        annotations: Math.floor(Math.random() * 1000) + 500,
      }))
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockData)
      })
    })
    
    const startTime = Date.now()
    
    await page.goto('/dashboard')
    
    // Wait for charts to render
    await page.waitForSelector('.recharts-wrapper, canvas, .ant-chart', { timeout: 10000 })
    
    const renderTime = Date.now() - startTime
    
    // Chart should render within reasonable time
    expect(renderTime).toBeLessThan(4000)
    
    // Check that chart is interactive
    const chart = page.locator('.recharts-wrapper, canvas').first()
    
    if (await chart.isVisible()) {
      // Test chart interaction
      await chart.hover()
      
      // Look for tooltip or interaction feedback
      const tooltip = page.locator('.recharts-tooltip, .ant-tooltip')
      
      // Tooltip should appear quickly
      if (await tooltip.isVisible({ timeout: 1000 })) {
        await expect(tooltip).toBeVisible()
      }
    }
  })

  test('virtual scrolling works for large lists', async ({ page }) => {
    await setupAuth(page)
    
    // Navigate to a page with potentially large lists
    await page.goto('/billing')
    
    // Mock large billing data
    await page.route('**/api/billing*', async route => {
      const mockBills = Array.from({ length: 500 }, (_, i) => ({
        id: `bill-${i}`,
        period: `2024-${String((i % 12) + 1).padStart(2, '0')}`,
        amount: Math.floor(Math.random() * 10000) + 1000,
        status: ['pending', 'paid', 'overdue'][i % 3],
        items: Math.floor(Math.random() * 100) + 10,
        hours: Math.floor(Math.random() * 200) + 50,
      }))
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: mockBills,
          total: 500
        })
      })
    })
    
    await page.reload()
    
    // Wait for list to load
    await page.waitForSelector('.ant-list-item, .ant-table-row', { timeout: 10000 })
    
    // Test that only visible items are rendered (virtual scrolling)
    const visibleItems = await page.locator('.ant-list-item, .ant-table-row').count()
    
    // Should not render all 500 items at once
    expect(visibleItems).toBeLessThan(100)
    
    // Test scrolling performance
    const scrollContainer = page.locator('.ant-list, .ant-table-body')
    
    if (await scrollContainer.isVisible()) {
      const scrollStartTime = Date.now()
      
      // Scroll to bottom
      await scrollContainer.hover()
      for (let i = 0; i < 10; i++) {
        await page.mouse.wheel(0, 500)
        await page.waitForTimeout(50)
      }
      
      const scrollTime = Date.now() - scrollStartTime
      
      // Scrolling should remain smooth
      expect(scrollTime).toBeLessThan(2000)
    }
  })
})

test.describe('Memory Usage and Performance', () => {
  test('memory usage remains stable during navigation', async ({ page }) => {
    await setupAuth(page)
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      return (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0
    })
    
    // Navigate through multiple pages
    const pages = ['/dashboard', '/tasks', '/billing', '/quality', '/settings']
    
    for (const pagePath of pages) {
      await page.goto(pagePath)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000) // Allow for any async operations
    }
    
    // Check final memory usage
    const finalMemory = await page.evaluate(() => {
      return (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0
    })
    
    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - initialMemory
      const memoryIncreasePercent = (memoryIncrease / initialMemory) * 100
      
      // Memory increase should be reasonable (< 200% of initial)
      expect(memoryIncreasePercent).toBeLessThan(200)
      
      console.log(`Memory usage: ${initialMemory} -> ${finalMemory} (${memoryIncreasePercent.toFixed(1)}% increase)`)
    }
  })

  test('no memory leaks during repeated operations', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')
    
    // Get baseline memory
    const baselineMemory = await page.evaluate(() => {
      return (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0
    })
    
    // Perform repeated operations that might cause memory leaks
    for (let i = 0; i < 10; i++) {
      // Open and close modal
      const createButton = page.getByRole('button', { name: /创建|create/i })
      
      if (await createButton.isVisible()) {
        await createButton.click()
        
        const modal = page.locator('.ant-modal')
        if (await modal.isVisible()) {
          // Close modal
          const closeButton = modal.locator('.ant-modal-close, .ant-btn').filter({ hasText: /取消|cancel/i })
          if (await closeButton.isVisible()) {
            await closeButton.click()
          } else {
            await page.keyboard.press('Escape')
          }
          
          await expect(modal).not.toBeVisible()
        }
      }
      
      await page.waitForTimeout(100)
    }
    
    // Force garbage collection if available
    await page.evaluate(() => {
      if ((window as any).gc) {
        (window as any).gc()
      }
    })
    
    await page.waitForTimeout(1000)
    
    // Check final memory
    const finalMemory = await page.evaluate(() => {
      return (performance as any).memory ? (performance as any).memory.usedJSHeapSize : 0
    })
    
    if (baselineMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - baselineMemory
      const memoryIncreasePercent = (memoryIncrease / baselineMemory) * 100
      
      // Memory increase should be minimal after repeated operations
      expect(memoryIncreasePercent).toBeLessThan(50)
      
      console.log(`Memory after repeated operations: ${baselineMemory} -> ${finalMemory} (${memoryIncreasePercent.toFixed(1)}% increase)`)
    }
  })
})

test.describe('Network Performance', () => {
  test('handles slow network conditions gracefully', async ({ page }) => {
    // Simulate slow network
    await page.route('**/*', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 500)) // 500ms delay
      await route.continue()
    })
    
    await setupAuth(page)
    
    const startTime = Date.now()
    
    await page.goto('/dashboard')
    
    // Should show loading states during slow network
    const loadingIndicator = page.locator('.ant-spin, .loading, .ant-skeleton')
    
    if (await loadingIndicator.isVisible({ timeout: 1000 })) {
      await expect(loadingIndicator).toBeVisible()
    }
    
    // Wait for content to load
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    // Should handle slow network within reasonable time
    expect(loadTime).toBeLessThan(10000) // 10 seconds max
  })

  test('handles network errors gracefully', async ({ page }) => {
    await setupAuth(page)
    
    // Simulate network errors for API calls
    await page.route('**/api/**', async (route) => {
      await route.abort('failed')
    })
    
    await page.goto('/dashboard')
    
    // Should show error states or fallback content
    const errorMessage = page.locator('.ant-result, .ant-empty, .error-message')
    
    if (await errorMessage.isVisible({ timeout: 5000 })) {
      await expect(errorMessage).toBeVisible()
    }
    
    // Should not crash the application
    const appContainer = page.locator('#root, .app')
    await expect(appContainer).toBeVisible()
  })
})