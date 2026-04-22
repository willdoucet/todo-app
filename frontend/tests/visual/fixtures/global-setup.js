import { seedKnownWeek } from './seed.js'

// Eng 10 — runs once per Playwright job, before any spec starts. Specs no
// longer declare beforeAll for seeding; they only do per-test state
// manipulation (e.g. the undo spec's throwaway row).
export default async function globalSetup() {
  await seedKnownWeek()
}
