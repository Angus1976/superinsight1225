/**
 * 设置页左侧 Tabs 切换（Ant Design）。
 */
describe('设置页 Tab 切换', () => {
  it('应能点击第二个 Tab 且仍保持登录态', () => {
    cy.login()
    cy.visit('/settings')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 2)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(1).click({ force: true })
    cy.url().should('not.include', '/login')
    cy.get('.ant-tabs-tab-active, [class*="tab-active"]', { timeout: 10_000 }).should('exist')
  })

  it('应能点击第三个 Tab 且仍保持登录态', () => {
    cy.login()
    cy.visit('/settings')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 3)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(2).click({ force: true })
    cy.url().should('not.include', '/login')
    cy.get('.ant-tabs-tab-active, [class*="tab-active"]', { timeout: 10_000 }).should('exist')
  })

  it('应能点击第四、五个 Tab 且仍保持登录态', () => {
    cy.login()
    cy.visit('/settings')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('.ant-tabs-nav .ant-tabs-tab').should('have.length.at.least', 5)
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(3).click({ force: true })
    cy.url().should('not.include', '/login')
    cy.get('.ant-tabs-nav .ant-tabs-tab').eq(4).click({ force: true })
    cy.url().should('not.include', '/login')
    cy.get('.ant-tabs-tab-active, [class*="tab-active"]', { timeout: 10_000 }).should('exist')
  })
})
