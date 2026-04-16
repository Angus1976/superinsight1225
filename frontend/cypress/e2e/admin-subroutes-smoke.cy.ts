/**
 * 管理端与业务子模块余下路由（与 core-routes-smoke 互补）。
 */
describe('管理端与子模块路由烟测', () => {
  const routes = [
    '/admin',
    '/admin/system',
    '/admin/permissions',
    '/admin/quotas',
    '/admin/billing',
    '/admin/workspaces',
    '/admin/members',
    '/admin/text-to-sql',
    '/admin/config/llm',
    '/admin/config/databases',
    '/admin/config/sync',
    '/admin/config/sql-builder',
    '/admin/config/history',
    '/admin/config/third-party',
    '/admin/ls-workspaces',
    '/quality/rules',
    '/quality/reports',
    '/license/usage',
    '/security/permissions',
    '/security/dashboard',
    '/data-sync/sources',
    '/data-lifecycle/temp-data',
    '/data-lifecycle/samples',
  ]

  it('登录后各路由应加载主布局且未退回登录页', () => {
    cy.login()
    for (const path of routes) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', path.split('?')[0])
      cy.get('.ant-layout, .ant-layout-content, [class*="layout"]', { timeout: 25_000 }).should('exist')
      cy.url().should('not.include', '/login')
    }
  })
})
