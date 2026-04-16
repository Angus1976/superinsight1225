/**
 * 全局搜索：Ctrl+K 打开弹层（useGlobalSearch；用 cy.trigger 模拟 keydown，因 Cypress.type 和弦在 Electron 下不稳定）。
 */
describe('全局搜索快捷键', () => {
  it('Ctrl+K 应打开搜索 Modal', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('[data-testid="global-search-trigger"]', { timeout: 25_000 }).should('be.visible')
    cy.get('body').trigger('keydown', {
      key: 'k',
      code: 'KeyK',
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    })
    cy.get('.ant-modal', { timeout: 10_000 }).should('be.visible')
    cy.get('.ant-modal .ant-input', { timeout: 10_000 }).should('be.visible')
    cy.get('.ant-modal .ant-input').clear().type('close-me{enter}')
    cy.get('.ant-modal', { timeout: 10_000 }).should('not.exist')
  })

  it('Meta+K 应打开搜索 Modal', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('[data-testid="global-search-trigger"]', { timeout: 25_000 }).should('be.visible')
    cy.get('body').trigger('keydown', {
      key: 'k',
      code: 'KeyK',
      metaKey: true,
      bubbles: true,
      cancelable: true,
    })
    cy.get('.ant-modal', { timeout: 10_000 }).should('be.visible')
    cy.get('.ant-modal .ant-input').clear().type('meta-close{enter}')
    cy.get('.ant-modal', { timeout: 10_000 }).should('not.exist')
  })
})
