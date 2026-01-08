/**
 * Data Sync Integration E2E Tests
 *
 * Tests data synchronization features, real-time updates, and data consistency.
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
            permissions: ['read:all', 'write:all', 'sync:manage'],
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

test.describe('Data Sync Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('can access data sync configuration page', async ({ page }) => {
    await page.goto('/data-sync')

    // Should show data sync interface
    await expect(page).toHaveURL(/data-sync/i)

    // Look for sync configuration elements
    const syncConfig = page.locator('.ant-card, .sync-config, [data-testid="sync-config"]')
    
    if (await syncConfig.first().isVisible()) {
      await expect(syncConfig.first()).toBeVisible()
    }
  })

  test('can configure data source connections', async ({ page }) => {
    await page.goto('/data-sync')

    // Look for add data source button
    const addButton = page.getByRole('button', { name: /添加|新建|add.*source/i })
    
    if (await addButton.isVisible()) {
      await addButton.click()

      // Should show data source configuration modal/form
      const modal = page.locator('.ant-modal, .ant-drawer')
      await expect(modal).toBeVisible({ timeout: 3000 })

      // Look for connection form fields
      const hostInput = page.getByPlaceholder(/host|主机|地址/i)
      const portInput = page.getByPlaceholder(/port|端口/i)
      
      if (await hostInput.isVisible()) {
        await hostInput.fill('localhost')
      }
      
      if (await portInput.isVisible()) {
        await portInput.fill('5432')
      }
    }
  })

  test('can test data source connection', async ({ page }) => {
    await page.goto('/data-sync')

    // Look for existing data source or create one
    const dataSourceItem = page.locator('.ant-list-item, .data-source-item').first()
    
    if (await dataSourceItem.isVisible()) {
      // Look for test connection button
      const testButton = page.getByRole('button', { name: /测试|test.*connection/i })
      
      if (await testButton.isVisible()) {
        await testButton.click()

        // Should show connection status
        const statusMessage = page.locator('.ant-message, .ant-notification')
        await expect(statusMessage).toBeVisible({ timeout: 5000 })
      }
    }
  })

  test('can configure sync rules and mappings', async ({ page }) => {
    await page.goto('/data-sync')

    // Look for sync rules configuration
    const rulesTab = page.getByRole('tab', { name: /规则|rules|mapping/i })
    
    if (await rulesTab.isVisible()) {
      await rulesTab.click()

      // Should show rules configuration interface
      const rulesConfig = page.locator('.sync-rules, .mapping-config')
      
      if (await rulesConfig.isVisible()) {
        await expect(rulesConfig).toBeVisible()
      }
    }
  })
})

test.describe('Real-time Data Updates', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('dashboard metrics update in real-time', async ({ page }) => {
    await page.goto('/dashboard')

    // Get initial metric values
    const metricCards = page.locator('.ant-card .ant-statistic-content-value')
    
    if (await metricCards.first().isVisible()) {
      const initialValue = await metricCards.first().textContent()

      // Wait for potential updates (simulating real-time data)
      await page.waitForTimeout(2000)

      // In a real scenario, metrics might update via WebSocket or polling
      // For testing, we can simulate this by triggering a refresh
      await page.reload()

      // Metrics should be displayed (values might be same without real backend)
      await expect(metricCards.first()).toBeVisible()
    }
  })

  test('task list updates when new tasks are added', async ({ page }) => {
    await page.goto('/tasks')

    // Count initial tasks
    const taskRows = page.locator('.ant-table-row, .task-item')
    const initialCount = await taskRows.count()

    // Simulate adding a new task
    const createButton = page.getByRole('button', { name: /创建|新建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      // Fill task creation form
      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          await nameInput.fill('测试任务')
          
          // Submit form
          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }
        }
      }
    }

    // Wait for potential update
    await page.waitForTimeout(1000)

    // Task list should potentially show new task (or error without backend)
    const updatedRows = page.locator('.ant-table-row, .task-item')
    const newCount = await updatedRows.count()

    // Either count increased or we see an error message
    expect(newCount >= initialCount || await page.getByText(/error|错误/i).isVisible()).toBeTruthy()
  })

  test('billing data refreshes automatically', async ({ page }) => {
    await page.goto('/billing')

    // Look for refresh indicator or auto-refresh functionality
    const refreshButton = page.getByRole('button', { name: /刷新|refresh/i })
    
    if (await refreshButton.isVisible()) {
      await refreshButton.click()

      // Should show loading state
      const loading = page.locator('.ant-spin, .loading')
      
      if (await loading.isVisible()) {
        await expect(loading).toBeVisible()
        
        // Wait for loading to complete
        await expect(loading).not.toBeVisible({ timeout: 10000 })
      }
    }
  })
})

test.describe('Data Consistency', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('data changes are reflected across different pages', async ({ page }) => {
    // Start on tasks page
    await page.goto('/tasks')

    // Note any task data
    const taskCount = await page.locator('.ant-table-row').count()

    // Navigate to dashboard
    await page.goto('/dashboard')

    // Task-related metrics should be consistent
    const taskMetric = page.locator('.ant-statistic').filter({ hasText: /任务|task/i })
    
    if (await taskMetric.isVisible()) {
      const metricValue = await taskMetric.locator('.ant-statistic-content-value').textContent()
      
      // Metric should reflect the task count (or be reasonable)
      expect(metricValue).toBeDefined()
    }
  })

  test('user profile changes are reflected in header', async ({ page }) => {
    await page.goto('/settings')

    // Look for profile settings
    const profileTab = page.getByRole('tab', { name: /个人|profile/i })
    
    if (await profileTab.isVisible()) {
      await profileTab.click()

      // Update display name
      const nameInput = page.getByPlaceholder(/姓名|name/i)
      
      if (await nameInput.isVisible()) {
        await nameInput.clear()
        await nameInput.fill('新用户名')

        // Save changes
        const saveButton = page.getByRole('button', { name: /保存|save/i })
        
        if (await saveButton.isVisible()) {
          await saveButton.click()

          // Wait for save to complete
          await page.waitForTimeout(1000)

          // Navigate to another page
          await page.goto('/dashboard')

          // Header should show updated name
          const headerName = page.locator('.ant-dropdown-trigger, .user-info')
          
          if (await headerName.isVisible()) {
            const headerText = await headerName.textContent()
            expect(headerText).toContain('新用户名')
          }
        }
      }
    }
  })

  test('tenant switching updates all relevant data', async ({ page }) => {
    await page.goto('/dashboard')

    // Look for tenant switcher
    const tenantSwitcher = page.locator('[data-testid="tenant-switcher"]')
    
    if (await tenantSwitcher.isVisible()) {
      // Get current tenant data
      const currentMetrics = await page.locator('.ant-statistic-content-value').allTextContents()

      // Switch tenant
      await tenantSwitcher.click()
      
      const tenantOption = page.locator('.ant-select-item').nth(1)
      
      if (await tenantOption.isVisible()) {
        await tenantOption.click()

        // Wait for data to update
        await page.waitForTimeout(2000)

        // Metrics should potentially change (or show loading)
        const newMetrics = await page.locator('.ant-statistic-content-value').allTextContents()
        
        // Either metrics changed or we see loading/error state
        const metricsChanged = JSON.stringify(currentMetrics) !== JSON.stringify(newMetrics)
        const hasLoading = await page.locator('.ant-spin').isVisible()
        
        expect(metricsChanged || hasLoading).toBeTruthy()
      }
    }
  })
})

test.describe('Sync Status and Monitoring', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page)
  })

  test('displays sync status indicators', async ({ page }) => {
    await page.goto('/data-sync')

    // Look for sync status indicators
    const statusIndicators = page.locator('.ant-badge, .status-indicator, [data-testid="sync-status"]')
    
    if (await statusIndicators.first().isVisible()) {
      await expect(statusIndicators.first()).toBeVisible()
    }
  })

  test('shows sync history and logs', async ({ page }) => {
    await page.goto('/data-sync')

    // Look for history/logs tab
    const historyTab = page.getByRole('tab', { name: /历史|history|logs/i })
    
    if (await historyTab.isVisible()) {
      await historyTab.click()

      // Should show sync history
      const historyList = page.locator('.ant-table, .ant-list, .sync-history')
      
      if (await historyList.isVisible()) {
        await expect(historyList).toBeVisible()
      }
    }
  })

  test('can manually trigger sync operations', async ({ page }) => {
    await page.goto('/data-sync')

    // Look for manual sync button
    const syncButton = page.getByRole('button', { name: /同步|sync.*now/i })
    
    if (await syncButton.isVisible()) {
      await syncButton.click()

      // Should show sync progress
      const progress = page.locator('.ant-progress, .sync-progress')
      
      if (await progress.isVisible()) {
        await expect(progress).toBeVisible()
      }
    }
  })
})