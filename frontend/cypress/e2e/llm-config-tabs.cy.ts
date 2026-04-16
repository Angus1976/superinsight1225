/**
 * 管理端 LLM 配置：主 Tabs（通用 / 本地 / 云端 / 国内）。
 */
describe('LLM 配置 Tab 切换', () => {
  it('应能切换到第二个主 Tab 且留在 LLM 配置页', () => {
    cy.login()
    cy.visit('/admin/llm-config')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/admin/llm-config')
    cy.url().should('not.include', '/login')
  })

  it('应能切换到第三个主 Tab 且留在 LLM 配置页', () => {
    cy.login()
    cy.visit('/admin/llm-config')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 3)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(2).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/admin/llm-config')
    cy.url().should('not.include', '/login')
  })
})
