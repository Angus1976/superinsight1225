/**
 * Auth / session invariants for E2E fixtures (Properties 11, 12, 34).
 */

import { ROLE_CONFIGS, type RoleConfig } from './role-permissions'

/** Public routes that do not require session. */
export const DEFAULT_PUBLIC_PATHS = ['/login', '/register', '/forgot-password', '/reset-password'] as const

export function shouldRedirectToLoginWhenLoggedOut(
  pathname: string,
  publicPaths: readonly string[] = DEFAULT_PUBLIC_PATHS,
): boolean {
  const normalized = pathname.startsWith('/') ? pathname : `/${pathname}`
  return !publicPaths.some((p) => normalized === p || normalized.startsWith(`${p}/`))
}

export function tenantIdAfterSwitch(_previous: string, next: string): string {
  return next
}

export function isValidRoleConfigFixture(role: string, config: RoleConfig): boolean {
  return config.role === role && config.tenantId.length > 0
}

export function allFixtureRolesMatchConfigs(): boolean {
  const entries = Object.entries(ROLE_CONFIGS) as [string, RoleConfig][]
  return entries.every(([key, cfg]) => cfg.role === key && isValidRoleConfigFixture(key, cfg))
}
