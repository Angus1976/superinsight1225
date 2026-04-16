/**
 * 登录页：空提交应触发表单校验（不发起登录）。
 */
describe('登录表单校验', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('未填账号密码提交应出现校验错误', () => {
    cy.intercept('GET', '**/api/auth/tenants*').as('authTenants')
    cy.visit('/login')
    cy.wait('@authTenants', { timeout: 20_000 })
    cy.location('pathname').should('eq', '/login')
    cy.get('[data-testid="login-submit"]', { timeout: 15_000 }).should('be.visible').click()
    cy.get('.ant-form-item-explain-error', { timeout: 10_000 }).should('have.length.at.least', 1)
    cy.url().should('include', '/login')
  })
})
