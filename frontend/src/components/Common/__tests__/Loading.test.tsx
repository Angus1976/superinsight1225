/**
 * Loading Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Loading } from '../Loading'

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

describe('Loading', () => {
  it('renders spinning indicator by default', () => {
    const { container } = render(<Loading />)

    // Ant Design Spin component should be present
    expect(container.querySelector('.ant-spin')).toBeInTheDocument()
  })

  it('renders with custom tip text', () => {
    const { container } = render(<Loading tip="加载中..." />)

    // The Spin component should be present with the tip
    expect(container.querySelector('.ant-spin')).toBeInTheDocument()
    expect(container.querySelector('.ant-spin-show-text')).toBeInTheDocument()
  })

  it('renders fullscreen loading', () => {
    const { container } = render(<Loading fullScreen />)

    // Should have fixed positioning for fullscreen
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveStyle({
      position: 'fixed',
    })
  })

  it('renders non-fullscreen loading with flex centering', () => {
    const { container } = render(<Loading />)

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveStyle({
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    })
  })
})
