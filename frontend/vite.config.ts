import { defineConfig, type BuildOptions, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Build optimization configuration for < 3s page load target
const buildConfig: BuildOptions = {
  // Enable minification with esbuild (faster than terser)
  minify: 'esbuild',

  // Disable source maps in production for smaller bundles
  sourcemap: false,

  // Optimize chunk splitting for better caching and parallel loading
  rollupOptions: {
    output: {
      // Manual chunk splitting for optimal loading
      manualChunks: (id) => {
        // React + Ant Design 必须同 chunk（antd 模块顶层读取 React.version，拆开会因 ESM 初始化顺序导致 undefined）
        if (
          id.includes('node_modules/react/') ||
          id.includes('node_modules/react-dom/') ||
          id.includes('node_modules/antd/') ||
          id.includes('node_modules/@ant-design/pro') ||
          id.includes('node_modules/@ant-design/icons/')
        ) {
          return 'vendor-antd';
        }
        // React Router - needed for navigation
        if (id.includes('node_modules/react-router')) {
          return 'vendor-react-router';
        }
        // TanStack Query - data fetching
        if (id.includes('node_modules/@tanstack/react-query')) {
          return 'vendor-query';
        }
        // State management
        if (id.includes('node_modules/zustand')) {
          return 'vendor-state';
        }
        // HTTP client
        if (id.includes('node_modules/axios')) {
          return 'vendor-http';
        }
        // Date utilities
        if (id.includes('node_modules/dayjs')) {
          return 'vendor-date';
        }
        // Lodash utilities
        if (id.includes('node_modules/lodash-es')) {
          return 'vendor-lodash';
        }
        // i18n - internationalization
        if (id.includes('node_modules/i18next') || id.includes('node_modules/react-i18next')) {
          return 'vendor-i18n';
        }
        // Charts - loaded on demand for dashboard
        if (id.includes('node_modules/recharts') || id.includes('node_modules/d3')) {
          return 'vendor-charts';
        }
      },
      // Asset file naming with content hash for caching
      assetFileNames: (assetInfo) => {
        const info = assetInfo.name?.split('.') || []
        const ext = info[info.length - 1]
        if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name || '')) {
          return `assets/images/[name]-[hash][extname]`
        }
        if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name || '')) {
          return `assets/fonts/[name]-[hash][extname]`
        }
        if (ext === 'css') {
          return `assets/css/[name]-[hash][extname]`
        }
        return `assets/[name]-[hash][extname]`
      },
      // Chunk file naming
      chunkFileNames: 'assets/js/[name]-[hash].js',
      // Entry file naming
      entryFileNames: 'assets/js/[name]-[hash].js',
    },
  },

  // Target modern browsers for smaller bundle (ES2020+)
  target: 'es2020',

  // Chunk size warnings - keep chunks under 250KB for fast loading
  chunkSizeWarningLimit: 250,

  // CSS code splitting for parallel loading
  cssCodeSplit: true,

  // Enable CSS minification
  cssMinify: true,

  // Inline assets smaller than 4KB
  assetsInlineLimit: 4096,

  // Report compressed size
  reportCompressedSize: true,
}

/** 终端里提示当前默认端口，避免仍用 5173 / 8000 的旧书签 */
function devPortsHint(): Plugin {
  return {
    name: 'superinsight-dev-ports-hint',
    configureServer(server) {
      server.httpServer?.once('listening', () => {
        const addr = server.httpServer?.address()
        const port =
          addr && typeof addr === 'object' && 'port' in addr ? String(addr.port) : '?'
        console.log(
          `\n  [SuperInsight] 请用此地址打开前端: http://localhost:${port}/\n` +
            `  [SuperInsight] API 默认端口为 18080（与 5173/8000 不同）；请先启动后端: python main.py\n`
        )
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  /** 本地直连后端宿主机端口；Docker 内由 compose 注入 VITE_DEV_PROXY_TARGET=http://app:8000 */
  const devProxyTarget = process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:18080'

  return {
  plugins: [
    react(),
    ...(mode !== 'production' ? [devPortsHint()] : []),
  ],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@stores': path.resolve(__dirname, './src/stores'),
      '@services': path.resolve(__dirname, './src/services'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@types': path.resolve(__dirname, './src/types'),
      '@constants': path.resolve(__dirname, './src/constants'),
      '@locales': path.resolve(__dirname, './src/locales'),
    },
  },

  server: {
    port: 15173,
    strictPort: true,
    host: '0.0.0.0',
    // Suppress specific warnings
    hmr: {
      overlay: true,
    },
    proxy: {
      '/api': {
        target: devProxyTarget,
        changeOrigin: true,
        // Enable SSE streaming support
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Disable buffering for SSE endpoints
            if (req.url?.includes('/stream')) {
              proxyReq.setHeader('X-Accel-Buffering', 'no');
            }
          });
        },
      },
      '/health': {
        target: devProxyTarget,
        changeOrigin: true,
      },
      '/system': {
        target: devProxyTarget,
        changeOrigin: true,
      },
      '/label-studio': {
        target: 'http://superinsight-label-studio:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/label-studio/, ''),
      },
    },
  },

  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/theme/designSystem.scss" as *;`,
      },
    },
    // Enable CSS modules
    modules: {
      localsConvention: 'camelCase',
    },
    // Optimize CSS for production
    devSourcemap: mode !== 'production',
  },

  // Production build configuration
  build: mode === 'production' ? buildConfig : {
    ...buildConfig,
    sourcemap: true,
    minify: false, // Faster dev builds
  },

  // Optimize dependencies for faster cold starts
  optimizeDeps: {
    // Pre-bundle these modules for better performance
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'antd',
      '@ant-design/icons',
      '@ant-design/pro-layout',
      '@ant-design/pro-components',
      '@tanstack/react-query',
      'zustand',
      'axios',
      'dayjs',
      'i18next',
      'react-i18next',
      'recharts',
      'lodash-es',
    ],
    // Exclude large dependencies that should be loaded on demand
    exclude: [],
    // Force optimization even if dependencies haven't changed
    force: false,
  },

  // Enable esbuild optimizations
  esbuild: {
    // Drop console and debugger in production
    drop: mode === 'production' ? ['console', 'debugger'] : [],
    // Enable legal comments removal
    legalComments: 'none',
    // Target modern browsers
    target: 'es2020',
  },

  // Preview server configuration
  preview: {
    port: 14173,
    strictPort: true,
  },

  // JSON handling
  json: {
    stringify: true, // Smaller JSON imports
  },
}
})
