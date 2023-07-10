// Copyright 2023 The MathWorks, Inc.
// Sets up the environment for all the playwright tests

import { chromium, FullConfig, expect } from '@playwright/test';

// Get username and password from environment variables.
// If env variables not set defaults to empty strings
const TEST_USERNAME = process.env.TEST_USERNAME ?? '';
const TEST_PASSWORD = process.env.TEST_PASSWORD ?? '';

async function globalSetup (config: FullConfig) {
    const { baseURL } = config.projects[0].use;
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(baseURL!);

    // Fills in the unsername textbox
    const emailTextbox = page.frameLocator('#loginframe').locator('#userId');
    await expect(emailTextbox, 'Wait for email ID textbox to appear').toBeVisible({ timeout: 60000 });
    await emailTextbox.fill(TEST_USERNAME);
    await emailTextbox.press('Enter');

    // Fills in the password textbox
    const passwordTextbox = page.frameLocator('#loginframe').locator('#password');
    await expect(passwordTextbox, 'Wait for password textbox to appear').toBeVisible();
    await passwordTextbox.fill(TEST_PASSWORD);
    await passwordTextbox.press('Enter');
    await passwordTextbox.press('Enter');

    // Verifies if licensing is successful by checking the status information
    const statusInfo = page.getByText('Status Information');
    await expect(statusInfo, 'Verify if Licensing is successful').toBeVisible({ timeout: 60000 });
    await browser.close();
}

export default globalSetup;