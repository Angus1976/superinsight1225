/**
 * 数据同步根页：数据源 / 同步任务 / 安全等 Tabs。
 */
describe('数据同步 Tab 切换', () => {
  it('应能切换到第二个 Tab 且留在数据同步页', () => {
    cy.login()
    cy.visit('/data-sync')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/data-sync')
    cy.url().should('not.include', '/login')
  })
})
