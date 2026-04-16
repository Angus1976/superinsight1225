/**
 * 忘记密码页：首屏返回登录（navigate，不依赖文案）。
 */
describe('忘记密码返回登录', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('顶部返回按钮应进入 /login', () => {
    cy.visit('/forgot-password')
    cy.get('.ant-card', { timeout: 20_000 }).should('be.visible')
    cy.get('.ant-card').within(() => {
      cy.get('button.ant-btn').first().click()
    })
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/login')
  })
})
