/**
 * Property Test: Role–route access matrix
 *
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.6, 5.5**
 *
 * Property: For every role defined in ROLE_CONFIGS and every route that appears
 * in the union of accessible/denied lists, {@link getExpectedRouteAccess}
 * matches the columns produced by {@link getRouteAccessMatrix}.
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  ROLE_CONFIGS,
  getRouteAccessMatrix,
  getExpectedRouteAccess,
  type RoleConfig,
} from '../../e2e/helpers/role-permissions'

const ROLE_KEYS = ['admin', 'data_manager', 'data_analyst', 'annotator'] as const

function columnForRole(
  row: ReturnType<typeof getRouteAccessMatrix>[number],
  role: (typeof ROLE_KEYS)[number],
): 'allow' | 'deny' {
  return row[role]
}

describe('role-permissions property', () => {
  it('getRouteAccessMatrix columns match getExpectedRouteAccess for every role × route', () => {
    const matrix = getRouteAccessMatrix()
    for (const row of matrix) {
      for (const role of ROLE_KEYS) {
        const config = ROLE_CONFIGS[role]
        expect(columnForRole(row, role)).toBe(getExpectedRouteAccess(config, row.route))
      }
    }
  })

  it('explicit accessible routes are allowed unless also listed as denied', () => {
    for (const config of Object.values(ROLE_CONFIGS)) {
      for (const route of config.accessibleRoutes) {
        if (config.deniedRoutes.includes(route)) {
          expect(getExpectedRouteAccess(config, route)).toBe('deny')
        } else {
          expect(getExpectedRouteAccess(config, route)).toBe('allow')
        }
      }
    }
  })

  it('explicit denied routes are always denied', () => {
    for (const config of Object.values(ROLE_CONFIGS)) {
      for (const route of config.deniedRoutes) {
        expect(getExpectedRouteAccess(config, route)).toBe('deny')
      }
    }
  })

  it('property: random path strings never throw; access is allow or deny', () => {
    fc.assert(
      fc.property(
        fc.constantFrom<RoleConfig>(...Object.values(ROLE_CONFIGS)),
        fc.string({ minLength: 0, maxLength: 120 }),
        (config, route) => {
          const normalized = route.startsWith('/') ? route : `/${route}`
          const a = getExpectedRouteAccess(config, normalized)
          return a === 'allow' || a === 'deny'
        },
      ),
      { numRuns: 200 },
    )
  })

  it('property: sampled routes from the matrix stay self-consistent on recomputation', () => {
    const matrix = getRouteAccessMatrix()
    fc.assert(
      fc.property(fc.integer({ min: 0, max: matrix.length - 1 }), (i) => {
        const row = matrix[i]
        for (const role of ROLE_KEYS) {
          const config = ROLE_CONFIGS[role]
          expect(columnForRole(row, role)).toBe(getExpectedRouteAccess(config, row.route))
        }
        return true
      }),
      { numRuns: 100 },
    )
  })
})
