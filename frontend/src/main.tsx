import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { initWebVitals } from '@/utils/performance'

// Initialize Web Vitals monitoring
if (typeof window !== 'undefined') {
  initWebVitals(undefined, {
    reportToConsole: import.meta.env.DEV,
    reportToAnalytics: import.meta.env.PROD,
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
