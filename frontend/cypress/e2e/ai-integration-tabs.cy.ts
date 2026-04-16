/**
 * 管理端 AI 集成页：顶部 Tabs 切换（概览 / 技能 / 配置 / 数据源等）。
 */
describe('AI 集成管理 Tab', () => {
  it('应能切换到第三个 Tab 且留在 AI 集成页', () => {
    cy.login()
    cy.visit('/admin/ai-integration')
    cy.get('.ant-tabs-nav .ant-tabs-tab', { timeout: 25_000 }).should('have.length.at.least', 3)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(2).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/admin/ai-integration')
    cy.url().should('not.include', '/login')
  })
})
