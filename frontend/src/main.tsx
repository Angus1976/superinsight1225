import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { reportWebVitals } from '@/utils/performance'
import { initPerformanceOptimizations } from '@/utils/performanceOptimization'
import { preloadCriticalRoutes } from '@/router/routes'

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
