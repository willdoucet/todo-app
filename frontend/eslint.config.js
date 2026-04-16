import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

// Vitest globals (describe/it/test/expect/beforeEach/afterEach/etc.) are
// injected at runtime via `vitest/globals` in vite.config; they're not real
// imports, so eslint needs them registered as globals for test files.
const vitestGlobals = {
  describe: 'readonly',
  it: 'readonly',
  test: 'readonly',
  expect: 'readonly',
  beforeAll: 'readonly',
  beforeEach: 'readonly',
  afterAll: 'readonly',
  afterEach: 'readonly',
  vi: 'readonly',
  vitest: 'readonly',
}

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': [
        'error',
        {
          varsIgnorePattern: '^[A-Z_]',
          // Allow destructured-and-renamed props like `as: Component = 'span'`
          // where the renamed identifier matches the var pattern.
          argsIgnorePattern: '^[A-Z_]',
          // Allow `_var` for intentionally unused destructured array elements
          // (e.g. `const [_value, setValue] = useState(...)` when only the
          // setter is needed).
          destructuredArrayIgnorePattern: '^_',
          // Allow `_e` and `_err` for intentionally unused catch parameters.
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  },
  {
    files: [
      '**/*.test.{js,jsx}',
      'tests/**/*.{js,jsx}',
      'src/**/*.test.{js,jsx}',
    ],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        ...vitestGlobals,
      },
    },
  },
])
