/**
 * 通知铃铛：可点击且不抛错（当前为占位 onClick）。
 */
describe('页头通知铃铛', () => {
  it('应可点击并保持当前页', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('[data-testid="header-notification-bell"]', { timeout: 20_000 }).should('be.visible').click()
    cy.location('pathname', { timeout: 10_000 }).should('include', '/dashboard')
    cy.url().should('not.include', '/login')
  })
})
