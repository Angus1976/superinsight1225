/**
 * 路由重定向与索引跳转（登录态下）。
 */
describe('路由重定向', () => {
  beforeEach(() => {
    cy.login()
  })

  it('/tasks/create 应重定向到任务列表', () => {
    cy.visit('/tasks/create')
    cy.location('pathname', { timeout: 15_000 }).should('match', /\/tasks\/?$|\/tasks\/list$/)
  })

  it('/billing 应进入计费 overview', () => {
    cy.visit('/billing')
    cy.location('pathname', { timeout: 15_000 }).should('include', '/billing')
    cy.location('pathname').should('include', 'overview')
  })
})
