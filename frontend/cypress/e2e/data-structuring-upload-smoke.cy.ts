/**
 * 数据结构化上传页：应展示 Ant Upload 拖拽区（登录态）。
 */
describe('数据结构化上传页', () => {
  it('应展示上传拖拽区域', () => {
    cy.login()
    cy.visit('/data-structuring/upload')
    cy.location('pathname', { timeout: 30_000 }).should('include', '/data-structuring/upload')
    cy.url().should('not.include', '/login')
    cy.get('.ant-upload-drag, .ant-upload.ant-upload-drag', { timeout: 25_000 }).should('exist')
  })
})
