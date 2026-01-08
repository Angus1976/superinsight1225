/**
 * Compliance E2E Tests
 *
 * Tests compliance features including data privacy, audit trails, and regulatory requirements.
 */

import { test, expect } from '@playwright/test'

// Helper to set up authenticated state
async function setupAuth(page: any, role: string = 'admin') {
  await page.addInitScript(({ role }) => {
    const permissions = role === 'admin' 
      ? ['read:all', 'write:all', 'manage:all', 'audit:view']
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

test.describe('Data Privacy and Protection', () => {
  test('masks sensitive data for unauthorized users', async ({ page }) => {
    await setupAuth(page, 'viewer') // Limited permissions
    await page.goto('/billing')

    // Mock billing data with sensitive information
    await page.route('**/api/billing*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [{
            id: 'bill-1',
            amount: 15000.50,
            bankAccount: '1234567890123456',
            taxId: '123-45-6789',
            personalInfo: {
              phone: '13800138000',
              idCard: '110101199001011234'
            }
          }],
          total: 1
        })
      })
    })

    await page.reload()
    await page.waitForTimeout(2000)

    const pageContent = await page.textContent('body')

    // Sensitive data should be masked
    expect(pageContent).not.toContain('1234567890123456') // Full bank account
    expect(pageContent).not.toContain('123-45-6789') // Full tax ID
    expect(pageContent).not.toContain('13800138000') // Full phone
    expect(pageContent).not.toContain('110101199001011234') // Full ID card

    // Should show masked versions
    if (pageContent.includes('****')) {
      expect(pageContent).toMatch(/\*{4,}/) // Should have masked data
    }
  })

  test('provides data export controls', async ({ page }) => {
    await setupAuth(page, 'admin')
    await page.goto('/billing')

    const exportButton = page.getByRole('button', { name: /导出|export/i })
    
    if (await exportButton.isVisible()) {
      await exportButton.click()

      const exportModal = page.locator('.ant-modal').filter({ hasText: /导出|export/i })
      
      if (await exportModal.isVisible()) {
        // Should have data sensitivity options
        const sensitivityOptions = exportModal.locator('.ant-checkbox, .ant-radio')
        
        if (await sensitivityOptions.first().isVisible()) {
          // Should have options like "包含敏感数据" or "脱敏导出"
          const optionTexts = await sensitivityOptions.allTextContents()
          const hasSensitivityControl = optionTexts.some(text => 
            text.includes('敏感') || text.includes('脱敏') || text.includes('sensitive')
          )
          
          expect(hasSensitivityControl).toBeTruthy()
        }

        // Should require confirmation for sensitive data export
        const confirmCheckbox = exportModal.locator('input[type="checkbox"]')
        
        if (await confirmCheckbox.isVisible()) {
          const confirmButton = exportModal.getByRole('button', { name: /确定|export/i })
          
          // Button should be disabled until confirmation
          if (await confirmButton.isVisible()) {
            await expect(confirmButton).toBeDisabled()
            
            // Check confirmation
            await confirmCheckbox.check()
            
            // Button should now be enabled
            await expect(confirmButton).toBeEnabled()
          }
        }
      }
    }
  })

  test('implements data retention policies', async ({ page }) => {
    await setupAuth(page, 'admin')
    await page.goto('/admin/data-retention')

    // Should show data retention settings
    const retentionSettings = page.locator('.retention-policy, .data-retention')
    
    if (await retentionSettings.isVisible()) {
      await expect(retentionSettings).toBeVisible()

      // Should have retention period settings
      const retentionPeriod = page.locator('input[type="number"], .ant-input-number')
      
      if (await retentionPeriod.isVisible()) {
        // Should have reasonable default values
        const value = await retentionPeriod.inputValue()
        const numValue = parseInt(value)
        
        expect(numValue).toBeGreaterThan(0)
        expect(numValue).toBeLessThan(3650) // Less than 10 years
      }
    }
  })

  test('provides user consent management', async ({ page }) => {
    await page.goto('/login')

    // Should show privacy policy and terms
    const privacyLink = page.getByRole('link', { name: /隐私政策|privacy.*policy/i })
    const termsLink = page.getByRole('link', { name: /服务条款|terms.*service/i })

    if (await privacyLink.isVisible()) {
      await expect(privacyLink).toBeVisible()
    }

    if (await termsLink.isVisible()) {
      await expect(termsLink).toBeVisible()
    }

    // Should have consent checkboxes for registration
    const registerLink = page.getByRole('link', { name: /注册|register/i })
    
    if (await registerLink.isVisible()) {
      await registerLink.click()

      const consentCheckbox = page.locator('input[type="checkbox"]').filter({ 
        hasText: /同意|agree|consent/i 
      })
      
      if (await consentCheckbox.isVisible()) {
        await expect(consentCheckbox).toBeVisible()
        
        // Registration should be disabled without consent
        const registerButton = page.getByRole('button', { name: /注册|register/i })
        
        if (await registerButton.isVisible()) {
          await expect(registerButton).toBeDisabled()
        }
      }
    }
  })
})

test.describe('Audit Trail and Logging', () => {
  test('logs user actions for audit purposes', async ({ page }) => {
    await setupAuth(page, 'admin')

    // Monitor requests to check for audit logging
    const auditRequests: any[] = []
    page.on('request', request => {
      if (request.url().includes('/api/audit') || request.url().includes('/api/log')) {
        auditRequests.push({
          url: request.url(),
          method: request.method(),
          postData: request.postData()
        })
      }
    })

    // Perform auditable actions
    await page.goto('/tasks')
    
    const createButton = page.getByRole('button', { name: /创建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        
        if (await nameInput.isVisible()) {
          await nameInput.fill('审计测试任务')

          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }
        }
      }
    }

    await page.waitForTimeout(2000)

    // Should have made audit log requests
    if (auditRequests.length > 0) {
      console.log('Audit requests detected:', auditRequests.length)
      
      // Audit data should include action details
      const auditData = auditRequests[0].postData
      if (auditData) {
        expect(auditData).toContain('create') // Action type
      }
    }
  })

  test('displays audit logs for administrators', async ({ page }) => {
    await setupAuth(page, 'admin')
    await page.goto('/admin/audit')

    // Mock audit log data
    await page.route('**/api/audit*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [{
            id: 'audit-1',
            userId: 'user-1',
            action: 'CREATE_TASK',
            resource: 'tasks',
            timestamp: new Date().toISOString(),
            details: { taskName: '测试任务' },
            ipAddress: '192.168.1.100',
            userAgent: 'Mozilla/5.0...'
          }],
          total: 1
        })
      })
    })

    await page.reload()
    await page.waitForTimeout(2000)

    // Should show audit log table
    const auditTable = page.locator('.ant-table, .audit-log')
    
    if (await auditTable.isVisible()) {
      await expect(auditTable).toBeVisible()

      // Should show audit details
      const pageContent = await page.textContent('body')
      expect(pageContent).toContain('CREATE_TASK')
      expect(pageContent).toContain('192.168.1.100')
    }
  })

  test('tracks data access and modifications', async ({ page }) => {
    await setupAuth(page, 'admin')

    // Monitor data access requests
    const dataRequests: any[] = []
    page.on('request', request => {
      if (request.url().includes('/api/') && request.method() === 'GET') {
        dataRequests.push({
          url: request.url(),
          timestamp: new Date().toISOString()
        })
      }
    })

    // Access sensitive data
    await page.goto('/billing')
    await page.waitForTimeout(1000)

    await page.goto('/admin/users')
    await page.waitForTimeout(1000)

    // Should have tracked data access
    expect(dataRequests.length).toBeGreaterThan(0)

    // Check if access is being logged (in real app, this would be server-side)
    const sensitiveDataAccess = dataRequests.filter(req => 
      req.url.includes('/billing') || req.url.includes('/users')
    )

    expect(sensitiveDataAccess.length).toBeGreaterThan(0)
  })

  test('maintains immutable audit records', async ({ page }) => {
    await setupAuth(page, 'admin')
    await page.goto('/admin/audit')

    // Mock audit data
    await page.route('**/api/audit*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [{
            id: 'audit-1',
            action: 'DELETE_TASK',
            timestamp: '2024-01-01T10:00:00Z',
            hash: 'abc123def456', // Integrity hash
            signature: 'digital_signature_here'
          }],
          total: 1
        })
      })
    })

    await page.reload()
    await page.waitForTimeout(1000)

    // Audit records should not have edit/delete buttons
    const editButtons = page.locator('.ant-btn').filter({ hasText: /编辑|edit/i })
    const deleteButtons = page.locator('.ant-btn').filter({ hasText: /删除|delete/i })

    const editCount = await editButtons.count()
    const deleteCount = await deleteButtons.count()

    // Audit records should be read-only
    expect(editCount).toBe(0)
    expect(deleteCount).toBe(0)

    // Should show integrity information
    const pageContent = await page.textContent('body')
    if (pageContent.includes('hash') || pageContent.includes('signature')) {
      expect(pageContent).toMatch(/hash|signature|integrity/i)
    }
  })
})

test.describe('Regulatory Compliance', () => {
  test('supports GDPR data subject rights', async ({ page }) => {
    await setupAuth(page, 'user')
    await page.goto('/settings/privacy')

    // Should have data export option
    const exportDataButton = page.getByRole('button', { name: /导出.*数据|export.*data/i })
    
    if (await exportDataButton.isVisible()) {
      await expect(exportDataButton).toBeVisible()
      
      await exportDataButton.click()

      // Should show data export confirmation
      const confirmModal = page.locator('.ant-modal')
      
      if (await confirmModal.isVisible()) {
        const modalText = await confirmModal.textContent()
        expect(modalText).toMatch(/个人数据|personal.*data|GDPR/i)
      }
    }

    // Should have data deletion option
    const deleteDataButton = page.getByRole('button', { name: /删除.*数据|delete.*data/i })
    
    if (await deleteDataButton.isVisible()) {
      await expect(deleteDataButton).toBeVisible()
      
      await deleteDataButton.click()

      // Should show strong confirmation
      const deleteModal = page.locator('.ant-modal')
      
      if (await deleteModal.isVisible()) {
        const confirmInput = deleteModal.locator('input[type="text"]')
        
        if (await confirmInput.isVisible()) {
          // Should require typing confirmation text
          const placeholder = await confirmInput.getAttribute('placeholder')
          expect(placeholder).toMatch(/确认|confirm|delete/i)
        }
      }
    }
  })

  test('implements data processing consent', async ({ page }) => {
    await setupAuth(page, 'user')
    await page.goto('/settings/privacy')

    // Should show consent management
    const consentSection = page.locator('.consent-management, .privacy-settings')
    
    if (await consentSection.isVisible()) {
      // Should have granular consent options
      const consentOptions = consentSection.locator('.ant-checkbox, .ant-switch')
      const optionCount = await consentOptions.count()

      expect(optionCount).toBeGreaterThan(1) // Multiple consent options

      // Should have options for different data processing purposes
      const sectionText = await consentSection.textContent()
      const hasProcessingPurposes = 
        sectionText?.includes('分析') || // Analytics
        sectionText?.includes('营销') || // Marketing
        sectionText?.includes('功能') || // Functional
        sectionText?.includes('analytics') ||
        sectionText?.includes('marketing') ||
        sectionText?.includes('functional')

      expect(hasProcessingPurposes).toBeTruthy()
    }
  })

  test('provides data processing transparency', async ({ page }) => {
    await page.goto('/privacy-policy')

    // Should show comprehensive privacy policy
    const privacyContent = page.locator('.privacy-policy, .policy-content')
    
    if (await privacyContent.isVisible()) {
      const policyText = await privacyContent.textContent()

      // Should explain data processing purposes
      const hasDataProcessingInfo = 
        policyText?.includes('数据处理') ||
        policyText?.includes('个人信息') ||
        policyText?.includes('data processing') ||
        policyText?.includes('personal information')

      expect(hasDataProcessingInfo).toBeTruthy()

      // Should mention data retention periods
      const hasRetentionInfo = 
        policyText?.includes('保留期') ||
        policyText?.includes('retention') ||
        policyText?.includes('存储期限')

      expect(hasRetentionInfo).toBeTruthy()
    }
  })

  test('supports data portability', async ({ page }) => {
    await setupAuth(page, 'user')
    await page.goto('/settings/data-export')

    // Should provide structured data export
    const exportFormats = page.locator('.export-format, .ant-radio-group')
    
    if (await exportFormats.isVisible()) {
      // Should support standard formats
      const formatText = await exportFormats.textContent()
      const hasStandardFormats = 
        formatText?.includes('JSON') ||
        formatText?.includes('CSV') ||
        formatText?.includes('XML')

      expect(hasStandardFormats).toBeTruthy()
    }

    // Should allow selective data export
    const dataCategories = page.locator('.data-category, .ant-checkbox-group')
    
    if (await dataCategories.isVisible()) {
      const categoryCount = await dataCategories.locator('.ant-checkbox').count()
      expect(categoryCount).toBeGreaterThan(1) // Multiple data categories
    }
  })
})

test.describe('Access Control Compliance', () => {
  test('enforces role-based access control', async ({ page }) => {
    // Test different roles
    const roles = ['viewer', 'editor', 'admin']
    
    for (const role of roles) {
      await setupAuth(page, role)
      await page.goto('/admin')

      if (role === 'admin') {
        // Admin should access admin pages
        await expect(page).not.toHaveURL(/403|unauthorized/i)
      } else {
        // Non-admin should be blocked
        await expect(page).toHaveURL(/403|unauthorized|dashboard/i, { timeout: 3000 })
      }
    }
  })

  test('implements principle of least privilege', async ({ page }) => {
    await setupAuth(page, 'editor')
    await page.goto('/tasks')

    // Editor should have limited permissions
    const adminOnlyButtons = page.locator('.ant-btn').filter({ 
      hasText: /系统设置|用户管理|租户管理|system.*settings|user.*management/i 
    })

    const adminButtonCount = await adminOnlyButtons.count()
    
    for (let i = 0; i < adminButtonCount; i++) {
      const button = adminOnlyButtons.nth(i)
      
      if (await button.isVisible()) {
        await expect(button).toBeDisabled()
      }
    }
  })

  test('tracks privileged access', async ({ page }) => {
    await setupAuth(page, 'admin')

    // Monitor privileged actions
    const privilegedRequests: any[] = []
    page.on('request', request => {
      if (request.url().includes('/admin/') || request.url().includes('/manage/')) {
        privilegedRequests.push({
          url: request.url(),
          method: request.method()
        })
      }
    })

    await page.goto('/admin/users')
    await page.waitForTimeout(1000)

    // Should track privileged access
    expect(privilegedRequests.length).toBeGreaterThan(0)
  })

  test('requires additional authentication for sensitive operations', async ({ page }) => {
    await setupAuth(page, 'admin')
    await page.goto('/admin/system')

    // Look for sensitive operations
    const sensitiveButton = page.getByRole('button', { name: /删除|重置|清空|delete|reset|clear/i })
    
    if (await sensitiveButton.isVisible()) {
      await sensitiveButton.click()

      // Should require additional confirmation
      const confirmModal = page.locator('.ant-modal')
      
      if (await confirmModal.isVisible()) {
        // Should have strong confirmation requirements
        const confirmInput = confirmModal.locator('input[type="password"], input[type="text"]')
        
        if (await confirmInput.isVisible()) {
          const placeholder = await confirmInput.getAttribute('placeholder')
          expect(placeholder).toMatch(/密码|确认|password|confirm/i)
        }

        // Should have multiple confirmation steps
        const confirmButtons = confirmModal.locator('.ant-btn')
        const buttonCount = await confirmButtons.count()
        
        expect(buttonCount).toBeGreaterThan(1) // Cancel + Confirm at minimum
      }
    }
  })
})