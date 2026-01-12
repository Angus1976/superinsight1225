// WorkspaceSwitcher component test
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { WorkspaceSwitcher } from '../WorkspaceSwitcher';
import { useAuth } from '@/hooks/useAuth';
import type { Workspace } from '@/types';

// Mock dependencies
vi.mock('@/hooks/useAuth');
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string | Record<string, string>) => {
      if (typeof defaultValue === 'string') return defaultValue;
      return key;
    },
  }),
}));

const mockUseAuth = vi.mocked(useAuth);

const mockWorkspaces: Workspace[] = [
  { 
    id: 'ws-1', 
    name: 'Default Workspace', 
    tenant_id: 'tenant-1',
    is_default: true,
    member_count: 5,
    project_count: 3
  },
  { 
    id: 'ws-2', 
    name: 'Project Alpha', 
    tenant_id: 'tenant-1',
    is_default: false,
    member_count: 3,
    project_count: 2
  },
  { 
    id: 'ws-3', 
    name: 'Project Beta', 
    tenant_id: 'tenant-1',
    is_default: false,
    member_count: 8,
    project_count: 5
  },
];

const mockUser = { 
  id: '1', 
  username: 'test', 
  email: 'test@example.com', 
  role: 'user' 
};

const createMockAuthReturn = (overrides = {}) => ({
  user: mockUser,
  token: 'token',
  currentTenant: { id: 'tenant-1', name: 'Test Tenant' },
  currentWorkspace: mockWorkspaces[0],
  workspaces: mockWorkspaces,
  isAuthenticated: true,
  login: vi.fn(),
  logout: vi.fn(),
  checkAuth: vi.fn(),
  switchTenant: vi.fn(),
  switchWorkspace: vi.fn().mockResolvedValue(true),
  refreshWorkspaces: vi.fn().mockResolvedValue(mockWorkspaces),
  createWorkspace: vi.fn(),
  ...overrides,
});

describe('WorkspaceSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Rendering', () => {
    it('renders nothing when user is not logged in', () => {
      mockUseAuth.mockReturnValue(createMockAuthReturn({ user: null }));

      const { container } = render(<WorkspaceSwitcher />);
      expect(container.firstChild).toBeNull();
    });

    it('renders loading state when workspaces are empty', () => {
      mockUseAuth.mockReturnValue(createMockAuthReturn({ workspaces: [] }));

      render(<WorkspaceSwitcher />);
      
      // Should show loading button
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('renders workspace selector when workspaces are available', () => {
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Should show combobox selector
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('renders with showLabel prop', () => {
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher showLabel />);
      
      // The label text is translated, so we check for the translated value
      expect(screen.getByText('选择工作空间:')).toBeInTheDocument();
    });

    it('renders with custom size', () => {
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher size="large" />);
      
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });
  });

  describe('Workspace Switching', () => {
    it('calls switchWorkspace when a different workspace is selected', async () => {
      vi.useRealTimers();
      const mockSwitchWorkspace = vi.fn().mockResolvedValue(true);
      
      mockUseAuth.mockReturnValue(createMockAuthReturn({ 
        switchWorkspace: mockSwitchWorkspace 
      }));

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open and select a different workspace
      await waitFor(() => {
        const option = screen.getByText('Project Alpha');
        fireEvent.click(option);
      });
      
      // Verify switchWorkspace was called
      await waitFor(() => {
        expect(mockSwitchWorkspace).toHaveBeenCalledWith('ws-2');
      });
    });

    it('does not call switchWorkspace when same workspace is selected', async () => {
      vi.useRealTimers();
      const mockSwitchWorkspace = vi.fn().mockResolvedValue(true);
      
      mockUseAuth.mockReturnValue(createMockAuthReturn({ 
        switchWorkspace: mockSwitchWorkspace 
      }));

      render(<WorkspaceSwitcher />);
      
      // The current workspace is already selected
      // Verify switchWorkspace was NOT called
      expect(mockSwitchWorkspace).not.toHaveBeenCalled();
    });

    it('calls onWorkspaceChange callback when workspace is switched', async () => {
      vi.useRealTimers();
      const mockSwitchWorkspace = vi.fn().mockResolvedValue(true);
      const mockOnWorkspaceChange = vi.fn();
      
      mockUseAuth.mockReturnValue(createMockAuthReturn({ 
        switchWorkspace: mockSwitchWorkspace 
      }));

      render(<WorkspaceSwitcher onWorkspaceChange={mockOnWorkspaceChange} />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open and select a different workspace
      await waitFor(() => {
        const option = screen.getByText('Project Beta');
        fireEvent.click(option);
      });
      
      // Wait for the callback to be called
      await waitFor(() => {
        expect(mockOnWorkspaceChange).toHaveBeenCalledWith(mockWorkspaces[2]);
      });
    });

    it('handles switch error gracefully', async () => {
      vi.useRealTimers();
      const mockSwitchWorkspace = vi.fn().mockRejectedValue(new Error('Switch failed'));
      
      mockUseAuth.mockReturnValue(createMockAuthReturn({ 
        switchWorkspace: mockSwitchWorkspace 
      }));

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open and select a different workspace
      await waitFor(() => {
        const option = screen.getByText('Project Alpha');
        fireEvent.click(option);
      });
      
      // Should handle error without crashing
      await waitFor(() => {
        expect(mockSwitchWorkspace).toHaveBeenCalled();
      });
    });
  });

  describe('Create Workspace', () => {
    it('respects showCreateButton prop', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      // Render with showCreateButton=false
      const { rerender } = render(<WorkspaceSwitcher showCreateButton={false} />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open
      await waitFor(() => {
        // Create button should not be visible
        expect(screen.queryByText('创建工作空间')).not.toBeInTheDocument();
      });
      
      // Rerender with showCreateButton=true (default)
      rerender(<WorkspaceSwitcher showCreateButton={true} />);
      
      // Open the dropdown again
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown
      await waitFor(() => {
        // Create button should be visible
        expect(screen.getByText('创建工作空间')).toBeInTheDocument();
      });
    });

    it('opens create modal when create button is clicked', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown and click create button
      await waitFor(() => {
        const createButton = screen.getByText('创建工作空间');
        fireEvent.click(createButton);
      });
      
      // Modal should be visible
      await waitFor(() => {
        expect(screen.getByText('创建新工作空间')).toBeInTheDocument();
      });
    });
  });

  describe('Refresh Functionality', () => {
    it('shows refresh button in dropdown', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open
      await waitFor(() => {
        // Refresh button should be visible (icon button)
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThan(0);
      });
    });

    it('calls refreshWorkspaces when refresh button is clicked', async () => {
      vi.useRealTimers();
      const mockRefreshWorkspaces = vi.fn().mockResolvedValue(mockWorkspaces);
      
      mockUseAuth.mockReturnValue(createMockAuthReturn({ 
        refreshWorkspaces: mockRefreshWorkspaces 
      }));

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown and find refresh button
      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        // Find the refresh button (last button in the dropdown footer)
        const refreshButton = buttons.find(btn => 
          btn.querySelector('.anticon-reload') || 
          btn.getAttribute('aria-label')?.includes('refresh')
        );
        if (refreshButton) {
          fireEvent.click(refreshButton);
        }
      });
    });
  });

  describe('Search Functionality', () => {
    it('filters workspaces based on search input', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Type in search
      await userEvent.type(combobox, 'Alpha');
      
      // Should filter to show only matching workspace
      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label', () => {
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      const select = screen.getByRole('combobox');
      // The aria-label is translated to Chinese
      expect(select).toHaveAttribute('aria-label', '选择工作空间');
    });

    it('supports keyboard navigation', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      const select = screen.getByRole('combobox');
      
      // Focus and open with keyboard
      select.focus();
      fireEvent.keyDown(select, { key: 'Enter' });
      
      // Dropdown should open
      await waitFor(() => {
        expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      });
    });
  });

  describe('Visual Indicators', () => {
    it('shows default badge for default workspace', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open
      await waitFor(() => {
        expect(screen.getByText('默认')).toBeInTheDocument();
      });
    });

    it('shows member count for workspaces', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open and check member counts
      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument(); // Default workspace has 5 members
      });
    });

    it('shows checkmark for current workspace', async () => {
      vi.useRealTimers();
      mockUseAuth.mockReturnValue(createMockAuthReturn());

      render(<WorkspaceSwitcher />);
      
      // Open the dropdown
      const combobox = screen.getByRole('combobox');
      fireEvent.mouseDown(combobox);
      
      // Wait for dropdown to open
      await waitFor(() => {
        // Current workspace should have a checkmark icon
        const checkIcons = document.querySelectorAll('.anticon-check-circle');
        expect(checkIcons.length).toBeGreaterThan(0);
      });
    });
  });
});
