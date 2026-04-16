/**
 * AI 标注模块内各横向子菜单对应路由（登录态）。
 */
describe('AI 标注子路由', () => {
  const paths = [
    '/ai-annotation',
    '/ai-annotation/tasks',
    '/ai-annotation/quality',
    '/ai-annotation/collaboration',
    '/ai-annotation/engines',
    '/ai-annotation/execution',
    '/ai-annotation/trial',
    '/ai-annotation/batch',
    '/ai-annotation/rhythm',
  ]

  it('应均能加载页面壳', () => {
    cy.login()
    for (const path of paths) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', '/ai-annotation')
      cy.url().should('not.include', '/login')
      cy.get('.ai-annotation-page, .ant-card, .ant-menu', { timeout: 25_000 }).should('exist')
    }
  })
})
