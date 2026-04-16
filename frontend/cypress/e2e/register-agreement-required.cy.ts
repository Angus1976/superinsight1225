/**
 * 注册页：其它必填已填但未勾选用户协议时，提交应出现协议校验错误（不调注册 API）。
 */
describe('注册用户协议校验', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('未勾选协议提交应出现校验错误', () => {
    const ph = (el: HTMLElement) => (el as HTMLInputElement).placeholder || ''

    cy.visit('/register')
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/register')

    cy.get('.ant-card .ant-form input')
      .filter((_, el) => /请输入用户名|Enter your username/.test(ph(el as HTMLElement)))
      .first()
      .type('e2eagruser')
    cy.get('.ant-card .ant-form input')
      .filter((_, el) => /请输入邮箱|Enter your email/.test(ph(el as HTMLElement)))
      .first()
      .type('e2eagr@test.local')
    cy.get('.ant-input-password input').eq(0).type('abcdefgh', { log: false })
    cy.get('.ant-input-password input').eq(1).type('abcdefgh', { log: false })
    cy.get('.ant-card .ant-form input')
      .filter((_, el) => /请输入组织名称|Enter organization name/.test(ph(el as HTMLElement)))
      .first()
      .type('E2E Org')

    cy.get('.ant-checkbox-input').should('not.be.checked')
    cy.get('.ant-card .ant-form button.ant-btn-primary').click()
    cy.get('.ant-form-item-explain-error', { timeout: 10_000 }).should('have.length.at.least', 1)
    cy.url().should('not.include', '/dashboard')
  })
})
