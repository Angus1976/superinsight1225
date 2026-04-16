/**
 * 帮助按钮：应调用 window.open 打开文档基址（不弹真实新窗口）。
 */
describe('页头帮助文档', () => {
  it('点击帮助应触发 window.open', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.window().then((win) => {
      cy.stub(win, 'open').as('winOpen')
    })
    cy.get('[data-testid="header-help-button"]', { timeout: 20_000 }).should('be.visible').click()
    cy.get('@winOpen').should('have.been.calledOnce')
    cy.get('@winOpen').its('firstCall.args.0').should('include', 'docs.')
  })
})
