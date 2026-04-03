import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores([
    'dist',
    // Playwright E2E suite is validated by `npm run test:e2e`, not by ESLint
    // rules aimed at React component code.
    'e2e',
    'playwright-report',
    'test-results',
  ]),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Keep lint signal focused on correctness for a near-finished project.
      // Test code and some integration layers legitimately use `any`.
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/no-unused-expressions': 'off',
      '@typescript-eslint/ban-ts-comment': 'off',
      'no-useless-escape': 'off',
      // Some helper files are not React; avoid false positives.
      'react-hooks/immutability': 'off',
      // These rules are too strict for this codebase and currently generate
      // large volumes of false positives (especially in custom hooks).
      'react-hooks/refs': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/use-memo': 'off',

      // This repo includes many utility modules exporting non-components in TSX.
      // Disabling avoids large volumes of false positives.
      'react-refresh/only-export-components': 'off',
    },
  },
])
