// SystemMonitoring component tests
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';
import SystemMonitoring from '../SystemMonitoring';

// Mock recharts to avoid rendering issues in tests
vi.mock('recharts', () => ({
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
}));

// Mock antd DatePicker to avoid dayjs issues
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    DatePicker: {
      RangePicker: ({ value, onChange }: any) => (
        <div data-testid="range-picker">
          <input type="text" value={value?.[0]?.toString() || ''} readOnly />
          <input type="text" value={value?.[1]?.toString() || ''} readOnly />
        </div>
      ),
    },
  };
});

// Mock the hooks
vi.mock('@/hooks', () => ({
  useSystemHealth: () => ({
    data: {
      status: 'healthy',
      services: [
        {
          name: 'api-server',
          status: 'healthy',
          uptime: 3600,
          response_time: 50,
          error_rate: 0.01,
        },
      ],
      uptime: 7200,
    },
  }),
  useSystemAlerts: () => ({
    data: [
      {
        id: '1',
        type: 'warning',
        title: 'High CPU Usage',
        message: 'CPU usage is above 80%',
        source: 'monitoring',
        acknowledged: false,
        resolved: false,
        created_at: '2024-01-01T10:00:00Z',
      },
    ],
  }),
  useSystemMetrics: () => ({
    data: [
      {
        timestamp: '2024-01-01T10:00:00Z',
        cpu_usage: 75,
        memory_usage: 60,
        disk_usage: 45,
      },
    ],
  }),
  useAcknowledgeAlert: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useResolveAlert: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useRestartService: () => ({
    mutate: vi.fn(),
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

describe('SystemMonitoring', () => {
  it('renders system monitoring dashboard', () => {
    renderWithProviders(<SystemMonitoring />);
    
    expect(screen.getByText('System Status')).toBeInTheDocument();
    expect(screen.getAllByText('Uptime').length).toBeGreaterThan(0);
    expect(screen.getByText('Critical Alerts')).toBeInTheDocument();
  });

  it('displays system health information', () => {
    renderWithProviders(<SystemMonitoring />);
    
    expect(screen.getByText('System Performance')).toBeInTheDocument();
    expect(screen.getByText('Service Health')).toBeInTheDocument();
  });
});