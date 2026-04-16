/**
 * 数据同步 → 数据湖：子页顶栏 Menu 用 href 在湖内切换。
 */
describe('数据湖顶栏导航', () => {
  it('从湖数据源应能链到湖仪表盘', () => {
    cy.login()
    cy.visit('/data-sync/datalake/sources')
    cy.get('.ant-menu-horizontal, .ant-menu', { timeout: 25_000 }).should('be.visible')
    cy.get('a[href="/data-sync/datalake/dashboard"]', { timeout: 15_000 }).first().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/data-sync/datalake/dashboard')
    cy.url().should('not.include', '/login')
  })
})
