/**
 * 安全模块子页顶栏横向 Menu：用 href 切换，避免文案随语言变化。
 */
describe('安全模块顶栏导航', () => {
  it('从 RBAC 子页应能通过菜单链到审计日志', () => {
    cy.login()
    cy.visit('/security/rbac')
    cy.get('.ant-menu-horizontal, .ant-menu', { timeout: 25_000 }).should('be.visible')
    cy.get('a[href="/security/audit"]', { timeout: 15_000 }).first().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/security/audit')
    cy.url().should('not.include', '/login')
  })
})
