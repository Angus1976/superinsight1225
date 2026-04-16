/**
 * 登录页底部/表单内公开链接（无需登录态）。
 */
describe('登录页外链', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
    cy.intercept('GET', '**/api/auth/tenants*').as('authTenants')
  })

  it('底部注册链接应跳到 /register', () => {
    cy.visit('/login')
    cy.wait('@authTenants', { timeout: 20_000 })
    cy.get('a[href="/register"]', { timeout: 15_000 }).first().click()
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/register')
  })

  it('忘记密码链接应跳到 /forgot-password', () => {
    cy.visit('/login')
    cy.wait('@authTenants', { timeout: 20_000 })
    cy.get('a[href="/forgot-password"]', { timeout: 15_000 }).first().click()
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/forgot-password')
  })
})
