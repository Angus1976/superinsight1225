/**
 * Frontend Test Utilities
 *
 * Comprehensive testing utilities for React components including:
 * - Component rendering with providers
 * - Mock API response factories
 * - User event simulation helpers
 * - Test router and navigation utilities
 */

import React, { ReactElement, ReactNode } from 'react'
import { render, RenderOptions, RenderResult, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, MemoryRouter, Routes, Route, useNavigate, useLocation, NavigateFunction, Location } from 'react-router-dom'
import { QueryClient, QueryClientProvider, UseQueryResult } from '@tanstack/react-query'
import { ConfigProvider, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import enUS from 'antd/locale/en_US'
import i18n from 'i18next'
import { I18nextProvider, initReactI18next } from 'react-i18next'
import userEvent, { UserEvent } from '@testing-library/user-event'
import { vi, Mock } from 'vitest'

// ============================================================================
// Query Client Factory
// ============================================================================

/**
 * Creates a QueryClient configured for testing
 * - Disables retries for faster tests
 * - Sets short cache times to avoid stale data
 */
export const createTestQueryClient = (options?: { defaultOptions?: QueryClient['defaultOptions'] }): QueryClient => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
        networkMode: 'offlineFirst',
        ...options?.defaultOptions?.queries,
      },
      mutations: {
        retry: false,
        networkMode: 'offlineFirst',
        ...options?.defaultOptions?.mutations,
      },
    },
  })
}

// ============================================================================
// Provider Components
// ============================================================================

interface ProvidersProps {
  children: ReactNode
  queryClient?: QueryClient
  locale?: 'zh-CN' | 'en-US'
  initialRoute?: string
}

const TestProvidersComponent: React.FC<ProvidersProps> = ({
  children,
  queryClient,
  locale = 'zh-CN',
}) => {
  const client = queryClient ?? createTestQueryClient()
  const antLocale = locale === 'zh-CN' ? zhCN : enUS

  return (
    <QueryClientProvider client={client}>
      <ConfigProvider locale={antLocale}>
        <AntApp>
          <BrowserRouter>{children}</BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  )
}

// ============================================================================
// Memory Router Provider for route testing
// ============================================================================

interface MemoryRouterProviderProps {
  children: ReactNode
  initialEntries?: string[]
  initialIndex?: number
}

/**
 * Memory Router Provider - use this instead of TestProvidersComponent when testing routes
 * Note: This component does NOT include BrowserRouter to avoid nested router issues
 */
export const MemoryRouterProvider: React.FC<MemoryRouterProviderProps> = ({
  children,
  initialEntries = ['/'],
}) => {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <QueryClientProvider client={createTestQueryClient()}>
        <ConfigProvider locale={zhCN}>
          <AntApp>{children}</AntApp>
        </ConfigProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
}

// ============================================================================
// Custom Render Functions
// ============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient
  locale?: 'zh-CN' | 'en-US'
  route?: string
}

/**
 * Custom render function with all providers configured
 */
export const renderWithProviders = (
  ui: ReactElement,
  options?: CustomRenderOptions
): RenderResult => {
  const { queryClient, locale, route, ...renderOptions } = options ?? {}

  const Wrapper: React.FC<{ children: ReactNode }> = ({ children }) => {
    if (route) {
      return (
        <MemoryRouter initialEntries={[route]}>
          <TestProvidersComponent queryClient={queryClient} locale={locale}>
            {children}
          </TestProvidersComponent>
        </MemoryRouter>
      )
    }
    return (
      <TestProvidersComponent queryClient={queryClient} locale={locale}>
        {children}
      </TestProvidersComponent>
    )
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

/**
 * Render with specific route using MemoryRouter
 * Note: This function does NOT use TestProvidersComponent to avoid nested router issues
 */
export const renderWithRoute = (
  ui: ReactElement,
  route: string,
  options?: Omit<CustomRenderOptions, 'route'>
): RenderResult => {
  const { queryClient, locale = 'zh-CN' } = options ?? {}
  const client = queryClient ?? createTestQueryClient()
  const antLocale = locale === 'zh-CN' ? zhCN : enUS

  return render(
    <MemoryRouter initialEntries={[route]}>
      <QueryClientProvider client={client}>
        <ConfigProvider locale={antLocale}>
          <AntApp>{ui}</AntApp>
        </ConfigProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
}

/**
 * Render with multiple routes for navigation testing
 */
export const renderWithRoutes = (
  ui: ReactElement,
  routes: { path: string; element: ReactElement }[],
  options?: Omit<CustomRenderOptions, 'route'>
): RenderResult => {
  const Wrapper: React.FC<{ children: ReactNode }> = ({ children }) => (
    <TestProvidersComponent {...options}>
      <BrowserRouter>
        <Routes>
          {routes.map((r) => (
            <Route key={r.path} path={r.path} element={r.element} />
          ))}
        </Routes>
      </BrowserRouter>
    </TestProvidersComponent>
  )

  return render(ui, { wrapper: Wrapper, ...options })
}

// ============================================================================
// Mock API Response Factories
// ============================================================================

/**
 * Generic API response factory
 */
export interface ApiResponse<T> {
  data: T
  status: number
  statusText: string
  headers: Record<string, string>
}

export const createApiResponse = <T,>(
  data: T,
  status = 200,
  statusText = 'OK'
): ApiResponse<T> => ({
  data,
  status,
  statusText,
  headers: {
    'content-type': 'application/json',
  },
})

/**
 * Paginated response factory
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export const createPaginatedResponse = <T,>(
  items: T[],
  total: number,
  page = 1,
  pageSize = 20
): PaginatedResponse<T> => ({
  items,
  total,
  page,
  pageSize,
  totalPages: Math.ceil(total / pageSize),
})

/**
 * Error response factory
 */
export interface ErrorResponse {
  code: string
  message: string
  details?: Record<string, unknown>
}

export const createErrorResponse = (
  code: string,
  message: string,
  details?: Record<string, unknown>
): ErrorResponse => ({
  code,
  message,
  details,
})

// ============================================================================
// Mock Data Factories
// ============================================================================

/**
 * User factory for testing
 */
export interface MockUser {
  id: string
  username: string
  email: string
  name: string
  avatar?: string
  tenantId: string
  tenantName: string
  roles: string[]
  permissions: string[]
  createdAt: string
  updatedAt: string
}

export const createMockUser = (overrides?: Partial<MockUser>): MockUser => ({
  id: 'user-1',
  username: 'testuser',
  email: 'test@example.com',
  name: '测试用户',
  avatar: undefined,
  tenantId: 'tenant-1',
  tenantName: '测试租户',
  roles: ['user'],
  permissions: ['read:tasks', 'write:tasks'],
  createdAt: '2025-01-01T00:00:00.000Z',
  updatedAt: '2025-01-01T00:00:00.000Z',
  ...overrides,
})

/**
 * Task factory for testing
 */
export interface MockTask {
  id: string
  name: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  assignee?: string
  assigneeName?: string
  projectId: string
  projectName: string
  dueDate?: string
  createdAt: string
  updatedAt: string
}

export const createMockTask = (overrides?: Partial<MockTask>): MockTask => ({
  id: 'task-1',
  name: '测试任务',
  description: '任务描述',
  status: 'pending',
  priority: 'medium',
  assignee: 'user-1',
  assigneeName: '测试用户',
  projectId: 'project-1',
  projectName: '测试项目',
  dueDate: undefined,
  createdAt: '2025-01-01T00:00:00.000Z',
  updatedAt: '2025-01-01T00:00:00.000Z',
  ...overrides,
})

/**
 * Annotation factory for testing
 */
export interface MockAnnotation {
  id: string
  taskId: string
  taskName: string
  data: Record<string, unknown>
  labels: MockLabel[]
  status: 'draft' | 'submitted' | 'reviewed' | 'approved' | 'rejected'
  annotatorId: string
  annotatorName: string
  reviewerId?: string
  reviewerName?: string
  createdAt: string
  updatedAt: string
}

export interface MockLabel {
  id: string
  name: string
  color: string
  value: string
}

export const createMockAnnotation = (overrides?: Partial<MockAnnotation>): MockAnnotation => ({
  id: 'annotation-1',
  taskId: 'task-1',
  taskName: '测试任务',
  data: { text: '测试文本', sentiment: 'positive' },
  labels: [
    { id: 'label-1', name: '正面', color: '#52c41a', value: 'positive' },
  ],
  status: 'draft',
  annotatorId: 'user-1',
  annotatorName: '测试用户',
  reviewerId: undefined,
  reviewerName: undefined,
  createdAt: '2025-01-01T00:00:00.000Z',
  updatedAt: '2025-01-01T00:00:00.000Z',
  ...overrides,
})

/**
 * Dataset factory for testing
 */
export interface MockDataset {
  id: string
  name: string
  description?: string
  type: 'text' | 'image' | 'audio' | 'video' | 'mixed'
  size: number
  itemCount: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  projectId: string
  createdAt: string
  updatedAt: string
}

export const createMockDataset = (overrides?: Partial<MockDataset>): MockDataset => ({
  id: 'dataset-1',
  name: '测试数据集',
  description: '数据集描述',
  type: 'text',
  size: 1024000,
  itemCount: 1000,
  status: 'completed',
  projectId: 'project-1',
  createdAt: '2025-01-01T00:00:00.000Z',
  updatedAt: '2025-01-01T00:00:00.000Z',
  ...overrides,
})

/**
 * Project factory for testing
 */
export interface MockProject {
  id: string
  name: string
  description?: string
  status: 'active' | 'completed' | 'archived'
  memberCount: number
  taskCount: number
  createdAt: string
  updatedAt: string
}

export const createMockProject = (overrides?: Partial<MockProject>): MockProject => ({
  id: 'project-1',
  name: '测试项目',
  description: '项目描述',
  status: 'active',
  memberCount: 5,
  taskCount: 100,
  createdAt: '2025-01-01T00:00:00.000Z',
  updatedAt: '2025-01-01T00:00:00.000Z',
  ...overrides,
})

// ============================================================================
// Mock API Service
// ============================================================================

/**
 * Mock API service for intercepting requests
 */
export class MockApiService {
  private handlers: Map<string, (params?: unknown) => unknown> = new Map()

  /**
   * Register a mock handler for a specific endpoint
   */
  mockGet<T>(url: string, response: T): void {
    this.handlers.set(`GET:${url}`, () => response)
  }

  mockPost<T>(url: string, response: T): void {
    this.handlers.set(`POST:${url}`, () => response)
  }

  mockPut<T>(url: string, response: T): void {
    this.handlers.set(`PUT:${url}`, () => response)
  }

  mockPatch<T>(url: string, response: T): void {
    this.handlers.set(`PATCH:${url}`, () => response)
  }

  mockDelete(url: string, response = { success: true }): void {
    this.handlers.set(`DELETE:${url}`, () => response)
  }

  /**
   * Get a mock handler
   */
  getHandler(method: string, url: string): ((params?: unknown) => unknown) | undefined {
    return this.handlers.get(`${method}:${url}`)
  }

  /**
   * Clear all handlers
   */
  clear(): void {
    this.handlers.clear()
  }
}

// Global mock API instance
export const mockApi = new MockApiService()

// ============================================================================
// User Event Helpers
// ============================================================================

/**
 * Extended user event utilities for complex interactions
 */
export interface UserEventHelpers {
  click: (element: HTMLElement) => Promise<void>
  doubleClick: (element: HTMLElement) => Promise<void>
  rightClick: (element: HTMLElement) => Promise<void>
  hover: (element: HTMLElement) => Promise<void>
  unhover: (element: HTMLElement) => Promise<void>
  type: (element: HTMLElement, text: string) => Promise<void>
  clear: (element: HTMLElement) => Promise<void>
  paste: (element: HTMLElement, text: string) => Promise<void>
  selectOptions: (element: HTMLElement, values: string | string[]) => Promise<void>
  deselectOptions: (element: HTMLElement, values: string | string[]) => Promise<void>
  upload: (element: HTMLElement, files: File[]) => Promise<void>
  drag: (element: HTMLElement, target: HTMLElement) => Promise<void>
  scroll: (element: HTMLElement, options?: { scrollX?: number; scrollY?: number }) => Promise<void>
  keyboard: (text: string) => Promise<void>
  tab: () => Promise<void>
}

export const createUserEventHelpers = (user: UserEvent): UserEventHelpers => ({
  click: (element) => user.click(element),
  doubleClick: (element) => user.dblClick(element),
  rightClick: (element) => user.pointer({ keys: '[MouseRight]', target: element }),
  hover: (element) => user.hover(element),
  unhover: (element) => user.unhover(element),
  type: (element, text) => user.type(element, text),
  clear: (element) => user.clear(element),
  paste: (element, text) => user.paste(element, text),
  selectOptions: (element, values) => user.selectOptions(element, values),
  deselectOptions: (element, values) => user.deselectOptions(element, values),
  upload: (element, files) => user.upload(element, files),
  drag: async (element, target) => {
    await user.pointer({
      keys: '[MouseLeft][MouseLeft]',
      target: element,
    })
    await user.pointer({ target })
  },
  scroll: async (element, options) => {
    element.scrollTo(options?.scrollX ?? 0, options?.scrollY ?? 0)
  },
  keyboard: (text) => user.keyboard(text),
  tab: () => user.tab(),
})

/**
 * Get user event instance with helpers
 */
export const getUserEvent = (): UserEventHelpers => {
  const user = userEvent.setup()
  return createUserEventHelpers(user)
}

// ============================================================================
// Form Testing Helpers
// ============================================================================

/**
 * Form testing utilities
 */
export interface FormTestingHelpers {
  click: (element: HTMLElement) => Promise<void>
  fillTextInput: (name: string, value: string) => Promise<void>
  fillTextarea: (name: string, value: string) => Promise<void>
  fillNumberInput: (name: string, value: number) => Promise<void>
  selectDropdown: (name: string, value: string) => Promise<void>
  selectMultiple: (name: string, values: string[]) => Promise<void>
  checkCheckbox: (name: string, checked?: boolean) => Promise<void>
  checkRadio: (name: string, value: string) => Promise<void>
  uploadFile: (name: string, files: File[]) => Promise<void>
  fillDatePicker: (name: string, date: string) => Promise<void>
  fillTimePicker: (name: string, time: string) => Promise<void>
  submitForm: (buttonText?: string) => Promise<void>
  resetForm: (buttonText?: string) => Promise<void>
}

export const createFormTestingHelpers = (user: UserEvent): FormTestingHelpers => ({
  async click(element) {
    await user.click(element)
  },

  async fillTextInput(name, value) {
    const input = screen.getByRole('textbox', { name: new RegExp(name, 'i') })
    await user.clear(input)
    await user.type(input, value)
  },

  async fillTextarea(name, value) {
    const textarea = screen.getByRole('textbox', { name: new RegExp(name, 'i') })
    await user.clear(textarea)
    await user.type(textarea, value)
  },

  async fillNumberInput(name, value) {
    const input = screen.getByRole('spinbutton', { name: new RegExp(name, 'i') })
    await user.clear(input)
    await user.type(input, String(value))
  },

  async selectDropdown(name, value) {
    const select = screen.getByRole('combobox', { name: new RegExp(name, 'i') })
    await user.selectOptions(select, value)
  },

  async selectMultiple(name, values) {
    const select = screen.getByRole('listbox', { name: new RegExp(name, 'i') })
    for (const value of values) {
      await user.selectOptions(select, value)
    }
  },

  async checkCheckbox(name, checked = true) {
    const checkbox = screen.getByRole('checkbox', { name: new RegExp(name, 'i') })
    if (checked && !checkbox.hasAttribute('checked')) {
      await user.click(checkbox)
    } else if (!checked && checkbox.hasAttribute('checked')) {
      await user.click(checkbox)
    }
  },

  async checkRadio(name, value) {
    const radio = screen.getByRole('radio', { name: new RegExp(value, 'i') })
    await user.click(radio)
  },

  async uploadFile(name, files) {
    const input = screen.getByRole('button', { name: new RegExp(name, 'i') })
      .closest('input[type="file"]') || screen.getByLabelText(new RegExp(name, 'i')).closest('input[type="file"]')
    await user.upload(input!, files)
  },

  async fillDatePicker(name, date) {
    const picker = screen.getByRole('textbox', { name: new RegExp(name, 'i') })
    await user.clear(picker)
    await user.type(picker, date)
    await user.keyboard('{Enter}')
  },

  async fillTimePicker(name, time) {
    const picker = screen.getByRole('textbox', { name: new RegExp(name, 'i') })
    await user.clear(picker)
    await user.type(picker, time)
  },

  async submitForm(buttonText = '提交') {
    const submitButton = screen.getByRole('button', { name: new RegExp(buttonText, 'i') })
    await user.click(submitButton)
  },

  async resetForm(buttonText = '重置') {
    const resetButton = screen.getByRole('button', { name: new RegExp(buttonText, 'i') })
    await user.click(resetButton)
  },
})

// ============================================================================
// Async Testing Helpers
// ============================================================================

/**
 * Wait for element to appear with timeout
 */
export const waitForElement = async <T extends HTMLElement>(
  callback: () => T | null,
  options?: { timeout?: number; interval?: number }
): Promise<T> => {
  return waitFor(callback, {
    timeout: options?.timeout ?? 5000,
    interval: options?.interval ?? 100,
  })
}

/**
 * Wait for element to disappear
 */
export const waitForElementToDisappear = async (
  callback: () => HTMLElement | null,
  options?: { timeout?: number; interval?: number }
): Promise<void> => {
  await waitFor(() => {
    expect(callback()).not.toBeInTheDocument()
  }, {
    timeout: options?.timeout ?? 5000,
    interval: options?.interval ?? 100,
  })
}

/**
 * Wait for loading state to finish
 */
export const waitForLoading = async (loadingText = '加载中'): Promise<void> => {
  await waitForElementToDisappear(
    () => screen.queryByText(new RegExp(loadingText, 'i')) as HTMLElement
  )
}

/**
 * Wait for API call to complete
 */
export const waitForApiCall = async (): Promise<void> => {
  await new Promise(resolve => setTimeout(resolve, 0))
}

// ============================================================================
// Navigation Testing Utilities
// ============================================================================

/**
 * Test navigation utilities
 */
export interface NavigationTestingHelpers {
  navigateTo: (path: string) => Promise<void>
  goBack: () => Promise<void>
  goForward: () => Promise<void>
  getCurrentPath: () => string
  getCurrentSearch: () => string
  expectCurrentPath: (path: string) => void
  expectCurrentSearch: (search: string) => void
}

export const createNavigationHelpers = (): NavigationTestingHelpers => {
  let navigateFn: NavigateFunction | null = null
  let currentPath = '/'
  let currentSearch = ''

  const TestNavigationComponent: React.FC<{ children: ReactNode }> = ({ children }) => {
    const navigate = useNavigate()
    const location = useLocation()
    navigateFn = navigate
    currentPath = location.pathname
    currentSearch = location.search
    return <>{children}</>
  }

  return {
    async navigateTo(path) {
      if (navigateFn) {
        await navigateFn(path)
      }
    },
    async goBack() {
      if (navigateFn) {
        await navigateFn(-1)
      }
    },
    async goForward() {
      if (navigateFn) {
        await navigateFn(1)
      }
    },
    getCurrentPath() {
      return currentPath
    },
    getCurrentSearch() {
      return currentSearch
    },
    expectCurrentPath(path) {
      expect(currentPath).toBe(path)
    },
    expectCurrentSearch(search) {
      expect(currentSearch).toBe(search)
    },
  }
}

// ============================================================================
// Mock Router Component
// ============================================================================

/**
 * Mock router for testing components that use routing
 */
export interface MockRouterOptions {
  initialPath?: string
  routes?: { path: string; element: ReactElement }[]
  navigate?: (path: string) => void
}

export const createMockRouter = (options?: MockRouterOptions) => {
  const { initialPath = '/', routes = [] } = options ?? {}

  return {
    MemoryRouter,
    initialEntries: [initialPath],
    routes,
    useNavigate: () => options?.navigate ?? vi.fn(),
    useLocation: () => ({ pathname: initialPath, search: '', hash: '', state: null, key: 'default' }),
    useParams: () => ({}),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  }
}

// ============================================================================
// Query Testing Utilities
// ============================================================================

/**
 * Wait for query to complete and return data
 */
export const waitForQuery = async <T,>(
  queryFn: () => UseQueryResult<T, unknown>
): Promise<T> => {
  const query = queryFn()

  if (query.isSuccess) {
    return query.data
  }

  if (query.isError) {
    throw query.error
  }

  await waitFor(() => {
    expect(query.isSuccess).toBe(true)
  })

  return query.data!
}

/**
 * Wait for query to be in loading state
 */
export const waitForQueryLoading = async <T,>(
  queryFn: () => UseQueryResult<T, unknown>
): Promise<void> => {
  const query = queryFn()
  await waitFor(() => {
    expect(query.isLoading).toBe(true)
  })
}

// ============================================================================
// Assertion Helpers
// ============================================================================

/**
 * Common assertion helpers for testing
 */
export const assertions = {
  toBeVisible: (element: HTMLElement) => expect(element).toBeVisible(),
  toBeHidden: (element: HTMLElement) => expect(element).not.toBeVisible(),
  toBeEnabled: (element: HTMLElement) => expect(element).toBeEnabled(),
  toBeDisabled: (element: HTMLElement) => expect(element).toBeDisabled(),
  toHaveText: (element: HTMLElement, text: string) => expect(element).toHaveTextContent(text),
  toHaveValue: (element: HTMLInputElement, value: string | number) => expect(element).toHaveValue(value),
  toBeChecked: (element: HTMLInputElement) => expect(element).toBeChecked(),
  toNotBeChecked: (element: HTMLInputElement) => expect(element).not.toBeChecked(),
  toHaveAttribute: (element: HTMLElement, attr: string, value?: string) =>
    value ? expect(element).toHaveAttribute(attr, value) : expect(element).toHaveAttribute(attr),
  toHaveClass: (element: HTMLElement, className: string) => expect(element).toHaveClass(className),
  toContainElement: (parent: HTMLElement, child: HTMLElement) => expect(parent).toContainElement(child),
}

// ============================================================================
// Re-exports
// ============================================================================

export { userEvent }
export { render, screen, waitFor }
export type { RenderResult }