// PermissionGuard component tests with tenant isolation
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { PermissionGuard } from '../PermissionGuard';
import { Permission } from '@/utils/permissions';

// Mock the usePermissions hook
const mockCheckPermission = vi.fn();
const mockCheckPermissionWithIsolation = vi.fn();
const mockCheckTenantAccess = vi.fn();
const mockCheckWorkspaceAccess = vi.fn();

vi.mock('@/hooks/usePermissions', () => ({
  usePermissions: () => ({
    checkPermission: mockCheckPermission,
    checkPermissionWithIsolation: mockCheckPermissionWithIsolation,
    checkTenantAccess: mockCheckTenantAccess,
    checkWorkspaceAccess: mockCheckWorkspaceAccess,
    roleDisplayName: 'Test Role',
    tenantRoleDisplayName: 'Tenant Member',
    workspaceRoleDisplayName: 'Workspace Member',
    tenantContext: {
      tenantId: 'tenant-1',
      workspaceId: 'workspace-1',
    },
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

describe('PermissionGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCheckPermission.mockReturnValue(true);
    mockCheckPermissionWithIsolation.mockReturnValue(true);
    mockCheckTenantAccess.mockReturnValue(true);
    mockCheckWorkspaceAccess.mockReturnValue(true);
  });

  describe('Basic Permission Checks', () => {
    it('renders children when user has required permission', () => {
      mockCheckPermission.mockReturnValue(true);

      renderWithRouter(
        <PermissionGuard permission={Permission.VIEW_TASKS}>
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('shows access denied when user lacks permission', () => {
      mockCheckPermission.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard permission={Permission.SYSTEM_ADMIN}>
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('权限不足')).toBeInTheDocument();
    });

    it('renders fallback when provided and permission denied', () => {
      mockCheckPermission.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.SYSTEM_ADMIN}
          fallback={<div data-testid="fallback">Custom Fallback</div>}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByTestId('fallback')).toBeInTheDocument();
    });
  });

  describe('Multiple Permissions', () => {
    it('allows access when user has any of the required permissions (requireAll=false)', () => {
      mockCheckPermission.mockImplementation((permission: Permission) => {
        return permission === Permission.VIEW_TASKS;
      });

      renderWithRouter(
        <PermissionGuard 
          permissions={[Permission.VIEW_TASKS, Permission.SYSTEM_ADMIN]}
          requireAll={false}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('denies access when user lacks all required permissions (requireAll=true)', () => {
      mockCheckPermission.mockImplementation((permission: Permission) => {
        return permission === Permission.VIEW_TASKS;
      });

      renderWithRouter(
        <PermissionGuard 
          permissions={[Permission.VIEW_TASKS, Permission.SYSTEM_ADMIN]}
          requireAll={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    });
  });

  describe('Tenant Isolation', () => {
    it('allows access when tenant isolation check passes', () => {
      mockCheckTenantAccess.mockReturnValue(true);
      mockCheckPermissionWithIsolation.mockReturnValue(true);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          resourceTenantId="tenant-1"
          requireTenantIsolation={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('denies access when tenant isolation check fails', () => {
      mockCheckTenantAccess.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          resourceTenantId="tenant-2"
          requireTenantIsolation={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('租户访问受限')).toBeInTheDocument();
    });
  });

  describe('Workspace Isolation', () => {
    it('allows access when workspace isolation check passes', () => {
      mockCheckWorkspaceAccess.mockReturnValue(true);
      mockCheckPermissionWithIsolation.mockReturnValue(true);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          resourceWorkspaceId="workspace-1"
          requireWorkspaceIsolation={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('denies access when workspace isolation check fails', () => {
      mockCheckWorkspaceAccess.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          resourceWorkspaceId="workspace-2"
          requireWorkspaceIsolation={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('工作空间访问受限')).toBeInTheDocument();
    });
  });

  describe('Combined Tenant and Workspace Isolation', () => {
    it('allows access when both tenant and workspace checks pass', () => {
      mockCheckTenantAccess.mockReturnValue(true);
      mockCheckWorkspaceAccess.mockReturnValue(true);
      mockCheckPermissionWithIsolation.mockReturnValue(true);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          resourceTenantId="tenant-1"
          resourceWorkspaceId="workspace-1"
          requireTenantIsolation={true}
          requireWorkspaceIsolation={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });

    it('denies access when tenant check fails even if workspace passes', () => {
      mockCheckTenantAccess.mockReturnValue(false);
      mockCheckWorkspaceAccess.mockReturnValue(true);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          resourceTenantId="tenant-2"
          resourceWorkspaceId="workspace-1"
          requireTenantIsolation={true}
          requireWorkspaceIsolation={true}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      expect(screen.getByText('租户访问受限')).toBeInTheDocument();
    });
  });

  describe('Graceful Degradation', () => {
    it('renders skeleton when fallbackMode is skeleton', () => {
      mockCheckPermission.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.SYSTEM_ADMIN}
          fallbackMode="skeleton"
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      // Skeleton renders with ant-skeleton class
      expect(document.querySelector('.ant-skeleton')).toBeInTheDocument();
    });

    it('renders nothing when fallbackMode is hidden', () => {
      mockCheckPermission.mockReturnValue(false);

      const { container } = renderWithRouter(
        <PermissionGuard 
          permission={Permission.SYSTEM_ADMIN}
          fallbackMode="hidden"
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
      // Container should be empty (only the router wrapper)
      expect(container.querySelector('[data-testid="protected-content"]')).not.toBeInTheDocument();
    });

    it('renders alert by default when permission denied', () => {
      mockCheckPermission.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard permission={Permission.SYSTEM_ADMIN}>
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(screen.getByText('权限不足')).toBeInTheDocument();
    });
  });

  describe('Permission Change Callback', () => {
    it('calls onPermissionChange when access is granted', () => {
      const onPermissionChange = vi.fn();
      mockCheckPermission.mockReturnValue(true);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.VIEW_TASKS}
          onPermissionChange={onPermissionChange}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(onPermissionChange).toHaveBeenCalledWith(true);
    });

    it('calls onPermissionChange when access is denied', () => {
      const onPermissionChange = vi.fn();
      mockCheckPermission.mockReturnValue(false);

      renderWithRouter(
        <PermissionGuard 
          permission={Permission.SYSTEM_ADMIN}
          onPermissionChange={onPermissionChange}
        >
          <div data-testid="protected-content">Protected Content</div>
        </PermissionGuard>
      );

      expect(onPermissionChange).toHaveBeenCalledWith(false);
    });
  });
});
