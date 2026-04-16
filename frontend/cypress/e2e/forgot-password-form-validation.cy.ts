/**
 * 忘记密码：空提交应触发邮箱必填校验。
 */
describe('忘记密码表单校验', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('未填邮箱提交应出现校验错误', () => {
    cy.visit('/forgot-password')
    cy.location('pathname', { timeout: 20_000 }).should('eq', '/forgot-password')
    cy.get('.ant-card', { timeout: 20_000 }).should('be.visible')
    cy.get('.ant-card .ant-form', { timeout: 15_000 }).should('be.visible')
    cy.get('.ant-card .ant-form button.ant-btn-primary').click()
    cy.get('.ant-form-item-explain-error', { timeout: 10_000 }).should('be.visible')
    cy.url().should('not.include', '/dashboard')
  })
})
