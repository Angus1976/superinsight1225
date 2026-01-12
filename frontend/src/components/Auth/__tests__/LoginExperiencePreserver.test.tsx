/**
 * LoginExperiencePreserver Component Tests
 * 
 * Tests to ensure the existing login experience is preserved
 * while supporting multi-tenant features.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { 
  useLoginExperience, 
  prepareLoginCredentials,
  checkMultiTenantMode 
} from '../LoginExperiencePreserver';

// Mock authService
vi.mock('@/services/auth', () => ({
  authService: {
    getTenants: vi.fn(),
  },
}));

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('LoginExperiencePreserver', () => {
  let mockGetTenants: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    vi.clearAllMocks();
    const { authService } = await import('@/services/auth');
    mockGetTenants = authService.getTenants as ReturnType<typeof vi.fn>;
  });

  describe('useLoginExperience hook', () => {
    it('should detect single-tenant mode when only one tenant exists', async () => {
      const singleTenant = [{ id: 'tenant1', name: 'Single Tenant' }];
      mockGetTenants.mockResolvedValue(singleTenant);

      const { result } = renderHook(() => useLoginExperience());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isMultiTenant).toBe(false);
      expect(result.current.tenants).toHaveLength(1);
      expect(result.current.shouldShowTenantSelector).toBe(false);
    });

    it('should detect multi-tenant mode when multiple tenants exist', async () => {
      const multipleTenants = [
        { id: 'tenant1', name: 'Tenant 1' },
        { id: 'tenant2', name: 'Tenant 2' },
      ];
      mockGetTenants.mockResolvedValue(multipleTenants);

      const { result } = renderHook(() => useLoginExperience());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isMultiTenant).toBe(true);
      expect(result.current.tenants).toHaveLength(2);
      expect(result.current.shouldShowTenantSelector).toBe(true);
    });

    it('should auto-select single tenant when autoSelectSingleTenant is true', async () => {
      const singleTenant = [{ id: 'auto-tenant', name: 'Auto Tenant' }];
      mockGetTenants.mockResolvedValue(singleTenant);

      const { result } = renderHook(() => 
        useLoginExperience({ autoSelectSingleTenant: true })
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.selectedTenantId).toBe('auto-tenant');
    });

    it('should use default tenant ID when specified', async () => {
      const tenants = [
        { id: 'tenant1', name: 'Tenant 1' },
        { id: 'default-tenant', name: 'Default Tenant' },
      ];
      mockGetTenants.mockResolvedValue(tenants);

      const { result } = renderHook(() => 
        useLoginExperience({ defaultTenantId: 'default-tenant' })
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.selectedTenantId).toBe('default-tenant');
    });

    it('should gracefully handle API errors and preserve login experience', async () => {
      mockGetTenants.mockRejectedValue(new Error('API Error'));

      const { result } = renderHook(() => useLoginExperience());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should fallback to single-tenant mode without showing error
      expect(result.current.isMultiTenant).toBe(false);
      expect(result.current.tenants).toHaveLength(0);
      expect(result.current.error).toBeNull();
      expect(result.current.shouldShowTenantSelector).toBe(false);
    });

    it('should allow manual tenant selection', async () => {
      const tenants = [
        { id: 'tenant1', name: 'Tenant 1' },
        { id: 'tenant2', name: 'Tenant 2' },
      ];
      mockGetTenants.mockResolvedValue(tenants);

      const { result } = renderHook(() => useLoginExperience());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.selectTenant('tenant2');
      });

      expect(result.current.selectedTenantId).toBe('tenant2');
    });

    it('should call onTenantModeDetected callback', async () => {
      const onTenantModeDetected = vi.fn();
      const tenants = [
        { id: 'tenant1', name: 'Tenant 1' },
        { id: 'tenant2', name: 'Tenant 2' },
      ];
      mockGetTenants.mockResolvedValue(tenants);

      renderHook(() => 
        useLoginExperience({ onTenantModeDetected })
      );

      await waitFor(() => {
        expect(onTenantModeDetected).toHaveBeenCalledWith(true);
      });
    });

    it('should respect showTenantSelector override', async () => {
      const tenants = [
        { id: 'tenant1', name: 'Tenant 1' },
        { id: 'tenant2', name: 'Tenant 2' },
      ];
      mockGetTenants.mockResolvedValue(tenants);

      const { result } = renderHook(() => 
        useLoginExperience({ showTenantSelector: false })
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Even with multiple tenants, selector should be hidden
      expect(result.current.shouldShowTenantSelector).toBe(false);
    });

    it('should handle empty tenant list', async () => {
      mockGetTenants.mockResolvedValue([]);

      const { result } = renderHook(() => useLoginExperience());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isMultiTenant).toBe(false);
      expect(result.current.tenants).toHaveLength(0);
      expect(result.current.shouldShowTenantSelector).toBe(false);
    });
  });

  describe('prepareLoginCredentials', () => {
    it('should return basic credentials without tenant_id in single-tenant mode', () => {
      const credentials = prepareLoginCredentials(
        'testuser',
        'password123',
        null,
        false
      );

      expect(credentials).toEqual({
        username: 'testuser',
        password: 'password123',
      });
      expect(credentials.tenant_id).toBeUndefined();
    });

    it('should include tenant_id in multi-tenant mode', () => {
      const credentials = prepareLoginCredentials(
        'testuser',
        'password123',
        'tenant-123',
        true
      );

      expect(credentials).toEqual({
        username: 'testuser',
        password: 'password123',
        tenant_id: 'tenant-123',
      });
    });

    it('should not include tenant_id if not selected in multi-tenant mode', () => {
      const credentials = prepareLoginCredentials(
        'testuser',
        'password123',
        null,
        true
      );

      expect(credentials).toEqual({
        username: 'testuser',
        password: 'password123',
      });
      expect(credentials.tenant_id).toBeUndefined();
    });
  });

  describe('checkMultiTenantMode', () => {
    it('should return true when multiple tenants exist', async () => {
      mockGetTenants.mockResolvedValue([
        { id: 'tenant1', name: 'Tenant 1' },
        { id: 'tenant2', name: 'Tenant 2' },
      ]);

      const result = await checkMultiTenantMode();
      expect(result).toBe(true);
    });

    it('should return false when only one tenant exists', async () => {
      mockGetTenants.mockResolvedValue([
        { id: 'tenant1', name: 'Single Tenant' },
      ]);

      const result = await checkMultiTenantMode();
      expect(result).toBe(false);
    });

    it('should return false when API fails', async () => {
      mockGetTenants.mockRejectedValue(new Error('API Error'));

      const result = await checkMultiTenantMode();
      expect(result).toBe(false);
    });

    it('should return false when no tenants exist', async () => {
      mockGetTenants.mockResolvedValue([]);

      const result = await checkMultiTenantMode();
      expect(result).toBe(false);
    });
  });
});
