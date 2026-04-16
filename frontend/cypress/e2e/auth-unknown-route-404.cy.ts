/**
 * 登录态访问未注册路径：应展示 404 Result（与公开环境 misc 烟测互补）。
 */
describe('登录态 404', () => {
  it('未知路径应展示 Result 且不退回登录', () => {
    cy.login()
    cy.visit('/e2e-authed-unknown-route-404-zz')
    cy.get('.ant-result', { timeout: 25_000 }).should('be.visible')
    cy.url().should('not.include', '/login')
  })
})
