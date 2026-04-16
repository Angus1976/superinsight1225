/**
 * 侧栏更多主导航项（与 navGroups 中常见模块一致，非 admin 亦可见）。
 */
describe('侧栏更多主导航', () => {
  // 带子菜单的顶栏项（如 /quality）在侧栏里多为子路径节点，未必挂父级 path；此处只测无子菜单或已验证存在的顶栏 path。
  const navPaths = ['/ai-assistant', '/data-lifecycle']

  it('各 data-nav-path 点击后应进入对应模块', () => {
    cy.login()
    for (const navPath of navPaths) {
      cy.visit('/dashboard')
      cy.get('.ant-layout-sider', { timeout: 25_000 }).should('be.visible')
      cy.get(`[data-nav-path="${navPath}"]`, { timeout: 15_000 }).scrollIntoView().click({ force: true })
      cy.location('pathname', { timeout: 15_000 }).should('include', navPath)
      cy.url().should('not.include', '/login')
    }
  })
})
