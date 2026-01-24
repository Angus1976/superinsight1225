/**
 * QualityDashboard Component Tests
 *
 * Tests for the Quality Dashboard component including:
 * - Quality metrics display
 * - Accuracy trend section
 * - Confidence distribution section
 * - Engine performance table
 * - Filter controls
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import QualityDashboard from '../QualityDashboard';

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'ai_annotation:quality.ai_accuracy': 'AI Accuracy',
        'ai_annotation:quality.agreement_rate': 'Agreement Rate',
        'ai_annotation:quality.total_samples': 'Total Samples',
        'ai_annotation:quality.active_alerts': 'Active Alerts',
        'ai_annotation:quality.accuracy_trend': 'Accuracy Trend',
        'ai_annotation:quality.confidence_distribution': 'Confidence Distribution',
        'ai_annotation:quality.engine_performance': 'Engine Performance',
        'ai_annotation:quality.inconsistencies': 'Inconsistencies',
        'ai_annotation:quality.engine': 'Engine',
        'ai_annotation:quality.accuracy': 'Accuracy',
        'ai_annotation:quality.confidence': 'Confidence',
        'ai_annotation:quality.samples': 'Samples',
        'ai_annotation:quality.acceptance_rate': 'Acceptance Rate',
        'ai_annotation:quality.type': 'Type',
        'ai_annotation:quality.severity': 'Severity',
        'ai_annotation:quality.affected_documents': 'Affected Documents',
        'ai_annotation:quality.documents': 'documents',
        'ai_annotation:quality.description': 'Description',
        'ai_annotation:quality.suggested_fix': 'Suggested Fix',
        'ai_annotation:quality.date': 'Date',
        'ai_annotation:quality.human_accuracy': 'Human Accuracy',
        'ai_annotation:quality.accepted': 'accepted',
        'ai_annotation:quality.last_7_days': 'Last 7 Days',
        'ai_annotation:quality.last_30_days': 'Last 30 Days',
        'ai_annotation:quality.last_90_days': 'Last 90 Days',
        'ai_annotation:quality.all_engines': 'All Engines',
        'ai_annotation:quality.no_trend_data': 'No trend data available',
        'ai_annotation:quality.no_distribution_data': 'No distribution data available',
        'ai_annotation:quality.severity_levels.low': 'Low',
        'ai_annotation:quality.severity_levels.medium': 'Medium',
        'ai_annotation:quality.severity_levels.high': 'High',
        'common:actions.refresh': 'Refresh',
      };
      return translations[key] || key;
    },
  }),
}));

// Mock fetch
global.fetch = vi.fn();

const mockQualityMetrics = {
  aiAccuracy: 0.92,
  agreementRate: 0.88,
  totalSamples: 1500,
  activeAlerts: 2,
};

const mockTrendData = [
  { date: '2026-01-18', aiAccuracy: 0.90, humanAccuracy: 0.94, agreementRate: 0.87, sampleCount: 200 },
  { date: '2026-01-19', aiAccuracy: 0.91, humanAccuracy: 0.94, agreementRate: 0.88, sampleCount: 210 },
  { date: '2026-01-20', aiAccuracy: 0.89, humanAccuracy: 0.95, agreementRate: 0.86, sampleCount: 195 },
];

const mockDistributionData = [
  { range: '0.0-0.2', count: 50, acceptanceRate: 0.3 },
  { range: '0.2-0.4', count: 100, acceptanceRate: 0.5 },
  { range: '0.4-0.6', count: 200, acceptanceRate: 0.7 },
  { range: '0.6-0.8', count: 450, acceptanceRate: 0.85 },
  { range: '0.8-1.0', count: 700, acceptanceRate: 0.95 },
];

const mockEnginePerformance = [
  { engineId: 'engine_1', engineName: 'Pre-Annotation', accuracy: 0.92, confidence: 0.88, samples: 500, suggestions: 450, acceptanceRate: 0.85 },
  { engineId: 'engine_2', engineName: 'Mid-Coverage', accuracy: 0.89, confidence: 0.82, samples: 600, suggestions: 520, acceptanceRate: 0.78 },
];

const mockInconsistencies = [
  {
    id: 'inc_1',
    type: 'label_mismatch',
    severity: 'high' as const,
    affectedDocuments: ['doc_1', 'doc_2', 'doc_3'],
    description: 'Inconsistent labeling of PERSON entities',
    suggestedFix: 'Review annotation guidelines for PERSON entity',
  },
];

describe('QualityDashboard', () => {
  const defaultProps = {
    projectId: 'project_1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/quality-metrics')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            overview: mockQualityMetrics,
            accuracy_trend: mockTrendData,
            confidence_distribution: mockDistributionData,
            engine_performance: mockEnginePerformance,
            degradation_alerts: [],
          }),
        });
      }
      if (url.includes('/inconsistencies')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockInconsistencies,
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders quality dashboard with overview stats', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      // Use getAllByText since "AI Accuracy" appears in both stats and table header
      expect(screen.getAllByText('AI Accuracy').length).toBeGreaterThan(0);
      expect(screen.getByText('Agreement Rate')).toBeInTheDocument();
      expect(screen.getByText('Total Samples')).toBeInTheDocument();
      expect(screen.getByText('Active Alerts')).toBeInTheDocument();
    });
  });

  it('displays accuracy trend section', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Accuracy Trend')).toBeInTheDocument();
    });
  });

  it('displays confidence distribution section', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Confidence Distribution')).toBeInTheDocument();
    });
  });

  it('displays engine performance table', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Engine Performance')).toBeInTheDocument();
    });
  });

  it('shows time range filter with default value', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Last 30 Days')).toBeInTheDocument();
    });
  });

  it('shows refresh button', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    (global.fetch as any).mockRejectedValue(new Error('Network error'));
    
    render(<QualityDashboard {...defaultProps} />);
    
    // Component should not crash - wait for loading to finish
    await waitFor(() => {
      expect(screen.getByText('AI Accuracy')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('displays engine names in performance table', async () => {
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('Pre-Annotation')).toBeInTheDocument();
      expect(screen.getByText('Mid-Coverage')).toBeInTheDocument();
    });
  });

  it('shows empty state when no trend data', async () => {
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/quality-metrics')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            overview: mockQualityMetrics,
            accuracy_trend: [],
            confidence_distribution: [],
            engine_performance: [],
            degradation_alerts: [],
          }),
        });
      }
      if (url.includes('/inconsistencies')) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
    
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('No trend data available')).toBeInTheDocument();
    });
  });

  it('shows empty state when no distribution data', async () => {
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes('/quality-metrics')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            overview: mockQualityMetrics,
            accuracy_trend: mockTrendData,
            confidence_distribution: [],
            engine_performance: [],
            degradation_alerts: [],
          }),
        });
      }
      if (url.includes('/inconsistencies')) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    });
    
    render(<QualityDashboard {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('No distribution data available')).toBeInTheDocument();
    });
  });
});
