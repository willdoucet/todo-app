import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/visual/specs',
  // Eng 10 — seed runs once per job before any spec starts. Removes the need
  // for per-spec beforeAll blocks.
  globalSetup: './tests/visual/fixtures/global-setup.js',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  // Adversarial review A4 — lets aaa-smoke.spec.js short-circuit CI noise
  // when the mealboard page is broken at the root. Without this, four more
  // geometric specs fail with the same symptom and bury the signal.
  maxFailures: process.env.CI ? 1 : undefined,
  use: {
    baseURL: process.env.PREVIEW_URL || 'http://localhost:4173',
    trace: 'on-first-retry',
    actionTimeout: 5000,
    // Eng 4A — SwimlaneGrid.jsx:49 honors prefers-reduced-motion via
    // useMediaQuery. Emulating reduced motion disables hover transitions in
    // the app; target-state geometry (e.g. +48px hover-expand) is unchanged,
    // just applied instantly. Kills the 300ms settleTransitions flake vector.
    reducedMotion: 'reduce',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
  reporter: [
    ['html', { outputFolder: 'test-results/report' }],
    ['list'],
  ],
})
