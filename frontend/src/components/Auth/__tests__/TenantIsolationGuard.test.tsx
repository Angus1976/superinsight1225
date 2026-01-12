// TenantIsolationGuard component tests
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TenantIsolationGuard } from '../TenantIsolationGuard';

// Mock the hooks
const mockCheckTenantAccess = vi.fn();
const mockCheckWorkspaceAccess = vi.fn();

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => ({
    checkTenantAccess: mockCheckTenantAccess,
    checkWorkspaceAccess: mockCheckWorkspaceAccess,
    roleDisplayName: 'Test Role',
    tenantRoleDisplayName: 'Tenant Member',
    workspaceRoleDisplayName: 'Workspace Member',
    system: {
      isSystemAdmin: false,
    },
  }),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    currentTenant: { id: 'tenant-1', name: 'Test Tenant' },
    currentWorkspace: { id: 'workspace-1', name: 'Test Workspace' },
  }),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderWithRouter = (component: React.ReactNode) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('TenantIsolationGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCheckTenantAccess.mockReturnValue(true);
    mockCheckWorkspaceAccess.mockReturnValue(true);
  });

  describe('Tenant Access', () => {
    it('renders children when user has access to the tenant', () => {
      mockCheckTenantAccess.mockReturnValue(true);

      renderWithRouter(
        <TenantIsolationGuard resourceTenantId="tenant-1">
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('shows access denied when user lacks tenant access', () => {
      mockCheckTenantAccess.mockReturnValue(false);

      renderWithRouter(
        <TenantIsolationGuard resourceTenantId="tenant-2">
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('租户隔离保护')).toBeInTheDocument();
    });

    it('renders custom fallback when provided', () => {
      mockCheckTenantAccess.mockReturnValue(false);

      renderWithRouter(
        <TenantIsolationGuard 
          resourceTenantId="tenant-2"
          fallback={<div data-testid="custom-fallback">Custom Fallback</div>}
        >
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    });
  });

  describe('Workspace Access', () => {
    it('renders children when user has access to the workspace', () => {
      mockCheckTenantAccess.mockReturnValue(true);
      mockCheckWorkspaceAccess.mockReturnValue(true);

      renderWithRouter(
        <TenantIsolationGuard 
          resourceTenantId="tenant-1"
          resourceWorkspaceId="workspace-1"
        >
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('shows workspace access denied when user lacks workspace access', () => {
      mockCheckTenantAccess.mockReturnValue(true);
      mockCheckWorkspaceAccess.mockReturnValue(false);

      renderWithRouter(
        <TenantIsolationGuard 
          resourceTenantId="tenant-1"
          resourceWorkspaceId="workspace-2"
        >
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('工作空间隔离保护')).toBeInTheDocument();
    });
  });

  describe('Simple Mode', () => {
    it('shows simple access denied message when showDetailedReason is false', () => {
      mockCheckTenantAccess.mockReturnValue(false);

      renderWithRouter(
        <TenantIsolationGuard 
          resourceTenantId="tenant-2"
          showDetailedReason={false}
        >
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('访问受限')).toBeInTheDocument();
    });
  });

  describe('Callback', () => {
    it('calls onAccessDenied callback when tenant access is denied', () => {
      mockCheckTenantAccess.mockReturnValue(false);
      const onAccessDenied = vi.fn();

      renderWithRouter(
        <TenantIsolationGuard 
          resourceTenantId="tenant-2"
          onAccessDenied={onAccessDenied}
        >
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(onAccessDenied).toHaveBeenCalledWith('tenant');
    });

    it('calls onAccessDenied callback when workspace access is denied', () => {
      mockCheckTenantAccess.mockReturnValue(true);
      mockCheckWorkspaceAccess.mockReturnValue(false);
      const onAccessDenied = vi.fn();

      renderWithRouter(
        <TenantIsolationGuard 
          resourceTenantId="tenant-1"
          resourceWorkspaceId="workspace-2"
          onAccessDenied={onAccessDenied}
        >
          <div data-testid="protected-content">Protected Content</div>
        </TenantIsolationGuard>
      );

      expect(onAccessDenied).toHaveBeenCalledWith('workspace');
    });
  });
});
