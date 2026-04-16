/**
 * 带子路由的模块「父级」路径（此前烟测多直达子页）。
 */
describe('模块父级路由', () => {
  const paths = ['/security', '/data-sync/datalake']

  it('登录后父级页应加载布局', () => {
    cy.login()
    for (const path of paths) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', path)
      cy.url().should('not.include', '/login')
      cy.get('.ant-layout, .ant-layout-content, [class*="layout"], .ant-card, .ant-menu', {
        timeout: 25_000,
      }).should('exist')
    }
  })
})
