/**
 * 按业务顺序点测：认证 → 管理端 LLM/AI 集成 → AI 助手对话。
 * 对话使用 SSE 拦截模拟，避免依赖真实 LLM/OpenClaw 返回。
 */
describe('管理端与 AI 助手栈', () => {
  beforeEach(() => {
    cy.intercept('POST', '**/api/v1/ai-assistant/chat/stream', (req) => {
      req.reply({
        statusCode: 200,
        headers: {
          'content-type': 'text/event-stream; charset=utf-8',
        },
        body: 'data: {"content":"[E2E 模拟回复] "}\n\ndata: {"done":true}\n\n',
      })
    }).as('chatStream')
  })

  it('登录 → LLM 应用绑定 → AI 集成各 Tab → 工作流管理 → AI 助手发送', () => {
    cy.login()

    cy.visit('/admin/llm-config')
    cy.location('pathname', { timeout: 30_000 }).should('include', '/admin/llm-config')
    cy.get('.ant-card', { timeout: 25_000 }).should('exist')

    cy.visit('/admin/ai-integration')
    cy.location('pathname').should('include', '/admin/ai-integration')
    cy.get('.ant-tabs-nav', { timeout: 25_000 }).should('be.visible')

    cy.get('.ant-tabs-nav .ant-tabs-tab').then(($tabs) => {
      expect($tabs.length).to.be.at.least(3)
      cy.wrap($tabs.eq(1)).click({ force: true })
      cy.wrap($tabs.eq(2)).click({ force: true })
      cy.wrap($tabs.eq(3)).click({ force: true })
      cy.wrap($tabs.eq(0)).click({ force: true })
    })

    cy.visit('/admin/workflow-admin')
    cy.location('pathname').should('include', '/admin/workflow-admin')
    cy.get('.ant-card, .ant-table, .ant-spin-nested-loading', { timeout: 25_000 }).first().should('be.visible')

    cy.visit('/ai-assistant')
    cy.get('.ai-assistant-container', { timeout: 25_000 }).should('be.visible')
    cy.get('.input-area textarea').should('be.visible').clear().type('E2E 点测短问')
    cy.get('.input-area').within(() => {
      cy.get('button.ant-btn-primary').filter(':visible').first().click()
    })
    cy.wait('@chatStream', { timeout: 30_000 })
    cy.contains('[E2E 模拟回复]', { timeout: 20_000 }).should('be.visible')
  })
})
