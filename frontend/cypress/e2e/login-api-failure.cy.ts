/**
 * 登录接口失败：应留在登录页并出现错误提示（不写入登录态）。
 */
describe('登录失败', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('401 时不应进入仪表盘', () => {
    cy.intercept('GET', '**/api/auth/tenants*', { body: [] }).as('authTenants')
    cy.intercept('POST', '**/api/auth/login', {
      statusCode: 401,
      body: { detail: 'Invalid credentials' },
    }).as('loginPost')

    cy.visit('/login')
    cy.wait('@authTenants', { timeout: 20_000 })
    cy.get('[data-testid="login-email"]', { timeout: 15_000 }).should('be.visible').clear().type('wrong@example.com')
    cy.get('[data-testid="login-password"]').clear().type('wrong-password', { log: false })
    cy.get('[data-testid="login-submit"]').click()

    cy.wait('@loginPost', { timeout: 20_000 })
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/login')
    cy.url().should('not.include', '/dashboard')
    cy.get('.ant-message', { timeout: 10_000 }).should('be.visible')
  })
})
