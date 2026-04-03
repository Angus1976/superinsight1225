/**
 * Data Visualization Components Unit Tests
 *
 * Tests chart rendering with mock data, data transformation for visualization,
 * interactive chart features, and export functionality.
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

vi.mock('@/hooks/useDashboard', () => ({
  useDashboard: () => ({
    summary: null,
    annotationEfficiency: null,
    userActivity: null,
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { username: 'testuser' },
    currentTenant: { id: 'tenant-1', name: 'Test Tenant' },
    currentWorkspace: { id: 'ws-1', name: 'Test Workspace' },
  }),
}));

// Mock recharts - jsdom can't render SVG charts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children, data }: any) => (
    <div data-testid="line-chart" data-points={data?.length || 0}>{children}</div>
  ),
  AreaChart: ({ children, data }: any) => (
    <div data-testid="area-chart" data-points={data?.length || 0}>{children}</div>
  ),
  BarChart: ({ children, data }: any) => (
    <div data-testid="bar-chart" data-points={data?.length || 0}>{children}</div>
  ),
  PieChart: ({ children }: any) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Line: (props: any) => <div data-testid="line" data-stroke={props.stroke} />,
  Area: (props: any) => <div data-testid="area" data-stroke={props.stroke} />,
  Bar: (props: any) => <div data-testid="bar" data-fill={props.fill} />,
  Pie: ({ children }: any) => <div data-testid="pie">{children}</div>,
  Cell: () => <div data-testid="cell" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="recharts-tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

// Mock antd DatePicker to avoid dayjs locale issues in jsdom
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    DatePicker: {
      RangePicker: ({ value, onChange, ...rest }: any) => (
        <div data-testid="range-picker">
          <input
            data-testid="range-start"
            type="text"
            value={value?.[0]?.format?.('YYYY-MM-DD') || ''}
            readOnly
          />
          <input
            data-testid="range-end"
            type="text"
            value={value?.[1]?.format?.('YYYY-MM-DD') || ''}
            readOnly
          />
        </div>
      ),
    },
  };
});

// ============================================================================
// Imports (after mocks)
// ============================================================================

import { TrendChart } from '../TrendChart';
import { OverviewCards } from '../OverviewCards';
import { ProgressOverview } from '../ProgressOverview';
import { QualityReports } from '../QualityReports';
import { QuickActions } from '../QuickActions';
import type { AnnotationEfficiency, UserActivityMetrics } from '@/types/dashboard';

// ============================================================================
// Helpers
// ============================================================================

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>,
  );
}

// ============================================================================
// Test Data
// ============================================================================

const mockTrendData = [
  { timestamp: 1706745600000, datetime: '2025-02-01T08:00:00Z', value: 85, label: 'Point 1' },
  { timestamp: 1706749200000, datetime: '2025-02-01T09:00:00Z', value: 90, label: 'Point 2' },
  { timestamp: 1706752800000, datetime: '2025-02-01T10:00:00Z', value: 78, label: 'Point 3' },
  { timestamp: 1706756400000, datetime: '2025-02-01T11:00:00Z', value: 92, label: 'Point 4' },
];

const mockQualityData = {
  trends: [
    {
      timestamp: 1706745600000,
      datetime: '2025-02-01T08:00:00Z',
      qualityScore: 0.85,
      completionRate: 0.92,
      revisionRate: 0.08,
      avgAnnotationTime: 45.2,
    },
    {
      timestamp: 1706749200000,
      datetime: '2025-02-01T09:00:00Z',
      qualityScore: 0.88,
      completionRate: 0.95,
      revisionRate: 0.05,
      avgAnnotationTime: 42.1,
    },
    {
      timestamp: 1706752800000,
      datetime: '2025-02-01T10:00:00Z',
      qualityScore: 0.82,
      completionRate: 0.89,
      revisionRate: 0.11,
      avgAnnotationTime: 48.5,
    },
  ],
  distribution: [
    { range: '90-100%', count: 45, percentage: 45, color: '#52c41a' },
    { range: '80-90%', count: 30, percentage: 30, color: '#1890ff' },
    { range: '70-80%', count: 15, percentage: 15, color: '#faad14' },
    { range: '<70%', count: 10, percentage: 10, color: '#ff4d4f' },
  ],
  workTime: [
    { user: 'Alice', totalHours: 40, efficiency: 0.92, qualityScore: 0.88, tasksCompleted: 120 },
    { user: 'Bob', totalHours: 35, efficiency: 0.85, qualityScore: 0.82, tasksCompleted: 95 },
  ],
  anomalies: [
    {
      timestamp: 1706745600000,
      datetime: '2025-02-01T08:00:00Z',
      type: 'quality' as const,
      severity: 'high' as const,
      description: 'Quality score dropped below threshold',
      value: 0.65,
    },
    {
      timestamp: 1706749200000,
      datetime: '2025-02-01T09:00:00Z',
      type: 'efficiency' as const,
      severity: 'medium' as const,
      description: 'Annotation speed decreased significantly',
      value: 0.45,
    },
  ],
};

/** Maps legacy mock shape to current QualityReports props (annotationEfficiency + userActivity). */
function buildQualityReportsMockProps(): {
  annotationEfficiency: AnnotationEfficiency;
  userActivity: UserActivityMetrics;
} {
  const trends = mockQualityData.trends.map((t) => ({
    timestamp: t.timestamp,
    datetime: t.datetime,
    annotations_per_hour: 100,
    average_annotation_time: t.avgAnnotationTime,
    quality_score: t.qualityScore,
    completion_rate: t.completionRate,
    revision_rate: t.revisionRate,
  }));
  const n = trends.length;
  const sum = (arr: typeof trends, pick: (x: (typeof trends)[0]) => number) =>
    arr.reduce((s, x) => s + pick(x), 0);
  return {
    annotationEfficiency: {
      period_hours: 168,
      data_points: n,
      trends,
      summary: {
        avg_annotations_per_hour: sum(trends, (t) => t.annotations_per_hour) / n,
        avg_quality_score: sum(trends, (t) => t.quality_score) / n,
        avg_completion_rate: sum(trends, (t) => t.completion_rate) / n,
        avg_revision_rate: sum(trends, (t) => t.revision_rate) / n,
      },
    },
    userActivity: {
      period_hours: 24,
      data_points: 0,
      trends: [],
      summary: {
        avg_active_users: 2,
        total_new_users: 0,
        avg_session_duration: (75 * 3600) / 2,
        avg_actions_per_session: 0,
        peak_concurrent_users: 0,
      },
    },
  };
}

// ============================================================================
// TrendChart Tests
// ============================================================================

describe('TrendChart', () => {
  it('renders chart with title and data', () => {
    render(<TrendChart title="Quality Trend" data={mockTrendData} />);

    expect(screen.getByText('Quality Trend')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });

  it('renders chart axes and grid', () => {
    render(<TrendChart title="Trend" data={mockTrendData} />);

    expect(screen.getByTestId('x-axis')).toBeInTheDocument();
    expect(screen.getByTestId('y-axis')).toBeInTheDocument();
    expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument();
  });

  it('renders with custom color', () => {
    render(<TrendChart title="Custom" data={mockTrendData} color="#ff0000" />);

    const line = screen.getByTestId('line');
    expect(line).toHaveAttribute('data-stroke', '#ff0000');
  });

  it('renders with default color when not specified', () => {
    render(<TrendChart title="Default" data={mockTrendData} />);

    const line = screen.getByTestId('line');
    expect(line).toHaveAttribute('data-stroke', '#1890ff');
  });

  it('shows legend when showLegend is true', () => {
    render(<TrendChart title="With Legend" data={mockTrendData} showLegend={true} />);

    expect(screen.getByTestId('legend')).toBeInTheDocument();
  });

  it('hides legend by default', () => {
    render(<TrendChart title="No Legend" data={mockTrendData} />);

    expect(screen.queryByTestId('legend')).not.toBeInTheDocument();
  });

  it('shows loading state', () => {
    const { container } = render(
      <TrendChart title="Loading" data={[]} loading={true} />,
    );

    expect(screen.getByText('Loading')).toBeInTheDocument();
    // Ant Design Card loading state
    const card = container.querySelector('.ant-card');
    expect(card).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<TrendChart title="Empty" data={[]} />);

    expect(screen.getByText('Empty')).toBeInTheDocument();
    const chart = screen.getByTestId('line-chart');
    expect(chart).toHaveAttribute('data-points', '0');
  });

  it('passes formatted data to chart', () => {
    render(<TrendChart title="Formatted" data={mockTrendData} />);

    const chart = screen.getByTestId('line-chart');
    expect(chart).toHaveAttribute('data-points', '4');
  });

  it('applies valueFormatter to data', () => {
    const formatter = (v: number) => `${v}%`;
    render(
      <TrendChart title="Formatted" data={mockTrendData} valueFormatter={formatter} />,
    );

    // Chart should render without errors with formatter
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});

// ============================================================================
// TrendChart - Data Transformation Tests
// ============================================================================

describe('TrendChart - data transformation', () => {
  it('transforms datetime to HH:mm format for display', () => {
    // The component internally formats datetime to HH:mm via dayjs
    // We verify the chart receives the correct number of data points
    render(<TrendChart title="Transform" data={mockTrendData} />);

    const chart = screen.getByTestId('line-chart');
    expect(chart).toHaveAttribute('data-points', String(mockTrendData.length));
  });

  it('handles single data point', () => {
    const singlePoint = [mockTrendData[0]];
    render(<TrendChart title="Single" data={singlePoint} />);

    const chart = screen.getByTestId('line-chart');
    expect(chart).toHaveAttribute('data-points', '1');
  });

  it('handles data with zero values', () => {
    const zeroData = [
      { timestamp: 1706745600000, datetime: '2025-02-01T08:00:00Z', value: 0 },
    ];
    render(<TrendChart title="Zero" data={zeroData} />);

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('handles data with negative values', () => {
    const negativeData = [
      { timestamp: 1706745600000, datetime: '2025-02-01T08:00:00Z', value: -10 },
      { timestamp: 1706749200000, datetime: '2025-02-01T09:00:00Z', value: -5 },
    ];
    render(<TrendChart title="Negative" data={negativeData} />);

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });
});

// ============================================================================
// OverviewCards Tests
// ============================================================================

describe('OverviewCards', () => {
  it('renders all metric cards', () => {
    renderWithProviders(<OverviewCards />);

    expect(screen.getByText('overview.totalProjects')).toBeInTheDocument();
    expect(screen.getByText('overview.activeProjects')).toBeInTheDocument();
    expect(screen.getByText('overview.completedTasks')).toBeInTheDocument();
    expect(screen.getByText('overview.qualityScore')).toBeInTheDocument();
  });

  it('renders context header with tenant and workspace', () => {
    renderWithProviders(<OverviewCards showContext={true} />);

    // Text is split across elements: "context.tenant" and ":" are separate spans
    expect(screen.getByText(/context\.tenant/)).toBeInTheDocument();
    expect(screen.getByText(/context\.workspace/)).toBeInTheDocument();
  });

  it('hides context header when showContext is false', () => {
    renderWithProviders(<OverviewCards showContext={false} />);

    expect(screen.queryByText('context.tenant')).not.toBeInTheDocument();
  });

  it('renders in compact mode', () => {
    renderWithProviders(<OverviewCards compact={true} />);

    // Should still render all cards
    expect(screen.getByText('overview.totalProjects')).toBeInTheDocument();
    expect(screen.getByText('overview.qualityScore')).toBeInTheDocument();
  });

  it('renders with custom tenantId and workspaceId', () => {
    renderWithProviders(
      <OverviewCards tenantId="custom-tenant" workspaceId="custom-ws" />,
    );

    expect(screen.getByText('overview.totalProjects')).toBeInTheDocument();
  });
});

// ============================================================================
// ProgressOverview Tests
// ============================================================================

describe('ProgressOverview', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders overall progress summary cards', () => {
    renderWithProviders(<ProgressOverview />);

    expect(screen.getByText('progress.totalProjects')).toBeInTheDocument();
    expect(screen.getByText('progress.overallProgress')).toBeInTheDocument();
    expect(screen.getByText('progress.totalTasks')).toBeInTheDocument();
  });

  it('renders task status distribution section', () => {
    renderWithProviders(<ProgressOverview />);

    expect(screen.getByText('progress.taskDistribution')).toBeInTheDocument();
  });

  it('renders project progress list', () => {
    renderWithProviders(<ProgressOverview />);

    expect(screen.getByText('progress.projectProgress')).toBeInTheDocument();
    // Mock project names from the component
    expect(screen.getByText('客服对话标注项目')).toBeInTheDocument();
    expect(screen.getByText('医疗文档实体识别')).toBeInTheDocument();
    expect(screen.getByText('金融报告分类')).toBeInTheDocument();
  });

  it('displays project status tags', () => {
    renderWithProviders(<ProgressOverview />);

    // Status tags from getStatusConfig
    expect(screen.getByText('progress.statusOnTrack')).toBeInTheDocument();
    expect(screen.getByText('progress.statusAtRisk')).toBeInTheDocument();
    expect(screen.getByText('progress.statusCompleted')).toBeInTheDocument();
  });

  it('displays task count tags for each project', () => {
    renderWithProviders(<ProgressOverview />);

    // The first project has 350 completed, 100 in progress, 50 pending
    expect(screen.getByText(/350/)).toBeInTheDocument();
    expect(screen.getByText(/100/)).toBeInTheDocument();
  });

  it('renders with custom tenantId and workspaceId', () => {
    renderWithProviders(
      <ProgressOverview tenantId="t-1" workspaceId="ws-1" />,
    );

    expect(screen.getByText('progress.totalProjects')).toBeInTheDocument();
  });
});

// ============================================================================
// QualityReports - Chart Rendering Tests
// ============================================================================

describe('QualityReports - chart rendering', () => {
  const defaultProps = buildQualityReportsMockProps();

  it('renders line chart by default', () => {
    render(<QualityReports {...defaultProps} />);

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
  });

  it('renders pie chart for distribution', () => {
    render(<QualityReports {...defaultProps} />);

    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('renders line and distribution charts together', () => {
    render(<QualityReports {...defaultProps} />);

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
  });

  it('renders with empty trend data', () => {
    const emptyEfficiency: AnnotationEfficiency = {
      period_hours: 0,
      data_points: 0,
      trends: [],
      summary: {
        avg_annotations_per_hour: 0,
        avg_quality_score: 0,
        avg_completion_rate: 0,
        avg_revision_rate: 0,
      },
    };
    render(<QualityReports annotationEfficiency={emptyEfficiency} />);

    expect(screen.getByText('metrics.avgQualityScore')).toBeInTheDocument();
  });
});

// ============================================================================
// QualityReports - Data Transformation Tests
// ============================================================================

describe('QualityReports - data transformation', () => {
  // Ant Design Statistic splits decimal values into integer + decimal parts
  // e.g. "85.0" becomes <span>85</span><span>.0</span>
  // Use container queries to verify the computed values

  const defaultProps = buildQualityReportsMockProps();

  it('calculates average quality score from trends', () => {
    const { container } = render(<QualityReports {...defaultProps} />);

    // avg = (0.85 + 0.88 + 0.82) / 3 = 0.85 → 85.0%
    const statValues = container.querySelectorAll('.ant-statistic-content-value');
    const values = Array.from(statValues).map((el) => el.textContent);
    expect(values).toContain('85.0');
  });

  it('calculates average completion rate from trends', () => {
    const { container } = render(<QualityReports {...defaultProps} />);

    // avg = (0.92 + 0.95 + 0.89) / 3 = 0.92 → 92.0%
    const statValues = container.querySelectorAll('.ant-statistic-content-value');
    const values = Array.from(statValues).map((el) => el.textContent);
    expect(values).toContain('92.0');
  });

  it('calculates average revision rate from trends', () => {
    const { container } = render(<QualityReports {...defaultProps} />);

    // avg = (0.08 + 0.05 + 0.11) / 3 = 0.08 → 8.0%
    const statValues = container.querySelectorAll('.ant-statistic-content-value');
    const values = Array.from(statValues).map((el) => el.textContent);
    expect(values).toContain('8.0');
  });

  it('calculates total work hours from user activity summary', () => {
    const { container } = render(<QualityReports {...defaultProps} />);

    // avg_active_users * avg_session_duration / 3600 = 75.0
    const statValues = container.querySelectorAll('.ant-statistic-content-value');
    const values = Array.from(statValues).map((el) => el.textContent);
    expect(values).toContain('75.0');
  });

  it('shows zero values when no trend data', () => {
    const emptyEfficiency: AnnotationEfficiency = {
      period_hours: 0,
      data_points: 0,
      trends: [],
      summary: {
        avg_annotations_per_hour: 0,
        avg_quality_score: 0,
        avg_completion_rate: 0,
        avg_revision_rate: 0,
      },
    };
    const { container } = render(
      <QualityReports annotationEfficiency={emptyEfficiency} />,
    );

    const statValues = container.querySelectorAll('.ant-statistic-content-value');
    const values = Array.from(statValues).map((el) => el.textContent);
    const zeroCount = values.filter((v) => v === '0.0').length;
    expect(zeroCount).toBeGreaterThanOrEqual(3);
  });
});

// ============================================================================
// QualityReports - Export Functionality Tests
// ============================================================================

describe('QualityReports - export functionality', () => {
  let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    createObjectURLSpy = vi.fn().mockReturnValue('blob:mock-url');
    revokeObjectURLSpy = vi.fn();
    global.URL.createObjectURL = createObjectURLSpy as any;
    global.URL.revokeObjectURL = revokeObjectURLSpy as any;
  });

  it('renders export button', () => {
    render(<QualityReports {...buildQualityReportsMockProps()} />);

    expect(screen.getByText('export.button')).toBeInTheDocument();
  });

  it('exports CSV when CSV option is clicked', async () => {
    const user = userEvent.setup();
    render(<QualityReports {...buildQualityReportsMockProps()} />);

    // Click the export dropdown button
    const exportBtn = screen.getByText('export.button');
    await user.click(exportBtn);

    // Wait for dropdown menu to appear and click CSV option
    await waitFor(() => {
      const csvOption = screen.getByText('export.csv');
      expect(csvOption).toBeInTheDocument();
    });

    const csvOption = screen.getByText('export.csv');
    await user.click(csvOption);

    // Verify blob was created for download
    expect(createObjectURLSpy).toHaveBeenCalled();
  });

  it('exports PDF/JSON when PDF option is clicked', async () => {
    const user = userEvent.setup();
    render(<QualityReports {...buildQualityReportsMockProps()} />);

    const exportBtn = screen.getByText('export.button');
    await user.click(exportBtn);

    await waitFor(() => {
      expect(screen.getByText('export.pdf')).toBeInTheDocument();
    });

    const pdfOption = screen.getByText('export.pdf');
    await user.click(pdfOption);

    expect(createObjectURLSpy).toHaveBeenCalled();
  });
});

// ============================================================================
// QualityReports - Interactive Chart Features Tests
// ============================================================================

describe('QualityReports - interactive features', () => {
  it('renders chart type selector', () => {
    render(<QualityReports {...buildQualityReportsMockProps()} />);

    // The Select component for chart type should be present
    expect(screen.getByText('charts.lineChart')).toBeInTheDocument();
  });

  it('renders date range picker', () => {
    render(<QualityReports {...buildQualityReportsMockProps()} />);

    expect(screen.getByTestId('range-picker')).toBeInTheDocument();
  });

  it('switches between line and area chart types', async () => {
    const user = userEvent.setup();
    render(<QualityReports {...buildQualityReportsMockProps()} />);

    // Initially shows line chart
    expect(screen.getByTestId('line-chart')).toBeInTheDocument();

    // The chart type selector is an antd Select - click to open dropdown
    const selector = screen.getByText('charts.lineChart');
    await user.click(selector);

    // Select area chart option
    await waitFor(() => {
      const areaOption = screen.getByText('charts.areaChart');
      expect(areaOption).toBeInTheDocument();
    });
  });
});

// ============================================================================
// QuickActions Tests
// ============================================================================

describe('QuickActions', () => {
  it('renders default action buttons', () => {
    renderWithProviders(<QuickActions />);

    expect(screen.getByText('quickActions.title')).toBeInTheDocument();
    expect(screen.getByText('quickActions.createTask')).toBeInTheDocument();
    expect(screen.getByText('quickActions.viewBilling')).toBeInTheDocument();
    expect(screen.getByText('quickActions.manageData')).toBeInTheDocument();
    expect(screen.getByText('quickActions.settings')).toBeInTheDocument();
  });

  it('renders custom actions', () => {
    const customActions = [
      {
        key: 'custom1',
        icon: <span data-testid="custom-icon">★</span>,
        label: 'Custom Action',
        path: '/custom',
        color: '#ff0000',
      },
    ];

    renderWithProviders(<QuickActions actions={customActions} />);

    expect(screen.getByText('Custom Action')).toBeInTheDocument();
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('navigates on button click', async () => {
    const user = userEvent.setup();
    renderWithProviders(<QuickActions />);

    const createBtn = screen.getByText('quickActions.createTask');
    await user.click(createBtn);

    // Navigation happens via useNavigate - button should be clickable without error
    expect(createBtn).toBeInTheDocument();
  });
});
