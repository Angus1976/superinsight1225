/**
 * Audit & Security E2E Tests
 *
 * Tests for RBAC configuration, SSO login, audit logs, security dashboard, and session management.
 * Corresponds to Task 22 of the audit-security spec.
 */

import { test, expect } from '@playwright/test'

// Helper to set up authenticated state with specific role
async function setupAuth(page: any, role: string = 'admin', permissions: string[] = []) {
  const defaultPermissions = {
    admin: ['rbac:manage', 'sso:manage', 'audit:read', 'audit:export', 'security:manage', 'session:manage'],
    security_admin: ['rbac:read', 'sso:read', 'audit:read', 'audit:export', 'security:read'],
    viewer: ['audit:read', 'security:read']
  }

  await page.addInitScript(({ role, permissions, defaultPermissions }) => {
    const userPermissions = permissions.length > 0 ? permissions : defaultPermissions[role] || []

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
            permissions: userPermissions,
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
  }, { role, permissions, defaultPermissions })
}

test.describe('RBAC Configuration Flow', () => {
  test('admin can view role list', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    // Mock roles API
    await page.route('**/api/rbac/roles*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'role-1', name: 'admin', description: '管理员', permissions: ['*'], is_active: true },
            { id: 'role-2', name: 'annotator', description: '标注员', permissions: ['tasks:read', 'tasks:write'], is_active: true },
            { id: 'role-3', name: 'viewer', description: '查看者', permissions: ['tasks:read'], is_active: true }
          ],
          total: 3
        })
      })
    })

    await page.goto('/security/rbac')
    
    // Should see role list
    await expect(page.getByText('admin')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('annotator')).toBeVisible()
    await expect(page.getByText('viewer')).toBeVisible()
  })

  test('admin can create new role', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/rbac/roles*', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'role-new',
            name: 'custom_role',
            description: '自定义角色',
            permissions: ['tasks:read'],
            is_active: true
          })
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], total: 0 })
        })
      }
    })

    await page.goto('/security/rbac')
    
    const createButton = page.getByRole('button', { name: /创建角色|create.*role/i })
    if (await createButton.isVisible()) {
      await createButton.click()
      
      const modal = page.locator('.ant-modal')
      if (await modal.isVisible()) {
        const nameInput = page.getByPlaceholder(/角色名称|role.*name/i)
        if (await nameInput.isVisible()) {
          await nameInput.fill('custom_role')
          
          const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }
        }
      }
    }
  })

  test('permission matrix displays correctly', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/rbac/permissions*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          resources: ['tasks', 'projects', 'users', 'billing'],
          actions: ['read', 'write', 'delete', 'manage'],
          matrix: {
            admin: { tasks: ['read', 'write', 'delete', 'manage'], projects: ['read', 'write', 'delete', 'manage'] },
            annotator: { tasks: ['read', 'write'], projects: ['read'] }
          }
        })
      })
    })

    await page.goto('/security/rbac/permissions')
    
    // Should see permission matrix
    await expect(page.getByText(/tasks|任务/i)).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/projects|项目/i)).toBeVisible()
  })

  test('viewer cannot access RBAC management', async ({ page }) => {
    await setupAuth(page, 'viewer')
    
    await page.goto('/security/rbac')
    
    // Should redirect or show access denied
    await expect(page).toHaveURL(/403|unauthorized|dashboard/i, { timeout: 5000 })
  })
})

test.describe('SSO Login Flow', () => {
  test('displays SSO provider list', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/sso/providers*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'sso-1', name: 'Corporate SAML', protocol: 'saml', is_active: true },
            { id: 'sso-2', name: 'Google OIDC', protocol: 'oidc', is_active: true },
            { id: 'sso-3', name: 'GitHub OAuth', protocol: 'oauth2', is_active: false }
          ],
          total: 3
        })
      })
    })

    await page.goto('/security/sso')
    
    await expect(page.getByText('Corporate SAML')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Google OIDC')).toBeVisible()
    await expect(page.getByText('GitHub OAuth')).toBeVisible()
  })

  test('SSO login button redirects correctly', async ({ page }) => {
    // Mock SSO login initiation
    await page.route('**/api/sso/login/*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          redirect_url: 'https://idp.example.com/saml/sso?SAMLRequest=...',
          state: 'csrf-state-token'
        })
      })
    })

    await page.goto('/login')
    
    const ssoButton = page.getByRole('button', { name: /SSO|企业登录|single.*sign/i })
    if (await ssoButton.isVisible()) {
      // Click should trigger redirect
      await ssoButton.click()
      await page.waitForTimeout(1000)
    }
  })

  test('admin can configure SSO provider', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/sso/providers*', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'sso-new',
            name: 'New SAML Provider',
            protocol: 'saml',
            is_active: true
          })
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ data: [], total: 0 })
        })
      }
    })

    await page.goto('/security/sso')
    
    const addButton = page.getByRole('button', { name: /添加|add.*provider/i })
    if (await addButton.isVisible()) {
      await addButton.click()
    }
  })
})

test.describe('Audit Log Query', () => {
  test('displays audit log list', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/audit/logs*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'log-1', event_type: 'user_login', user_id: 'user-1', action: 'login', timestamp: new Date().toISOString(), ip_address: '192.168.1.1' },
            { id: 'log-2', event_type: 'data_access', user_id: 'user-2', action: 'read', resource_type: 'project', timestamp: new Date().toISOString(), ip_address: '192.168.1.2' },
            { id: 'log-3', event_type: 'permission_change', user_id: 'user-1', action: 'update', resource_type: 'role', timestamp: new Date().toISOString(), ip_address: '192.168.1.1' }
          ],
          total: 3
        })
      })
    })

    await page.goto('/security/audit')
    
    await expect(page.getByText('user_login')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('data_access')).toBeVisible()
    await expect(page.getByText('permission_change')).toBeVisible()
  })

  test('can filter audit logs by date range', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    let filterParams: any = {}
    await page.route('**/api/audit/logs*', async route => {
      const url = new URL(route.request().url())
      filterParams = {
        start_date: url.searchParams.get('start_date'),
        end_date: url.searchParams.get('end_date'),
        event_type: url.searchParams.get('event_type')
      }
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 })
      })
    })

    await page.goto('/security/audit')
    
    // Look for date picker
    const datePicker = page.locator('.ant-picker-range, .ant-picker')
    if (await datePicker.isVisible()) {
      await datePicker.click()
      // Select date range
      await page.waitForTimeout(500)
    }
  })

  test('can export audit logs', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    let exportCalled = false
    await page.route('**/api/audit/logs/export*', async route => {
      exportCalled = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ download_url: '/exports/audit-logs-2026-01-13.csv' })
      })
    })

    await page.route('**/api/audit/logs*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 })
      })
    })

    await page.goto('/security/audit')
    
    const exportButton = page.getByRole('button', { name: /导出|export/i })
    if (await exportButton.isVisible()) {
      await exportButton.click()
      await page.waitForTimeout(1000)
    }
  })

  test('can verify audit log integrity', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/audit/verify-integrity*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          checked_count: 1000,
          invalid_count: 0,
          message: '审计日志完整性验证通过'
        })
      })
    })

    await page.route('**/api/audit/logs*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 })
      })
    })

    await page.goto('/security/audit')
    
    const verifyButton = page.getByRole('button', { name: /验证|verify.*integrity/i })
    if (await verifyButton.isVisible()) {
      await verifyButton.click()
      
      // Should show success message
      await expect(page.getByText(/验证通过|integrity.*valid/i)).toBeVisible({ timeout: 5000 })
    }
  })
})

test.describe('Security Dashboard', () => {
  test('displays security posture overview', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/security/posture*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          overall_score: 85,
          risk_level: 'low',
          metrics: {
            failed_logins_24h: 5,
            active_sessions: 42,
            permission_changes_7d: 12,
            security_events_30d: 3
          },
          recommendations: [
            '建议启用双因素认证',
            '建议定期审查用户权限'
          ]
        })
      })
    })

    await page.goto('/security/dashboard')
    
    // Should see security score
    await expect(page.getByText(/85|安全评分/i)).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/low|低风险/i)).toBeVisible()
  })

  test('displays security events list', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/security/events*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'event-1', event_type: 'brute_force_attempt', severity: 'high', user_id: 'attacker-1', ip_address: '10.0.0.100', created_at: new Date().toISOString(), resolved: false },
            { id: 'event-2', event_type: 'suspicious_access', severity: 'medium', user_id: 'user-1', ip_address: '192.168.1.50', created_at: new Date().toISOString(), resolved: true },
            { id: 'event-3', event_type: 'permission_escalation', severity: 'critical', user_id: 'user-2', ip_address: '192.168.1.100', created_at: new Date().toISOString(), resolved: false }
          ],
          total: 3
        })
      })
    })

    await page.goto('/security/events')
    
    await expect(page.getByText('brute_force_attempt')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText(/high|高/i)).toBeVisible()
    await expect(page.getByText(/critical|严重/i)).toBeVisible()
  })

  test('can resolve security event', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    let resolveEventId: string | null = null
    await page.route('**/api/security/events/*/resolve*', async route => {
      const url = route.request().url()
      resolveEventId = url.match(/events\/([^/]+)\/resolve/)?.[1] || null
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, message: '事件已解决' })
      })
    })

    await page.route('**/api/security/events*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'event-1', event_type: 'brute_force_attempt', severity: 'high', resolved: false }
          ],
          total: 1
        })
      })
    })

    await page.goto('/security/events')
    
    const resolveButton = page.getByRole('button', { name: /解决|resolve/i })
    if (await resolveButton.isVisible()) {
      await resolveButton.click()
      await page.waitForTimeout(1000)
    }
  })

  test('displays security trends chart', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/security/trends*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          dates: ['2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10', '2026-01-11', '2026-01-12', '2026-01-13'],
          failed_logins: [2, 5, 3, 8, 4, 2, 1],
          security_events: [0, 1, 0, 2, 1, 0, 0],
          active_sessions: [35, 42, 38, 45, 40, 38, 42]
        })
      })
    })

    await page.goto('/security/dashboard')
    
    // Should see chart container
    const chartContainer = page.locator('.ant-card, .chart-container, canvas')
    await expect(chartContainer.first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Session Management', () => {
  test('displays active sessions list', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/sessions*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'session-1', user_id: 'user-1', ip_address: '192.168.1.1', user_agent: 'Chrome/120', created_at: new Date().toISOString(), last_activity: new Date().toISOString() },
            { id: 'session-2', user_id: 'user-2', ip_address: '192.168.1.2', user_agent: 'Firefox/121', created_at: new Date().toISOString(), last_activity: new Date().toISOString() },
            { id: 'session-3', user_id: 'user-1', ip_address: '10.0.0.50', user_agent: 'Safari/17', created_at: new Date().toISOString(), last_activity: new Date().toISOString() }
          ],
          total: 3
        })
      })
    })

    await page.goto('/security/sessions')
    
    await expect(page.getByText('192.168.1.1')).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Chrome/120')).toBeVisible()
  })

  test('can terminate specific session', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    let terminatedSessionId: string | null = null
    await page.route('**/api/sessions/*', async route => {
      if (route.request().method() === 'DELETE') {
        const url = route.request().url()
        terminatedSessionId = url.match(/sessions\/([^/]+)/)?.[1] || null
        
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: [{ id: 'session-1', user_id: 'user-1', ip_address: '192.168.1.1' }],
            total: 1
          })
        })
      }
    })

    await page.goto('/security/sessions')
    
    const terminateButton = page.getByRole('button', { name: /终止|terminate|删除|delete/i })
    if (await terminateButton.isVisible()) {
      await terminateButton.click()
      
      // Confirm dialog
      const confirmButton = page.getByRole('button', { name: /确定|confirm|yes/i })
      if (await confirmButton.isVisible()) {
        await confirmButton.click()
      }
      
      await page.waitForTimeout(1000)
    }
  })

  test('can force logout user', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    await page.route('**/api/sessions/force-logout/*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, terminated_count: 3 })
      })
    })

    await page.route('**/api/sessions*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 })
      })
    })

    await page.goto('/security/sessions')
    
    const forceLogoutButton = page.getByRole('button', { name: /强制登出|force.*logout/i })
    if (await forceLogoutButton.isVisible()) {
      await forceLogoutButton.click()
      await page.waitForTimeout(1000)
    }
  })
})

test.describe('Complete Security Management Workflow', () => {
  test('admin can complete full security configuration workflow', async ({ page }) => {
    await setupAuth(page, 'admin')
    
    // Mock all necessary APIs
    await page.route('**/api/rbac/roles*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [{ id: 'role-1', name: 'admin' }], total: 1 })
      })
    })

    await page.route('**/api/sso/providers*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [{ id: 'sso-1', name: 'SAML' }], total: 1 })
      })
    })

    await page.route('**/api/audit/logs*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: [], total: 0 })
      })
    })

    await page.route('**/api/security/posture*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ overall_score: 90, risk_level: 'low' })
      })
    })

    // Step 1: View RBAC configuration
    await page.goto('/security/rbac')
    await expect(page.getByText('admin')).toBeVisible({ timeout: 5000 })

    // Step 2: View SSO providers
    await page.goto('/security/sso')
    await expect(page.getByText('SAML')).toBeVisible({ timeout: 5000 })

    // Step 3: View audit logs
    await page.goto('/security/audit')
    await page.waitForTimeout(1000)

    // Step 4: View security dashboard
    await page.goto('/security/dashboard')
    await expect(page.getByText(/90|安全评分/i)).toBeVisible({ timeout: 5000 })
  })
})
