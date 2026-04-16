/**
 * 任务列表页：按状态筛选的 Tabs（全部 / 待处理 / 进行中等）。
 */
describe('任务列表 Tab 切换', () => {
  it('应能切换到第二个状态 Tab 且留在任务页', () => {
    cy.login()
    cy.visit('/tasks/list')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('satisfy', (p: string) =>
      p.includes('/tasks') || p.includes('/tasks/list'),
    )
    cy.url().should('not.include', '/login')
  })
})
