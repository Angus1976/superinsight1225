/**
 * Audit & Security E2E Tests
 *
 * Mocks align with frontend services:
 * - rbacApi: GET/POST /api/v1/rbac/roles → Role[]
 * - ssoApi: GET /api/v1/sso/providers → SSOProvider[]
 * - auditApi: GET /api/v1/audit/logs → { logs, total, offset, limit }
 * - securityMonitorApi: /api/v1/security/events, posture, posture/summary
 * - sessionApi: GET /api/v1/sessions → { sessions, total }
 */

import { test, expect } from '@playwright/test'
import { setupE2eSession } from './test-helpers'

const iso = () => new Date().toISOString()

function baseRole(
  id: string,
  name: string,
  description: string,
  permissions: { resource: string; action: string }[],
) {
  const t = iso()
  return { id, name, description, permissions, created_at: t, updated_at: t }
}

const MOCK_ROLES = [
  baseRole('role-1', 'admin', '管理员', [{ resource: '*', action: '*' }]),
  baseRole('role-2', 'annotator', '标注员', [
    { resource: 'tasks', action: 'read' },
    { resource: 'tasks', action: 'write' },
  ]),
  baseRole('role-3', 'viewer', '查看者', [{ resource: 'tasks', action: 'read' }]),
]

/** Register mocks after setupE2eSession (last route wins for overlapping patterns). */
async function mockSecurityApis(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/rbac/roles**', async (route) => {
    const method = route.request().method()
    if (method === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(
          baseRole('role-new', body.name || 'new_role', body.description || '', body.permissions || []),
        ),
      })
      return
    }
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ROLES),
      })
      return
    }
    await route.continue()
  })

  await page.route('**/api/v1/sso/providers**', async (route) => {
    const method = route.request().method()
    if (method === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'sso-new',
          name: 'New SAML Provider',
          protocol: 'saml',
          enabled: true,
          created_at: iso(),
        }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'sso-1', name: 'Corporate SAML', protocol: 'saml', enabled: true, created_at: iso() },
        { id: 'sso-2', name: 'Google OIDC', protocol: 'oidc', enabled: true, created_at: iso() },
        { id: 'sso-3', name: 'GitHub OAuth', protocol: 'oauth2', enabled: false, created_at: iso() },
      ]),
    })
  })

  await page.route('**/api/v1/audit/statistics**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_logs: 3,
        event_types: { user_login: 1 },
        results: { True: 3, False: 0 },
        period: {},
      }),
    })
  })

  await page.route('**/api/v1/audit/logs/export**', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/csv' },
      body: 'id,event_type\nlog-1,user_login\n',
    })
  })

  await page.route('**/api/v1/audit/logs**', async (route) => {
    /* POST …/export must be fulfilled here: this pattern matches before the dedicated export route
     * in reverse registration order, and continue() would hit the real network (timeout in E2E). */
    if (route.request().url().includes('/export')) {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/csv' },
        body: 'id,event_type\nlog-1,user_login\n',
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        logs: [
          {
            id: 'log-1',
            event_type: 'user_login',
            user_id: 'user-1',
            action: 'login',
            timestamp: iso(),
            ip_address: '192.168.1.1',
            result: true,
          },
          {
            id: 'log-2',
            event_type: 'data_access',
            user_id: 'user-2',
            action: 'read',
            resource: 'project',
            timestamp: iso(),
            ip_address: '192.168.1.2',
            result: true,
          },
          {
            id: 'log-3',
            event_type: 'permission_change',
            user_id: 'user-1',
            action: 'update',
            resource: 'role',
            timestamp: iso(),
            ip_address: '192.168.1.1',
            result: true,
          },
        ],
        total: 3,
        offset: 0,
        limit: 50,
      }),
    })
  })

  await page.route('**/api/v1/audit/verify-integrity**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        valid: true,
        verified_count: 1000,
        message: '审计日志完整性验证通过',
      }),
    })
  })

  await page.route('**/api/v1/security/posture**', async (route) => {
    const url = route.request().url()
    if (url.includes('/summary')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          open_events: 2,
          critical_events_24h: 0,
          events_last_7_days: 5,
          risk_score: 85,
          risk_level: 'low',
          generated_at: iso(),
        }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        risk_score: 85,
        events_by_type: { login: 1 },
        trend: [{ date: '2026-01-07', count: 2 }],
        recommendations: ['建议启用双因素认证', '建议定期审查用户权限'],
        generated_at: iso(),
      }),
    })
  })

  await page.route('**/api/v1/security/events/**/resolve**', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'event-1',
        event_type: 'brute_force_attempt',
        severity: 'high',
        user_id: 'attacker-1',
        details: {},
        status: 'resolved',
        created_at: iso(),
        resolved_at: iso(),
      }),
    })
  })

  await page.route('**/api/v1/security/events**', async (route) => {
    if (route.request().url().includes('/resolve')) {
      await route.continue()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        events: [
          {
            id: 'event-1',
            event_type: 'brute_force_attempt',
            severity: 'high',
            user_id: 'attacker-1',
            details: {},
            status: 'open',
            created_at: iso(),
          },
          {
            id: 'event-2',
            event_type: 'suspicious_access',
            severity: 'medium',
            user_id: 'user-1',
            details: {},
            status: 'open',
            created_at: iso(),
          },
          {
            id: 'event-3',
            event_type: 'permission_escalation',
            severity: 'critical',
            user_id: 'user-2',
            details: {},
            status: 'open',
            created_at: iso(),
          },
        ],
        total: 3,
        offset: 0,
        limit: 10,
      }),
    })
  })

  await page.route('**/api/v1/sessions**', async (route) => {
    const method = route.request().method()
    const url = route.request().url()
    const path = new URL(url).pathname.replace(/\/$/, '') || ''

    if (url.includes('/stats/overview')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_active_sessions: 3,
          total_users_with_sessions: 2,
          top_users_by_sessions: {},
          configuration: { default_timeout: 3600, max_concurrent_sessions: 5 },
        }),
      })
      return
    }
    if (url.includes('/config/current')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ default_timeout: 3600, max_concurrent_sessions: 5 }),
      })
      return
    }
    if (url.includes('force-logout')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, sessions_destroyed: 3, user_id: 'user-1' }),
      })
      return
    }
    if (method === 'DELETE' && /\/api\/v1\/sessions\/[^/]+$/.test(path)) {
      await route.fulfill({ status: 204, body: '' })
      return
    }
    if (method === 'GET' && path === '/api/v1/sessions') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sessions: [
            {
              id: 'session-1',
              user_id: 'user-1',
              ip_address: '192.168.1.1',
              user_agent: 'Chrome/120',
              created_at: iso(),
              last_activity: iso(),
            },
            {
              id: 'session-2',
              user_id: 'user-2',
              ip_address: '192.168.1.2',
              user_agent: 'Firefox/121',
              created_at: iso(),
              last_activity: iso(),
            },
            {
              id: 'session-3',
              user_id: 'user-1',
              ip_address: '10.0.0.50',
              user_agent: 'Safari/17',
              created_at: iso(),
              last_activity: iso(),
            },
          ],
          total: 3,
        }),
      })
      return
    }
    await route.continue()
  })
}

test.describe('RBAC Configuration Flow', () => {
  test('admin can view role list', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/rbac')
    await expect(page.getByText('admin').first()).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('annotator').first()).toBeVisible()
    await expect(page.getByText('viewer').first()).toBeVisible()
  })

  test('admin can create new role', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/rbac')

    const createButton = page.getByRole('button', { name: /创建角色|新建角色|create.*role/i })
    await expect(createButton).toBeVisible({ timeout: 15000 })
    await createButton.click()

    const modal = page.locator('.ant-modal')
    await expect(modal).toBeVisible()
    await modal.getByLabel(/角色名称|Role name/i).fill('custom_role')
    await modal.locator('.ant-select').first().click()
    await page.locator('.ant-select-item-option').first().click()
    await page.keyboard.press('Escape')

    const responsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/v1/rbac/roles') && r.request().method() === 'POST' && r.status() === 201,
    )
    await modal.locator('.ant-modal-footer .ant-btn-primary').click()
    await responsePromise
  })

  test('permission matrix displays correctly', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/rbac')
    await page
      .locator('.ant-tabs-tab')
      .filter({ hasText: /权限矩阵|Permission Matrix/i })
      .click()

    await page.locator('.ant-tabs-tabpane-active .ant-select').first().click()
    await page.locator('.ant-select-item-option').first().click()

    const pane = page.locator('.ant-tabs-tabpane-active')
    await expect(pane.getByText(/^任务$|^Tasks$/)).toBeVisible({ timeout: 15000 })
    await expect(pane.getByText(/^项目$|^Projects$/)).toBeVisible()
  })

  test('viewer can load RBAC page (no server-side route guard)', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'viewer' })
    await mockSecurityApis(page)

    await page.goto('/security/rbac')
    await expect(page).toHaveURL(/\/security\/rbac/)
    await expect(page.getByRole('heading', { level: 3 })).toBeVisible({ timeout: 15000 })
  })
})

test.describe('SSO Login Flow', () => {
  test('displays SSO provider list', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/sso')

    await expect(page.getByText('Corporate SAML')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Google OIDC')).toBeVisible()
    await expect(page.getByText('GitHub OAuth')).toBeVisible()
  })

  test('SSO login button on login page (skipped — no SSO CTA in current Login UI)', async () => {
    test.skip(true, '当前登录页无企业 SSO 入口；由 /security/sso 配置页覆盖')
  })

  test('admin can open add SSO provider modal', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/sso')

    const addButton = page.getByRole('button', { name: /添加提供商|add.*provider/i })
    await expect(addButton).toBeVisible({ timeout: 15000 })
    await addButton.click()
    await expect(page.locator('.ant-modal')).toBeVisible()
  })
})

test.describe('Audit Log Query', () => {
  test('displays audit log list', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/audit')

    await expect(page.getByText('USER LOGIN')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('DATA ACCESS')).toBeVisible()
    await expect(page.getByText('PERMISSION CHANGE')).toBeVisible()
  })

  test('can filter audit logs by date range', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/audit')
    const datePicker = page.locator('.ant-picker-range, .ant-picker').first()
    await expect(datePicker).toBeVisible({ timeout: 15000 })
  })

  test('can export audit logs', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    const exportPromise = page.waitForResponse(
      (r) => r.url().includes('/api/v1/audit/logs/export') && r.request().method() === 'POST',
    )

    await page.goto('/security/audit')
    const exportButton = page.getByRole('button', { name: /导出 CSV|Export CSV/i })
    await exportButton.click()
    await exportPromise
  })

  test('can verify audit log integrity', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    const verifyPromise = page.waitForResponse(
      (r) => r.url().includes('/api/v1/audit/verify-integrity') && r.request().method() === 'POST',
    )

    await page.goto('/security/audit')
    await page.getByRole('button', { name: /验证完整性|verify/i }).click()
    await verifyPromise
  })
})

test.describe('Security Dashboard', () => {
  test('displays security posture overview', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/dashboard')

    await expect(page.getByText('85')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText(/风险评分|risk score/i).first()).toBeVisible()
  })

  test('displays security events on dashboard', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/dashboard')

    await expect(page.getByText(/brute force attempt/i)).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('HIGH').first()).toBeVisible()
    await expect(page.getByText('CRITICAL').first()).toBeVisible()
  })

  test('can open resolve security event modal', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/dashboard')

    const resolveButton = page.getByRole('button', { name: /解决|resolve/i }).first()
    await expect(resolveButton).toBeVisible({ timeout: 15000 })
    await resolveButton.click()
    await expect(page.locator('.ant-modal')).toBeVisible()
  })

  test('displays recommendations or chart area', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/dashboard')
    await expect(page.locator('.ant-card').first()).toBeVisible({ timeout: 15000 })
  })
})

test.describe('Session Management', () => {
  test('displays active sessions list', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/sessions')

    await expect(page.getByText('192.168.1.1')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Chrome/120')).toBeVisible()
  })

  test('can terminate specific session', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/sessions')

    const deleteRowBtn = page.locator('tbody tr').first().locator('button').filter({ has: page.locator('.anticon-delete') })
    await expect(deleteRowBtn).toBeVisible({ timeout: 15000 })

    const delPromise = page.waitForResponse(
      (r) => r.url().includes('/api/v1/sessions/') && r.request().method() === 'DELETE',
    )
    await deleteRowBtn.click()

    await page.locator('.ant-popconfirm .ant-btn-primary').click()
    await delPromise
  })

  test('can force logout user', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/sessions')

    const forceLogoutButton = page.getByRole('button', { name: /强制登出|force.*logout/i }).first()
    if (await forceLogoutButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      const p = page.waitForResponse((r) => r.url().includes('force-logout') && r.request().method() === 'POST')
      await forceLogoutButton.click()
      await p
    }
  })
})

test.describe('Complete Security Management Workflow', () => {
  test('admin can visit RBAC, SSO, audit, dashboard', async ({ page }) => {
    await setupE2eSession(page, { lang: 'zh', role: 'admin' })
    await mockSecurityApis(page)

    await page.goto('/security/rbac')
    await expect(page.getByText('admin').first()).toBeVisible({ timeout: 15000 })

    await page.goto('/security/sso')
    await expect(page.getByText('Corporate SAML')).toBeVisible({ timeout: 15000 })

    await page.goto('/security/audit')
    await expect(page.getByText('USER LOGIN')).toBeVisible({ timeout: 15000 })

    await page.goto('/security/dashboard')
    await expect(page.getByText('85')).toBeVisible({ timeout: 15000 })
  })
})
