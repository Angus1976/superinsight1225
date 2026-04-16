/**
 * 头部用户菜单 → 退出登录（danger 项），应回到 /login。
 */
describe('退出登录', () => {
  it('登录后应能通过用户菜单退出', () => {
    cy.intercept('POST', '**/api/auth/logout*', { statusCode: 204, body: '' }).as('logoutApi')
    cy.login()
    cy.visit('/dashboard')
    cy.get('[data-testid="header-user-menu"]', { timeout: 20_000 }).should('be.visible').click()
    cy.get('.ant-dropdown:not(.ant-dropdown-hidden)', { timeout: 10_000 })
      .find('.ant-dropdown-menu-item-danger, li.ant-menu-item-danger')
      .first()
      .click()
    cy.wait('@logoutApi', { timeout: 15_000 })
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/login')
  })
})
