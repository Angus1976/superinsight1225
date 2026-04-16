/**
 * 质量管理子页顶栏横向 Menu：用 href 切换，避免文案随语言变化。
 */
describe('质量管理顶栏导航', () => {
  it('从规则子页应能通过菜单链到报告', () => {
    cy.login()
    cy.visit('/quality/rules')
    cy.get('.ant-menu-horizontal, .ant-menu', { timeout: 25_000 }).should('be.visible')
    cy.get('a[href="/quality/reports"]', { timeout: 15_000 }).first().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/quality/reports')
    cy.url().should('not.include', '/login')
  })
})
