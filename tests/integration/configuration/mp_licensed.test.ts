// Copyright 2023 The MathWorks, Inc.
// Test to check if MATLAB is licensed and is in

import {Page, test, expect, Locator} from '@playwright/test';
import config from './playwright.config';

// Tests to check the licensing workflow in the MATLAB Proxy UI
test.describe('MATLAB Proxy online licensing', () => {

    // Before each test case, checks if the MATLAB Proxy page is loaded
    test.beforeEach(async ({page}) => {
        // Checks if the MATLAB Proxy page is available
        await waitForPageLoad(page);
    });

    // Test to check the "Stop MATLAB" Button in the tools icon
    test('Check if MATLAB Proxy is running', async({ page }) => {

        // Goes to the MATLAB Proxy page
        await page.goto(config.webServer.url + '/index.html');

        // Clicks the tools icon button and checks the status of MATLAB is Running
        await clickToolsIconButton(page);
        const MATLABStatusInformation = await getMATLABStatusInformation(page);
        await expect(MATLABStatusInformation.getByText('Running'), 'The Status of MATLAB should be Running').toHaveText('Running', { timeout: 120000 });
    });

});

// HELPER FUNCTIONS FOR THE TESTS

async function waitForPageLoad(matlabJsdPage: Page) {
    // Waits for the page to finish loading
    await matlabJsdPage.waitForLoadState();
}

async function getMATLABStatusInformation(matlabJsdPage: Page) : Promise<Locator>{
    // This gets the dialog having all the buttons
    const MATLABStatusInformation = matlabJsdPage.getByRole('dialog', { name: 'Status Information' });
    await expect(MATLABStatusInformation, 'Wait for the MATLAB status Information dialog box').toBeVisible({timeout: 120000});
    return MATLABStatusInformation;
}

async function clickToolsIconButton(matlabJsdPage: Page){
    // Clicks the Tools Icon button
    const toolIcon = matlabJsdPage.getByRole('button', { name: 'Menu' });
    await expect(toolIcon, 'Wait for Tool Icon button in MATLAB Web Desktop').toBeVisible();
    await toolIcon.click();
}
