/**
 * 质量管理根页：规则 / 模板 / 问题 / 工单 / 报告等 Tabs。
 */
describe('质量管理 Tab 切换', () => {
  it('应能切换到第二个 Tab 且留在质量页', () => {
    cy.login()
    cy.visit('/quality')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/quality')
    cy.url().should('not.include', '/login')
  })
})
