/**
 * 数据增强子页顶栏横向 Menu：用 href 切换。
 */
describe('数据增强顶栏导航', () => {
  it('从样本库子页应能通过菜单链到配置', () => {
    cy.login()
    cy.visit('/augmentation/samples')
    cy.get('.ant-menu-horizontal, .ant-menu', { timeout: 25_000 }).should('be.visible')
    cy.get('a[href="/augmentation/config"]', { timeout: 15_000 }).first().click({ force: true })
    cy.location('pathname', { timeout: 15_000 }).should('include', '/augmentation/config')
    cy.url().should('not.include', '/login')
  })
})
