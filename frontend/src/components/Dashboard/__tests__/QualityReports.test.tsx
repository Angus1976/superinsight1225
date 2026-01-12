// QualityReports component test
import { render, screen } from '@testing-library/react';
import { QualityReports } from '../QualityReports';
import { vi } from 'vitest';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

// Mock recharts to avoid rendering issues in tests
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  BarChart: ({ children }: any) => <div data-testid="bar-chart">{children}</div>,
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  Area: () => <div data-testid="area" />,
  Bar: () => <div data-testid="bar" />,
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

// Mock antd DatePicker to avoid dayjs issues
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd');
  return {
    ...actual,
    DatePicker: {
      RangePicker: ({ value, onChange }: any) => (
        <div data-testid="range-picker">
          <input type="text" value={value?.[0]?.format?.('YYYY-MM-DD') || ''} readOnly />
          <input type="text" value={value?.[1]?.format?.('YYYY-MM-DD') || ''} readOnly />
        </div>
      ),
    },
  };
});

describe('QualityReports', () => {
  it('renders without crashing', () => {
    render(<QualityReports />);

    // Should render quality metrics (using translation keys)
    expect(screen.getByText('metrics.avgQualityScore')).toBeInTheDocument();
    expect(screen.getByText('metrics.avgCompletionRate')).toBeInTheDocument();
    expect(screen.getByText('metrics.avgRevisionRate')).toBeInTheDocument();
    expect(screen.getByText('metrics.totalWorkHours')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<QualityReports loading={true} />);

    // Should show metric cards even in loading state
    expect(screen.getByText('metrics.avgQualityScore')).toBeInTheDocument();
  });

  it('renders with custom data', () => {
    const mockData = {
      trends: [],
      distribution: [],
      workTime: [],
      anomalies: [],
    };

    render(<QualityReports data={mockData} />);

    // Should render with provided data
    expect(screen.getByText('metrics.avgQualityScore')).toBeInTheDocument();
  });
});