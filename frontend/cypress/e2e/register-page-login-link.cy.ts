/**
 * 注册页底部「已有账号」链回登录（未登录态）。
 */
describe('注册页返回登录', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('底部登录链接应跳到 /login', () => {
    cy.visit('/register')
    cy.get('a[href="/login"]', { timeout: 20_000 }).first().click()
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/login')
  })
})
