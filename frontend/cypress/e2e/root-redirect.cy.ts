/**
 * 受保护根路径 / 应重定向到仪表盘（与路由 index Navigate 一致）。
 */
describe('根路径重定向', () => {
  it('登录后访问 / 应落在 dashboard', () => {
    cy.login()
    cy.visit('/')
    cy.location('pathname', { timeout: 20_000 }).should('include', 'dashboard')
    cy.url().should('not.include', '/login')
  })
})
