// QualityReports component test
import { render, screen } from '@testing-library/react';
import { QualityReports } from '../QualityReports';

describe('QualityReports', () => {
  it('renders without crashing', () => {
    render(<QualityReports />);

    // Should render quality metrics
    expect(screen.getByText('平均质量分')).toBeInTheDocument();
    expect(screen.getByText('平均完成率')).toBeInTheDocument();
    expect(screen.getByText('平均修订率')).toBeInTheDocument();
    expect(screen.getByText('总工时')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<QualityReports loading={true} />);

    // Should show loading cards
    expect(screen.getByText('平均质量分')).toBeInTheDocument();
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
    expect(screen.getByText('平均质量分')).toBeInTheDocument();
  });
});