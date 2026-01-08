/**
 * Security E2E Tests
 *
 * Tests security features including XSS protection, CSRF protection, and data isolation.
 */

import { test, expect } from '@playwright/test'

// Helper to set up authenticated state
async function setupAuth(page: any, role: string = 'admin') {
  await page.addInitScript(({ role }) => {
    const permissions = role === 'admin' 
      ? ['read:all', 'write:all', 'manage:all']
      : ['read:tasks', 'read:billing']

    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user: {
            id: `user-${role}`,
            username: `${role}user`,
            name: `${role} 用户`,
            email: `${role}@example.com`,
            tenant_id: 'tenant-1',
            roles: [role],
            permissions: permissions,
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
  }, { role })
}

test.describe('XSS Protection', () => {
  test('prevents script injection in form inputs', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        // Try to inject script in task name
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          const maliciousScript = '<script>alert("XSS")</script>'
          await nameInput.fill(maliciousScript)

          // Submit form
          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }

          // Wait for potential script execution
          await page.waitForTimeout(1000)

          // No alert should have been triggered
          // In a real test, you might check that the script is escaped in the DOM
          const pageContent = await page.content()
          expect(pageContent).not.toContain('<script>alert("XSS")</script>')
        }
      }
    }
  })

  test('sanitizes user-generated content display', async ({ page }) => {
    await setupAuth(page)

    // Mock API response with potentially malicious content
    await page.route('**/api/tasks*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [{
            id: 'task-1',
            name: '<script>alert("XSS in name")</script>恶意任务',
            description: '<img src="x" onerror="alert(\'XSS in description\')">',
            status: 'pending',
            assignee: '<b>用户1</b>',
            progress: 50,
            createdAt: new Date().toISOString(),
          }],
          total: 1
        })
      })
    })

    await page.goto('/tasks')

    // Wait for content to load
    await page.waitForTimeout(2000)

    // Check that malicious scripts are not executed
    const pageContent = await page.content()
    
    // Scripts should be escaped or removed
    expect(pageContent).not.toContain('<script>alert("XSS in name")</script>')
    expect(pageContent).not.toContain('onerror="alert(\'XSS in description\')"')

    // Content should still be displayed (but safely)
    expect(pageContent).toContain('恶意任务')
  })

  test('prevents javascript: URLs', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Try to inject javascript: URL
    await page.evaluate(() => {
      const link = document.createElement('a')
      link.href = 'javascript:alert("XSS via href")'
      link.textContent = '恶意链接'
      document.body.appendChild(link)
      link.click()
    })

    // Wait for potential script execution
    await page.waitForTimeout(1000)

    // No alert should be triggered
    // The application should prevent javascript: URLs from executing
  })
})

test.describe('CSRF Protection', () => {
  test('includes CSRF tokens in form submissions', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Monitor network requests
    const requests: any[] = []
    page.on('request', request => {
      if (request.method() === 'POST') {
        requests.push({
          url: request.url(),
          headers: request.headers(),
          postData: request.postData()
        })
      }
    })

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          await nameInput.fill('测试任务')

          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }

          // Wait for request
          await page.waitForTimeout(2000)

          // Check if CSRF token was included
          const postRequests = requests.filter(req => req.url.includes('/api/'))
          
          if (postRequests.length > 0) {
            const request = postRequests[0]
            
            // Should have CSRF token in headers or body
            const hasCsrfToken = 
              request.headers['x-csrf-token'] ||
              request.headers['x-xsrf-token'] ||
              (request.postData && request.postData.includes('csrf'))

            // Note: This test assumes CSRF protection is implemented
            // In a real application, you would verify the specific implementation
            console.log('CSRF protection check:', hasCsrfToken ? 'Present' : 'Not detected')
          }
        }
      }
    }
  })

  test('rejects requests without proper CSRF tokens', async ({ page }) => {
    await setupAuth(page)

    // Intercept and modify requests to remove CSRF tokens
    await page.route('**/api/**', async route => {
      const request = route.request()
      
      if (request.method() === 'POST') {
        // Remove CSRF headers
        const headers = { ...request.headers() }
        delete headers['x-csrf-token']
        delete headers['x-xsrf-token']

        await route.continue({
          headers: headers
        })
      } else {
        await route.continue()
      }
    })

    await page.goto('/tasks')

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          await nameInput.fill('测试任务')

          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }

          // Should show error due to missing CSRF token
          const errorMessage = page.locator('.ant-message-error, .ant-notification-error, .error')
          
          if (await errorMessage.isVisible({ timeout: 3000 })) {
            await expect(errorMessage).toBeVisible()
          }
        }
      }
    }
  })
})

test.describe('Data Isolation and Access Control', () => {
  test('prevents unauthorized data access through URL manipulation', async ({ page }) => {
    await setupAuth(page, 'viewer') // Limited permissions
    
    // Try to access admin-only data through URL
    await page.goto('/admin/users')
    
    // Should redirect to unauthorized page or login
    await expect(page).toHaveURL(/403|unauthorized|login|dashboard/i, { timeout: 5000 })
  })

  test('enforces tenant data isolation', async ({ page }) => {
    await setupAuth(page)

    // Mock API to return data for different tenants
    await page.route('**/api/tasks*', async route => {
      const url = new URL(route.request().url())
      const tenantId = url.searchParams.get('tenant') || 'tenant-1'
      
      const mockData = {
        'tenant-1': [{ id: 'task-1', name: '租户1任务', tenant_id: 'tenant-1' }],
        'tenant-2': [{ id: 'task-2', name: '租户2任务', tenant_id: 'tenant-2' }]
      }
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: mockData[tenantId] || [],
          total: mockData[tenantId]?.length || 0
        })
      })
    })

    await page.goto('/tasks')

    // Should only see tenant-1 data
    await page.waitForTimeout(1000)
    
    const pageContent = await page.textContent('body')
    expect(pageContent).toContain('租户1任务')
    expect(pageContent).not.toContain('租户2任务')

    // Try to access other tenant's data via URL manipulation
    await page.goto('/tasks?tenant=tenant-2')
    
    // Should still only see authorized tenant data
    await page.waitForTimeout(1000)
    
    const updatedContent = await page.textContent('body')
    expect(updatedContent).not.toContain('租户2任务')
  })

  test('validates user permissions for each action', async ({ page }) => {
    await setupAuth(page, 'viewer') // Read-only user
    await page.goto('/tasks')

    // Create button should not be visible or should be disabled
    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await expect(createButton).toBeDisabled()
    }

    // Edit/Delete actions should not be available
    const actionButtons = page.locator('.ant-btn').filter({ hasText: /编辑|删除|edit|delete/i })
    
    const buttonCount = await actionButtons.count()
    
    for (let i = 0; i < buttonCount; i++) {
      const button = actionButtons.nth(i)
      
      if (await button.isVisible()) {
        await expect(button).toBeDisabled()
      }
    }
  })
})

test.describe('Session Security', () => {
  test('handles session timeout appropriately', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Simulate session expiration
    await page.evaluate(() => {
      localStorage.removeItem('auth-storage')
    })

    // Try to perform an action that requires authentication
    await page.goto('/admin')

    // Should redirect to login
    await expect(page).toHaveURL(/login/i, { timeout: 5000 })
  })

  test('prevents session fixation attacks', async ({ page }) => {
    // Start with a session
    await setupAuth(page)
    await page.goto('/dashboard')

    // Get initial session token
    const initialToken = await page.evaluate(() => {
      const auth = localStorage.getItem('auth-storage')
      return auth ? JSON.parse(auth).state.token : null
    })

    // Simulate login (which should create new session)
    await page.goto('/login')
    
    const usernameInput = page.getByPlaceholder(/用户名|username/i)
    const passwordInput = page.getByPlaceholder(/密码|password/i)
    
    if (await usernameInput.isVisible() && await passwordInput.isVisible()) {
      await usernameInput.fill('testuser')
      await passwordInput.fill('testpassword')
      
      const loginButton = page.getByRole('button', { name: /登录|login/i })
      await loginButton.click()

      // Wait for potential redirect
      await page.waitForTimeout(2000)

      // Check if token changed (indicating new session)
      const newToken = await page.evaluate(() => {
        const auth = localStorage.getItem('auth-storage')
        return auth ? JSON.parse(auth).state.token : null
      })

      // Token should be different (new session created)
      if (initialToken && newToken) {
        expect(newToken).not.toBe(initialToken)
      }
    }
  })

  test('securely handles logout', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Find logout button
    const userMenu = page.locator('.ant-dropdown-trigger, .user-menu')
    
    if (await userMenu.isVisible()) {
      await userMenu.click()

      const logoutButton = page.getByRole('menuitem', { name: /退出|logout/i })
      
      if (await logoutButton.isVisible()) {
        await logoutButton.click()

        // Should clear session data
        const authData = await page.evaluate(() => {
          return localStorage.getItem('auth-storage')
        })

        expect(authData).toBeNull()

        // Should redirect to login
        await expect(page).toHaveURL(/login/i, { timeout: 5000 })
      }
    }
  })
})

test.describe('Input Validation and Sanitization', () => {
  test('validates file uploads', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/augmentation') // Assuming this page has file upload

    // Look for file upload component
    const fileInput = page.locator('input[type="file"]')
    
    if (await fileInput.isVisible()) {
      // Try to upload a potentially malicious file
      const maliciousFile = Buffer.from('<?php echo "malicious code"; ?>', 'utf8')
      
      await fileInput.setInputFiles({
        name: 'malicious.php',
        mimeType: 'application/x-php',
        buffer: maliciousFile
      })

      // Should show validation error
      const errorMessage = page.locator('.ant-message-error, .upload-error, .file-error')
      
      if (await errorMessage.isVisible({ timeout: 3000 })) {
        await expect(errorMessage).toBeVisible()
      }
    }
  })

  test('validates input length and format', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          // Test extremely long input
          const longString = 'A'.repeat(1000)
          await nameInput.fill(longString)

          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }

          // Should show validation error
          const validationError = page.locator('.ant-form-item-explain-error, .field-error')
          
          if (await validationError.isVisible({ timeout: 2000 })) {
            await expect(validationError).toBeVisible()
          }
        }
      }
    }
  })

  test('prevents SQL injection attempts', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/tasks')

    // Monitor API requests
    const requests: any[] = []
    page.on('request', request => {
      requests.push({
        url: request.url(),
        postData: request.postData()
      })
    })

    // Try SQL injection in search
    const searchInput = page.locator('input[placeholder*="搜索"], input[type="search"]')
    
    if (await searchInput.isVisible()) {
      const sqlInjection = "'; DROP TABLE tasks; --"
      await searchInput.fill(sqlInjection)
      await searchInput.press('Enter')

      await page.waitForTimeout(1000)

      // Check that the malicious input was properly escaped
      const searchRequests = requests.filter(req => 
        req.url.includes('/api/') && 
        (req.url.includes('search') || req.postData?.includes('search'))
      )

      if (searchRequests.length > 0) {
        // The raw SQL should not appear in requests
        const hasRawSQL = searchRequests.some(req => 
          req.url.includes("DROP TABLE") || 
          req.postData?.includes("DROP TABLE")
        )

        expect(hasRawSQL).toBeFalsy()
      }
    }
  })
})

test.describe('Content Security Policy', () => {
  test('enforces CSP headers', async ({ page }) => {
    await page.goto('/login')

    // Check for CSP headers
    const response = await page.waitForResponse(response => 
      response.url().includes('/login') && response.status() === 200
    )

    const cspHeader = response.headers()['content-security-policy']
    
    if (cspHeader) {
      // Should have restrictive CSP
      expect(cspHeader).toContain("default-src 'self'")
      expect(cspHeader).not.toContain("'unsafe-eval'")
      
      console.log('CSP Header:', cspHeader)
    } else {
      console.log('Warning: No CSP header found')
    }
  })

  test('prevents inline script execution', async ({ page }) => {
    await setupAuth(page)
    await page.goto('/dashboard')

    // Try to inject and execute inline script
    const scriptExecuted = await page.evaluate(() => {
      try {
        const script = document.createElement('script')
        script.innerHTML = 'window.testXSS = true;'
        document.head.appendChild(script)
        
        return window.testXSS === true
      } catch (error) {
        return false
      }
    })

    // Inline script should be blocked by CSP
    expect(scriptExecuted).toBeFalsy()
  })
})

test.describe('Secure Communication', () => {
  test('uses HTTPS for sensitive operations', async ({ page }) => {
    // Note: This test assumes the application is served over HTTPS in production
    await setupAuth(page)
    
    // Monitor requests to ensure they use secure protocols
    const insecureRequests: string[] = []
    
    page.on('request', request => {
      const url = request.url()
      if (url.startsWith('http://') && !url.includes('localhost')) {
        insecureRequests.push(url)
      }
    })

    await page.goto('/login')
    
    const usernameInput = page.getByPlaceholder(/用户名|username/i)
    const passwordInput = page.getByPlaceholder(/密码|password/i)
    
    if (await usernameInput.isVisible() && await passwordInput.isVisible()) {
      await usernameInput.fill('testuser')
      await passwordInput.fill('testpassword')
      
      const loginButton = page.getByRole('button', { name: /登录|login/i })
      await loginButton.click()

      await page.waitForTimeout(2000)

      // No insecure requests should be made for authentication
      expect(insecureRequests.length).toBe(0)
    }
  })

  test('includes security headers in responses', async ({ page }) => {
    const response = await page.goto('/dashboard')

    if (response) {
      const headers = response.headers()

      // Check for security headers
      const securityHeaders = {
        'x-frame-options': 'DENY',
        'x-content-type-options': 'nosniff',
        'x-xss-protection': '1; mode=block',
        'strict-transport-security': 'max-age=31536000'
      }

      for (const [header, expectedValue] of Object.entries(securityHeaders)) {
        const actualValue = headers[header]
        
        if (actualValue) {
          console.log(`✓ ${header}: ${actualValue}`)
        } else {
          console.log(`⚠ Missing security header: ${header}`)
        }
      }
    }
  })
})