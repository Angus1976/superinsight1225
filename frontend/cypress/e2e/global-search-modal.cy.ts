/**
 * 全局搜索：打开 Modal、输入非空后 Enter 会触发 onSearch 并 close（见 GlobalSearch 逻辑）。
 */
describe('全局搜索弹层', () => {
  it('应能打开并在检索后关闭', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('[data-testid="global-search-trigger"]', { timeout: 25_000 }).should('be.visible').click()
    cy.get('.ant-modal', { timeout: 10_000 }).should('be.visible')
    cy.get('.ant-modal .ant-input', { timeout: 10_000 }).should('be.visible').clear().type('e2e-smoke{enter}')
    cy.get('.ant-modal', { timeout: 10_000 }).should('not.exist')
  })
})
