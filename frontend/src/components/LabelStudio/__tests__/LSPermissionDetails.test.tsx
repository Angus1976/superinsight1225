/**
 * LSPermissionDetails component tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LSPermissionDetails, ROLE_PERMISSIONS, ROLES, hasPermission } from '../LSPermissionDetails';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      // Return the key or format with options
      if (options) {
        return key.replace(/\{\{(\w+)\}\}/g, (_, name) => String(options[name] ?? ''));
      }
      // Return last part of the key for readability
      return key.split('.').pop() || key;
    },
  }),
}));

describe('LSPermissionDetails', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders full table view by default', () => {
      render(<LSPermissionDetails />);

      // Should show title
      expect(screen.getByText('title')).toBeInTheDocument();

      // Should show subtitle
      expect(screen.getByText('subtitle')).toBeInTheDocument();

      // Should render a table
      expect(document.querySelector('table')).toBeInTheDocument();
    });

    it('renders compact card view when compact prop is true', () => {
      render(<LSPermissionDetails compact />);

      // Should show title in card
      expect(screen.getByText('title')).toBeInTheDocument();

      // Should render collapse panels
      expect(document.querySelectorAll('.ant-collapse-item').length).toBeGreaterThan(0);
    });

    it('renders all 5 roles by default', () => {
      render(<LSPermissionDetails />);

      ROLES.forEach((role) => {
        const label = role.labelKey.split('.').pop()!;
        expect(screen.getAllByText(label).length).toBeGreaterThan(0);
      });
    });

    it('filters roles when showRoles is specified', () => {
      render(<LSPermissionDetails showRoles={['owner', 'admin']} />);

      expect(screen.getAllByText('owner').length).toBeGreaterThan(0);
      expect(screen.getAllByText('admin').length).toBeGreaterThan(0);

      expect(screen.queryAllByText('manager')).toHaveLength(0);
      expect(screen.queryAllByText('reviewer')).toHaveLength(0);
      expect(screen.queryAllByText('annotator')).toHaveLength(0);
    });
  });

  describe('Role Highlighting', () => {
    it('highlights current role in full view', () => {
      render(<LSPermissionDetails currentRole="admin" />);

      expect(screen.getByText(/\(currentRole\)/)).toBeInTheDocument();
    });

    it('shows current role indicator text', () => {
      render(<LSPermissionDetails currentRole="manager" />);

      // Should show "(Your Role)" text
      expect(screen.getByText('(currentRole)')).toBeInTheDocument();
    });
  });

  describe('Permission Categories', () => {
    it('renders all 4 permission categories', () => {
      render(<LSPermissionDetails />);

      // Categories in compact mode are collapse panels
      render(<LSPermissionDetails compact />);

      // Check for category labels
      expect(screen.getAllByText('workspace').length).toBeGreaterThan(0);
      expect(screen.getAllByText('project').length).toBeGreaterThan(0);
      expect(screen.getAllByText('task').length).toBeGreaterThan(0);
      expect(screen.getAllByText('data').length).toBeGreaterThan(0);
    });

    it('renders 15 total permissions', () => {
      render(<LSPermissionDetails />);

      const table = document.querySelector('table');
      const rows = table?.querySelectorAll('tbody tr[data-row-key]');
      expect(rows?.length ?? 0).toBe(15);
    });
  });

  describe('Permission Matrix Logic', () => {
    it('owner has all 15 permissions', () => {
      expect(ROLE_PERMISSIONS.owner.length).toBe(15);
    });

    it('admin has 14 permissions (missing workspace:delete)', () => {
      expect(ROLE_PERMISSIONS.admin.length).toBe(14);
      expect(hasPermission('admin', 'workspace:delete')).toBe(false);
    });

    it('manager has 10 permissions', () => {
      expect(ROLE_PERMISSIONS.manager.length).toBe(10);
    });

    it('reviewer has 6 permissions', () => {
      expect(ROLE_PERMISSIONS.reviewer.length).toBe(6);
    });

    it('annotator has 4 permissions', () => {
      expect(ROLE_PERMISSIONS.annotator.length).toBe(4);
    });

    it('hasPermission returns correct values', () => {
      // Owner has everything
      expect(hasPermission('owner', 'workspace:delete')).toBe(true);
      expect(hasPermission('owner', 'data:import')).toBe(true);

      // Admin lacks workspace:delete
      expect(hasPermission('admin', 'workspace:delete')).toBe(false);
      expect(hasPermission('admin', 'workspace:edit')).toBe(true);

      // Annotator only has basic permissions
      expect(hasPermission('annotator', 'workspace:view')).toBe(true);
      expect(hasPermission('annotator', 'task:annotate')).toBe(true);
      expect(hasPermission('annotator', 'task:review')).toBe(false);
      expect(hasPermission('annotator', 'data:export')).toBe(false);
    });
  });

  describe('Permission Summary', () => {
    it('shows permission count summary', () => {
      render(<LSPermissionDetails />);

      // Check for permission counts
      const summaryCards = document.querySelectorAll('.ant-card');
      expect(summaryCards.length).toBeGreaterThan(0);

      expect(screen.getAllByText(/15\/15/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/4\/15/).length).toBeGreaterThan(0);
    });
  });

  describe('Compact Mode', () => {
    it('renders expand/collapse panels', async () => {
      render(<LSPermissionDetails compact />);

      // Should have collapse panels
      const collapse = document.querySelector('.ant-collapse');
      expect(collapse).toBeInTheDocument();

      // Should have 4 panels (one for each category)
      const panels = document.querySelectorAll('.ant-collapse-item');
      expect(panels.length).toBe(4);
    });

    it('shows permission badges in compact mode', () => {
      render(<LSPermissionDetails compact />);

      // Badges show permission count per category
      const badges = document.querySelectorAll('.ant-badge');
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  describe('Tooltips', () => {
    it('permission rows have tooltips', async () => {
      render(<LSPermissionDetails />);

      // Info icons should be present for tooltips
      const infoIcons = document.querySelectorAll('.anticon-info-circle');
      expect(infoIcons.length).toBe(15); // One for each permission
    });
  });

  describe('Custom className', () => {
    it('applies custom className', () => {
      const { container } = render(<LSPermissionDetails className="custom-class" />);

      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  describe('Role Definitions', () => {
    it('has correct role colors', () => {
      expect(ROLES.find((r) => r.role === 'owner')?.color).toBe('gold');
      expect(ROLES.find((r) => r.role === 'admin')?.color).toBe('purple');
      expect(ROLES.find((r) => r.role === 'manager')?.color).toBe('blue');
      expect(ROLES.find((r) => r.role === 'reviewer')?.color).toBe('green');
      expect(ROLES.find((r) => r.role === 'annotator')?.color).toBe('default');
    });

    it('has correct role hierarchy', () => {
      const roleOrder = ROLES.map((r) => r.role);
      expect(roleOrder).toEqual(['owner', 'admin', 'manager', 'reviewer', 'annotator']);
    });
  });

  describe('Accessibility', () => {
    it('table has proper structure', () => {
      render(<LSPermissionDetails />);

      const table = document.querySelector('table');
      expect(table).toBeInTheDocument();

      // Should have thead
      expect(table?.querySelector('thead')).toBeInTheDocument();

      // Should have tbody
      expect(table?.querySelector('tbody')).toBeInTheDocument();
    });
  });
});

describe('hasPermission helper', () => {
  it('returns true for valid permission', () => {
    expect(hasPermission('owner', 'workspace:view')).toBe(true);
  });

  it('returns false for invalid permission', () => {
    expect(hasPermission('annotator', 'workspace:delete')).toBe(false);
  });

  it('handles all workspace permissions correctly', () => {
    const workspacePermissions = [
      'workspace:view',
      'workspace:edit',
      'workspace:delete',
      'workspace:manage_members',
    ] as const;

    workspacePermissions.forEach((perm) => {
      expect(typeof hasPermission('owner', perm)).toBe('boolean');
    });
  });
});
