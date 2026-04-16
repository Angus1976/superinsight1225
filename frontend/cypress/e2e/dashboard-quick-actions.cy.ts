/**
 * 仪表盘「快捷操作」卡片内按钮顺序：创建任务 / 计费 / 数据 / 设置（与 QuickActions 默认数组一致）。
 */
describe('仪表盘快捷操作', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/dashboard')
    cy.get('.ant-tabs', { timeout: 30_000 }).should('be.visible')
    cy.get('[data-testid="dashboard-quick-actions"]', { timeout: 25_000 }).should('be.visible')
  })

  it('「创建任务」应进入任务模块', () => {
    cy.get('[data-testid="dashboard-quick-actions"]').within(() => {
      cy.get('button.ant-btn').eq(0).click()
    })
    cy.location('pathname', { timeout: 15_000 }).should('satisfy', (p: string) =>
      p === '/tasks' || p === '/tasks/' || p.includes('/tasks'),
    )
    cy.url().should('not.include', '/login')
  })

  it('「查看计费」应进入计费模块', () => {
    cy.get('[data-testid="dashboard-quick-actions"]').within(() => {
      cy.get('button.ant-btn').eq(1).click()
    })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/billing')
    cy.url().should('not.include', '/login')
  })

  it('「设置」应进入设置页', () => {
    cy.get('[data-testid="dashboard-quick-actions"]').within(() => {
      cy.get('button.ant-btn').eq(3).click()
    })
    cy.location('pathname', { timeout: 15_000 }).should('eq', '/settings')
    cy.url().should('not.include', '/login')
  })
})
