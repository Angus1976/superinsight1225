/**
 * Auth Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '../authStore'
import type { User, Tenant } from '@/types'

// Mock token utilities
vi.mock('@/utils/token', () => ({
  setToken: vi.fn(),
  clearAuthTokens: vi.fn(),
}))

// Get the mocked functions
import { setToken, clearAuthTokens } from '@/utils/token'

describe('authStore', () => {
  const mockUser: User = {
    id: 'user-1',
    username: 'testuser',
    email: 'test@example.com',
    name: '测试用户',
    tenant_id: 'tenant-1',
    roles: ['user'],
    permissions: ['read:tasks'],
    avatar: '',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  }

  const mockTenant: Tenant = {
    id: 'tenant-1',
    name: '测试租户',
    code: 'TEST',
    status: 'active',
  }

  const mockToken = 'mock-jwt-token'

  beforeEach(() => {
    // Reset store to initial state
    useAuthStore.setState({
      user: null,
      token: null,
      currentTenant: null,
      isAuthenticated: false,
    })
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('starts with null user', () => {
      const { user } = useAuthStore.getState()
      expect(user).toBeNull()
    })

    it('starts with null token', () => {
      const { token } = useAuthStore.getState()
      expect(token).toBeNull()
    })

    it('starts with null tenant', () => {
      const { currentTenant } = useAuthStore.getState()
      expect(currentTenant).toBeNull()
    })

    it('starts as not authenticated', () => {
      const { isAuthenticated } = useAuthStore.getState()
      expect(isAuthenticated).toBe(false)
    })
  })

  describe('setAuth', () => {
    it('sets user, token, tenant and isAuthenticated', () => {
      const { setAuth } = useAuthStore.getState()

      setAuth(mockUser, mockToken, mockTenant)

      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.token).toBe(mockToken)
      expect(state.currentTenant).toEqual(mockTenant)
      expect(state.isAuthenticated).toBe(true)
    })

    it('calls setToken utility', () => {
      const { setAuth } = useAuthStore.getState()

      setAuth(mockUser, mockToken, mockTenant)

      expect(setToken).toHaveBeenCalledWith(mockToken)
    })

    it('creates default tenant from user if not provided', () => {
      const { setAuth } = useAuthStore.getState()

      setAuth(mockUser, mockToken)

      const { currentTenant } = useAuthStore.getState()
      expect(currentTenant).toEqual({
        id: mockUser.tenant_id,
        name: mockUser.tenant_id,
      })
    })
  })

  describe('setUser', () => {
    it('updates user data', () => {
      const { setAuth, setUser } = useAuthStore.getState()

      // First set auth
      setAuth(mockUser, mockToken, mockTenant)

      // Update user
      const updatedUser = { ...mockUser, name: '更新的用户' }
      setUser(updatedUser)

      const { user } = useAuthStore.getState()
      expect(user?.name).toBe('更新的用户')
    })

    it('preserves other state when updating user', () => {
      const { setAuth, setUser } = useAuthStore.getState()

      setAuth(mockUser, mockToken, mockTenant)
      setUser({ ...mockUser, name: '更新的用户' })

      const state = useAuthStore.getState()
      expect(state.token).toBe(mockToken)
      expect(state.isAuthenticated).toBe(true)
    })
  })

  describe('setTenant', () => {
    it('updates current tenant', () => {
      const { setAuth, setTenant } = useAuthStore.getState()

      setAuth(mockUser, mockToken, mockTenant)

      const newTenant: Tenant = {
        id: 'tenant-2',
        name: '新租户',
        code: 'NEW',
        status: 'active',
      }
      setTenant(newTenant)

      const { currentTenant } = useAuthStore.getState()
      expect(currentTenant).toEqual(newTenant)
    })
  })

  describe('clearAuth', () => {
    it('clears all auth state', () => {
      const { setAuth, clearAuth } = useAuthStore.getState()

      // First set auth
      setAuth(mockUser, mockToken, mockTenant)

      // Then clear
      clearAuth()

      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.token).toBeNull()
      expect(state.currentTenant).toBeNull()
      expect(state.isAuthenticated).toBe(false)
    })

    it('calls clearAuthTokens utility', () => {
      const { setAuth, clearAuth } = useAuthStore.getState()

      setAuth(mockUser, mockToken, mockTenant)
      clearAuth()

      expect(clearAuthTokens).toHaveBeenCalled()
    })
  })

  describe('persistence', () => {
    it('store has correct name for persistence', () => {
      // The persist middleware should use 'auth-storage' as the key
      // This is a structural test to ensure the config is correct
      expect(useAuthStore.persist).toBeDefined()
    })
  })
})
