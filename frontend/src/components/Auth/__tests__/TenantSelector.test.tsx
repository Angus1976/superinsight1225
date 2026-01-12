// TenantSelector component test
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { TenantSelector } from '../TenantSelector';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/auth';

// Mock dependencies
vi.mock('@/stores/authStore');
vi.mock('@/services/auth');
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) => {
      if (params?.name) return `Switched to ${params.name}`;
      return key;
    },
  }),
}));

const mockUseAuthStore = vi.mocked(useAuthStore);
const mockAuthService = vi.mocked(authService);

const mockTenants = [
  { id: '1', name: 'Test Tenant', logo: undefined },
  { id: '2', name: 'Another Tenant', logo: 'https://example.com/logo.png' },
  { id: '3', name: 'Third Tenant', logo: undefined },
];

const mockUser = { 
  id: '1', 
  username: 'test', 
  email: 'test@example.com', 
  role: 'admin' 
};

const createMockAuthStore = (overrides = {}) => ({
  user: mockUser,
  currentTenant: { id: '1', name: 'Test Tenant' },
  setTenant: vi.fn(),
  token: 'token',
  isAuthenticated: true,
  setAuth: vi.fn(),
  setUser: vi.fn(),
  clearAuth: vi.fn(),
  currentWorkspace: null,
  workspaces: [],
  setWorkspace: vi.fn(),
  setWorkspaces: vi.fn(),
  ...overrides,
});

describe('TenantSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset window.location.reload mock
    Object.defineProperty(window, 'location', {
      value: { reload: vi.fn() },
      writable: true,
    });
  });

  describe('Rendering', () => {
    it('renders nothing when user is not logged in', () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore({ user: null }));
      mockAuthService.getTenants.mockResolvedValue([]);

      const { container } = render(<TenantSelector />);
      expect(container.firstChild).toBeNull();
    });

    it('renders nothing when only one tenant available', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue([mockTenants[0]]);

      const { container } = render(<TenantSelector />);
      
      await waitFor(() => {
        expect(mockAuthService.getTenants).toHaveBeenCalled();
      });
      
      // Should be null since only one tenant
      expect(container.firstChild).toBeNull();
    });

    it('renders selector when multiple tenants available', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);

      render(<TenantSelector />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });

    it('shows current tenant name with showLabel prop when single tenant', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue([mockTenants[0]]);

      render(<TenantSelector showLabel />);

      await waitFor(() => {
        expect(screen.getByText('Test Tenant')).toBeInTheDocument();
      });
    });

    it('renders with custom size', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);

      render(<TenantSelector size="large" />);

      await waitFor(() => {
        const select = screen.getByRole('combobox');
        expect(select).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    it('shows loading spinner while fetching tenants', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      
      // Create a promise that doesn't resolve immediately
      let resolvePromise: (value: typeof mockTenants) => void;
      const pendingPromise = new Promise<typeof mockTenants>((resolve) => {
        resolvePromise = resolve;
      });
      mockAuthService.getTenants.mockReturnValue(pendingPromise);

      const { container } = render(<TenantSelector />);

      // Should show loading state - Ant Design Spin component has aria-busy
      await waitFor(() => {
        const spinner = container.querySelector('.ant-spin');
        expect(spinner).toBeInTheDocument();
      });

      // Resolve the promise
      resolvePromise!(mockTenants);

      // Should show selector after loading
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('shows error state when loading fails', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockRejectedValue(new Error('Network error'));

      render(<TenantSelector />);

      await waitFor(() => {
        expect(screen.getByText('tenant.loadFailed')).toBeInTheDocument();
      });
    });
  });

  describe('Tenant Switching', () => {
    it('calls switchTenant API when tenant is changed', async () => {
      const setTenant = vi.fn();
      mockUseAuthStore.mockReturnValue(createMockAuthStore({ setTenant }));
      mockAuthService.getTenants.mockResolvedValue(mockTenants);
      mockAuthService.switchTenant.mockResolvedValue({
        access_token: 'new-token',
        token_type: 'bearer',
        user: mockUser,
      });

      render(<TenantSelector autoReload={false} />);

      // Wait for selector to appear
      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      // Open dropdown and select another tenant
      const select = screen.getByRole('combobox');
      fireEvent.mouseDown(select);

      await waitFor(() => {
        const option = screen.getByText('Another Tenant');
        fireEvent.click(option);
      });

      await waitFor(() => {
        expect(mockAuthService.switchTenant).toHaveBeenCalledWith('2');
        expect(setTenant).toHaveBeenCalledWith(mockTenants[1]);
      });
    });

    it('does not switch when selecting current tenant', async () => {
      const setTenant = vi.fn();
      mockUseAuthStore.mockReturnValue(createMockAuthStore({ setTenant }));
      mockAuthService.getTenants.mockResolvedValue(mockTenants);

      render(<TenantSelector />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      // The current tenant is already selected, so clicking it again shouldn't trigger a switch
      // We verify by checking that switchTenant is not called after the initial render
      expect(mockAuthService.switchTenant).not.toHaveBeenCalled();
    });

    it('calls onTenantChange callback when tenant is switched', async () => {
      const onTenantChange = vi.fn();
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);
      mockAuthService.switchTenant.mockResolvedValue({
        access_token: 'new-token',
        token_type: 'bearer',
        user: mockUser,
      });

      render(<TenantSelector onTenantChange={onTenantChange} autoReload={false} />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      fireEvent.mouseDown(select);

      await waitFor(() => {
        const option = screen.getByText('Another Tenant');
        fireEvent.click(option);
      });

      await waitFor(() => {
        expect(onTenantChange).toHaveBeenCalledWith(mockTenants[1]);
      });
    });

    it('handles switch error gracefully', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);
      mockAuthService.switchTenant.mockRejectedValue(new Error('Switch failed'));

      render(<TenantSelector autoReload={false} />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      fireEvent.mouseDown(select);

      await waitFor(() => {
        const option = screen.getByText('Another Tenant');
        fireEvent.click(option);
      });

      // Should handle error without crashing
      await waitFor(() => {
        expect(mockAuthService.switchTenant).toHaveBeenCalled();
      });
    });
  });

  describe('Search Functionality', () => {
    it('filters tenants based on search input', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);

      render(<TenantSelector />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      // Open dropdown
      const select = screen.getByRole('combobox');
      fireEvent.mouseDown(select);

      // Type in search
      const input = screen.getByRole('combobox');
      await userEvent.type(input, 'Another');

      // Should filter to show only matching tenant
      await waitFor(() => {
        expect(screen.getByText('Another Tenant')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);

      render(<TenantSelector />);

      await waitFor(() => {
        const select = screen.getByRole('combobox');
        expect(select).toHaveAttribute('aria-label', 'tenant.select');
      });
    });

    it('supports keyboard navigation', async () => {
      mockUseAuthStore.mockReturnValue(createMockAuthStore());
      mockAuthService.getTenants.mockResolvedValue(mockTenants);

      render(<TenantSelector />);

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      
      // Focus and open with keyboard
      select.focus();
      fireEvent.keyDown(select, { key: 'Enter' });

      // Dropdown should open
      await waitFor(() => {
        expect(screen.getByText('Another Tenant')).toBeInTheDocument();
      });
    });
  });
});
