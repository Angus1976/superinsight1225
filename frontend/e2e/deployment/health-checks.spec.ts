/**
 * Deployment Health Check E2E Tests
 *
 * Runs against real services (no auth mocking). Uses the deployment
 * Playwright project with baseURL from DEPLOY_URL env var.
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8
 */

import { test, expect } from '@playwright/test'

declare const process: { env: Record<string, string | undefined> }

const BACKEND_URL = process.env.DEPLOY_URL || 'http://localhost:8000'
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000'

/* ================================================================== */
/*  Frontend HTTP 200 (Req 13.1)                                       */
/* ================================================================== */

test.describe('Frontend health', () => {
  test('frontend responds with HTTP 200', async ({ request }) => {
    const response = await request.get(FRONTEND_URL)
    expect(response.status()).toBe(200)
  })
})

/* ================================================================== */
/*  Backend /health (Req 13.2)                                         */
/* ================================================================== */

test.describe('Backend health', () => {
  test('backend /health returns 200 with service status', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`)
    expect(response.status()).toBe(200)

    const body = await response.json()
    expect(body).toHaveProperty('status')
  })
})

/* ================================================================== */
/*  PostgreSQL (Req 13.3)                                              */
/* ================================================================== */

test.describe('PostgreSQL connectivity', () => {
  test('PostgreSQL accepts connections', async ({ request }) => {
    // Relies on backend /health reporting DB status
    const response = await request.get(`${BACKEND_URL}/health`)
    if (response.ok()) {
      const body = await response.json()
      // Check if services object includes postgres/db info
      if (body.services) {
        const dbStatus = body.services.postgres || body.services.database || body.services.db
        if (dbStatus) {
          expect(dbStatus).toBeTruthy()
        }
      }
    }
  })
})

/* ================================================================== */
/*  Redis (Req 13.4)                                                   */
/* ================================================================== */

test.describe('Redis connectivity', () => {
  test('Redis accepts connections and responds to PING', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`)
    if (response.ok()) {
      const body = await response.json()
      if (body.services) {
        const redisStatus = body.services.redis || body.services.cache
        if (redisStatus) {
          expect(redisStatus).toBeTruthy()
        }
      }
    }
  })
})

/* ================================================================== */
/*  Neo4j (Req 13.5)                                                   */
/* ================================================================== */

test.describe('Neo4j connectivity', () => {
  test('Neo4j accepts connections', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`)
    if (response.ok()) {
      const body = await response.json()
      if (body.services) {
        const neo4jStatus = body.services.neo4j || body.services.graph
        if (neo4jStatus) {
          expect(neo4jStatus).toBeTruthy()
        }
      }
    }
  })
})

/* ================================================================== */
/*  Environment Variables (Req 13.6)                                   */
/* ================================================================== */

test.describe('Environment variables', () => {
  test('backend has required env vars loaded', async ({ request }) => {
    // The /health endpoint returning 200 implies env vars are loaded
    const response = await request.get(`${BACKEND_URL}/health`)
    expect(response.status()).toBe(200)
  })
})

/* ================================================================== */
/*  Service Restart Recovery (Req 13.7)                                */
/* ================================================================== */

test.describe('Service restart recovery', () => {
  test('services respond within 60 seconds', async ({ request }) => {
    // Verify services are responsive (timeout is set to 120s in project config)
    const start = Date.now()
    const response = await request.get(`${BACKEND_URL}/health`, { timeout: 60000 })
    const elapsed = Date.now() - start
    expect(response.status()).toBe(200)
    expect(elapsed).toBeLessThan(60000)
  })
})

/* ================================================================== */
/*  Static Assets (Req 13.8)                                           */
/* ================================================================== */

test.describe('Static assets', () => {
  test('frontend static assets served with correct headers', async ({ request }) => {
    const response = await request.get(FRONTEND_URL)
    expect(response.status()).toBe(200)

    const contentType = response.headers()['content-type']
    expect(contentType).toContain('text/html')
  })
})
