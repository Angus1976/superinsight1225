/**
 * 页头主题开关：切换后 `document.documentElement[data-theme]` 应变（与 uiStore.toggleTheme 一致）。
 */
describe('页头主题切换', () => {
  it('点击开关应切换 data-theme', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.document().then((doc) => {
      const before = doc.documentElement.getAttribute('data-theme')
      cy.get('.ant-layout-header .ant-switch', { timeout: 20_000 }).first().click({ force: true })
      cy.document()
        .its('documentElement')
        .invoke('getAttribute', 'data-theme')
        .should('not.eq', before)
    })
  })
})
