/**
 * 重置密码：缺少 token/email 时应展示错误 Result，主按钮回登录。
 */
describe('重置密码无效链接', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('无查询参数时点击回登录应进入 /login', () => {
    cy.visit('/reset-password')
    cy.get('.ant-result', { timeout: 20_000 }).should('be.visible')
    cy.get('.ant-result').within(() => {
      cy.get('button.ant-btn-primary').first().click()
    })
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/login')
  })
})
