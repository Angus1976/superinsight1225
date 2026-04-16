/**
 * 仪表盘顶部 Tabs（概览 / 质量报告 / 知识图谱）。
 */
describe('仪表盘 Tab 切换', () => {
  it('应能切换到第二个 Tab 且保持登录', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.url().should('not.include', '/login')
    cy.location('pathname').should('include', 'dashboard')
  })

  it('应能切换到第三个 Tab 且保持登录', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 3)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(2).click({ force: true })
    cy.url().should('not.include', '/login')
    cy.location('pathname').should('include', 'dashboard')
  })
})
