/**
 * 侧栏主导航：`SidebarMenuItem` 上 `data-nav-path` 与路由一致（不依赖菜单文案）。
 */
describe('侧栏主导航', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('.ant-layout-sider', { timeout: 25_000 }).should('be.visible')
  })

  it('点击「设置」路径应进入 /settings', () => {
    cy.get('[data-nav-path="/settings"]', { timeout: 15_000 })
      .scrollIntoView()
      .click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/settings')
    cy.url().should('not.include', '/login')
  })

  it('点击「任务」路径应进入任务模块', () => {
    cy.get('[data-nav-path="/tasks"]', { timeout: 15_000 }).scrollIntoView().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('satisfy', (p: string) =>
      p === '/tasks' || p === '/tasks/' || p.includes('/tasks'),
    )
    cy.url().should('not.include', '/login')
  })
})
