/**
 * LoginForm Component Tests
 * 
 * Tests to ensure the existing login experience is preserved
 * while supporting multi-tenant features.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { LoginForm } from '../LoginForm'

// Create persistent mock functions
const mockLogin = vi.fn()
const mockGetTenants = vi.fn()

// Mock authService
vi.mock('@/services/auth', () => ({
  authService: {
    getTenants: () => mockGetTenants(),
  },
}))

// Mock useAuth hook with persistent mock
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
        'tenant.select': '选择租户',
        'tenant.selectRequired': '请选择租户',
        'tenant.selectPlaceholder': '请选择您的组织',
      }
      return translations[key] || key
    },
  }),
}))

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock empty tenants by default
    mockGetTenants.mockResolvedValue([])
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

    // Check for submit button (use more flexible selector)
    expect(screen.getByRole('button', { name: /登录|登 录/ })).toBeInTheDocument()
  })

  it('shows tenant selection when tenants are available', async () => {
    const mockTenants = [
      { id: 'tenant1', name: 'Organization 1' },
      { id: 'tenant2', name: 'Organization 2' },
    ]
    mockGetTenants.mockResolvedValue(mockTenants)

    render(<LoginForm />)

    // Wait for tenants to load and tenant selector to appear
    await waitFor(() => {
      expect(screen.getByText('选择租户')).toBeInTheDocument()
    })

    // Check tenant selector is present
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('does not show tenant selection when no tenants available', () => {
    mockGetTenants.mockResolvedValue([])
    
    render(<LoginForm />)

    // Tenant selector should not be present
    expect(screen.queryByText('选择租户')).not.toBeInTheDocument()
  })

  it('shows validation errors when submitting empty form', async () => {
    const user = userEvent.setup()
    render(<LoginForm />)

    // Click submit button without filling form
    await user.click(screen.getByRole('button', { name: /登录|登 录/ }))

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
    await user.click(screen.getByRole('button', { name: /登录|登 录/ }))

    // Wait for login to be called
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
      })
    })
  })

  it('calls login function with tenant_id when tenant is selected', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    const mockTenants = [
      { id: 'tenant1', name: 'Organization 1' },
      { id: 'tenant2', name: 'Organization 2' },
    ]
    mockGetTenants.mockResolvedValue(mockTenants)
    mockLogin.mockResolvedValueOnce(undefined)

    render(<LoginForm onSuccess={onSuccess} />)

    // Wait for tenants to load
    await waitFor(() => {
      expect(screen.getByText('选择租户')).toBeInTheDocument()
    })

    // Fill in the form
    await user.type(screen.getByPlaceholderText('请输入用户名'), 'testuser')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')
    
    // Select a tenant
    await user.click(screen.getByRole('combobox'))
    await user.click(screen.getByText('Organization 1'))

    // Submit the form
    await user.click(screen.getByRole('button', { name: /登录|登 录/ }))

    // Wait for login to be called with tenant_id
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
        tenant_id: 'tenant1',
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
    await user.click(screen.getByRole('button', { name: /登录|登 录/ }))

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
    await user.click(screen.getByRole('button', { name: /登录|登 录/ }))

    // Login should be called
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled()
    })

    // Button should not be in loading state after error
    await waitFor(() => {
      const button = screen.getByRole('button', { name: /登录|登 录/ })
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
    await user.click(screen.getByRole('button', { name: /登录|登 录/ }))

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