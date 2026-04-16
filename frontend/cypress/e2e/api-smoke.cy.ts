/**
 * 登录后从 localStorage 读取 JWT，对后端做轻量 cy.request 烟测（不跑 LLM 流式）。
 */
describe('后端 API 烟测', () => {
  function bearerFromWindow(win: Window) {
    const raw = win.localStorage.getItem('auth-storage')
    expect(raw, 'auth-storage').to.be.a('string')
    const parsed = JSON.parse(raw as string) as { state?: { token?: string } }
    const token = parsed.state?.token
    expect(token, 'JWT').to.be.a('string').and.have.length.greaterThan(20)
    return token as string
  }

  it('健康检查与 AI 助手相关 GET 在鉴权下为 2xx', () => {
    const api = Cypress.env('API_BASE_URL') as string

    cy.request({ url: `${api}/health`, failOnStatusCode: false }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/auth/tenants` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/llm-configs/applications` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/llm-configs` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/ai-integration/skills`, failOnStatusCode: false }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/versioning/changes`, qs: { limit: 5 } }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/quality-rules`, qs: { project_id: 'e2e-smoke' } }).its('status').should('eq', 200)
    cy.request({ url: `${api}/admin/enhanced/health` }).its('status').should('eq', 200)
    cy.request({
      url: `${api}/api/v1/quality-reports/schedules`,
      qs: { project_id: 'e2e-smoke' },
    }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/activation/fingerprint` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/data-permissions/cache/stats` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/collaboration/platforms` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/permission-monitoring/health/default_tenant` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/annotation/engines` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/annotation/metrics` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/ontology-collaboration/experts`, qs: { limit: 5 } }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/quality-rules/templates/list` }).its('status').should('eq', 200)
    cy.request({ url: `${api}/api/v1/quality-workflow/tasks` }).its('status').should('eq', 200)

    cy.login()
    cy.window().then((win) => {
      const token = bearerFromWindow(win)
      const headers = { Authorization: `Bearer ${token}` }

      cy.request({ url: `${api}/api/v1/ai-assistant/service-status`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-assistant/workflows`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-assistant/chat/openclaw-status`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-assistant/data-sources/available`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-integration/gateways`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/auth/me`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-assistant/stats/today`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-assistant/skills/available`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/ai-assistant/skills/role-permissions`, headers }).its('status').should('eq', 200)
      cy.request({
        url: `${api}/api/v1/ai-assistant/access-logs`,
        headers,
        qs: { page: 1, page_size: 5 },
      }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/admin/skills/`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/security/roles`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/security/permissions`, headers }).its('status').should('eq', 200)
      cy.request({ url: `${api}/api/v1/augmentation/samples`, headers, qs: { limit: 5 } }).its('status').should('eq', 200)
    })
  })
})
