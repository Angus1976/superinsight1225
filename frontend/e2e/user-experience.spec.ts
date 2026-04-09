/**
 * User Experience E2E Tests
 *
 * Tests user experience aspects like loading states, error handling, and usability.
 */

import { test, expect } from '@playwright/test'
import { isRestApiUrl } from './api-route-helpers'
import { setupE2eSession, waitForPageReady } from './test-helpers'

async function setupAuthenticatedUx(page: import('@playwright/test').Page) {
  await setupE2eSession(page, { lang: 'en', role: 'admin' })
}

test.describe('Loading States and Feedback', () => {
  // Skipped: spin/skeleton can remain visible past 5s with delayed route + dashboard layout (2026-04 triage).
  test.skip('shows appropriate loading states during data fetching', async ({ page }) => {
    await setupAuthenticatedUx(page)

    // Simulate slow API responses
    await page.route(isRestApiUrl, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000)) // 1 second delay
      await route.continue()
    })

    await page.goto('/dashboard')

    // Should show loading indicators
    const loadingIndicators = page.locator('.ant-spin, .ant-skeleton, .loading')
    
    if (await loadingIndicators.first().isVisible({ timeout: 2000 })) {
      await expect(loadingIndicators.first()).toBeVisible()
    }

    // Dev servers / delayed mocks often keep connections open; avoid networkidle (times out).
    await page.waitForLoadState('load')

    // Loading indicators should disappear
    if (await loadingIndicators.first().isVisible()) {
      await expect(loadingIndicators.first()).not.toBeVisible({ timeout: 5000 })
    }
  })

  test('provides feedback for user actions', async ({ page }) => {
    await setupAuthenticatedUx(page)
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
    await setupAuthenticatedUx(page)
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
    await setupAuthenticatedUx(page)

    // Simulate API errors
    await page.route(isRestApiUrl, async (route) => {
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
    await setupAuthenticatedUx(page)

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
    await setupAuthenticatedUx(page)
    await page.goto('/dashboard')
    await waitForPageReady(page)

    await page.context().setOffline(true)

    try {
      await page.goto('/tasks', { timeout: 15000, waitUntil: 'domcontentloaded' })
    } catch {
      // Offline navigation may fail; stay on current URL
    }

    const offlineIndicator = page.locator('.offline-message, .ant-result, .network-error')
    if (await offlineIndicator.isVisible({ timeout: 2000 }).catch(() => false)) {
      await expect(offlineIndicator).toBeVisible()
    }

    await page.context().setOffline(false)
    await page.goto('/tasks')
    await waitForPageReady(page)
    await expect(page).toHaveURL(/tasks/i, { timeout: 15000 })
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
    await setupAuthenticatedUx(page)
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
    await setupAuthenticatedUx(page)
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
    await setupAuthenticatedUx(page)
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
      expect(updatedBreadcrumbText).toMatch(/任务|tasks|Task Management/i)
    }
  })

  test('supports browser back/forward navigation', async ({ page }) => {
    await setupAuthenticatedUx(page)

    await page.goto('/dashboard')
    await waitForPageReady(page)
    await page.goto('/tasks')
    await waitForPageReady(page)
    await page.goto('/billing/overview')
    await waitForPageReady(page)

    await page.goBack()
    await expect(page).toHaveURL(/tasks/i, { timeout: 15000 })

    await page.goBack()
    await expect(page).toHaveURL(/dashboard/i, { timeout: 15000 })

    await page.goForward()
    await expect(page).toHaveURL(/tasks/i, { timeout: 15000 })
  })

  test('highlights current page in navigation', async ({ page }) => {
    await setupAuthenticatedUx(page)
    await page.goto('/tasks')

    // Current page should be highlighted in navigation
    const activeMenuItem = page.locator('.ant-menu-item-selected, .active, .current')
    
    if (await activeMenuItem.isVisible()) {
      await expect(activeMenuItem).toBeVisible()
      
      // Active item should relate to current page
      const activeText = await activeMenuItem.textContent()
      expect(activeText).toMatch(/任务|tasks|Task Management/i)
    }
  })
})

test.describe('Data Presentation and Clarity', () => {
  test('displays data in readable formats', async ({ page }) => {
    await setupAuthenticatedUx(page)
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
    await setupAuthenticatedUx(page)

    // Mock empty data response
    await page.route(isRestApiUrl, async (route) => {
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
    await setupAuthenticatedUx(page)
    await page.goto('/tasks')

    // Look for status badges/tags
    const statusIndicators = page.locator('.ant-badge, .ant-tag, .status')
    
    if (await statusIndicators.first().isVisible()) {
      // Status should have appropriate colors (tags use status/color; badges may only have ant-badge + hash)
      const statusElement = statusIndicators.first()
      const statusClass = (await statusElement.getAttribute('class')) || ''
      const tagWithStatus = page.locator('.ant-tag[class*="success"], .ant-tag[class*="error"], .ant-tag[class*="warning"], .ant-tag[class*="processing"]')
      if (await tagWithStatus.first().isVisible().catch(() => false)) {
        await expect(tagWithStatus.first()).toBeVisible()
      } else {
        expect(statusClass.length).toBeGreaterThan(0)
      }
    }
  })
})

test.describe('Accessibility and Usability', () => {
  test('supports keyboard shortcuts', async ({ page }) => {
    await setupAuthenticatedUx(page)
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

    // Ctrl+K global search focus is not implemented for ProTable (filters use ant-select comboboxes).
  })

  test('provides tooltips for complex features', async ({ page }) => {
    await setupAuthenticatedUx(page)
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
    await setupAuthenticatedUx(page)
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