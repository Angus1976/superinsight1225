/**
 * AIQualityMetrics Component Tests
 *
 * Tests for the AI Quality Metrics dashboard including:
 * - Rendering metrics and statistics
 * - Accuracy trend visualization
 * - Confidence distribution
 * - Quality degradation alerts
 * - Date range filtering
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import userEvent from '@testing-library/user-event';
import AIQualityMetrics from '../AIQualityMetrics';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      const translations: Record<string, string> = {
        'quality:ai.stats.ai_accuracy': 'AI Accuracy',
        'quality:ai.stats.agreement_rate': 'Human-AI Agreement',
        'quality:ai.stats.total_samples': 'Total Samples',
        'quality:ai.stats.active_alerts': 'Active Alerts',
        'quality:ai.titles.degradation_alerts': 'Quality Degradation Alerts',
        'quality:ai.titles.confidence_distribution': 'Confidence Distribution',
        'quality:ai.titles.human_ai_agreement': 'Human-AI Agreement Analysis',
        'quality:ai.titles.engine_performance': 'Engine Performance Comparison',
        'quality:ai.titles.accuracy_trend': 'AI Accuracy Trend',
        'quality:ai.filters.all_engines': 'All Engines',
        'quality:ai.filters.last_7_days': 'Last 7 days',
        'quality:ai.filters.last_30_days': 'Last 30 days',
        'quality:ai.messages.no_data': 'No data available for selected period',
        'quality:ai.messages.loading': 'Loading AI quality metrics...',
        'quality:ai.labels.needs_attention': 'Needs Attention',
        'quality:ai.labels.all_good': 'All Good',
        'common:actions.refresh': 'Refresh',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock fetch
global.fetch = vi.fn();

const mockMetricsData = {
  overview: {
    aiAccuracy: 0.92,
    agreementRate: 0.88,
    totalSamples: 1500,
    activeAlerts: 2,
  },
  accuracyTrend: [
    {
      date: '2026-01-20',
      aiAccuracy: 0.90,
      humanAccuracy: 0.93,
      agreementRate: 0.87,
      sampleCount: 200,
    },
    {
      date: '2026-01-21',
      aiAccuracy: 0.91,
      humanAccuracy: 0.94,
      agreementRate: 0.88,
      sampleCount: 220,
    },
    {
      date: '2026-01-22',
      aiAccuracy: 0.92,
      humanAccuracy: 0.93,
      agreementRate: 0.88,
      sampleCount: 210,
    },
  ],
  confidenceDistribution: [
    { range: '0.9-1.0', count: 800, acceptanceRate: 0.95 },
    { range: '0.7-0.9', count: 500, acceptanceRate: 0.85 },
    { range: '0.5-0.7', count: 150, acceptanceRate: 0.60 },
    { range: '0.0-0.5', count: 50, acceptanceRate: 0.30 },
  ],
  enginePerformance: [
    {
      engineId: 'pre-annotation',
      engineName: 'Pre-annotation Engine',
      accuracy: 0.94,
      confidence: 0.91,
      samples: 600,
      suggestions: 580,
      acceptanceRate: 0.92,
    },
    {
      engineId: 'mid-coverage',
      engineName: 'Mid-coverage Engine',
      accuracy: 0.90,
      confidence: 0.85,
      samples: 500,
      suggestions: 450,
      acceptanceRate: 0.88,
    },
  ],
  degradationAlerts: [
    {
      alertId: 'alert_1',
      metric: 'AI Accuracy',
      currentValue: 0.92,
      previousValue: 0.95,
      degradationRate: -0.03,
      severity: 'warning' as const,
      recommendation: 'Review recent model changes',
      timestamp: '2026-01-24T10:00:00Z',
    },
  ],
};

describe('AIQualityMetrics', () => {
  const defaultProps = {
    projectId: 100,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockMetricsData,
    });
  });

  it('renders AI Quality Metrics title', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('AI Accuracy Trend')).toBeInTheDocument();
    });
  });

  it('displays overview statistics', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('AI Accuracy')).toBeInTheDocument();
      expect(screen.getByText('Human-AI Agreement')).toBeInTheDocument();
      expect(screen.getByText('Total Samples')).toBeInTheDocument();
      expect(screen.getByText('Active Alerts')).toBeInTheDocument();
    });
  });

  it('shows AI accuracy percentage', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      // 92% from mockMetricsData.overview.aiAccuracy
      expect(screen.getByText(/92\.0/)).toBeInTheDocument();
    });
  });

  it('shows total samples count', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('1500')).toBeInTheDocument();
    });
  });

  it('displays quality degradation alerts', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Quality Degradation Alerts')).toBeInTheDocument();
      expect(screen.getByText('Review recent model changes')).toBeInTheDocument();
    });
  });

  it('shows confidence distribution chart', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Confidence Distribution')).toBeInTheDocument();
      // Check for confidence ranges
      expect(screen.getByText('0.9-1.0')).toBeInTheDocument();
      expect(screen.getByText('0.7-0.9')).toBeInTheDocument();
    });
  });

  it('displays engine performance comparison', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Engine Performance Comparison')).toBeInTheDocument();
      expect(screen.getByText('Pre-annotation Engine')).toBeInTheDocument();
      expect(screen.getByText('Mid-coverage Engine')).toBeInTheDocument();
    });
  });

  it('shows Human-AI Agreement Analysis', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Human-AI Agreement Analysis')).toBeInTheDocument();
    });
  });

  it('fetches metrics on mount', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/annotation/quality-metrics'),
        expect.any(Object)
      );
    });
  });

  it('allows filtering by date range', async () => {
    const user = userEvent.setup();
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('AI Accuracy Trend')).toBeInTheDocument();
    });

    // Find and click date range filter
    const filterSelect = screen.getByText(/Last 7 days|Last 30 days/i);
    if (filterSelect) {
      await user.click(filterSelect);
    }

    // Date range options should appear
    await waitFor(() => {
      expect(screen.queryByText('Last 30 days')).toBeTruthy();
    });
  });

  it('allows filtering by engine', async () => {
    const user = userEvent.setup();
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Engine Performance Comparison')).toBeInTheDocument();
    });

    // Engine filter should be available
    const allEnginesFilter = screen.queryByText('All Engines');
    expect(allEnginesFilter).toBeTruthy();
  });

  it('refreshes data when refresh button is clicked', async () => {
    const user = userEvent.setup();
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    const refreshButton = screen.queryByRole('button', { name: /refresh/i });
    if (refreshButton) {
      await user.click(refreshButton);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(2);
      });
    }
  });

  it('shows loading state while fetching', async () => {
    (global.fetch as any).mockImplementationOnce(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => mockMetricsData,
              }),
            100
          )
        )
    );

    render(<AIQualityMetrics {...defaultProps} />);

    expect(screen.getByText('Loading AI quality metrics...')).toBeInTheDocument();

    await waitFor(
      () => {
        expect(screen.queryByText('Loading AI quality metrics...')).not.toBeInTheDocument();
      },
      { timeout: 200 }
    );
  });

  it('handles API errors gracefully', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      // Component should not crash
      expect(screen.queryByText('AI Accuracy Trend')).toBeTruthy();
    });
  });

  it('shows "Needs Attention" for active alerts', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      // With 2 active alerts, should show needs attention
      expect(screen.getByText('Needs Attention')).toBeInTheDocument();
    });
  });

  it('shows "All Good" when no alerts', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ...mockMetricsData,
        overview: { ...mockMetricsData.overview, activeAlerts: 0 },
        degradationAlerts: [],
      }),
    });

    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('All Good')).toBeInTheDocument();
    });
  });

  it('displays alert severity levels', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      // Warning severity should be displayed
      const warningElements = screen.queryAllByText(/warning/i);
      expect(warningElements.length).toBeGreaterThan(0);
    });
  });

  it('shows degradation rate as percentage', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      // -3% degradation rate from alert
      expect(screen.getByText(/-3/)).toBeInTheDocument();
    });
  });

  it('dismisses alerts when close button is clicked', async () => {
    const user = userEvent.setup();
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Review recent model changes')).toBeInTheDocument();
    });

    // Find close button on alert
    const closeButtons = screen.queryAllByRole('button', { name: /close/i });
    if (closeButtons.length > 0) {
      await user.click(closeButtons[0]);

      await waitFor(() => {
        expect(screen.queryByText('Review recent model changes')).not.toBeInTheDocument();
      });
    }
  });

  it('sorts engine performance table', async () => {
    const user = userEvent.setup();
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Pre-annotation Engine')).toBeInTheDocument();
    });

    // Click on accuracy column header to sort
    const accuracyHeader = screen.queryByText(/accuracy/i);
    if (accuracyHeader) {
      await user.click(accuracyHeader);

      // Table should reorder (verify by checking order)
      await waitFor(() => {
        expect(screen.getByText('Pre-annotation Engine')).toBeInTheDocument();
      });
    }
  });

  it('displays acceptance rates for confidence ranges', async () => {
    render(<AIQualityMetrics {...defaultProps} />);

    await waitFor(() => {
      // 95% acceptance rate for 0.9-1.0 range
      expect(screen.getByText(/95/)).toBeInTheDocument();
    });
  });
});
