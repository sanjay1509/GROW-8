import { defineConfig, devices } from '@playwright/test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const layer = process.env.QA_LAYER;
const suite = process.env.QA_SUITE;
const runId = process.env.QA_RUN_ID;
const validLayers = new Set(['frontend', 'backend', 'database']);
const validSuites = new Set(['smoke', 'sanity', 'regression', 'all']);
if (!validLayers.has(layer) || !validSuites.has(suite) || !runId) {
  throw new Error('Run tests using npm run test:<layer>:<suite> (from qa/)');
}
const reportRoot = `reports/${layer}/${suite}/${runId}`;

export default defineConfig({
  testDir: `./${layer}/tests`,
  // The 62-case release runs ONLY its own specs, leaving older QA tests untouched.
  ...(layer === 'frontend' ? { testMatch: '**/*.grow8-62.spec.js' } : {}),
  timeout: 30_000,
  expect: { timeout: 10_000 },
  workers: process.env.CI ? 2 : undefined,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: [
    [process.env.CI ? 'github' : 'list'],
    ['html', { outputFolder: `${reportRoot}/html`, open: 'never', title: `Grow8 ${layer} ${suite} (${runId})` }],
    ['junit', { outputFile: `${reportRoot}/junit.xml` }],
  ],
  outputDir: `${reportRoot}/artifacts`,
  use: {
    ...(layer === 'frontend' ? devices['Desktop Chrome'] : {}),
    baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  // Only UI tests start Vite; API and database suites do not depend on the UI.
  ...(layer === 'frontend' ? {
    webServer: {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      cwd: resolve(root, '../grow8-'),
      url: 'http://127.0.0.1:5173',
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
    },
  } : {}),
});
