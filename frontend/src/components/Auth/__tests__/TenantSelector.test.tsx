// TenantSelector component test
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { TenantSelector } from '../TenantSelector';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/auth';

// Mock dependencies
vi.mock('@/stores/authStore');
vi.mock('@/services/auth');
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockUseAuthStore = vi.mocked(useAuthStore);
const mockAuthService = vi.mocked(authService);

describe('TenantSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when user is not logged in', () => {
    mockUseAuthStore.mockReturnValue({
      user: null,
      currentTenant: null,
      setTenant: vi.fn(),
      token: null,
      isAuthenticated: false,
      setAuth: vi.fn(),
      setUser: vi.fn(),
      clearAuth: vi.fn(),
    });

    const { container } = render(<TenantSelector />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when only one tenant available', () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'test', email: 'test@example.com', role: 'user' },
      currentTenant: { id: '1', name: 'Test Tenant' },
      setTenant: vi.fn(),
      token: 'token',
      isAuthenticated: true,
      setAuth: vi.fn(),
      setUser: vi.fn(),
      clearAuth: vi.fn(),
    });

    mockAuthService.getTenants.mockResolvedValue([
      { id: '1', name: 'Test Tenant' }
    ]);

    const { container } = render(<TenantSelector />);
    expect(container.firstChild).toBeNull();
  });

  it('renders selector when multiple tenants available', async () => {
    mockUseAuthStore.mockReturnValue({
      user: { id: '1', username: 'test', email: 'test@example.com', role: 'user' },
      currentTenant: { id: '1', name: 'Test Tenant' },
      setTenant: vi.fn(),
      token: 'token',
      isAuthenticated: true,
      setAuth: vi.fn(),
      setUser: vi.fn(),
      clearAuth: vi.fn(),
    });

    mockAuthService.getTenants.mockResolvedValue([
      { id: '1', name: 'Test Tenant' },
      { id: '2', name: 'Another Tenant' }
    ]);

    render(<TenantSelector />);

    // Should show loading initially, then render selector
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });
});