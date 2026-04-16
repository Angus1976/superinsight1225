/**
 * 管理控制台概览页：卡片/统计区域应渲染（登录态）。
 */
describe('管理控制台', () => {
  it('/admin/console 应展示内容区', () => {
    cy.login()
    cy.visit('/admin/console')
    cy.location('pathname', { timeout: 25_000 }).should('include', '/admin/console')
    cy.url().should('not.include', '/login')
    cy.get('.ant-card, .ant-statistic, .ant-row', { timeout: 25_000 }).should('exist')
  })
})
