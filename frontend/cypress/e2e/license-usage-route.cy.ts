/**
 * 许可证用量页（路由存在且需登录）。
 */
describe('许可证用量页', () => {
  it('应能打开 /license/usage', () => {
    cy.login()
    cy.visit('/license/usage')
    cy.location('pathname', { timeout: 30_000 }).should('include', '/license/usage')
    cy.url().should('not.include', '/login')
    cy.get('.ant-layout, .ant-layout-content, [class*="layout"], .ant-card, .ant-spin-nested-loading', {
      timeout: 25_000,
    }).should('exist')
  })
})
