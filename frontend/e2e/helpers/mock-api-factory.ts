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
  /** Initial rows for `GET /api/llm-configs` (see `LLMApplicationBinding`). */
  llmConfigs?: Record<string, unknown>[]
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
// Delay helper + CORS (SPA on :5173, API on VITE_API_BASE_URL — cross-origin mocks must expose headers)
// ---------------------------------------------------------------------------

const CORS_PREFLIGHT_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,HEAD,PUT,PATCH,POST,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': '*',
}

async function fulfillCorsPreflightIfNeeded(route: any): Promise<boolean> {
  if (route.request().method() !== 'OPTIONS') return false
  await route.fulfill({ status: 204, headers: CORS_PREFLIGHT_HEADERS })
  return true
}

async function withDelay(route: any, delay: number | undefined, body: object, status = 200) {
  if (delay) await new Promise((r) => setTimeout(r, delay))
  await route.fulfill({
    status,
    contentType: 'application/json',
    headers: CORS_PREFLIGHT_HEADERS,
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

  // Quality workflow API (ImprovementTaskList / Detail / WorkflowConfig)
  const sampleImprovementTask = {
    id: 'task_001',
    annotation_id: 'ann-001',
    project_id: 'default',
    issues: [
      {
        rule_id: 'r1',
        rule_name: 'Label Consistency Check',
        severity: 'high' as const,
        message: 'Sample issue',
      },
    ],
    assignee_id: 'user1',
    assignee_name: 'John Doe',
    status: 'pending' as const,
    priority: 3,
    created_at: new Date().toISOString(),
  }

  await page.route(
    (url) => /\/api\/v1\/quality-workflow\/tasks\/[^/]+\/history\/?$/.test(url.pathname),
    (route) => {
      if (route.request().method() !== 'GET') return route.continue()
      return withDelay(route, delay, [])
    },
  )

  await page.route((url) => {
    const p = url.pathname
    return /\/api\/v1\/quality-workflow\/tasks\/[^/]+$/.test(p) && !p.endsWith('/history')
  }, (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    const id = new URL(route.request().url()).pathname.split('/').pop() || 'task_001'
    return withDelay(route, delay, { ...sampleImprovementTask, id })
  })

  await page.route((url) => /\/api\/v1\/quality-workflow\/tasks\/?$/.test(url.pathname), (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    return withDelay(route, delay, {
      items: [sampleImprovementTask],
      total: 1,
      page: 1,
      page_size: 10,
    })
  })

  await page.route('**/api/v1/quality-workflow/config/**', (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    return withDelay(route, delay, {
      id: 'wf-1',
      project_id: 'default',
      stages: ['identify', 'assign', 'improve', 'review', 'verify'],
      auto_create_task: true,
      escalation_rules: { hours: 24, max_level: 3 },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  })

  await page.route('**/api/v1/quality-workflow/configure', async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'POST') return route.continue()
    return withDelay(route, delay, {
      id: 'wf-1',
      project_id: 'default',
      stages: ['identify', 'assign', 'improve', 'review', 'verify'],
      auto_create_task: true,
      escalation_rules: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  })

  await page.route('**/api/v1/quality-workflow/effect/**', (route) => {
    if (route.request().method() !== 'GET') return route.continue()
    return withDelay(route, delay, {
      project_id: 'default',
      period: 'month',
      total_tasks: 10,
      completed_tasks: 7,
      average_improvement_score: 0.85,
      improvement_by_dimension: { accuracy: 0.1, completeness: 0.05 },
    })
  })

  await page.route('**/api/v1/quality-workflow/tasks/*/submit', async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'POST') return route.continue()
    return withDelay(route, delay, { ...sampleImprovementTask, status: 'submitted' })
  })

  await page.route('**/api/v1/quality-workflow/tasks/*/review', async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'POST') return route.continue()
    return withDelay(route, delay, { ...sampleImprovementTask, status: 'approved' })
  })

  // Reports page (/quality/reports) — React Query fetches metrics + report list
  await page.route('**/api/v1/quality/metrics**', (route) =>
    withDelay(route, delay, {
      overallScore: 0.92,
      totalSamples: 1000,
      passedSamples: 920,
      failedSamples: 80,
      trendData: [{ date: '2025-01-01', score: 0.9, samples: 100 }],
      scoreDistribution: [{ type: 'semantic', score: 0.9 }],
      ruleViolations: [{ rule: 'r1', count: 5, severity: 'high' }],
    }),
  )

  await page.route('**/api/v1/quality/reports**', (route) =>
    withDelay(route, delay, [
      {
        id: 'rep-1',
        name: '周报',
        type: 'weekly',
        overallScore: 0.88,
        semanticScore: 0.9,
        syntacticScore: 0.85,
        completenessScore: 0.87,
        consistencyScore: 0.86,
        accuracyScore: 0.89,
        totalSamples: 500,
        passedSamples: 440,
        failedSamples: 60,
        createdAt: new Date().toISOString(),
      },
    ]),
  )
}

/** Default apps for `ConfigurationMatrix` (fetchApplications). */
const DEFAULT_LLM_APPLICATIONS = [
  {
    id: 'app-structuring',
    code: 'structuring',
    name: '数据结构化',
    description: '模式推断和实体提取',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

/**
 * Mocks `/api/llm-configs` and related routes used by `LLMApplicationBinding` / `llmConfigStore`.
 * Register before `mockAllApis` when tests need non-empty configs; first matching route wins.
 */
export async function mockLlmApplicationBindingApis(
  page: Page,
  options: {
    configs?: Record<string, unknown>[]
    applications?: Record<string, unknown>[]
    delay?: number
  } = {},
): Promise<void> {
  const { delay } = options
  const applications = options.applications ?? DEFAULT_LLM_APPLICATIONS
  let configs: Record<string, unknown>[] = structuredClone(options.configs ?? [])

  const fulfillJson = async (route: Parameters<typeof withDelay>[0], body: object, status = 200) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    await withDelay(route, delay, body, status)
  }

  await page.route('**/api/llm-configs/applications**', async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'GET') return route.continue()
    const p = new URL(route.request().url()).pathname.replace(/\/$/, '')
    const last = p.split('/').pop() || ''
    if (last === 'applications') {
      await fulfillJson(route, applications as unknown as object)
      return
    }
    const app = applications.find((a: Record<string, unknown>) => (a.code as string) === last)
    await fulfillJson(route, (app ?? applications[0]) as unknown as object)
  })

  await page.route('**/api/llm-configs/bindings**', async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'GET') return route.continue()
    const p = new URL(route.request().url()).pathname.replace(/\/$/, '')
    if (p !== '/api/llm-configs/bindings') return route.continue()
    await fulfillJson(route, [])
  })

  await page.route(/\/api\/llm-configs\/[^/]+\/test\/?$/, async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'POST') return route.continue()
    await fulfillJson(route, { status: 'success', latency_ms: 245 })
  })

  await page.route(/\/api\/llm-configs\/[^/]+$/, async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    const p = new URL(route.request().url()).pathname.replace(/\/$/, '')
    const last = p.split('/').pop() || ''
    if (last === 'applications' || last === 'bindings') return route.continue()
    const id = last
    const method = route.request().method()

    if (method === 'GET') {
      const c = configs.find((x) => x.id === id)
      if (!c) return fulfillJson(route, { message: 'Not found' }, 404)
      return fulfillJson(route, c as object)
    }
    if (method === 'PUT') {
      const body = JSON.parse(route.request().postData() || '{}')
      const idx = configs.findIndex((x) => x.id === id)
      if (idx >= 0) {
        configs[idx] = {
          ...configs[idx],
          ...body,
          updated_at: new Date().toISOString(),
        }
        return fulfillJson(route, configs[idx] as object)
      }
      return fulfillJson(route, { message: 'Not found' }, 404)
    }
    if (method === 'DELETE') {
      configs = configs.filter((x) => x.id !== id)
      return fulfillJson(route, {}, 204)
    }
    return route.continue()
  })

  await page.route('**/api/llm-configs', async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    const pathname = new URL(route.request().url()).pathname.replace(/\/$/, '')
    if (pathname !== '/api/llm-configs') return route.continue()
    const method = route.request().method()
    if (method === 'GET') return fulfillJson(route, configs as unknown as object)
    if (method === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      const newConfig = {
        id: `llm-${Date.now()}`,
        name: body.name,
        provider: body.provider,
        base_url: body.base_url,
        model_name: body.model_name,
        parameters: typeof body.parameters === 'object' && body.parameters ? body.parameters : {},
        is_active: body.is_active !== false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      configs.push(newConfig)
      return fulfillJson(route, newConfig as object, 201)
    }
    return route.continue()
  })
}

export async function mockAdminApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { count = 5, tenantId = 'tenant-1', delay } = options
  const users = generateUsers(count, tenantId)

  await page.route('**/api/auth/tenants', (route) => {
    if (route.request().method() === 'GET') {
      // authService.getTenants() returns response.data as Tenant[] (not paginated wrapper)
      return withDelay(route, delay, [
        { id: 'tenant-1', name: '测试租户1', status: 'active' },
        { id: 'tenant-2', name: '测试租户2', status: 'active' },
      ])
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

  await page.route('**/api/llm-bindings', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )

  await page.route('**/api/applications', (route) =>
    withDelay(route, delay, { data: [], total: 0 }),
  )
}

/**
 * Multi-tenant REST API for Admin Quota Management (`QuotaManagement.tsx`).
 */
export async function mockMultiTenantQuotaApi(page: Page, options: MockOptions = {}): Promise<void> {
  const { delay } = options

  const sampleTenant = {
    id: 'tenant-1',
    name: '测试租户1',
    description: 'E2E tenant',
    status: 'active' as const,
    admin_email: 'admin@example.com',
    plan: 'enterprise',
    config: {
      features: {} as Record<string, boolean>,
      security: {} as Record<string, unknown>,
      workspace_defaults: {} as Record<string, unknown>,
      custom_settings: {} as Record<string, unknown>,
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }

  const quotaFor = (entityId: string) => ({
    entity_id: entityId,
    entity_type: 'tenant' as const,
    storage_bytes: 100 * 1024 * 1024 * 1024,
    project_count: 100,
    user_count: 50,
    api_call_count: 1_000_000,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })

  const usageBody = () => ({
    storage_bytes: 10 * 1024 * 1024 * 1024,
    project_count: 5,
    user_count: 8,
    api_call_count: 50_000,
    last_updated: new Date().toISOString(),
  })

  await page.route((url) => {
    const p = url.pathname.replace(/\/$/, '') || url.pathname
    return p === '/api/v1/tenants'
  }, async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'GET') return route.continue()
    return withDelay(route, delay, [sampleTenant])
  })

  await page.route((url) => /\/api\/v1\/quotas\/tenant\/[^/]+\/usage\/?$/.test(url.pathname), async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    if (route.request().method() !== 'GET') return route.continue()
    return withDelay(route, delay, usageBody())
  })

  await page.route((url) => {
    const p = url.pathname
    return /\/api\/v1\/quotas\/tenant\/[^/]+$/.test(p) && !p.endsWith('/usage')
  }, async (route) => {
    if (await fulfillCorsPreflightIfNeeded(route)) return
    const method = route.request().method()
    if (method === 'PUT' || method === 'PATCH') {
      return withDelay(route, delay, quotaFor('tenant-1'))
    }
    if (method !== 'GET') return route.continue()
    const parts = route.request().url().split('/')
    const id = parts[parts.length - 1]?.split('?')[0] || 'tenant-1'
    return withDelay(route, delay, quotaFor(id))
  })
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
  await mockLlmApplicationBindingApis(page, {
    delay: options.delay,
    configs: options.llmConfigs ?? [],
  })

  // Session + workspaces: avoid real 401s when E2E uses mocked localStorage auth
  await page.route('**/api/auth/me', (route) =>
    withDelay(route, options.delay, {
      id: 'e2e-user',
      username: 'e2euser',
      email: 'e2e@example.com',
      role: 'admin',
      tenant_id: 'tenant-1',
      is_active: true,
    }),
  )
  await page.route('**/api/workspaces/my', (route) => withDelay(route, options.delay, []))

  await mockDashboardApi(page, options)
  await mockTasksApi(page, options)
  await mockBillingApi(page, options)
  await mockDataSyncApi(page, options)
  await mockQualityApi(page, options)
  await mockAdminApi(page, options)
  await mockMultiTenantQuotaApi(page, options)
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
