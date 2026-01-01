/**
 * Loading Component Tests
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Loading } from '../Loading'

describe('Loading', () => {
  it('renders spinning indicator by default', () => {
    const { container } = render(<Loading />)

    // Ant Design Spin component should be present
    expect(container.querySelector('.ant-spin')).toBeInTheDocument()
    expect(container.querySelector('.ant-spin-spinning')).toBeInTheDocument()
  })

  it('renders with custom tip text', () => {
    render(<Loading tip="加载中..." />)

    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('renders with default size', () => {
    const { container } = render(<Loading />)

    // Default should not have specific size class (default is small)
    const spin = container.querySelector('.ant-spin')
    expect(spin).toBeInTheDocument()
  })

  it('renders with large size', () => {
    const { container } = render(<Loading size="large" />)

    expect(container.querySelector('.ant-spin-lg')).toBeInTheDocument()
  })

  it('renders with small size', () => {
    const { container } = render(<Loading size="small" />)

    expect(container.querySelector('.ant-spin-sm')).toBeInTheDocument()
  })

  it('renders fullscreen loading', () => {
    const { container } = render(<Loading fullscreen />)

    // Should have center positioning
    const wrapper = container.firstChild
    expect(wrapper).toHaveStyle({
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
    })
  })

  it('applies custom className', () => {
    const { container } = render(<Loading className="custom-loading" />)

    expect(container.querySelector('.custom-loading')).toBeInTheDocument()
  })

  it('renders children when not loading', () => {
    render(
      <Loading spinning={false}>
        <div data-testid="child-content">内容</div>
      </Loading>
    )

    expect(screen.getByTestId('child-content')).toBeInTheDocument()
  })

  it('wraps children when loading', () => {
    const { container } = render(
      <Loading spinning={true}>
        <div data-testid="child-content">内容</div>
      </Loading>
    )

    // The nested content should be wrapped by spin
    expect(container.querySelector('.ant-spin-nested-loading')).toBeInTheDocument()
    expect(screen.getByTestId('child-content')).toBeInTheDocument()
  })
})
