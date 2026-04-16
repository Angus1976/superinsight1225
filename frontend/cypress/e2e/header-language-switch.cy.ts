/**
 * 页头语言下拉：在 zh / en 两项间切换一次，并校验持久化 `ui-storage` 中的 language 已变。
 */
describe('页头语言切换', () => {
  it('切换语言后 ui-storage 中 language 应变', () => {
    cy.login()
    cy.visit('/dashboard')
    cy.window().then((win) => {
      const raw = win.localStorage.getItem('ui-storage')
      const startLang = (raw ? JSON.parse(raw).state?.language : 'zh') as string

      cy.get('.ant-layout-header button.ant-btn')
        .filter((_, el) => /中文|EN|🇨🇳|🇺🇸/.test(Cypress.$(el).text()))
        .first()
        .click()

      cy.get('.ant-dropdown:not(.ant-dropdown-hidden) .ant-dropdown-menu-item', { timeout: 10_000 })
        .should('have.length.at.least', 2)
        .eq(startLang === 'zh' ? 1 : 0)
        .click()

      cy.window().then((w2) => {
        const r2 = w2.localStorage.getItem('ui-storage')
        const after = (r2 ? JSON.parse(r2).state?.language : '') as string
        expect(after, 'language in ui-storage should change').to.not.equal(startLang)
      })
    })
  })
})
