/**
 * 侧栏「仪表盘」：从其它页通过 data-nav-path 回到 /dashboard。
 */
describe('侧栏回仪表盘', () => {
  it('从任务列表应能点侧栏仪表盘进入 dashboard', () => {
    cy.login()
    cy.visit('/tasks/list')
    cy.get('.ant-layout-sider', { timeout: 25_000 }).should('be.visible')
    cy.get('[data-nav-path="/dashboard"]', { timeout: 15_000 }).scrollIntoView().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/dashboard')
    cy.url().should('not.include', '/login')
  })
})
