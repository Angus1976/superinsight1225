/**
 * Properties 11, 12, 34 — auth / tenant / fixture correctness
 * **Validates: Requirements 4.5, 4.7, 16.1**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  shouldRedirectToLoginWhenLoggedOut,
  tenantIdAfterSwitch,
  allFixtureRolesMatchConfigs,
  isValidRoleConfigFixture,
} from '../../e2e/helpers/auth-fixture-pure'
import { ROLE_CONFIGS } from '../../e2e/helpers/role-permissions'

describe('auth-fixture property', () => {
  it('Property 11: protected paths require login when logged out model', () => {
    expect(shouldRedirectToLoginWhenLoggedOut('/dashboard')).toBe(true)
    expect(shouldRedirectToLoginWhenLoggedOut('/login')).toBe(false)
    fc.assert(
      fc.property(fc.string({ minLength: 1, maxLength: 40 }), (seg) => {
        const p = seg.startsWith('/') ? seg : `/${seg}`
        if (p === '/login' || p.startsWith('/login/')) {
          expect(shouldRedirectToLoginWhenLoggedOut(p)).toBe(false)
        }
        return true
      }),
      { numRuns: 80 },
    )
  })

  it('Property 12: tenant id after switch equals target tenant', () => {
    fc.assert(
      fc.property(fc.string({ maxLength: 32 }), fc.string({ minLength: 1, maxLength: 32 }), (a, b) => {
        expect(tenantIdAfterSwitch(a, b)).toBe(b)
        return true
      }),
      { numRuns: 100 },
    )
  })

  it('Property 34: ROLE_CONFIGS fixtures match role keys', () => {
    expect(allFixtureRolesMatchConfigs()).toBe(true)
    for (const [k, cfg] of Object.entries(ROLE_CONFIGS)) {
      expect(isValidRoleConfigFixture(k, cfg)).toBe(true)
    }
  })
})
