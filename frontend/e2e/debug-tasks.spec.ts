import { test } from './fixtures'
import { waitForPageReady } from './test-helpers'

function base64url(obj: Record<string, unknown>): string {
  return Buffer.from(JSON.stringify(obj))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

function buildMockJwt(): string {
  const header = base64url({ alg: 'HS256', typ: 'JWT' })
  const payload = base64url({
    sub: 'user-admin',
    exp: Math.floor(Date.now() / 1000) + 3600,
    tenant_id: 'tenant-1',
    role: 'admin',
  })
  return `${header}.${payload}.mock-signature`
}

test('debug tasks page', async ({ page }) => {
  const consoleMsgs: string[] = []
  page.on('console', msg => consoleMsgs.push(`[${msg.type()}] ${msg.text()}`))

  const token = buildMockJwt()
  await page.addInitScript((tkn) => {
    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user: {
            id: 'user-admin', username: 'admin', name: '管理员',
            email: 'admin@example.com', tenant_id: 'tenant-1',
            role: 'admin', roles: ['admin'], permissions: ['read:all', 'write:all', 'manage:all'],
          },
          token: tkn,
          currentTenant: { id: 'tenant-1', name: '测试租户' },
          isAuthenticated: true,
        },
      })
    )
    localStorage.setItem('auth_token', JSON.stringify(tkn))
  }, token)

  // Log all intercepted requests for debugging
  page.on('request', req => {
    if (req.url().includes('/api/')) {
      console.log('REQUEST:', req.method(), req.url())
    }
  })
  page.on('response', res => {
    if (res.url().includes('/api/')) {
      console.log('RESPONSE:', res.status(), res.url())
    }
  })

  await page.route('**/api/tasks/stats', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: 1, pending: 1, in_progress: 0, completed: 0, cancelled: 0 }),
    })
  })

  await page.route('**/api/tasks**', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 'task-1', name: 'Test', status: 'pending', priority: 'medium', annotation_type: 'text_classification', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
          total: 1, page: 1, page_size: 10,
        }),
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.route('**/api/auth/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/auth/tenants**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 'tenant-1', name: '测试租户' }]) })
  })
  await page.route('**/api/workspaces/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/api/label-studio/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/billing/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/users/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.route('**/api/quality/**', async (route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto('/tasks')
  await waitForPageReady(page)
  await page.waitForTimeout(3000)

  const buttons = await page.locator('button').allTextContents()
  console.log('BUTTONS:', JSON.stringify(buttons))

  // Also check for links and other clickable elements
  const links = await page.locator('a').allTextContents()
  console.log('LINKS:', JSON.stringify(links))

  const allText = await page.locator('body').innerText()
  console.log('PAGE_TEXT (500):', allText.substring(0, 500))

  console.log('CONSOLE_MSGS:', JSON.stringify(consoleMsgs.slice(0, 15)))
  console.log('CURRENT_URL:', page.url())
})
