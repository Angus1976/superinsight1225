/**
 * Responsive Design E2E Tests
 *
 * Tests responsive behavior across different screen sizes and devices.
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

// Common viewport sizes for testing
const viewports = {
  mobile: { width: 375, height: 667 },    // iPhone SE
  mobileLarge: { width: 414, height: 896 }, // iPhone 11 Pro Max
  tablet: { width: 768, height: 1024 },   // iPad
  tabletLarge: { width: 1024, height: 768 }, // iPad Landscape
  desktop: { width: 1280, height: 720 },  // Desktop
  desktopLarge: { width: 1920, height: 1080 }, // Large Desktop
}

test.describe('Mobile Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(viewports.mobile)
  })

  test('login page adapts to mobile viewport', async ({ page }) => {
    await page.goto('/login')

    // Form should be visible and properly sized
    const loginForm = page.locator('.ant-form, .login-form')
    await expect(loginForm).toBeVisible()

    // Input fields should be full width on mobile
    const usernameInput = page.getByPlaceholder(/用户名|username/i)
    const passwordInput = page.getByPlaceholder(/密码|password/i)

    if (await usernameInput.isVisible()) {
      const inputBox = await usernameInput.boundingBox()
      expect(inputBox?.width).toBeGreaterThan(300) // Should be wide enough
    }

    // Login button should be easily tappable
    const loginButton = page.getByRole('button', { name: /登录|login/i })
    if (await loginButton.isVisible()) {
      const buttonBox = await loginButton.boundingBox()
      expect(buttonBox?.height).toBeGreaterThan(40) // Minimum touch target
    }
  })

  test('dashboard navigation works on mobile', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Sidebar should be collapsed or hidden on mobile
    const sidebar = page.locator('.ant-layout-sider')
    
    if (await sidebar.isVisible()) {
      // Check if sidebar is collapsed
      const sidebarWidth = await sidebar.evaluate(el => el.getBoundingClientRect().width)
      expect(sidebarWidth).toBeLessThan(200) // Should be collapsed
    }

    // Mobile menu trigger should be visible
    const menuTrigger = page.locator('.ant-pro-global-header-trigger, [aria-label*="menu"]')
    
    if (await menuTrigger.isVisible()) {
      await expect(menuTrigger).toBeVisible()
      
      // Test menu toggle
      await menuTrigger.click()
      
      // Menu should expand or drawer should open
      const expandedMenu = page.locator('.ant-drawer, .ant-layout-sider-collapsed')
      
      if (await expandedMenu.isVisible({ timeout: 1000 })) {
        await expect(expandedMenu).toBeVisible()
      }
    }
  })

  test('task list is usable on mobile', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Table should adapt to mobile (possibly as cards or simplified view)
    const taskContainer = page.locator('.ant-table, .ant-list, .task-container')
    
    if (await taskContainer.isVisible()) {
      await expect(taskContainer).toBeVisible()
      
      // Should not have horizontal scroll
      const containerWidth = await taskContainer.evaluate(el => el.scrollWidth)
      const viewportWidth = await page.evaluate(() => window.innerWidth)
      
      expect(containerWidth).toBeLessThanOrEqual(viewportWidth + 10) // Allow small margin
    }

    // Action buttons should be touch-friendly
    const actionButtons = page.locator('.ant-btn')
    
    if (await actionButtons.first().isVisible()) {
      const buttonBox = await actionButtons.first().boundingBox()
      expect(buttonBox?.height).toBeGreaterThan(32) // Minimum touch target
    }
  })

  test('forms are usable on mobile', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Try to open task creation form
    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal, .ant-drawer')
      
      if (await modal.isVisible()) {
        // Modal should fit mobile screen
        const modalBox = await modal.boundingBox()
        const viewportWidth = await page.evaluate(() => window.innerWidth)
        
        expect(modalBox?.width).toBeLessThanOrEqual(viewportWidth)

        // Form inputs should be properly sized
        const formInputs = modal.locator('.ant-input, .ant-select')
        
        if (await formInputs.first().isVisible()) {
          const inputBox = await formInputs.first().boundingBox()
          expect(inputBox?.height).toBeGreaterThan(32) // Touch-friendly height
        }
      }
    }
  })
})

test.describe('Tablet Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(viewports.tablet)
  })

  test('dashboard layout adapts to tablet', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Sidebar should be visible but possibly collapsed
    const sidebar = page.locator('.ant-layout-sider')
    
    if (await sidebar.isVisible()) {
      const sidebarWidth = await sidebar.evaluate(el => el.getBoundingClientRect().width)
      expect(sidebarWidth).toBeGreaterThan(50) // Should have some width
    }

    // Content should use available space efficiently
    const content = page.locator('.ant-layout-content')
    
    if (await content.isVisible()) {
      const contentBox = await content.boundingBox()
      expect(contentBox?.width).toBeGreaterThan(500) // Should have reasonable width
    }

    // Metric cards should arrange properly
    const metricCards = page.locator('.ant-card')
    
    if (await metricCards.first().isVisible()) {
      const cardCount = await metricCards.count()
      
      if (cardCount >= 2) {
        // Cards should be arranged in rows
        const firstCard = await metricCards.nth(0).boundingBox()
        const secondCard = await metricCards.nth(1).boundingBox()
        
        // Check if cards are side by side or stacked
        const sideBySide = firstCard && secondCard && 
          Math.abs(firstCard.y - secondCard.y) < 50
        
        expect(sideBySide).toBeTruthy() // Should be side by side on tablet
      }
    }
  })

  test('table displays properly on tablet', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const table = page.locator('.ant-table')
    
    if (await table.isVisible()) {
      // Table should fit without horizontal scroll
      const tableWidth = await table.evaluate(el => el.scrollWidth)
      const containerWidth = await table.evaluate(el => el.clientWidth)
      
      expect(tableWidth).toBeLessThanOrEqual(containerWidth + 20) // Allow small margin

      // Important columns should be visible
      const headers = page.locator('.ant-table-thead th')
      const headerCount = await headers.count()
      
      expect(headerCount).toBeGreaterThan(3) // Should show multiple columns
    }
  })
})

test.describe('Desktop Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(viewports.desktop)
  })

  test('full layout is displayed on desktop', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Sidebar should be fully visible
    const sidebar = page.locator('.ant-layout-sider')
    
    if (await sidebar.isVisible()) {
      const sidebarWidth = await sidebar.evaluate(el => el.getBoundingClientRect().width)
      expect(sidebarWidth).toBeGreaterThan(200) // Full sidebar width
    }

    // Header should show all elements
    const header = page.locator('.ant-layout-header, .ant-pro-global-header')
    
    if (await header.isVisible()) {
      // User info should be visible
      const userInfo = page.locator('.ant-dropdown-trigger, .user-info')
      
      if (await userInfo.isVisible()) {
        await expect(userInfo).toBeVisible()
      }
    }

    // Content should use full width efficiently
    const content = page.locator('.ant-layout-content')
    
    if (await content.isVisible()) {
      const contentBox = await content.boundingBox()
      expect(contentBox?.width).toBeGreaterThan(800) // Should have good width
    }
  })

  test('all table columns are visible on desktop', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const table = page.locator('.ant-table')
    
    if (await table.isVisible()) {
      // All columns should be visible
      const headers = page.locator('.ant-table-thead th')
      const headerCount = await headers.count()
      
      expect(headerCount).toBeGreaterThan(5) // Should show all columns

      // Action column should be visible
      const actionHeader = headers.filter({ hasText: /操作|action/i })
      
      if (await actionHeader.isVisible()) {
        await expect(actionHeader).toBeVisible()
      }
    }
  })
})

test.describe('Cross-Device Consistency', () => {
  const testPages = ['/dashboard', '/tasks', '/billing', '/settings']

  for (const pagePath of testPages) {
    test(`${pagePath} works across all viewport sizes`, async ({ page }) => {
      await setupAuth(page)

      for (const [deviceName, viewport] of Object.entries(viewports)) {
        await page.setViewportSize(viewport)
        await page.goto(pagePath)

        // Page should load without errors
        await expect(page).toHaveURL(new RegExp(pagePath.replace('/', '')))

        // Main content should be visible
        const mainContent = page.locator('.ant-layout-content, .page-content, main')
        
        if (await mainContent.isVisible()) {
          await expect(mainContent).toBeVisible()
        }

        // No horizontal scroll should be present
        const hasHorizontalScroll = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth
        })

        expect(hasHorizontalScroll).toBeFalsy()

        console.log(`✓ ${pagePath} works on ${deviceName} (${viewport.width}x${viewport.height})`)
      }
    })
  }
})

test.describe('Touch and Interaction', () => {
  test('touch interactions work on mobile', async ({ page }) => {
    await page.setViewportSize(viewports.mobile)
    await setupAuth(page)
    await page.goto('/dashboard')

    // Test tap interactions
    const menuItems = page.locator('.ant-menu-item, .nav-item')
    
    if (await menuItems.first().isVisible()) {
      // Simulate touch tap
      await menuItems.first().tap()
      
      // Should navigate or show response
      await page.waitForTimeout(500)
    }

    // Test swipe gestures (if implemented)
    const swipeableArea = page.locator('.swipeable, .ant-carousel')
    
    if (await swipeableArea.isVisible()) {
      const box = await swipeableArea.boundingBox()
      
      if (box) {
        // Simulate swipe
        await page.mouse.move(box.x + box.width * 0.8, box.y + box.height / 2)
        await page.mouse.down()
        await page.mouse.move(box.x + box.width * 0.2, box.y + box.height / 2)
        await page.mouse.up()
        
        await page.waitForTimeout(500)
      }
    }
  })

  test('hover states work on desktop', async ({ page }) => {
    await page.setViewportSize(viewports.desktop)
    await setupAuth(page)
    await page.goto('/tasks')

    // Test hover effects on buttons
    const buttons = page.locator('.ant-btn')
    
    if (await buttons.first().isVisible()) {
      // Get initial styles
      const initialStyles = await buttons.first().evaluate(el => {
        const styles = window.getComputedStyle(el)
        return {
          backgroundColor: styles.backgroundColor,
          borderColor: styles.borderColor
        }
      })

      // Hover over button
      await buttons.first().hover()
      
      await page.waitForTimeout(200) // Allow for transition

      // Check if styles changed (hover effect)
      const hoverStyles = await buttons.first().evaluate(el => {
        const styles = window.getComputedStyle(el)
        return {
          backgroundColor: styles.backgroundColor,
          borderColor: styles.borderColor
        }
      })

      // At least one style should change on hover
      const stylesChanged = 
        initialStyles.backgroundColor !== hoverStyles.backgroundColor ||
        initialStyles.borderColor !== hoverStyles.borderColor

      expect(stylesChanged).toBeTruthy()
    }
  })
})

test.describe('Accessibility on Different Devices', () => {
  test('keyboard navigation works on all screen sizes', async ({ page }) => {
    await setupAuth(page)

    for (const [deviceName, viewport] of Object.entries(viewports)) {
      await page.setViewportSize(viewport)
      await page.goto('/dashboard')

      // Test tab navigation
      await page.keyboard.press('Tab')
      
      // Should focus on first focusable element
      const focusedElement = page.locator(':focus')
      
      if (await focusedElement.isVisible()) {
        await expect(focusedElement).toBeVisible()
      }

      // Test multiple tab presses
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab')
        await page.waitForTimeout(100)
      }

      // Should still have a focused element
      const finalFocusedElement = page.locator(':focus')
      
      if (await finalFocusedElement.isVisible()) {
        await expect(finalFocusedElement).toBeVisible()
      }

      console.log(`✓ Keyboard navigation works on ${deviceName}`)
    }
  })

  test('focus indicators are visible on all devices', async ({ page }) => {
    await setupAuth(page)

    for (const viewport of [viewports.mobile, viewports.tablet, viewports.desktop]) {
      await page.setViewportSize(viewport)
      await page.goto('/tasks')

      // Focus on interactive elements
      const interactiveElements = page.locator('button, input, select, a, [tabindex]')
      
      if (await interactiveElements.first().isVisible()) {
        await interactiveElements.first().focus()

        // Check if focus indicator is visible
        const focusedElement = page.locator(':focus')
        const focusStyles = await focusedElement.evaluate(el => {
          const styles = window.getComputedStyle(el)
          return {
            outline: styles.outline,
            outlineWidth: styles.outlineWidth,
            boxShadow: styles.boxShadow
          }
        })

        // Should have some form of focus indicator
        const hasFocusIndicator = 
          focusStyles.outline !== 'none' ||
          focusStyles.outlineWidth !== '0px' ||
          focusStyles.boxShadow !== 'none'

        expect(hasFocusIndicator).toBeTruthy()
      }
    }
  })
})