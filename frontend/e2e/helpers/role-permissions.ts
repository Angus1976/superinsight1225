/**
 * Role Permissions Matrix for E2E Testing
 *
 * Defines the authoritative mapping of roles to accessible/denied routes
 * and permissions, used by parameterized role workflow tests.
 *
 * Requirements: 1.1, 1.2, 1.3, 1.4, 1.6
 */

export interface RoleConfig {
  role: string
  permissions: string[]
  accessibleRoutes: string[]
  deniedRoutes: string[]
  tenantId: string
}

export const ROLE_CONFIGS: Record<string, RoleConfig> = {
  admin: {
    role: 'admin',
    permissions: ['read:all', 'write:all', 'manage:all'],
    accessibleRoutes: [
      '/dashboard',
      '/tasks',
      '/quality',
      '/quality/rules',
      '/quality/reports',
      '/security',
      '/security/rbac',
      '/security/audit',
      '/security/dashboard',
      '/admin',
      '/admin/console',
      '/admin/tenants',
      '/admin/users',
      '/admin/system',
      '/admin/llm-config',
      '/admin/permissions',
      '/admin/quotas',
      '/admin/billing',
      '/data-sync',
      '/data-sync/sources',
      '/data-sync/history',
      '/data-sync/scheduler',
      '/data-sync/export',
      '/augmentation',
      '/license',
      '/license/usage',
      '/data-lifecycle',
      '/billing',
      '/billing/overview',
      '/settings',
      '/ai-annotation',
      '/ai-assistant',
    ],
    deniedRoutes: [],
    tenantId: 'tenant-1',
  },

  data_manager: {
    role: 'data_manager',
    permissions: ['read:data', 'write:data', 'manage:sync', 'read:tasks', 'write:tasks'],
    accessibleRoutes: [
      '/dashboard',
      '/data-sync',
      '/data-sync/sources',
      '/data-sync/history',
      '/data-sync/scheduler',
      '/data-sync/export',
      '/data-lifecycle',
      '/augmentation',
      '/tasks',
    ],
    deniedRoutes: [
      '/admin',
      '/admin/console',
      '/admin/tenants',
      '/admin/users',
      '/security/rbac',
      '/billing',
      '/billing/overview',
    ],
    tenantId: 'tenant-1',
  },

  data_analyst: {
    role: 'data_analyst',
    permissions: ['read:dashboard', 'read:quality', 'read:billing', 'read:license'],
    accessibleRoutes: [
      '/dashboard',
      '/quality/reports',
      '/billing/overview',
      '/license/usage',
    ],
    deniedRoutes: [
      '/admin',
      '/admin/console',
      '/admin/tenants',
      '/admin/users',
      '/data-sync',
      '/data-sync/sources',
      '/tasks',
    ],
    tenantId: 'tenant-1',
  },

  annotator: {
    role: 'annotator',
    permissions: ['read:tasks', 'write:annotations'],
    accessibleRoutes: [
      '/tasks',
      '/tasks/1/annotate',
    ],
    deniedRoutes: [
      '/admin',
      '/admin/console',
      '/admin/tenants',
      '/quality/rules',
      '/security',
      '/security/rbac',
      '/security/audit',
      '/data-sync',
      '/data-sync/sources',
      '/billing',
      '/billing/overview',
    ],
    tenantId: 'tenant-1',
  },
}

/**
 * Route access expectation for a single route across all roles.
 */
export interface RouteAccessExpectation {
  route: string
  admin: 'allow' | 'deny'
  data_manager: 'allow' | 'deny'
  data_analyst: 'allow' | 'deny'
  annotator: 'allow' | 'deny'
}

/**
 * Build a complete route-access matrix from ROLE_CONFIGS.
 *
 * For each unique route found across all roles, returns whether each role
 * is expected to be allowed or denied access.
 */
export function getRouteAccessMatrix(): RouteAccessExpectation[] {
  const allRoutes = new Set<string>()

  for (const config of Object.values(ROLE_CONFIGS)) {
    config.accessibleRoutes.forEach((r) => allRoutes.add(r))
    config.deniedRoutes.forEach((r) => allRoutes.add(r))
  }

  const matrix: RouteAccessExpectation[] = []

  for (const route of allRoutes) {
    const expectation: RouteAccessExpectation = {
      route,
      admin: resolveAccess(ROLE_CONFIGS.admin, route),
      data_manager: resolveAccess(ROLE_CONFIGS.data_manager, route),
      data_analyst: resolveAccess(ROLE_CONFIGS.data_analyst, route),
      annotator: resolveAccess(ROLE_CONFIGS.annotator, route),
    }
    matrix.push(expectation)
  }

  return matrix
}

/**
 * Determine whether a role is allowed or denied for a given route.
 * Explicit deny takes precedence, then explicit allow, then default deny.
 */
function resolveAccess(config: RoleConfig, route: string): 'allow' | 'deny' {
  if (config.deniedRoutes.includes(route)) return 'deny'
  if (config.accessibleRoutes.includes(route)) return 'allow'
  // Admin with empty deniedRoutes gets allow by default
  if (config.deniedRoutes.length === 0) return 'allow'
  return 'deny'
}
