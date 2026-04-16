/**
 * 其余子路由与错误页烟测（与 core / admin-subroutes 互补）。
 * 断言：未退回登录；页面出现常见 Ant 壳或 Result。
 */
describe('其余路由与错误页', () => {
  const authedPaths = [
    '/ai-assistant',
    '/tasks/list',
    '/billing/reports',
    '/augmentation/samples',
    '/augmentation/config',
    '/quality/workflow/tasks',
    '/quality/workflow/config',
    '/quality/workflow/tasks/00000000-0000-4000-8000-000000000001',
    '/license/activate',
    '/license/report',
    '/license/alerts',
    '/security/rbac',
    '/security/sso',
    '/security/sessions',
    '/security/data-permissions',
    '/data-sync/history',
    '/data-sync/scheduler',
    '/data-sync/security',
    '/data-sync/export',
    '/data-sync/datalake/sources',
    '/data-sync/datalake/dashboard',
    '/data-sync/datalake/schema-browser',
    '/data-sync/api-management',
    '/data-lifecycle/tasks',
    '/data-lifecycle/enhancement',
    '/data-lifecycle/trials',
    '/data-lifecycle/audit',
  ]

  function assertLoadedPage(path: string, pathPrefix: string) {
    cy.visit(path)
    cy.location('pathname', { timeout: 30_000 }).should('include', pathPrefix)
    cy.url().should('not.include', '/login')
    cy.get('.ant-layout, .ant-layout-content, [class*="layout"], .ant-card, .ant-result, .ant-table, .ant-spin-nested-loading', {
      timeout: 25_000,
    }).should('exist')
  }

  it('登录后子模块深层路由可打开', () => {
    cy.login()
    for (const path of authedPaths) {
      const prefix = path.split('?')[0]
      assertLoadedPage(path, prefix)
    }
  })

  it('/404、/403、/500 应展示 Result 页', () => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
    cy.visit('/404')
    cy.get('.ant-result', { timeout: 15_000 }).should('be.visible')
    cy.visit('/403')
    cy.get('.ant-result', { timeout: 15_000 }).should('be.visible')
    cy.visit('/500')
    cy.get('.ant-result', { timeout: 15_000 }).should('be.visible')
  })
})
