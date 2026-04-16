/**
 * 注册页：空提交应触发 Ant Design 表单校验（不调用注册接口）。
 */
describe('注册表单校验', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('未填必填项提交应出现校验错误', () => {
    cy.visit('/register')
    cy.location('pathname', { timeout: 20_000 }).should('eq', '/register')
    cy.get('.ant-card .ant-form', { timeout: 20_000 }).should('be.visible')
    cy.get('.ant-card .ant-form button.ant-btn-primary').click()
    cy.get('.ant-form-item-explain-error', { timeout: 10_000 }).should('have.length.at.least', 1)
    cy.url().should('not.include', '/dashboard')
  })
})
