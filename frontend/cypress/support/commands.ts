/// <reference types="cypress" />

declare global {
  namespace Cypress {
    interface Chainable {
      /** 登录并断言进入仪表盘（需后端与种子用户可用） */
      login(email?: string, password?: string): Chainable<void>
    }
  }
}

function selectTenantIfPresent() {
  cy.get('body').then(($body) => {
    const $tenant = $body.find('[data-testid="login-tenant"]')
    if (!$tenant.length) {
      return
    }
    const forcedId = (Cypress.env('E2E_TENANT_ID') as string | undefined)?.trim()
    cy.get('[data-testid="login-tenant"]').should('be.visible').click()
    cy.get('.ant-select-dropdown:not(.ant-select-dropdown-hidden)', { timeout: 10_000 }).should(
      'be.visible'
    )
    if (forcedId) {
      cy.get(
        `.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[data-value="${forcedId}"]`
      ).click()
    } else {
      cy.get(
        '.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option'
      ).first().click()
    }
  })
}

Cypress.Commands.add('login', (email?: string, password?: string) => {
  const e = email ?? (Cypress.env('E2E_USER_EMAIL') as string)
  const p = password ?? (Cypress.env('E2E_USER_PASSWORD') as string)
  cy.intercept('GET', '**/api/auth/tenants*').as('authTenants')
  cy.visit('/login')
  cy.wait('@authTenants', { timeout: 20_000 })
  cy.get('[data-testid="login-email"]').should('be.visible').clear().type(e)
  cy.get('[data-testid="login-password"]').should('be.visible').type(p, { log: false })
  selectTenantIfPresent()
  cy.get('[data-testid="login-submit"]').click()
  cy.location('pathname', { timeout: 30_000 }).should('include', '/dashboard')
})

export {}
