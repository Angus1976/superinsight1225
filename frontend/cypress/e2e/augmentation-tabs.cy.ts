/**
 * 数据增强根页：任务 / 样本 Tabs。
 */
describe('数据增强 Tab 切换', () => {
  it('应能切换到样本 Tab 且留在增强页', () => {
    cy.login()
    cy.visit('/augmentation')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/augmentation')
    cy.url().should('not.include', '/login')
  })
})
