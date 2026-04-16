/**
 * AI 助手页：主容器与输入区存在（不触发流式请求）。
 */
describe('AI 助手页烟测', () => {
  it('登录后应展示对话容器与输入框', () => {
    cy.login()
    cy.visit('/ai-assistant')
    cy.get('.ai-assistant-container', { timeout: 25_000 }).should('be.visible')
    cy.get('.ai-assistant-container textarea', { timeout: 15_000 }).should('be.visible')
    cy.url().should('not.include', '/login')
  })
})
