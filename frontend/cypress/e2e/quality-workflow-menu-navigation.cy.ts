/**
 * 质量改进任务列表仍在质量模块下：顶栏 Menu 与 /quality/rules 等一致。
 */
describe('质量工作流页顶栏导航', () => {
  it('从 workflow/tasks 应能通过菜单链到规则页', () => {
    cy.login()
    cy.visit('/quality/workflow/tasks')
    cy.get('.ant-menu-horizontal, .ant-menu', { timeout: 25_000 }).should('be.visible')
    cy.get('a[href="/quality/rules"]', { timeout: 15_000 }).first().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/quality/rules')
    cy.url().should('not.include', '/login')
  })
})
