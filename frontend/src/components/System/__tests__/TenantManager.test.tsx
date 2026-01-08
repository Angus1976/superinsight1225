// TenantManager component tests
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import TenantManager from '../TenantManager';

// Mock the hooks
vi.mock('@/hooks', () => ({
  useTenants: () => ({
    data: [
      {
        id: '1',
        name: 'Test Tenant',
        status: 'active',
        plan: 'pro',
        users_count: 5,
        storage_used: 10,
        storage_limit: 100,
        cpu_quota: 4,
        memory_quota: 8,
        api_rate_limit: 1000,
        created_at: '2024-01-01',
      },
    ],
    isLoading: false,
  }),
  useCreateTenant: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateTenant: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteTenant: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe('TenantManager', () => {
  it('renders tenant management interface', () => {
    renderWithProviders(<TenantManager />);
    
    expect(screen.getByText('Total Tenants')).toBeInTheDocument();
    expect(screen.getByText('Active Tenants')).toBeInTheDocument();
    expect(screen.getByText('Create Tenant')).toBeInTheDocument();
  });

  it('displays tenant data in table', () => {
    renderWithProviders(<TenantManager />);
    
    expect(screen.getByText('Test Tenant')).toBeInTheDocument();
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('PRO')).toBeInTheDocument();
  });
});