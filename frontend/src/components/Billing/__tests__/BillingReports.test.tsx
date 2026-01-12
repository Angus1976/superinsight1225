/**
 * BillingReports Component Tests
 * Task 11.5: Additional module unit tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { BillingReports } from '../BillingReports'

// Mock billing hooks
const mockGenerateReport = vi.fn()
vi.mock('@/hooks/useBilling', () => ({
  useGenerateReport: () => ({
    mutateAsync: mockGenerateReport,
    isPending: false,
  }),
  useProjectBreakdown: () => ({
    data: {
      breakdowns: [
        {
          project_id: 'proj-1',
          project_name: 'Test Project 1',
          total_cost: 5000,
          total_annotations: 1000,
          total_time_spent: 50,
          avg_cost_per_annotation: 5,
          percentage_of_total: 50,
        },
        {
          project_id: 'proj-2',
          project_name: 'Test Project 2',
          total_cost: 3000,
          total_annotations: 600,
          total_time_spent: 30,
          avg_cost_per_annotation: 5,
          percentage_of_total: 30,
        },
      ],
    },
    isLoading: false,
  }),
  useDepartmentAllocation: () => ({
    data: {
      allocations: [
        {
          department_id: 'dept-1',
          department_name: 'Engineering',
          total_cost: 4000,
          user_count: 10,
          projects: ['Project A', 'Project B'],
          percentage_of_total: 40,
        },
      ],
    },
    isLoading: false,
  }),
  useCostTrends: () => ({
    data: {
      total_cost: 10000,
      average_daily_cost: 333.33,
      trend_percentage: 5.5,
      daily_costs: [
        { date: '2024-01-01', cost: 300, annotations: 60 },
        { date: '2024-01-02', cost: 350, annotations: 70 },
        { date: '2024-01-03', cost: 320, annotations: 64 },
      ],
    },
    isLoading: false,
  }),
  useWorkHoursStatistics: () => ({
    data: {
      user_count: 5,
      statistics: [
        {
          user_id: 'user-1',
          user_name: 'Alice',
          total_hours: 40,
          billable_hours: 38,
          total_annotations: 800,
          annotations_per_hour: 20,
          total_cost: 2000,
          efficiency_score: 85,
        },
        {
          user_id: 'user-2',
          user_name: 'Bob',
          total_hours: 35,
          billable_hours: 32,
          total_annotations: 600,
          annotations_per_hour: 17.14,
          total_cost: 1500,
          efficiency_score: 75,
        },
      ],
    },
    isLoading: false,
  }),
}))

// Mock recharts to avoid rendering issues in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  ComposedChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="composed-chart">{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Area: () => <div data-testid="area" />,
  Line: () => <div data-testid="line" />,
  Bar: () => <div data-testid="bar" />,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}))

// Mock antd DatePicker to avoid dayjs issues
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    DatePicker: {
      RangePicker: ({ value, onChange, presets }: any) => (
        <div data-testid="range-picker">
          <input type="text" value={value?.[0]?.format?.('YYYY-MM-DD') || ''} readOnly />
          <input type="text" value={value?.[1]?.format?.('YYYY-MM-DD') || ''} readOnly />
        </div>
      ),
    },
  }
})

describe('BillingReports', () => {
  const defaultProps = {
    tenantId: 'tenant-123',
    currentUserId: 'user-123',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders billing reports with all sections', () => {
    render(<BillingReports {...defaultProps} />)

    // Check for main controls
    expect(screen.getByText('日期范围:')).toBeInTheDocument()
    expect(screen.getByText('报表类型:')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /生成报表/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /导出报表/i })).toBeInTheDocument()
  })

  it('displays summary statistics correctly', () => {
    render(<BillingReports {...defaultProps} />)

    // Check for statistics cards
    expect(screen.getByText('总成本')).toBeInTheDocument()
    expect(screen.getByText('日均成本')).toBeInTheDocument()
    expect(screen.getByText('项目数量')).toBeInTheDocument()
    // Note: 成本趋势 appears multiple times (as tab and statistic)
    expect(screen.getAllByText('成本趋势').length).toBeGreaterThan(0)
  })

  it('shows all tabs', () => {
    render(<BillingReports {...defaultProps} />)

    // Check for tab labels - use getAllByText since some appear multiple times
    expect(screen.getAllByText('成本趋势').length).toBeGreaterThan(0)
    expect(screen.getByText('项目分析')).toBeInTheDocument()
    expect(screen.getByText('部门分析')).toBeInTheDocument()
    expect(screen.getByText('工时统计')).toBeInTheDocument()
    expect(screen.getByText('报表详情')).toBeInTheDocument()
  })

  it('can switch to work hours statistics tab', async () => {
    const user = userEvent.setup()
    render(<BillingReports {...defaultProps} />)

    await user.click(screen.getByText('工时统计'))

    await waitFor(() => {
      expect(screen.getByText('统计人数')).toBeInTheDocument()
    })
  })

  it('calls generate report when button is clicked', async () => {
    const user = userEvent.setup()
    mockGenerateReport.mockResolvedValueOnce({
      id: 'report-1',
      report_type: 'summary',
      start_date: '2024-01-01',
      end_date: '2024-01-31',
      generated_at: '2024-01-31T12:00:00Z',
      total_cost: 10000,
      total_annotations: 2000,
      total_time_spent: 100,
      user_breakdown: {},
    })

    render(<BillingReports {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /生成报表/i }))

    await waitFor(() => {
      expect(mockGenerateReport).toHaveBeenCalledWith(
        expect.objectContaining({
          tenant_id: 'tenant-123',
          report_type: 'summary',
        })
      )
    })
  })

  it('export button is disabled when no report is generated', () => {
    render(<BillingReports {...defaultProps} />)

    const exportButton = screen.getByRole('button', { name: /导出报表/i })
    expect(exportButton).toBeDisabled()
  })
})
