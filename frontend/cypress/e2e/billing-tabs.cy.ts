/**
 * 计费页主 Tabs（仪表盘 / 记录 / 工时 / 导出等）。
 */
describe('计费页 Tab 切换', () => {
  it('应能切换到第二个 Tab 且留在计费模块', () => {
    cy.login()
    cy.visit('/billing/overview')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/billing')
    cy.url().should('not.include', '/login')
  })

  it('应能切换到第三、四个 Tab 且留在计费模块', () => {
    cy.login()
    cy.visit('/billing/overview')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 4)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(2).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/billing')
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(3).click({ force: true })
    cy.location('pathname').should('include', '/billing')
    cy.url().should('not.include', '/login')
  })
})
