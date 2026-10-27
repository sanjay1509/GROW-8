import { test as base, expect } from '@playwright/test';

// Automatically attaches a full-page PNG to the HTML report for every
// executed frontend test, whether it passes or fails. This is a page-fixture
// teardown (not a global afterEach hook), so it applies to every spec file.
export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    try {
      await use(page);
    } finally {
      if (!page.isClosed()) {
        try {
          const image = await page.screenshot({fullPage:true,animations:'disabled',timeout:10000});
          await testInfo.attach(`Full-page screenshot (${testInfo.status})`, {
            body:image,contentType:'image/png',
          });
        } catch (error) {
          console.warn(`Screenshot unavailable for ${testInfo.title}: ${error.message}`);
        }
      }
    }
  },
});
export {expect};
