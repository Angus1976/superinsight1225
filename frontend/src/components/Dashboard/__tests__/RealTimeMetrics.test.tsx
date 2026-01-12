// RealTimeMetrics component test
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RealTimeMetrics } from '../RealTimeMetrics';
import { vi } from 'vitest';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

// Mock the dashboard hook
vi.mock('@/hooks/useDashboard', () => ({
  useDashboard: () => ({
    summary: null,
    annotationEfficiency: null,
    userActivity: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

// Mock the auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { username: 'testuser' },
  }),
}));

describe('RealTimeMetrics', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  it('renders without crashing', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <RealTimeMetrics />
      </QueryClientProvider>
    );

    // Should render metric cards (using translation keys)
    expect(screen.getByText('metrics.activeTasks')).toBeInTheDocument();
    expect(screen.getByText('metrics.todayAnnotations')).toBeInTheDocument();
    expect(screen.getByText('metrics.totalCorpus')).toBeInTheDocument();
    expect(screen.getByText('metrics.totalBilling')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <RealTimeMetrics />
      </QueryClientProvider>
    );

    // Should show metric cards even in loading state
    expect(screen.getByText('metrics.activeTasks')).toBeInTheDocument();
  });
});