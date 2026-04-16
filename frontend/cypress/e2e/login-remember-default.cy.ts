/**
 * 登录页：「记住我」在 LoginForm initialValues 中默认为勾选。
 */
describe('登录记住我默认', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('记住我复选框应为选中', () => {
    cy.intercept('GET', '**/api/auth/tenants*').as('authTenants')
    cy.visit('/login')
    cy.wait('@authTenants', { timeout: 20_000 })
    cy.get('.ant-form input.ant-checkbox-input', { timeout: 15_000 }).should('be.checked')
  })
})
