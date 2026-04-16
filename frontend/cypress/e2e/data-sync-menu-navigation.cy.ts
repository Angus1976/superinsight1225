/**
 * 数据同步子页顶栏横向 Menu：用 href 切换。
 */
describe('数据同步顶栏导航', () => {
  it('从数据源子页应能通过菜单链到同步历史', () => {
    cy.login()
    cy.visit('/data-sync/sources')
    cy.get('.ant-menu-horizontal, .ant-menu', { timeout: 25_000 }).should('be.visible')
    cy.get('a[href="/data-sync/history"]', { timeout: 15_000 }).first().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/data-sync/history')
    cy.url().should('not.include', '/login')
  })
})
