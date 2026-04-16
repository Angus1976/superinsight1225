describe('认证流程', () => {
  it('应能登录并进入仪表盘', () => {
    cy.login()
    cy.url().should('include', '/dashboard')
  })

  it('登录后应能看到欢迎文案', () => {
    cy.login()
    cy.contains(/欢迎/, { timeout: 20_000 }).should('be.visible')
  })
})
