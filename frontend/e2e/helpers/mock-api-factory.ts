/**
 * Mock API Factory for E2E Testing
 *
 * Centralized, typed mock response generators using page.route() interception.
 * Each function returns schema-valid JSON matching backend response formats
 * from frontend/src/constants/api.ts.
 *
 * Requirements: 16.2, 2.1, 2.2
 */

import { Page } from '@playwright/test'

export interface MockOptions {
  count?: number
  status?: string
  tenantId?: string
  delay?: number
}

// ---------------------------------------------------------------------------
// Mock data generators
// ---------------------------------------------------------------------------

function generateTasks(count: number, tenantId: string, status?: string) {
  return Array.from({ length: count }, (_, i) => ({
    id: `task-${i + 1}`,
    name: `测试任务 ${i + 1}`,
    status: status || ['pending', 'in_progress', 'completed'][i % 3],
    assignee: `用户${(i % 5) + 1}`,
    progress: Math.min(100, (i + 1) * 20),
    tenant_id: tenantId,
    createdAt: new Date(Date.now() - i * 86400000).toISOString(),
    updatedAt: new Date().toISOString(),
  }))
}

function generateBillingRecords(count: number, tenantId: string, status?: string) {
  return Array.from({ length: count }, (_, i) => ({
    id: `bill-${i + 1}`,
    period: `2024-${String(i + 1).padStart(2, '0')}`,
    amount: 10000 + i * 5000,
    status: status || ['pending', 'paid', 'overdue'][i % 3],
    tenant_id: tenantId,
  }))
}

function generateDataSources(count: number) {
  const types = ['postgresql', 'mysql', 'mongodb', 'api'] as const
  return Array.from({ length: count }, (_, i) => ({
    id: `source-${i + 1}`,
    name: `数据源 ${i + 1}`,
    type: types[i % types.length],
    status: i % 3 === 2 ? 'error' : 'connected',
    lastSyncAt: new Date(Date.now() - i * 3600000).toISOString(),
    rowCount: 1000 * (i + 1),
  }))
}

function generateUsers(count: number, tenantId: string) {
  const roles = ['admin', 'data_manager', 'data_analyst', 'annotator'] as const
  return Array.from({ length: count }, (_, i) => ({
    id: `user-${i + 1}`,
    username: `user${i + 1}`,
    email: `user${i + 1}@example.com`,
    role: roles[i % roles.length],
    is_active: i % 5 !== 4,
    tenant_id: tenantId,
  }))
}

// ---------------------------------------------------------------------------
// Delay helper
// ---------------------------------------------------------------------------

async function withDelay(route: any, delay: number | undefined, body: object, status = 200) {
  if (delay) await new Promise((r) => setTimeout(r, delay))
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

// ---------------------------------------------------------------------------
// Per-domain mock functions
// ---------------------------------------------------------------------------

export async function mockTasksApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { count = 5, status, tenantId = 'tenant-1', delay } = options
  const tasks = generateTasks(count, tenantId, status)

  await page.route('**/api/tasks/stats', (route) =>
    withDelay(route, delay, { total: count, pending: 1, in_progress: 2, completed: 2 }),
  )

  await page.route('**/api/tasks?**', (route) =>
    withDelay(route, delay, { data: tasks, total: count }),
  )

  await page.route('**/api/tasks', (route) => {
    if (route.request().method() === 'GET') {
      return withDelay(route, delay, { data: tasks, total: count })
    }
    return withDelay(route, delay, { ...tasks[0], id: `task-new-${Date.now()}` }, 201)
  })

  await page.route(/\/api\/tasks\/[^/]+$/, (route) => {
    const method = route.request().method()
    if (method === 'GET') return withDelay(route, delay, tasks[0])
    if (method === 'PUT' || method === 'PATCH') return withDelay(route, delay, tasks[0])
    if (method === 'DELETE') return withDelay(route, delay, { success: true })
    return route.continue()
  })

  await page.route(/\/api\/tasks\/[^/]+\/assign$/, (route) =>
    withDelay(route, delay, { success: true }),
  )
}

export async function mockBillingApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { count = 5, status, tenantId = 'tenant-1', delay } = options
  const records = generateBillingRecords(count, tenantId, status)

  await page.route('**/api/billing/records/**', (route) =>
    withDelay(route, delay, { data: records, total: count }),
  )

  await page.route('**/api/billing/analysis/**', (route) =>
    withDelay(route, delay, {
      totalAmount: records.reduce((s, r) => s + r.amount, 0),
      paidAmount: records.filter((r) => r.status === 'paid').reduce((s, r) => s + r.amount, 0),
      pendingAmount: records.filter((r) => r.status === 'pending').reduce((s, r) => s + r.amount, 0),
    }),
  )

  await page.route('**/api/billing/analytics/trends/**', (route) =>
    withDelay(route, delay, {
      data: records.map((r) => ({ period: r.period, amount: r.amount })),
    }),
  )
}

export async function mockDashboardApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { delay } = options

  await page.route('**/api/business-metrics/summary', (route) =>
    withDelay(route, delay, {
      activeTasks: 42,
      todayAnnotations: 156,
      totalCorpus: 12500,
      totalBilling: 89750.5,
    }),
  )

  await page.route('**/api/business-metrics/annotation-efficiency', (route) =>
    withDelay(route, delay, { avgTime: 45, completionRate: 0.87, dailyCount: 156 }),
  )

  await page.route('**/api/business-metrics/user-activity', (route) =>
    withDelay(route, delay, { activeUsers: 12, totalSessions: 48 }),
  )

  await page.route('**/api/business-metrics/ai-models', (route) =>
    withDelay(route, delay, { models: [], totalInferences: 0 }),
  )

  await page.route('**/api/business-metrics/projects', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )
}

export async function mockDataSyncApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { count = 3, delay } = options
  const sources = generateDataSources(count)

  await page.route('**/api/v1/datalake/sources', (route) => {
    if (route.request().method() === 'GET') {
      return withDelay(route, delay, { data: sources, total: count })
    }
    return withDelay(route, delay, sources[0], 201)
  })

  await page.route(/\/api\/v1\/datalake\/sources\/[^/]+\/test$/, (route) =>
    withDelay(route, delay, { connected: true, latency: 42 }),
  )

  await page.route(/\/api\/v1\/datalake\/sources\/[^/]+\/databases$/, (route) =>
    withDelay(route, delay, { data: ['db_main', 'db_analytics'] }),
  )

  await page.route(/\/api\/v1\/datalake\/sources\/[^/]+\/tables$/, (route) =>
    withDelay(route, delay, { data: ['users', 'tasks', 'annotations'] }),
  )

  await page.route('**/api/v1/datalake/dashboard/overview', (route) =>
    withDelay(route, delay, { totalSources: count, totalRows: 50000, healthScore: 0.95 }),
  )

  await page.route('**/api/v1/datalake/dashboard/health', (route) =>
    withDelay(route, delay, { status: 'healthy', checks: [] }),
  )

  await page.route('**/api/v1/datalake/dashboard/volume-trends', (route) =>
    withDelay(route, delay, { data: [] }),
  )

  await page.route('**/api/v1/datalake/dashboard/query-performance', (route) =>
    withDelay(route, delay, { avgLatency: 120, p95Latency: 350 }),
  )
}

export async function mockQualityApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { delay } = options

  await page.route('**/api/quality/dashboard/summary', (route) =>
    withDelay(route, delay, {
      totalAnnotations: 5000,
      qualityScore: 0.92,
      passRate: 0.88,
      issueCount: 14,
    }),
  )

  await page.route('**/api/quality/rules', (route) => {
    if (route.request().method() === 'GET') {
      return withDelay(route, delay, {
        data: [
          { id: 'rule-1', name: '完整性检查', enabled: true, severity: 'high' },
          { id: 'rule-2', name: '一致性检查', enabled: true, severity: 'medium' },
        ],
        total: 2,
      })
    }
    return withDelay(route, delay, { success: true }, 201)
  })

  await page.route('**/api/quality/issues', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )

  await page.route('**/api/quality/rules/run-all', (route) =>
    withDelay(route, delay, { success: true, issuesFound: 3 }),
  )

  await page.route('**/api/quality/stats', (route) =>
    withDelay(route, delay, { totalRules: 2, enabledRules: 2, lastRunAt: new Date().toISOString() }),
  )
}

export async function mockAdminApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { count = 5, tenantId = 'tenant-1', delay } = options
  const users = generateUsers(count, tenantId)

  await page.route('**/api/auth/tenants', (route) => {
    if (route.request().method() === 'GET') {
      return withDelay(route, delay, {
        data: [
          { id: 'tenant-1', name: '测试租户1', status: 'active' },
          { id: 'tenant-2', name: '测试租户2', status: 'active' },
        ],
        total: 2,
      })
    }
    return withDelay(route, delay, { id: 'tenant-new', name: 'New Tenant', status: 'active' }, 201)
  })

  await page.route(/\/api\/auth\/tenants\/[^/]+$/, (route) => {
    const method = route.request().method()
    if (method === 'DELETE') return withDelay(route, delay, { success: true })
    return withDelay(route, delay, { id: 'tenant-1', name: '测试租户1', status: 'active' })
  })

  await page.route('**/api/security/users', (route) =>
    withDelay(route, delay, { data: users, total: count }),
  )

  await page.route(/\/api\/security\/users\/[^/]+$/, (route) =>
    withDelay(route, delay, users[0]),
  )

  await page.route(/\/api\/security\/users\/[^/]+\/role$/, (route) =>
    withDelay(route, delay, { success: true }),
  )

  await page.route('**/api/llm-configs', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )

  await page.route(/\/api\/llm-configs\/[^/]+\/test$/, (route) =>
    withDelay(route, delay, { success: true, latency: 200 }),
  )

  await page.route('**/api/llm-bindings', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )

  await page.route('**/api/applications', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )
}

export async function mockAIApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { delay } = options

  await page.route('**/api/augmentation/jobs', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )

  await page.route('**/api/augmentation/samples', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )

  await page.route('**/api/augmentation/stats', (route) =>
    withDelay(route, delay, { totalJobs: 0, completedJobs: 0, totalSamples: 0 }),
  )
}

/**
 * Mock all major API endpoints at once.
 * Convenience wrapper for tests that need a fully mocked backend.
 */
export async function mockAllApis(page: Page, options: MockOptions = {}): Promise<void> {
  await mockDashboardApi(page, options)
  await mockTasksApi(page, options)
  await mockBillingApi(page, options)
  await mockDataSyncApi(page, options)
  await mockQualityApi(page, options)
  await mockAdminApi(page, options)
  await mockAIApi(page, options)

  // Catch-all for security endpoints
  await page.route('**/api/security/audit-logs**', (route) =>
    withDelay(route, options.delay, { data: [], total: 0 }),
  )
  await page.route('**/api/security/audit/summary', (route) =>
    withDelay(route, options.delay, { totalEvents: 0, criticalEvents: 0 }),
  )
  await page.route('**/api/security/permissions', (route) =>
    withDelay(route, options.delay, { data: [], total: 0 }),
  )
  await page.route('**/api/security/stats', (route) =>
    withDelay(route, options.delay, { totalUsers: 5, activeSessions: 3 }),
  )
  await page.route('**/api/security/sessions', (route) =>
    withDelay(route, options.delay, { data: [], total: 0 }),
  )

  // Health / system
  await page.route('**/health', (route) =>
    withDelay(route, options.delay, { status: 'ok', services: {} }),
  )
  await page.route('**/system/status', (route) =>
    withDelay(route, options.delay, { status: 'running' }),
  )
}
