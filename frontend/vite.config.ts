import { defineConfig, type BuildOptions } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Build optimization configuration
const buildConfig: BuildOptions = {
  // Enable minification
  minify: 'esbuild',

  // Generate source maps for production debugging
  sourcemap: false,

  // Optimize chunk splitting
  rollupOptions: {
    output: {
      // Manual chunk splitting for better caching
      manualChunks: {
        // Vendor chunks
        'vendor-react': ['react', 'react-dom', 'react-router-dom'],
        'vendor-antd': ['antd', '@ant-design/icons'],
        'vendor-query': ['@tanstack/react-query'],
        'vendor-utils': ['axios', 'dayjs', 'lodash-es', 'zustand'],
        'vendor-i18n': ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
        'vendor-charts': ['recharts'],
      },
      // Asset file naming
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

  // Target modern browsers for smaller bundle
  target: 'esnext',

  // Chunk size warnings
  chunkSizeWarningLimit: 500,

  // CSS code splitting
  cssCodeSplit: true,

  // Enable CSS minification
  cssMinify: true,
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
  },

  // Production build configuration
  build: mode === 'production' ? buildConfig : {
    ...buildConfig,
    sourcemap: true,
  },

  // Optimize dependencies
  optimizeDeps: {
    // Pre-build these modules for better performance
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
  },

  // Enable esbuild optimizations
  esbuild: {
    // Drop console and debugger in production
    drop: mode === 'production' ? ['console', 'debugger'] : [],
    // Enable legal comments removal
    legalComments: 'none',
  },

  // Preview server configuration
  preview: {
    port: 4173,
    strictPort: true,
  },
}))
