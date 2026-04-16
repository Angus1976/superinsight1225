/**
 * 重置密码：两次密码不一致时应有校验错误（不调 API）。
 */
describe('重置密码确认不一致', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('密码与确认不一致应提示错误', () => {
    cy.visit('/reset-password?token=e2e-mismatch&email=e2e%40example.com')
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/reset-password')
    cy.get('.ant-card .ant-form', { timeout: 20_000 }).should('be.visible')
    cy.get('.ant-input-password input').eq(0).clear().type('abcdefgh', { log: false })
    cy.get('.ant-input-password input').eq(1).clear().type('abcdefgi', { log: false })
    cy.get('.ant-card .ant-form button.ant-btn-primary').click()
    cy.get('.ant-form-item-explain-error', { timeout: 10_000 }).should('have.length.at.least', 1)
  })
})
