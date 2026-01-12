/**
 * ESLint Quality Rules Configuration
 * 
 * This file contains additional ESLint rules for maintaining
 * high code quality and consistency across the codebase.
 * 
 * These rules can be imported into the main eslint.config.js
 * for stricter code quality enforcement.
 */

export const qualityRules = {
  // ============================================================================
  // TypeScript Strict Rules
  // ============================================================================
  
  // Require explicit return types on functions
  '@typescript-eslint/explicit-function-return-type': ['warn', {
    allowExpressions: true,
    allowTypedFunctionExpressions: true,
    allowHigherOrderFunctions: true,
    allowDirectConstAssertionInArrowFunctions: true,
  }],
  
  // Require explicit accessibility modifiers
  '@typescript-eslint/explicit-member-accessibility': ['warn', {
    accessibility: 'explicit',
    overrides: {
      constructors: 'no-public',
    },
  }],
  
  // Disallow any type
  '@typescript-eslint/no-explicit-any': 'warn',
  
  // Require consistent type imports
  '@typescript-eslint/consistent-type-imports': ['warn', {
    prefer: 'type-imports',
    disallowTypeAnnotations: false,
  }],
  
  // Require consistent type exports
  '@typescript-eslint/consistent-type-exports': 'warn',
  
  // Disallow non-null assertions
  '@typescript-eslint/no-non-null-assertion': 'warn',
  
  // Require array type to be consistent
  '@typescript-eslint/array-type': ['warn', { default: 'array-simple' }],
  
  // Require consistent naming conventions
  '@typescript-eslint/naming-convention': [
    'warn',
    // Variables and functions: camelCase
    {
      selector: 'variableLike',
      format: ['camelCase', 'PascalCase', 'UPPER_CASE'],
      leadingUnderscore: 'allow',
    },
    // Types and interfaces: PascalCase
    {
      selector: 'typeLike',
      format: ['PascalCase'],
    },
    // Enum members: PascalCase or UPPER_CASE
    {
      selector: 'enumMember',
      format: ['PascalCase', 'UPPER_CASE'],
    },
  ],

  // ============================================================================
  // React Best Practices
  // ============================================================================
  
  // Require displayName for components
  'react/display-name': 'warn',
  
  // Require key prop in iterators
  'react/jsx-key': ['error', { checkFragmentShorthand: true }],
  
  // Disallow duplicate props
  'react/jsx-no-duplicate-props': 'error',
  
  // Disallow unescaped entities
  'react/no-unescaped-entities': 'warn',
  
  // Require self-closing tags
  'react/self-closing-comp': 'warn',
  
  // Require consistent boolean prop naming
  'react/jsx-boolean-value': ['warn', 'never'],
  
  // Require consistent fragment syntax
  'react/jsx-fragments': ['warn', 'syntax'],
  
  // Require consistent handler naming
  'react/jsx-handler-names': ['warn', {
    eventHandlerPrefix: 'handle',
    eventHandlerPropPrefix: 'on',
  }],

  // ============================================================================
  // Code Quality Rules
  // ============================================================================
  
  // Require consistent return statements
  'consistent-return': 'warn',
  
  // Disallow console statements (except warn and error)
  'no-console': ['warn', { allow: ['warn', 'error'] }],
  
  // Disallow debugger statements
  'no-debugger': 'error',
  
  // Disallow alert statements
  'no-alert': 'error',
  
  // Require default case in switch statements
  'default-case': 'warn',
  
  // Require === and !==
  'eqeqeq': ['error', 'always', { null: 'ignore' }],
  
  // Disallow eval
  'no-eval': 'error',
  
  // Disallow implied eval
  'no-implied-eval': 'error',
  
  // Disallow extending native objects
  'no-extend-native': 'error',
  
  // Disallow unnecessary function binding
  'no-extra-bind': 'warn',
  
  // Disallow floating decimals
  'no-floating-decimal': 'warn',
  
  // Disallow reassigning function declarations
  'no-func-assign': 'error',
  
  // Disallow assignments in conditions
  'no-cond-assign': ['error', 'always'],
  
  // Disallow constant conditions
  'no-constant-condition': 'warn',
  
  // Disallow duplicate keys in objects
  'no-dupe-keys': 'error',
  
  // Disallow duplicate case labels
  'no-duplicate-case': 'error',
  
  // Disallow empty block statements
  'no-empty': ['warn', { allowEmptyCatch: true }],
  
  // Disallow unnecessary boolean casts
  'no-extra-boolean-cast': 'warn',
  
  // Disallow irregular whitespace
  'no-irregular-whitespace': 'error',
  
  // Disallow sparse arrays
  'no-sparse-arrays': 'error',
  
  // Disallow unreachable code
  'no-unreachable': 'error',
  
  // Require isNaN() for NaN checks
  'use-isnan': 'error',
  
  // Require valid typeof comparisons
  'valid-typeof': 'error',

  // ============================================================================
  // Complexity Rules
  // ============================================================================
  
  // Limit cyclomatic complexity
  'complexity': ['warn', { max: 15 }],
  
  // Limit function depth
  'max-depth': ['warn', { max: 4 }],
  
  // Limit function length
  'max-lines-per-function': ['warn', {
    max: 100,
    skipBlankLines: true,
    skipComments: true,
  }],
  
  // Limit file length
  'max-lines': ['warn', {
    max: 500,
    skipBlankLines: true,
    skipComments: true,
  }],
  
  // Limit function parameters
  'max-params': ['warn', { max: 5 }],
  
  // Limit nested callbacks
  'max-nested-callbacks': ['warn', { max: 3 }],

  // ============================================================================
  // Import Rules
  // ============================================================================
  
  // Disallow duplicate imports
  'no-duplicate-imports': 'error',
  
  // Require imports to be sorted
  'sort-imports': ['warn', {
    ignoreCase: true,
    ignoreDeclarationSort: true,
    ignoreMemberSort: false,
  }],
};

/**
 * Recommended rules for production code
 */
export const productionRules = {
  ...qualityRules,
  'no-console': 'error',
  'no-debugger': 'error',
};

/**
 * Relaxed rules for development
 */
export const developmentRules = {
  ...qualityRules,
  'no-console': 'off',
  'no-debugger': 'warn',
  '@typescript-eslint/explicit-function-return-type': 'off',
};

export default qualityRules;
