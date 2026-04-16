/**
 * 重置密码页：带 token/email 时，空提交应触发密码校验（不调 reset API）。
 */
describe('重置密码表单校验', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('未填密码提交应出现校验错误', () => {
    cy.visit('/reset-password?token=e2e-reset-token&email=e2e%40example.com')
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/reset-password')
    cy.get('.ant-card .ant-form', { timeout: 20_000 }).should('be.visible')
    cy.get('.ant-card .ant-form button.ant-btn-primary').click()
    cy.get('.ant-form-item-explain-error', { timeout: 10_000 }).should('have.length.at.least', 1)
    cy.url().should('not.include', '/dashboard')
  })
})
