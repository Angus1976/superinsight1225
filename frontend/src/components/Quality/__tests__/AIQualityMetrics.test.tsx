/**
 * AIQualityMetrics — 与当前组件内嵌数据与文案 key 对齐（无远程 fetch）。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import AIQualityMetrics from '../AIQualityMetrics'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'quality:columns.metric': 'Metric',
        'quality:columns.ai_value': 'AI Value',
        'quality:columns.human_value': 'Human Value',
        'quality:columns.agreement_rate': 'Agreement Rate',
        'quality:columns.discrepancies': 'Discrepancies',
        'quality:columns.engine': 'Engine',
        'quality:columns.samples': 'Samples',
        'ai_annotation:metrics.accuracy': 'Accuracy',
        'ai_annotation:metrics.avg_latency': 'Avg Latency',
        'ai_annotation:metrics.cost_per_1k': 'Cost / 1K',
        'ai_annotation:metrics.throughput': 'Throughput',
        'quality:stats.ai_accuracy': 'AI Accuracy',
        'quality:labels.vs_previous': 'vs previous',
        'quality:stats.agreement_rate': 'Agreement Rate',
        'quality:labels.human_accuracy': 'Human accuracy',
        'quality:stats.total_samples': 'Total Samples',
        'quality:labels.avg_per_day': 'Avg per day',
        'quality:stats.active_alerts': 'Active Alerts',
        'quality:labels.needs_attention': 'Needs Attention',
        'quality:labels.all_good': 'All Good',
        'quality:titles.degradation_alerts': 'Quality Degradation Alerts',
        'quality:labels.current': 'Current',
        'quality:labels.previous': 'Previous',
        'quality:titles.confidence_distribution': 'Confidence Distribution',
        'quality:titles.human_ai_agreement': 'Human-AI Agreement Analysis',
        'quality:titles.engine_performance': 'Engine Performance Comparison',
        'quality:filters.all_engines': 'All Engines',
      }
      return map[key] ?? key
    },
    i18n: { language: 'en' },
  }),
}))

describe('AIQualityMetrics', () => {
  const defaultProps = { projectId: '100' }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders summary statistics and trend labels', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getAllByText('AI Accuracy').length).toBeGreaterThan(0)
      expect(screen.getByText('Total Samples')).toBeInTheDocument()
      expect(screen.getByText('Active Alerts')).toBeInTheDocument()
    })
  })

  it('shows latest AI accuracy from embedded trend (last day)', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      const statTitle = screen
        .getAllByText('AI Accuracy')
        .find((el) => el.classList.contains('ant-statistic-title'))
      const card = statTitle?.closest('.ant-card')
      expect(card?.textContent).toMatch(/90/)
    })
  })

  it('renders degradation alerts with recommendation text', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Quality Degradation Alerts')).toBeInTheDocument()
      expect(
        screen.getByText('Review recent training data quality', { exact: false })
      ).toBeInTheDocument()
    })
  })

  it('shows confidence distribution ranges and acceptance tags', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Confidence Distribution')).toBeInTheDocument()
      expect(screen.getByText('0.90-1.00')).toBeInTheDocument()
      expect(screen.getByText(/95% accepted/)).toBeInTheDocument()
    })
  })

  it('renders engine performance table with embedded engine names', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Engine Performance Comparison')).toBeInTheDocument()
      expect(screen.getByText('GPT-4 Pre-annotation')).toBeInTheDocument()
      expect(screen.getByText('Qwen Mid-coverage')).toBeInTheDocument()
    })
  })

  it('renders Human-AI agreement table', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Human-AI Agreement Analysis')).toBeInTheDocument()
      expect(screen.getByText('Label Selection')).toBeInTheDocument()
    })
  })

  it('shows engine filter with All Engines option', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('All Engines')).toBeInTheDocument()
    })
  })

  it('shows Needs Attention when degradation alerts exist', async () => {
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('Needs Attention')).toBeInTheDocument()
    })
  })

  it('sorts engine table when accuracy header clicked', async () => {
    const user = userEvent.setup()
    render(<AIQualityMetrics {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('GPT-4 Pre-annotation')).toBeInTheDocument()
    })
    const accuracyHeader = screen.getByRole('columnheader', { name: /^Accuracy$/i })
    await user.click(accuracyHeader)
    await waitFor(() => {
      expect(screen.getByText('GPT-4 Pre-annotation')).toBeInTheDocument()
    })
  })
})
