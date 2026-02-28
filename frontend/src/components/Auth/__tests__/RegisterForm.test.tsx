/**
 * RegisterForm Component Tests
 *
 * Tests for registration form rendering, validation, and submission.
 * Validates: Requirements 1.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@/test/test-utils'
import userEvent from '@testing-library/user-event'
import { RegisterForm } from '../RegisterForm'

// Mock authService
const mockRegister = vi.fn()
vi.mock('@/services/auth', () => ({
  authService: {
    register: (...args: unknown[]) => mockRegister(...args),
  },
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'register.usernameRequired': '请输入用户名',
        'register.usernameLength': '用户名长度3-20',
        'register.usernamePattern': '用户名只能包含字母数字下划线',
        'register.usernamePlaceholder': '请输入用户名',
        'register.emailRequired': '请输入邮箱',
        'register.emailInvalid': '邮箱格式不正确',
        'register.emailPlaceholder': '请输入邮箱',
        'register.passwordRequired': '请输入密码',
        'register.passwordLength': '密码至少8位',
        'register.passwordPlaceholder': '请输入密码',
        'register.confirmPasswordRequired': '请确认密码',
        'register.confirmPasswordPlaceholder': '请再次输入密码',
        'register.passwordMismatch': '两次密码不一致',
        'register.tenantType': '组织类型',
        'register.createNewTenant': '创建新组织',
        'register.joinExistingTenant': '加入已有组织',
        'register.tenantNameRequired': '请输入组织名称',
        'register.tenantNameLength': '组织名称2-50字符',
        'register.tenantNamePlaceholder': '请输入组织名称',
        'register.inviteCodeRequired': '请输入邀请码',
        'register.inviteCodePlaceholder': '请输入邀请码',
        'register.agreementRequired': '请同意服务条款',
        'register.agreementText': '我已阅读并同意',
        'register.termsOfService': '服务条款',
        'register.and': '和',
        'register.privacyPolicy': '隐私政策',
        'register.submit': '注册',
        'register.success': '注册成功',
        'register.failed': '注册失败',
      }
      return translations[key] || key
    },
  }),
}))

// Mock antd message
vi.mock('antd', async () => {
  const actual = await vi.importActual('antd')
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
    },
  }
})

import { message } from 'antd'

/** Helper to find the submit button (Ant Design may insert spaces in CJK text) */
const getSubmitButton = () =>
  screen.getByRole('button', { name: /注册|注 册/ })

describe('RegisterForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRegister.mockResolvedValue(undefined)
  })

  it('renders all required form fields', () => {
    render(<RegisterForm />)

    expect(screen.getByPlaceholderText('请输入用户名')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入邮箱')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入密码')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请再次输入密码')).toBeInTheDocument()
    expect(screen.getByText('组织类型')).toBeInTheDocument()
    expect(getSubmitButton()).toBeInTheDocument()
  })

  it('renders agreement checkbox with links', () => {
    render(<RegisterForm />)

    // The agreement text is split across multiple elements (text + links)
    expect(screen.getByText('服务条款')).toBeInTheDocument()
    expect(screen.getByText('隐私政策')).toBeInTheDocument()
    expect(screen.getByRole('checkbox')).toBeInTheDocument()
  })

  it('shows tenant name field by default (create new tenant)', () => {
    render(<RegisterForm />)
    expect(screen.getByPlaceholderText('请输入组织名称')).toBeInTheDocument()
  })

  it('shows validation errors for empty required fields', async () => {
    const user = userEvent.setup()
    render(<RegisterForm />)

    await user.click(getSubmitButton())

    await waitFor(() => {
      expect(screen.getByText('请输入用户名')).toBeInTheDocument()
    })
  })

  it('validates email format', async () => {
    const user = userEvent.setup()
    render(<RegisterForm />)

    await user.type(screen.getByPlaceholderText('请输入邮箱'), 'invalid-email')
    await user.click(getSubmitButton())

    await waitFor(() => {
      expect(screen.getByText('邮箱格式不正确')).toBeInTheDocument()
    })
  })

  it('validates password minimum length', async () => {
    const user = userEvent.setup()
    render(<RegisterForm />)

    await user.type(screen.getByPlaceholderText('请输入密码'), 'short')
    await user.click(getSubmitButton())

    await waitFor(() => {
      expect(screen.getByText('密码至少8位')).toBeInTheDocument()
    })
  })

  it('calls register service and navigates on success', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    render(<RegisterForm onSuccess={onSuccess} />)

    await user.type(screen.getByPlaceholderText('请输入用户名'), 'newuser')
    await user.type(screen.getByPlaceholderText('请输入邮箱'), 'new@example.com')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')
    await user.type(screen.getByPlaceholderText('请再次输入密码'), 'password123')
    await user.type(screen.getByPlaceholderText('请输入组织名称'), 'MyOrg')

    // Check agreement checkbox
    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)

    await user.click(getSubmitButton())

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        username: 'newuser',
        email: 'new@example.com',
        password: 'password123',
        tenant_name: 'MyOrg',
        invite_code: undefined,
      })
    })

    await waitFor(() => {
      expect(message.success).toHaveBeenCalledWith('注册成功')
      expect(onSuccess).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  it('shows error message on registration failure', async () => {
    mockRegister.mockRejectedValueOnce(new Error('Registration failed'))
    const user = userEvent.setup()
    render(<RegisterForm />)

    await user.type(screen.getByPlaceholderText('请输入用户名'), 'newuser')
    await user.type(screen.getByPlaceholderText('请输入邮箱'), 'new@example.com')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')
    await user.type(screen.getByPlaceholderText('请再次输入密码'), 'password123')
    await user.type(screen.getByPlaceholderText('请输入组织名称'), 'MyOrg')

    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)

    await user.click(getSubmitButton())

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('注册失败')
    })
  })

  it('disables submit button while loading', async () => {
    mockRegister.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 200))
    )
    const user = userEvent.setup()
    render(<RegisterForm />)

    await user.type(screen.getByPlaceholderText('请输入用户名'), 'newuser')
    await user.type(screen.getByPlaceholderText('请输入邮箱'), 'new@example.com')
    await user.type(screen.getByPlaceholderText('请输入密码'), 'password123')
    await user.type(screen.getByPlaceholderText('请再次输入密码'), 'password123')
    await user.type(screen.getByPlaceholderText('请输入组织名称'), 'MyOrg')

    const checkbox = screen.getByRole('checkbox')
    await user.click(checkbox)

    await user.click(getSubmitButton())

    await waitFor(() => {
      const button = screen.getByRole('button')
      expect(button).toHaveClass('ant-btn-loading')
    })
  })
})
