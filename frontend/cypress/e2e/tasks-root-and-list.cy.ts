/**
 * 任务列表：`/tasks` 与 `/tasks/list` 均应加载同一类界面（Ant Tabs + 未退回登录）。
 */
describe('任务根路径与 list 路径', () => {
  it('两者均应展示任务页 Tabs', () => {
    cy.login()
    for (const path of ['/tasks', '/tasks/list']) {
      cy.visit(path)
      if (path === '/tasks/list') {
        cy.location('pathname', { timeout: 30_000 }).should('include', '/tasks/list')
      } else {
        cy.location('pathname', { timeout: 30_000 }).should('satisfy', (p: string) =>
          p === '/tasks' || p === '/tasks/',
        )
      }
      cy.url().should('not.include', '/login')
      cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    }
  })
})
