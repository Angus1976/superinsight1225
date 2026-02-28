/**
 * Test Utilities Verification Tests
 *
 * Tests to verify the frontend test utilities work correctly.
 */

import React, { useState } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import {
  renderWithProviders,
  renderWithRoute,
  createMockUser,
  createMockTask,
  createMockAnnotation,
  createMockDataset,
  createMockProject,
  createApiResponse,
  createPaginatedResponse,
  createErrorResponse,
  createTestQueryClient,
  getUserEvent,
  createFormTestingHelpers,
  waitForLoading,
  assertions,
} from '@/test/test-utilities'

// ============================================================================
// Mock Components for Testing
// ============================================================================

const TestComponent: React.FC = () => {
  const [text, setText] = useState('')
  const [count, setCount] = useState(0)
  const [selected, setSelected] = useState<string>('')
  const [isChecked, setIsChecked] = useState(false)

  return (
    <div>
      <h1>测试组件</h1>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="输入文本"
        aria-label="文本输入"
      />
      <button onClick={() => setCount(count + 1)}>计数: {count}</button>
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        aria-label="选择框"
      >
        <option value="">请选择</option>
        <option value="a">选项 A</option>
        <option value="b">选项 B</option>
      </select>
      <label>
        <input
          type="checkbox"
          checked={isChecked}
          onChange={(e) => setIsChecked(e.target.checked)}
        />
        复选框
      </label>
    </div>
  )
}

const RouteComponent: React.FC = () => <div>路由页面</div>

// ============================================================================
// Render Tests
// ============================================================================

describe('renderWithProviders', () => {
  it('should render component with all providers', () => {
    renderWithProviders(<TestComponent />)
    expect(screen.getByText('测试组件')).toBeInTheDocument()
  })

  it('should render with custom query client', () => {
    const queryClient = createTestQueryClient()
    renderWithProviders(<TestComponent />, { queryClient })
    expect(screen.getByText('测试组件')).toBeInTheDocument()
  })

  it('should render with different locale', () => {
    renderWithProviders(<TestComponent />, { locale: 'en-US' })
    expect(screen.getByText('测试组件')).toBeInTheDocument()
  })
})

describe('renderWithRoute', () => {
  it('should render component with specific route', () => {
    renderWithRoute(<RouteComponent />, '/test-route')
    expect(screen.getByText('路由页面')).toBeInTheDocument()
  })
})

// ============================================================================
// Mock Data Factory Tests
// ============================================================================

describe('createMockUser', () => {
  it('should create user with default values', () => {
    const user = createMockUser()
    expect(user.id).toBe('user-1')
    expect(user.username).toBe('testuser')
    expect(user.email).toBe('test@example.com')
    expect(user.roles).toContain('user')
  })

  it('should override values with provided options', () => {
    const user = createMockUser({ username: 'custom', roles: ['admin'] })
    expect(user.username).toBe('custom')
    expect(user.roles).toEqual(['admin'])
  })
})

describe('createMockTask', () => {
  it('should create task with default values', () => {
    const task = createMockTask()
    expect(task.id).toBe('task-1')
    expect(task.status).toBe('pending')
    expect(task.priority).toBe('medium')
  })

  it('should override values with provided options', () => {
    const task = createMockTask({ status: 'completed', priority: 'high' })
    expect(task.status).toBe('completed')
    expect(task.priority).toBe('high')
  })
})

describe('createMockAnnotation', () => {
  it('should create annotation with default values', () => {
    const annotation = createMockAnnotation()
    expect(annotation.id).toBe('annotation-1')
    expect(annotation.status).toBe('draft')
    expect(annotation.labels).toHaveLength(1)
  })
})

describe('createMockDataset', () => {
  it('should create dataset with default values', () => {
    const dataset = createMockDataset()
    expect(dataset.id).toBe('dataset-1')
    expect(dataset.type).toBe('text')
    expect(dataset.status).toBe('completed')
  })
})

describe('createMockProject', () => {
  it('should create project with default values', () => {
    const project = createMockProject()
    expect(project.id).toBe('project-1')
    expect(project.status).toBe('active')
  })
})

// ============================================================================
// API Response Factory Tests
// ============================================================================

describe('createApiResponse', () => {
  it('should create API response with default values', () => {
    const response = createApiResponse({ data: 'test' })
    expect(response.data).toEqual({ data: 'test' })
    expect(response.status).toBe(200)
    expect(response.statusText).toBe('OK')
  })

  it('should create API response with custom status', () => {
    const response = createApiResponse({ error: true }, 404, 'Not Found')
    expect(response.status).toBe(404)
    expect(response.statusText).toBe('Not Found')
  })
})

describe('createPaginatedResponse', () => {
  it('should create paginated response', () => {
    const response = createPaginatedResponse([1, 2, 3], 100, 1, 20)
    expect(response.items).toEqual([1, 2, 3])
    expect(response.total).toBe(100)
    expect(response.page).toBe(1)
    expect(response.pageSize).toBe(20)
    expect(response.totalPages).toBe(5)
  })
})

describe('createErrorResponse', () => {
  it('should create error response', () => {
    const error = createErrorResponse('VALIDATION_ERROR', 'Invalid input')
    expect(error.code).toBe('VALIDATION_ERROR')
    expect(error.message).toBe('Invalid input')
  })

  it('should include details when provided', () => {
    const error = createErrorResponse('VALIDATION_ERROR', 'Invalid input', { field: 'email' })
    expect(error.details).toEqual({ field: 'email' })
  })
})

// ============================================================================
// Query Client Tests
// ============================================================================

describe('createTestQueryClient', () => {
  it('should create query client with test configuration', () => {
    const client = createTestQueryClient()
    expect(client).toBeInstanceOf(QueryClient)
  })

  it('should accept custom default options', () => {
    const client = createTestQueryClient({
      defaultOptions: {
        queries: { staleTime: 60000 },
      },
    })
    expect(client).toBeInstanceOf(QueryClient)
  })
})

// ============================================================================
// User Event Tests
// ============================================================================

describe('getUserEvent', () => {
  it('should return user event helpers', async () => {
    renderWithProviders(<TestComponent />)
    const user = getUserEvent()

    const button = screen.getByRole('button', { name: /计数:/ })
    await user.click(button)
    expect(button).toHaveTextContent('计数: 1')
  })
})

// ============================================================================
// Form Testing Helpers Tests
// ============================================================================

describe('createFormTestingHelpers', () => {
  it('should fill text input', async () => {
    renderWithProviders(<TestComponent />)
    const user = getUserEvent()
    const helpers = createFormTestingHelpers(user)

    await helpers.fillTextInput('文本输入', 'Hello')
    expect(screen.getByRole('textbox')).toHaveValue('Hello')
  })

  it('should click button', async () => {
    renderWithProviders(<TestComponent />)
    const user = getUserEvent()
    const helpers = createFormTestingHelpers(user)

    await helpers.click(screen.getByRole('button', { name: /计数:/ }))
    expect(screen.getByRole('button')).toHaveTextContent('计数: 1')
  })
})

// ============================================================================
// Assertion Helpers Tests
// ============================================================================

describe('assertions', () => {
  it('should check element visibility', () => {
    renderWithProviders(<TestComponent />)
    const element = screen.getByRole('heading', { name: '测试组件' })
    assertions.toBeVisible(element)
  })

  it('should check element is enabled', () => {
    renderWithProviders(<TestComponent />)
    const button = screen.getByRole('button', { name: /计数:/ })
    assertions.toBeEnabled(button)
  })

  it('should check element has text', () => {
    renderWithProviders(<TestComponent />)
    const button = screen.getByRole('button', { name: /计数:/ })
    assertions.toHaveText(button, '计数: 0')
  })
})

// ============================================================================
// Import QueryClient for tests
// ============================================================================
import { QueryClient } from '@tanstack/react-query'