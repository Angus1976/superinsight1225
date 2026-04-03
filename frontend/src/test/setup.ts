/**
 * Test Setup File for Vitest
 *
 * This file runs before each test file and sets up the testing environment.
 */

import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Ensure i18n is initialized for components using `useTranslation()`.
// Many unit tests render components directly (without `main.tsx`), so we must
// initialize the shared i18next instance here.
import '../locales/config'

// Runs a cleanup after each test case
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
  root: null,
  rootMargin: '',
  thresholds: [],
}))

// Mock scrollTo
window.scrollTo = vi.fn()

// jsdom 无 scrollIntoView，ChatPanel 等组件在 effect 中会调用
Element.prototype.scrollIntoView = vi.fn()

// Mock getComputedStyle (required for Ant Design modals + rc-util scrollbar measurement)
window.getComputedStyle = vi.fn().mockImplementation((_elt, pseudoElt?: string) => {
  const base = {
    getPropertyValue: vi.fn().mockReturnValue(''),
    width: '0px',
    height: '0px',
    overflow: 'visible',
    display: 'block',
    scrollbarColor: '',
    scrollbarWidth: '',
  } as CSSStyleDeclaration & { scrollbarColor?: string; scrollbarWidth?: string }
  if (pseudoElt === '::-webkit-scrollbar') {
    return { ...base, width: '0px', height: '0px' } as unknown as CSSStyleDeclaration
  }
  return base as unknown as CSSStyleDeclaration
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock })

// Suppress console errors during tests (optional)
// vi.spyOn(console, 'error').mockImplementation(() => {})
// vi.spyOn(console, 'warn').mockImplementation(() => {})
