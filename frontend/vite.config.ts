import { defineConfig, type BuildOptions } from 'vite'
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
        // Core React runtime - loaded first
        if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
          return 'vendor-react-core';
        }
        // React Router - needed for navigation
        if (id.includes('node_modules/react-router')) {
          return 'vendor-react-router';
        }
        // Ant Design core - UI framework
        if (id.includes('node_modules/antd/')) {
          return 'vendor-antd';
        }
        // Ant Design icons - can be loaded separately
        if (id.includes('node_modules/@ant-design/icons/')) {
          return 'vendor-antd-icons';
        }
        // Ant Design Pro components - loaded on demand
        if (id.includes('node_modules/@ant-design/pro')) {
          return 'vendor-antd-pro';
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

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
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
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/system': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables" as *;`,
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
    port: 4173,
    strictPort: true,
  },

  // JSON handling
  json: {
    stringify: true, // Smaller JSON imports
  },
}))
