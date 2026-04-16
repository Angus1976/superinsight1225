describe('登录页', () => {
  it('应展示登录表单', () => {
    cy.visit('/login')
    cy.get('[data-testid="login-email"]').should('be.visible')
    cy.get('[data-testid="login-password"]').should('be.visible')
    cy.get('[data-testid="login-submit"]').should('be.visible')
  })
})
