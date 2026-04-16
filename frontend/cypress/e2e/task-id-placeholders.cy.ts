/**
 * 任务详情 / 编辑 / 标注页在占位 UUID 下仍应渲染壳层（后端可能 404，前端不崩、不退登录）。
 */
describe('任务占位 ID 路由', () => {
  const id = '00000000-0000-4000-8000-00000000abe1'

  it('登录后详情、编辑、标注路径可打开', () => {
    cy.login()
    const paths = [`/tasks/${id}`, `/tasks/${id}/edit`, `/tasks/${id}/annotate`]
    for (const path of paths) {
      cy.visit(path)
      cy.location('pathname', { timeout: 30_000 }).should('include', id)
      cy.url().should('not.include', '/login')
      cy.get('.ant-layout, .ant-card, .ant-result, .ant-spin-nested-loading, .ant-alert, .ant-empty', {
        timeout: 25_000,
      }).should('exist')
    }
  })
})
