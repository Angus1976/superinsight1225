// 放在所有 import 之前
import * as React from 'react'

// 临时 polyfill / 覆盖
if (!('useSyncExternalStore' in React)) {
  console.error('React.useSyncExternalStore missing!')
} else {
  // 很多库内部会用 shim，这里强制走 React 内置
  (globalThis as any).useSyncExternalStore = React.useSyncExternalStore
}

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
