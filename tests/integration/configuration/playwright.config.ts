// Copyright 2023 The MathWorks, Inc.

import { devices } from '@playwright/test';
import dotenv from 'dotenv';

/**
 * Read environment variables from .env file present at the root of the project.
 * https://github.com/motdotla/dotenv
 */
dotenv.config();

/**
 * See https://playwright.dev/docs/test-configuration.
 */
const BASEURL = 'http://localhost:'+ process.env.MWI_APP_PORT + process.env.MWI_BASE_URL;

const config = {
    webServer: {
        command: 'matlab-proxy-app',
        url: BASEURL,
        reuseExistingServer: !process.env.CI,
        stdout: 'ignore',
        stderr: 'pipe',
    },

    globalSetup: require.resolve('./global-setup'),
    /**
     * This setting points Playwright to the directory where the test files exist.
     * Each "project" (defined at the end of the file) can pattern match against
     * the test filenames to select a subset of the files to run.
     */
    testDir: '.',

    /** Maximum time one test can run for. */
    /** This is kept to 60s because time taken by a test sometimes depends on server and network speed */
    timeout: 300 * 1000,

    /** Customise the settings for each assertion 'expect' statement. */
    expect: {
        /** Maximum time expect() should wait for the condition to be met. */
        timeout: 120 * 1000
    },

    /**
     * This setting fails the tests if you accidently left a test.only in the source code
     * This guards you from the tests passing trivially in CI/CD pipelines.
     */
    forbidOnly: !!process.env.CI,

    /** Retry on CI three times, and locally retry once. */
    retries: process.env.CI ? 3 : 2,

    /** Opt out of parallel tests on CI. */
    workers: process.env.CI ? 1 : 1,


    /** Some tests could be 'slow' in Playwright's eyes. This variable controls whether they are reported. */
    reportSlowTests: null,

    /** Reporter to use. See https://playwright.dev/docs/test-reporters */
    reporter: [
        ['line'],
        ['html', {
            open: 'never'
        }]
    ],

    /** Folder for test artifacts such as screenshots, videos, traces, etc. */
    // outputDir: './test-results/artifacts',

    /**
     * The 'use' setting can be specified globally, per project and per test file.
     * The settings below are the default and can overridden by the project and test files
     */
    use: {
      /**
       * The setting baseURL allows us to customise actions like `await page.goto('/')` on
       * a per-project or per-file basis. Rather than hard coding the base url to be used.
       * See the docker-compose.yaml file for which ports correspond to which container.
      */
      baseURL: BASEURL,

      /** Run the test without showing the browser */
      headless: true,
      ignoreHTTPSErrors: true,

      /** Maximum time each action such as `click()` can take. Defaults to 0 (no limit). */
      actionTimeout: 0,

      /**
       * Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer
       * This produces a .zip file with a record of each of the steps for debugging.
       * I haven't made use of this yet, but it might be worthwhile when these tests are automated
       */
      trace: 'on-first-retry',

      screenshot: 'only-on-failure',
      video: 'on',

      /** The default viewport size, can be overridden by the tests. */
      viewport: { width: 1024, height: 768 }

  },

  /**
     * Here we have only one project and hence we have not defined 'name' property explicitly. In
     * case of multiple projects, each of them can be called individually by using `jlpm playwright
     * test --project=project_name`
     */
  projects: [
    {
        use: {
            ...devices['Desktop Chrome'],
            baseURL: BASEURL
        }
    }
  ]
};


export default config;