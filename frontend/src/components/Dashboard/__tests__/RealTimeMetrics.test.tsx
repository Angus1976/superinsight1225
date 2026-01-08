// RealTimeMetrics component test
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RealTimeMetrics } from '../RealTimeMetrics';
import { vi } from 'vitest';

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

    // Should render metric cards
    expect(screen.getByText('活跃任务')).toBeInTheDocument();
    expect(screen.getByText('今日标注')).toBeInTheDocument();
    expect(screen.getByText('语料总数')).toBeInTheDocument();
    expect(screen.getByText('账单总额')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    // Mock loading state
    vi.doMock('@/hooks/useDashboard', () => ({
      useDashboard: () => ({
        summary: null,
        annotationEfficiency: null,
        userActivity: null,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      }),
    }));

    render(
      <QueryClientProvider client={queryClient}>
        <RealTimeMetrics />
      </QueryClientProvider>
    );

    // Should show loading cards
    expect(screen.getByText('活跃任务')).toBeInTheDocument();
  });
});