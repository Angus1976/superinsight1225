/**
 * 无需登录的公开页：应展示表单区域且不被主应用重定向到 dashboard。
 */
describe('公开页', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  ;[
    '/register',
    '/forgot-password',
    '/reset-password?token=e2e-smoke&email=e2e%40example.com',
  ].forEach((pathAndQuery) => {
    it(`${pathAndQuery.split('?')[0]} 应展示表单骨架`, () => {
      cy.visit(pathAndQuery)
      cy.location('pathname').should('eq', pathAndQuery.split('?')[0])
      cy.get('.ant-form, form', { timeout: 20_000 }).should('exist')
      cy.url().should('not.include', '/dashboard')
    })
  })
})
