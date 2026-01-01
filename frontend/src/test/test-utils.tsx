/**
 * Test Utilities
 *
 * Custom render function and utilities for testing React components.
 */

import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'

// Create a custom QueryClient for tests
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

// All providers wrapper
interface AllProvidersProps {
  children: React.ReactNode
}

const AllProviders: React.FC<AllProvidersProps> = ({ children }) => {
  const queryClient = createTestQueryClient()

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <BrowserRouter>{children}</BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  )
}

// Custom render function
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllProviders, ...options })

// Re-export everything from testing-library
export * from '@testing-library/react'
export { userEvent } from '@testing-library/user-event'

// Override render method
export { customRender as render }

// Helper to create mock API responses
export const createMockResponse = <T,>(data: T, status = 200) => ({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {},
})

// Helper to wait for loading to finish
export const waitForLoadingToFinish = () =>
  new Promise((resolve) => setTimeout(resolve, 0))

// Mock user data
export const mockUser = {
  id: 'user-1',
  username: 'testuser',
  email: 'test@example.com',
  name: '测试用户',
  tenantId: 'tenant-1',
  tenantName: '测试租户',
  roles: ['user'],
  permissions: ['read:tasks', 'write:tasks'],
}

// Mock auth token
export const mockToken = 'mock-jwt-token-for-testing'

// Mock tenant data
export const mockTenant = {
  id: 'tenant-1',
  name: '测试租户',
  code: 'TEST',
  status: 'active',
}

// Mock task data
export const mockTask = {
  id: 'task-1',
  name: '测试任务',
  description: '这是一个测试任务',
  status: 'in_progress',
  priority: 'medium',
  assignee: 'user-1',
  createdAt: '2025-01-01T00:00:00Z',
  updatedAt: '2025-01-01T00:00:00Z',
}

// Mock billing data
export const mockBill = {
  id: 'bill-1',
  tenantId: 'tenant-1',
  period: '2024-12',
  totalAmount: 12500.00,
  status: 'pending',
  createdAt: '2025-01-01T00:00:00Z',
}
