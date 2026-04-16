const { defineConfig } = require('cypress')

/**
 * Cypress E2E — 需先启动本地栈：
 *   后端 http://127.0.0.1:18080 、前端 http://localhost:15173（Docker）或 http://localhost:5173
 * 凭证：复制 cypress.env.json.example 为 cypress.env.json，或设置 CYPRESS_E2E_USER_* 环境变量。
 */
module.exports = defineConfig({
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL ?? 'http://localhost:5173',
    specPattern: 'cypress/e2e/**/*.cy.ts',
    supportFile: 'cypress/support/e2e.ts',
    video: false,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 15_000,
    pageLoadTimeout: 60_000,
    env: {
      E2E_USER_EMAIL: process.env.CYPRESS_E2E_USER_EMAIL ?? 'admin@superinsight.local',
      E2E_USER_PASSWORD: process.env.CYPRESS_E2E_USER_PASSWORD ?? 'Admin@123456',
      E2E_TENANT_ID: process.env.CYPRESS_E2E_TENANT_ID ?? '',
      /** 与前端 VITE_API_BASE_URL 对齐，供 cy.request 烟测 */
      API_BASE_URL: process.env.CYPRESS_API_BASE_URL ?? 'http://127.0.0.1:18080',
    },
  },
})
