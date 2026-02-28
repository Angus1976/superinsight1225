/**
 * ProtectedRoute Component Tests
 *
 * Tests for authentication gating, token expiration, permission checks,
 * and tenant/workspace isolation in protected routes.
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ProtectedRoute } from '../ProtectedRoute'
import { useAuthStore } from '@/stores/authStore'
import { Permission } from '@/utils/permissions'

// Mock usePermissions hook
const mockCheckPermission = vi.fn()
const mockCheckTenantAccess = vi.fn()
const mockCheckWorkspaceAccess = vi.fn()

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => ({
    checkPermission: mockCheckPermission,
    checkTenantAccess: mockCheckTenantAccess,
    checkWorkspaceAccess: mockCheckWorkspaceAccess,
    roleDisplayName: '测试角色',
  }),
}))

// Mock isTokenExpired
const mockIsTokenExpired = vi.fn()
vi.mock('@/utils/token', () => ({
  setToken: vi.fn(),
  clearAuthTokens: vi.fn(),
  isTokenExpired: (...args: unknown[]) => mockIsTokenExpired(...args),
  getToken: vi.fn(),
}))

/**
 * Renders ProtectedRoute inside a proper routing context with a login route
 * so Navigate redirects don't cause issues.
 */
const renderProtectedRoute = (
  props: Partial<React.ComponentProps<typeof ProtectedRoute>> = {},
  initialEntries = ['/protected']
) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route
          path="/protected"
          element={
            <ProtectedRoute {...props}>
              <div data-testid="protected-content">Protected Content</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCheckPermission.mockReturnValue(true)
    mockCheckTenantAccess.mockReturnValue(true)
    mockCheckWorkspaceAccess.mockReturnValue(true)
    mockIsTokenExpired.mockReturnValue(false)

    // Default: authenticated user with valid state
    useAuthStore.setState({
      isAuthenticated: true,
      token: 'valid-token',
      user: {
        id: 'user-1',
        username: 'testuser',
        email: 'test@example.com',
        role: 'ADMIN',
        tenant_id: 'tenant-1',
      },
      currentTenant: { id: 'tenant-1', name: 'Test Tenant' },
      currentWorkspace: { id: 'ws-1', name: 'Test Workspace', tenant_id: 'tenant-1' },
      _hasHydrated: true,
    })
  })

  describe('Authentication checks', () => {
    it('renders children when user is authenticated', () => {
      renderProtectedRoute()
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('redirects to login when not authenticated', () => {
      useAuthStore.setState({ isAuthenticated: false, token: null })
      renderProtectedRoute()

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })

    it('redirects to login when token is null', () => {
      useAuthStore.setState({ token: null })
      renderProtectedRoute()

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })

    it('redirects to login when token is expired', () => {
      mockIsTokenExpired.mockReturnValue(true)
      renderProtectedRoute()

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByTestId('login-page')).toBeInTheDocument()
    })
  })

  describe('Hydration loading state', () => {
    it('shows loading spinner while store is hydrating', () => {
      useAuthStore.setState({ _hasHydrated: false })
      renderProtectedRoute()

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByText('正在验证身份...')).toBeInTheDocument()
    })

    it('renders content after hydration completes', () => {
      useAuthStore.setState({ _hasHydrated: true })
      renderProtectedRoute()
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })

  describe('Tenant loading state', () => {
    it('shows loading when tenant is not yet loaded', () => {
      useAuthStore.setState({ currentTenant: null })
      renderProtectedRoute()

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByText('正在加载租户信息...')).toBeInTheDocument()
    })
  })

  describe('Permission checks', () => {
    it('renders children when user has required permission', () => {
      mockCheckPermission.mockReturnValue(true)
      renderProtectedRoute({ requiredPermission: Permission.VIEW_TASKS })
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })

    it('shows permission denied when user lacks required permission', () => {
      mockCheckPermission.mockReturnValue(false)
      renderProtectedRoute({ requiredPermission: Permission.SYSTEM_ADMIN })

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByText('权限不足')).toBeInTheDocument()
    })

    it('checks all permissions when requireAll is true', () => {
      mockCheckPermission.mockImplementation(
        (p: Permission) => p === Permission.VIEW_TASKS
      )
      renderProtectedRoute({
        requiredPermissions: [Permission.VIEW_TASKS, Permission.SYSTEM_ADMIN],
        requireAll: true,
      })

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByText('权限不足')).toBeInTheDocument()
    })

    it('allows access with any permission when requireAll is false', () => {
      mockCheckPermission.mockImplementation(
        (p: Permission) => p === Permission.VIEW_TASKS
      )
      renderProtectedRoute({
        requiredPermissions: [Permission.VIEW_TASKS, Permission.SYSTEM_ADMIN],
        requireAll: false,
      })

      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })

  describe('Tenant isolation', () => {
    it('shows tenant access denied when tenant check fails', () => {
      mockCheckTenantAccess.mockReturnValue(false)
      renderProtectedRoute({ requiredTenantId: 'other-tenant' })

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByText('租户访问受限')).toBeInTheDocument()
    })

    it('allows access when tenant check passes', () => {
      mockCheckTenantAccess.mockReturnValue(true)
      renderProtectedRoute({ requiredTenantId: 'tenant-1' })
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })

  describe('Workspace isolation', () => {
    it('shows workspace access denied when workspace check fails', () => {
      mockCheckWorkspaceAccess.mockReturnValue(false)
      renderProtectedRoute({ requiredWorkspaceId: 'other-ws' })

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      expect(screen.getByText('工作空间访问受限')).toBeInTheDocument()
    })

    it('allows access when workspace check passes', () => {
      mockCheckWorkspaceAccess.mockReturnValue(true)
      renderProtectedRoute({ requiredWorkspaceId: 'ws-1' })
      expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    })
  })
})
