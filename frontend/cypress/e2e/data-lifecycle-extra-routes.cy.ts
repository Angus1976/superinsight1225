/**
 * 数据生命周期：misc 烟测未覆盖的 temp-data / samples 子路由。
 */
describe('数据生命周期额外子路由', () => {
  const paths = ['/data-lifecycle/temp-data', '/data-lifecycle/samples']

  it('应能打开临时数据与样本库页', () => {
    cy.login()
    for (const path of paths) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', path)
      cy.url().should('not.include', '/login')
      cy.get('.ant-layout, .ant-layout-content, [class*="layout"], .ant-card, .ant-table, .ant-spin-nested-loading', {
        timeout: 25_000,
      }).should('exist')
    }
  })
})
