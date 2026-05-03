const { defineConfig } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Load project-root .env so KEYFORGE_FRONTEND_PORT (and any future overrides)
// flow into both `docker compose` and Playwright from a single source. Compose
// reads .env natively; Playwright does not, so parse it inline. Existing
// process.env wins, so shell exports still override the file.
const rootEnv = path.join(__dirname, '..', '.env');
if (fs.existsSync(rootEnv)) {
  for (const line of fs.readFileSync(rootEnv, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/i);
    if (m && process.env[m[1]] === undefined) process.env[m[1]] = m[2];
  }
}

const FRONTEND_PORT = parseInt(process.env.KEYFORGE_FRONTEND_PORT, 10) || 3000;

module.exports = defineConfig({
  testDir: './tests',
  // 60s per test gives the cookie + cold React hydration enough room.
  timeout: 60000,
  retries: 1,
  // Single worker forces auth.spec.js and dashboard.spec.js to run serially,
  // so the Tier 4.3 auth rate limiter (5-token burst per IP, refills at
  // 10/min) is not tripped by parallel register attempts and there is no
  // racing between the two suites' page lifecycle.
  workers: 1,
  // List for stdout, HTML for the artifact CI uploads on failure.
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    headless: true,
    // Capture every screenshot + every trace + retain video only on
    // failure. The HTML report bundles them so an artifact download has
    // the full picture without inflating success-path artifacts.
    screenshot: 'on',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
  webServer: [
    {
      command: 'cd ../frontend && npm start',
      port: FRONTEND_PORT,
      timeout: 120000,
      reuseExistingServer: true,
    },
  ],
});
