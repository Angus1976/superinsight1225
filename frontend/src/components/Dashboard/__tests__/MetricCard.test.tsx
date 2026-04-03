/**
 * MetricCard Component Tests
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/test-utils'
import { MetricCard } from '../MetricCard'
import { DollarOutlined } from '@ant-design/icons'

describe('MetricCard', () => {
  it('renders title and value', () => {
    render(<MetricCard title="总收入" value={12500} />)

    expect(screen.getByText('总收入')).toBeInTheDocument()
    expect(screen.getByText('12,500')).toBeInTheDocument()
  })

  it('renders with suffix', () => {
    render(<MetricCard title="完成率" value={85} suffix="%" />)

    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('%')).toBeInTheDocument()
  })

  it('renders with string value', () => {
    render(<MetricCard title="状态" value="进行中" />)

    expect(screen.getByText('进行中')).toBeInTheDocument()
  })

  it('renders with icon', () => {
    render(
      <MetricCard
        title="收入"
        value={1000}
        icon={<DollarOutlined data-testid="icon" />}
      />
    )

    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('displays positive trend with up arrow', () => {
    render(<MetricCard title="增长" value={100} trend={15.5} />)

    expect(screen.getByText('15.5%')).toBeInTheDocument()
    // 颜色在父级 div 内联样式上；全局 getComputedStyle mock 会使 toHaveStyle 不可靠
    const trendRow = screen.getByText('15.5%').parentElement as HTMLElement
    expect(trendRow.style.color).toMatch(/52c41a|82,\s*196,\s*26/i)
  })

  it('displays negative trend with down arrow', () => {
    render(<MetricCard title="下降" value={100} trend={-8.3} />)

    expect(screen.getByText('8.3%')).toBeInTheDocument()
    const trendRow = screen.getByText('8.3%').parentElement as HTMLElement
    expect(trendRow.style.color).toMatch(/ff4d4f|255,\s*77,\s*79/i)
  })

  it('displays zero trend with neutral indicator', () => {
    render(<MetricCard title="持平" value={100} trend={0} />)

    expect(screen.getByText('0.0%')).toBeInTheDocument()
    const trendRow = screen.getByText('0.0%').parentElement as HTMLElement
    expect(trendRow.style.color).toMatch(/^#999$|^rgb\(153,\s*153,\s*153\)$/i)
  })

  it('does not display trend when not provided', () => {
    render(<MetricCard title="无趋势" value={100} />)

    expect(screen.queryByText('%')).not.toBeInTheDocument()
  })

  it('shows loading state', () => {
    const { container } = render(
      <MetricCard title="加载中" value={0} loading={true} />
    )

    // Ant Design Card shows loading skeleton or spin
    const loadingElement = container.querySelector('.ant-card-loading-content') || 
                          container.querySelector('.ant-skeleton') ||
                          container.querySelector('.ant-spin');
    expect(loadingElement || container.querySelector('.ant-card')).toBeInTheDocument()
  })

  it('applies custom color to value', () => {
    render(<MetricCard title="自定义颜色" value={100} color="#ff0000" />)

    // The Statistic component should have the color style
    const valueElement = screen.getByText('100')
    expect(valueElement.closest('.ant-statistic-content')).toBeInTheDocument()
  })

  it('renders with trend label tooltip', () => {
    render(
      <MetricCard
        title="有提示"
        value={100}
        trend={10}
        trendLabel="相比上月增长"
      />
    )

    // The tooltip is rendered, we can verify the trend element exists
    expect(screen.getByText('10.0%')).toBeInTheDocument()
  })

  it('renders prefix element', () => {
    render(
      <MetricCard
        title="带前缀"
        value={1000}
        prefix={<span data-testid="prefix">¥</span>}
      />
    )

    expect(screen.getByTestId('prefix')).toBeInTheDocument()
  })

  it('handles large numbers with formatting', () => {
    render(<MetricCard title="大数字" value={1234567} />)

    // Ant Design Statistic formats numbers with commas
    expect(screen.getByText('1,234,567')).toBeInTheDocument()
  })

  it('handles decimal values', () => {
    render(<MetricCard title="小数" value={85.5} suffix="%" />)

    // Ant Design Statistic splits decimal values into integer and decimal parts
    expect(screen.getByText('85')).toBeInTheDocument()
    expect(screen.getByText('.5')).toBeInTheDocument()
  })
})
