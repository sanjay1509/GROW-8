import path from 'node:path';
import { defineConfig } from '@playwright/test';

const out = process.env.QA_REPORT_DIR || 'reports/manual';

export default defineConfig({
    testDir: '.',

    testIgnore: [
        '**/reports/**',
        '**/node_modules/**'
    ],

    timeout: 90000,

    expect: {
        timeout: 10000
    },

    workers: 1,
    fullyParallel: false,
    retries: 0,

    outputDir: path.join(out, 'evidence'),

    reporter: [
        ['list'],
        ['html', {
            outputFolder: path.join(out, 'html'),
            open: 'never'
        }],
        ['json', {
            outputFile: path.join(out, 'results.json')
        }],
        ['junit', {
            outputFile: path.join(out, 'junit.xml')
        }]
    ],

    use: {
        baseURL: process.env.QA_UI_URL || 'http://localhost:15173',
        trace: 'retain-on-failure',
        screenshot: 'on',
        video: 'retain-on-failure'
    },

    projects: [
        {
            name: 'ui',
            testMatch: [
                'tests/ui.spec.mjs',
                'legacy-ui/tests/**/*.grow8-62.spec.js'
            ],
            use: {
                browserName: 'chromium'
            }
        },
        {
            name: 'api',
            testMatch: 'tests/api.spec.mjs'
        }
    ]
});