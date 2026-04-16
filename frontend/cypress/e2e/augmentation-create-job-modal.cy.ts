/**
 * 数据增强根页：点击「创建任务」打开 Modal 并可关闭。
 */
describe('数据增强创建任务弹窗', () => {
  it('应能打开并关闭创建任务对话框', () => {
    cy.login()
    cy.visit('/augmentation')
    cy.get('.ant-tabs', { timeout: 25_000 }).should('be.visible')
    cy.get('button.ant-btn-primary')
      .filter((_, el) => /创建|Create/.test(Cypress.$(el).text()))
      .first()
      .click({ force: true })
    cy.get('.ant-modal', { timeout: 15_000 }).should('be.visible')
    cy.get('.ant-modal .ant-modal-close', { timeout: 10_000 }).should('be.visible').click({ force: true })
    cy.get('.ant-modal', { timeout: 10_000 }).should('not.be.visible')
    cy.url().should('not.include', '/login')
  })
})
