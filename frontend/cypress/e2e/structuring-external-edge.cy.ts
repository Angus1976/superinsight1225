/**
 * 数据结构化占位 jobId、外链标注、通配 404。
 */
describe('结构化流程与外链边界', () => {
  const jobId = '00000000-0000-4000-8000-00000000e2e1'

  it('登录后可打开结构化 preview/schema/results（占位 ID）', () => {
    cy.login()
    for (const path of [
      `/data-structuring/preview/${jobId}`,
      `/data-structuring/schema/${jobId}`,
      `/data-structuring/results/${jobId}`,
    ]) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', jobId)
      cy.url().should('not.include', '/login')
      cy.get('.ant-layout, .ant-layout-content, [class*="layout"], .ant-card, .ant-spin-nested-loading, .ant-result, .ant-alert', {
        timeout: 25_000,
      }).should('exist')
    }
  })

  it('未登录：外链标注页与未知路径应可渲染', () => {
    cy.clearAllCookies()
    cy.clearAllLocalStorage()
    cy.clearAllSessionStorage()

    cy.visit('/external-annotation/e2e-smoke-invalid-token')
    cy.location('pathname').should('include', '/external-annotation/')
    cy.get('.ant-spin, .ant-result, .ant-alert, .ant-card', { timeout: 20_000 }).should('exist')

    cy.visit('/e2e-route-that-does-not-exist-xyz')
    cy.get('.ant-result', { timeout: 15_000 }).should('be.visible')
  })

  it('登录后 AI 标注子路径可打开', () => {
    cy.login()
    cy.visit('/ai-annotation/quality')
    cy.location('pathname', { timeout: 30_000 }).should('include', '/ai-annotation/')
    cy.url().should('not.include', '/login')
    cy.get('.ant-layout, .ant-card, .ant-spin-nested-loading, .ant-table', { timeout: 25_000 }).should(
      'exist',
    )
  })
})
