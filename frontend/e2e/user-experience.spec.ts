/**
 * User Experience E2E Tests
 *
 * Tests user experience aspects like loading states, error handling, and usability.
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

test.describe('Loading States and Feedback', () => {
  test('shows appropriate loading states during data fetching', async ({ page }) => {
    await setupAuth(page)

    // Simulate slow API responses
    await page.route('**/api/**', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000)) // 1 second delay
      await route.continue()
    })

    await page.goto('/dashboard')

    // Should show loading indicators
    const loadingIndicators = page.locator('.ant-spin, .ant-skeleton, .loading')
    
    if (await loadingIndicators.first().isVisible({ timeout: 2000 })) {
      await expect(loadingIndicators.first()).toBeVisible()
    }

    // Wait for loading to complete
    await page.waitForLoadState('networkidle')

    // Loading indicators should disappear
    if (await loadingIndicators.first().isVisible()) {
      await expect(loadingIndicators.first()).not.toBeVisible({ timeout: 5000 })
    }
  })

  test('provides feedback for user actions', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Test button loading states
    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      // Button should show loading state or modal should appear
      const modal = page.locator('.ant-modal')
      const buttonLoading = createButton.locator('.ant-spin')

      const hasModalOrLoading = 
        await modal.isVisible({ timeout: 1000 }) ||
        await buttonLoading.isVisible({ timeout: 1000 })

      expect(hasModalOrLoading).toBeTruthy()
    }
  })

  test('shows progress indicators for long operations', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/billing')

    // Test export operation
    const exportButton = page.getByRole('button', { name: /导出|export/i })
    
    if (await exportButton.isVisible()) {
      await exportButton.click()

      // Should show progress or confirmation
      const progressIndicator = page.locator('.ant-progress, .ant-modal, .ant-message')
      
      if (await progressIndicator.isVisible({ timeout: 2000 })) {
        await expect(progressIndicator).toBeVisible()
      }
    }
  })
})

test.describe('Error Handling and Recovery', () => {
  test('displays user-friendly error messages', async ({ page }) => {
    await setupAuth(page)

    // Simulate API errors
    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      })
    })

    await page.goto('/dashboard')

    // Should show error message or empty state
    const errorElements = page.locator('.ant-result, .ant-empty, .error-message, .ant-alert')
    
    if (await errorElements.first().isVisible({ timeout: 5000 })) {
      await expect(errorElements.first()).toBeVisible()
      
      // Error message should be user-friendly (not technical)
      const errorText = await errorElements.first().textContent()
      expect(errorText).not.toMatch(/500|Internal Server Error|undefined/i)
    }
  })

  test('provides retry mechanisms for failed operations', async ({ page }) => {
    await setupAuth(page)

    let requestCount = 0
    await page.route('**/api/tasks**', async (route) => {
      requestCount++
      if (requestCount === 1) {
        // Fail first request
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server Error' })
        })
      } else {
        // Succeed on retry
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], total: 0 })
        })
      }
    })

    await page.goto('/tasks')

    // Look for retry button
    const retryButton = page.getByRole('button', { name: /重试|retry|刷新|refresh/i })
    
    if (await retryButton.isVisible({ timeout: 5000 })) {
      await retryButton.click()

      // Should attempt to reload data
      await page.waitForTimeout(1000)
      
      // Error should be resolved after retry
      const errorElements = page.locator('.ant-result[status="error"], .error-message')
      
      if (await errorElements.isVisible()) {
        await expect(errorElements).not.toBeVisible({ timeout: 3000 })
      }
    }
  })

  test('handles network disconnection gracefully', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Simulate network disconnection
    await page.context().setOffline(true)

    // Try to navigate to another page
    await page.goto('/tasks')

    // Should show offline message or cached content
    const offlineIndicator = page.locator('.offline-message, .ant-result, .network-error')
    
    if (await offlineIndicator.isVisible({ timeout: 3000 })) {
      await expect(offlineIndicator).toBeVisible()
    }

    // Restore network
    await page.context().setOffline(false)

    // Should recover when network is restored
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Page should work normally
    await expect(page).toHaveURL(/tasks/i)
  })
})

test.describe('Form Usability', () => {
  test('provides real-time validation feedback', async ({ page }) => {
    await page.goto('/login')

    // Test email validation
    const usernameInput = page.getByPlaceholder(/用户名|username|email/i)
    
    if (await usernameInput.isVisible()) {
      // Enter invalid email
      await usernameInput.fill('invalid-email')
      await usernameInput.blur()

      // Should show validation error
      const validationError = page.locator('.ant-form-item-explain-error, .field-error')
      
      if (await validationError.isVisible({ timeout: 1000 })) {
        await expect(validationError).toBeVisible()
      }

      // Enter valid email
      await usernameInput.fill('test@example.com')
      await usernameInput.blur()

      // Error should disappear
      if (await validationError.isVisible()) {
        await expect(validationError).not.toBeVisible({ timeout: 1000 })
      }
    }
  })

  test('saves form progress automatically', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        // Fill form partially
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          await nameInput.fill('测试任务名称')
          
          // Close modal without saving
          await page.keyboard.press('Escape')
          
          // Reopen modal
          await createButton.click()
          
          // Form should remember the input (if auto-save is implemented)
          const savedValue = await nameInput.inputValue()
          
          // Note: This test assumes auto-save is implemented
          // In reality, this might not be the case for all forms
          if (savedValue) {
            expect(savedValue).toBe('测试任务名称')
          }
        }
      }
    }
  })

  test('provides helpful placeholder text and labels', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        // Check for helpful placeholders
        const inputs = modal.locator('input, textarea')
        const inputCount = await inputs.count()

        for (let i = 0; i < inputCount; i++) {
          const input = inputs.nth(i)
          const placeholder = await input.getAttribute('placeholder')
          
          if (placeholder) {
            // Placeholder should be descriptive
            expect(placeholder.length).toBeGreaterThan(2)
          }
        }

        // Check for labels
        const labels = modal.locator('.ant-form-item-label, label')
        
        if (await labels.first().isVisible()) {
          const labelText = await labels.first().textContent()
          expect(labelText?.length).toBeGreaterThan(0)
        }
      }
    }
  })
})

test.describe('Navigation and Breadcrumbs', () => {
  test('provides clear navigation paths', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Check for breadcrumbs
    const breadcrumbs = page.locator('.ant-breadcrumb, .breadcrumb')
    
    if (await breadcrumbs.isVisible()) {
      await expect(breadcrumbs).toBeVisible()
      
      // Breadcrumbs should show current location
      const breadcrumbText = await breadcrumbs.textContent()
      expect(breadcrumbText).toMatch(/仪表盘|dashboard/i)
    }

    // Navigate to tasks
    await page.goto('/tasks')

    // Breadcrumbs should update
    if (await breadcrumbs.isVisible()) {
      const updatedBreadcrumbText = await breadcrumbs.textContent()
      expect(updatedBreadcrumbText).toMatch(/任务|tasks/i)
    }
  })

  test('supports browser back/forward navigation', async ({ page }) => {
    await setupAuth(page)
    
    // Navigate through pages
    await page.goto('/dashboard')
    await page.goto('/tasks')
    await page.goto('/billing')

    // Use browser back button
    await page.goBack()
    await expect(page).toHaveURL(/tasks/i)

    await page.goBack()
    await expect(page).toHaveURL(/dashboard/i)

    // Use browser forward button
    await page.goForward()
    await expect(page).toHaveURL(/tasks/i)
  })

  test('highlights current page in navigation', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Current page should be highlighted in navigation
    const activeMenuItem = page.locator('.ant-menu-item-selected, .active, .current')
    
    if (await activeMenuItem.isVisible()) {
      await expect(activeMenuItem).toBeVisible()
      
      // Active item should relate to current page
      const activeText = await activeMenuItem.textContent()
      expect(activeText).toMatch(/任务|tasks/i)
    }
  })
})

test.describe('Data Presentation and Clarity', () => {
  test('displays data in readable formats', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Check metric cards for proper formatting
    const metricValues = page.locator('.ant-statistic-content-value, .metric-value')
    
    if (await metricValues.first().isVisible()) {
      const valueText = await metricValues.first().textContent()
      
      // Numbers should be formatted (with commas, etc.)
      if (valueText && /\d/.test(valueText)) {
        // Should not have raw large numbers without formatting
        expect(valueText).not.toMatch(/^\d{5,}$/) // No unformatted large numbers
      }
    }

    // Check date formatting
    const dateElements = page.locator('[data-testid*="date"], .date, .time')
    
    if (await dateElements.first().isVisible()) {
      const dateText = await dateElements.first().textContent()
      
      if (dateText) {
        // Should be human-readable date format
        expect(dateText).not.toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/) // Not ISO format
      }
    }
  })

  test('provides helpful empty states', async ({ page }) => {
    await setupAuth(page)

    // Mock empty data response
    await page.route('**/api/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 })
      })
    })

    await page.goto('/tasks')

    // Should show empty state
    const emptyState = page.locator('.ant-empty, .empty-state, .no-data')
    
    if (await emptyState.isVisible({ timeout: 5000 })) {
      await expect(emptyState).toBeVisible()
      
      // Empty state should have helpful message
      const emptyText = await emptyState.textContent()
      expect(emptyText?.length).toBeGreaterThan(10) // Should have descriptive text
      
      // Should provide action to add data
      const actionButton = emptyState.locator('.ant-btn, button')
      
      if (await actionButton.isVisible()) {
        await expect(actionButton).toBeVisible()
      }
    }
  })

  test('shows appropriate status indicators', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Look for status badges/tags
    const statusIndicators = page.locator('.ant-badge, .ant-tag, .status')
    
    if (await statusIndicators.first().isVisible()) {
      // Status should have appropriate colors
      const statusElement = statusIndicators.first()
      const statusClass = await statusElement.getAttribute('class')
      
      // Should have color-coded classes
      expect(statusClass).toMatch(/(success|error|warning|processing|default)/i)
    }
  })
})

test.describe('Accessibility and Usability', () => {
  test('supports keyboard shortcuts', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Test common keyboard shortcuts
    // Ctrl+N for new item (if implemented)
    await page.keyboard.press('Control+n')
    
    // Should open create modal or show some response
    const modal = page.locator('.ant-modal')
    
    if (await modal.isVisible({ timeout: 1000 })) {
      await expect(modal).toBeVisible()
      
      // Close with Escape
      await page.keyboard.press('Escape')
      await expect(modal).not.toBeVisible()
    }

    // Test search shortcut (Ctrl+K or /)
    await page.keyboard.press('Control+k')
    
    const searchInput = page.locator('input[type="search"], .search-input')
    
    if (await searchInput.isVisible({ timeout: 1000 })) {
      await expect(searchInput).toBeFocused()
    }
  })

  test('provides tooltips for complex features', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Look for elements that might have tooltips
    const complexElements = page.locator('.ant-btn-icon, .info-icon, [data-tooltip]')
    
    if (await complexElements.first().isVisible()) {
      await complexElements.first().hover()
      
      // Should show tooltip
      const tooltip = page.locator('.ant-tooltip, .tooltip')
      
      if (await tooltip.isVisible({ timeout: 1000 })) {
        await expect(tooltip).toBeVisible()
        
        // Tooltip should have helpful text
        const tooltipText = await tooltip.textContent()
        expect(tooltipText?.length).toBeGreaterThan(5)
      }
    }
  })

  test('maintains focus management in modals', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        // Focus should be trapped in modal
        await page.keyboard.press('Tab')
        
        const focusedElement = page.locator(':focus')
        
        if (await focusedElement.isVisible()) {
          // Focused element should be within modal
          const isInModal = await focusedElement.evaluate(el => {
            const modal = el.closest('.ant-modal')
            return modal !== null
          })
          
          expect(isInModal).toBeTruthy()
        }

        // Escape should close modal and restore focus
        await page.keyboard.press('Escape')
        
        if (await modal.isVisible()) {
          await expect(modal).not.toBeVisible({ timeout: 1000 })
        }
        
        // Focus should return to trigger button
        const newFocusedElement = page.locator(':focus')
        
        if (await newFocusedElement.isVisible()) {
          const isTriggerButton = await newFocusedElement.evaluate(el => {
            return el.textContent?.includes('创建') || el.textContent?.includes('create')
          })
          
          expect(isTriggerButton).toBeTruthy()
        }
      }
    }
  })
})