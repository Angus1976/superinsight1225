/** Ant Design v5 + React 19 官方补丁，需在任意 antd 组件之前加载 */
import '@ant-design/v5-patch-for-react-19'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { reportWebVitals } from '@/utils/performance'
import { initPerformanceOptimizations } from '@/utils/performanceOptimization'
import { preloadCriticalRoutes } from '@/router/routes'

// Suppress specific Ant Design deprecation warnings from Pro Components
// These are internal to @ant-design/pro-components and will be fixed in their next release
const originalWarn = console.warn
console.warn = (...args: unknown[]) => {
  const message = args[0]
  if (
    typeof message === 'string' &&
    (message.includes('TableColumn') ||
     message.includes('Table.Column') ||
     message.includes('is deprecated'))
  ) {
    // Suppress these specific warnings
    return
  }
  originalWarn.apply(console, args)
}

// Initialize performance optimizations early
initPerformanceOptimizations()

// Initialize performance monitoring
reportWebVitals()

// Create root and render app
const root = createRoot(document.getElementById('root')!)
root.render(
  <StrictMode>
    <App />
  </StrictMode>
)

// Preload critical routes after initial render
// This improves subsequent navigation performance
if (typeof window !== 'undefined') {
  window.addEventListener('load', () => {
    // Preload routes during idle time
    preloadCriticalRoutes()
  })
}
