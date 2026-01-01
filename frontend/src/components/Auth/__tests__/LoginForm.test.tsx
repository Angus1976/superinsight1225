/**
 * LoginForm Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { LoginForm } from '../LoginForm'

// Mock useAuth hook
const mockLogin = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    isLoading: false,
  }),
}))

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'login.usernamePlaceholder': '请输入用户名',
        'login.passwordPlaceholder': '请输入密码',
        'login.rememberMe': '记住我',
        'login.forgotPassword': '忘记密码',
        'login.submit': '登录',
      }
      return translations[key] || key
    },
  }),
}))

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form with all required elements', () => {
    render(<LoginForm />)

    // Check for username input
    expect(screen.getByPlaceholderText('请输入用户名')).toBeInTheDocument()

    // Check for password input
    expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument()

    // Check for remember me checkbox
    expect(screen.getByText('记住我')).toBeInTheDocument()

    // Check for forgot password link
    expect(screen.getByText('忘记密码')).toBeInTheDocument()

    // Check for submit button
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
  })

  it('shows validation errors when submitting empty form', async () => {
    const user = userEvent.setup()
    render(<LoginForm />)

    // Click submit button without filling form
    await user.click(screen.getByRole('button', { name: '登录' }))

    // Wait for validation messages
    await waitFor(() => {
      expect(screen.getByText('请输入用户名')).toBeInTheDocument()
    })
  })

  it('calls login function with correct credentials on submit', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    mockLogin.mockResolvedValueOnce(undefined)

    render(<LoginForm onSuccess={onSuccess} />)

    // Fill in the form
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'testuser')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')

    // Submit the form
    await user.click(screen.getByRole('button', { name: '登录' }))

    // Wait for login to be called
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        remember: true,
      })
    })
  })

  it('calls onSuccess callback after successful login', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    mockLogin.mockResolvedValueOnce(undefined)

    render(<LoginForm onSuccess={onSuccess} />)

    // Fill and submit form
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'testuser')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')
    await user.click(screen.getByRole('button', { name: '登录' }))

    // Wait for success callback
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled()
    })
  })

  it('handles login error gracefully', async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))

    render(<LoginForm />)

    // Fill and submit form
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'wronguser')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'wrongpass')
    await user.click(screen.getByRole('button', { name: '登录' }))

    // Login should be called
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled()
    })

    // Button should not be in loading state after error
    await waitFor(() => {
      const button = screen.getByRole('button', { name: '登录' })
      expect(button).not.toBeDisabled()
    })
  })

  it('disables submit button while loading', async () => {
    const user = userEvent.setup()
    // Make login take some time
    mockLogin.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    )

    render(<LoginForm />)

    // Fill and submit form
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'testuser')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')
    await user.click(screen.getByRole('button', { name: '登录' }))

    // Button should be loading
    await waitFor(() => {
      const button = screen.getByRole('button')
      expect(button).toHaveClass('ant-btn-loading')
    })
  })

  it('has correct forgot password link', () => {
    render(<LoginForm />)

    const forgotLink = screen.getByText('忘记密码')
    expect(forgotLink).toHaveAttribute('href', '/forgot-password')
  })

  it('remember me checkbox is checked by default', () => {
    render(<LoginForm />)

    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeChecked()
  })

  it('can uncheck remember me checkbox', async () => {
    const user = userEvent.setup()
    render(<LoginForm />)

    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)

    expect(checkbox).not.toBeChecked()
  })
})
