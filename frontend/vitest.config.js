import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // Use jsdom to simulate browser environment
    environment: 'jsdom',

    // Run this file before each test file
    setupFiles: ['./tests/setup.js'],

    // Make describe, it, expect available globally (no imports needed)
    globals: true,

    // Include CSS so component styles don't break tests
    css: true,

    // Where to look for test files
    include: [
      'src/**/*.{test,spec}.{js,jsx}',
      'tests/**/*.{test,spec}.{js,jsx}',
    ],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.config.js',
        'src/main.jsx',
      ],
    },
  },
})
