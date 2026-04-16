/**
 * 注册页：服务条款与隐私政策外链属性（不发起注册）。
 */
describe('注册页法律链接', () => {
  beforeEach(() => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()
  })

  it('应展示 terms / privacy 且在新标签打开', () => {
    cy.visit('/register')
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/register')
    cy.get('a[href="/terms"]', { timeout: 15_000 }).should('be.visible').and('have.attr', 'target', '_blank')
    cy.get('a[href="/privacy"]').should('be.visible').and('have.attr', 'target', '_blank')
  })
})
