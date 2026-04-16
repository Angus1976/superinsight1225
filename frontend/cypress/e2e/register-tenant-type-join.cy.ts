/**
 * 注册页：租户类型选「加入已有租户」后应出现邀请码输入（不提交注册）。
 */
describe('注册租户类型切换', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('选择 join 后应展示邀请码占位', () => {
    cy.visit('/register')
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/register')
    cy.get('.ant-card .ant-form .ant-select', { timeout: 20_000 }).should('be.visible').click()
    cy.get('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option', {
      timeout: 10_000,
    })
      .eq(1)
      .click({ force: true })
    cy.get('.ant-card .ant-form input', { timeout: 10_000 })
      .filter((_, el) => /invite|邀请/i.test((el as HTMLInputElement).placeholder))
      .should('have.length.at.least', 1)
      .first()
      .should('be.visible')
  })
})
