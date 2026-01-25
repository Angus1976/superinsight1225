/**
 * Language Switching E2E Test
 * Tests switching between Chinese (zh) and English (en) on all admin pages
 * Validates Requirements 6.2 and 6.3
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

// Admin pages to test
const adminPages = [
  {
    name: 'Admin Console',
    path: '/admin/console',
    zhTitle: '管理控制台',
    enTitle: 'Admin Console',
    zhElements: ['系统概览', '快速操作', '系统状态'],
    enElements: ['System Overview', 'Quick Actions', 'System Status']
  },
  {
    name: 'Billing Management',
    path: '/admin/billing',
    zhTitle: '计费管理',
    enTitle: 'Billing Management',
    zhElements: ['计费概览', '账单列表', '计费统计'],
    enElements: ['Billing Overview', 'Bill List', 'Billing Statistics']
  },
  {
    name: 'Permission Configuration',
    path: '/admin/permission-config',
    zhTitle: '权限配置',
    enTitle: 'Permission Configuration',
    zhElements: ['角色管理', '权限管理', '角色列表'],
    enElements: ['Role Management', 'Permission Management', 'Role List']
  },
  {
    name: 'Quota Management',
    path: '/admin/quota-management',
    zhTitle: '配额管理',
    enTitle: 'Quota Management',
    zhElements: ['配额概览', '租户配额', '配额统计'],
    enElements: ['Quota Overview', 'Tenant Quotas', 'Quota Statistics']
  }
];

test.describe('Language Switching Tests', () => {
  let consoleMessages: string[] = [];
  let consoleWarnings: string[] = [];
  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    // Capture console messages
    consoleMessages = [];
    consoleWarnings = [];
    consoleErrors = [];

    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(text);
      
      if (msg.type() === 'warning') {
        consoleWarnings.push(text);
      } else if (msg.type() === 'error') {
        consoleErrors.push(text);
      }
    });
  });

  for (const adminPage of adminPages) {
    test.describe(adminPage.name, () => {
      test('should switch from Chinese to English', async ({ page }) => {
        // Navigate to page with Chinese locale
        await page.goto(`${BASE_URL}${adminPage.path}?locale=zh`);
        await page.waitForLoadState('networkidle');

        // Verify Chinese content is displayed
        await expect(page.locator('h1')).toContainText(adminPage.zhTitle);
        
        for (const zhElement of adminPage.zhElements) {
          await expect(page.getByText(zhElement, { exact: false })).toBeVisible();
        }

        // Find and click language switcher
        const languageSwitcher = page.locator('[data-testid="language-switcher"]')
          .or(page.locator('button:has-text("中文")'))
          .or(page.locator('button:has-text("EN")'))
          .or(page.locator('.language-selector'));

        if (await languageSwitcher.count() > 0) {
          await languageSwitcher.first().click();
          
          // Select English
          await page.getByText('English', { exact: false }).or(page.getByText('EN')).click();
          
          // Wait for language change to take effect
          await page.waitForTimeout(500);
          await page.waitForLoadState('networkidle');

          // Verify English content is displayed
          await expect(page.locator('h1')).toContainText(adminPage.enTitle);
          
          for (const enElement of adminPage.enElements) {
            await expect(page.getByText(enElement, { exact: false })).toBeVisible();
          }
        }

        // Check for i18n warnings in console
        const i18nWarnings = consoleWarnings.filter(w => 
          w.includes('i18n') || 
          w.includes('translation') || 
          w.includes('locale') ||
          w.includes('missing key')
        );
        
        expect(i18nWarnings).toHaveLength(0);
      });

      test('should switch from English to Chinese', async ({ page }) => {
        // Navigate to page with English locale
        await page.goto(`${BASE_URL}${adminPage.path}?locale=en`);
        await page.waitForLoadState('networkidle');

        // Verify English content is displayed
        await expect(page.locator('h1')).toContainText(adminPage.enTitle);
        
        for (const enElement of adminPage.enElements) {
          await expect(page.getByText(enElement, { exact: false })).toBeVisible();
        }

        // Find and click language switcher
        const languageSwitcher = page.locator('[data-testid="language-switcher"]')
          .or(page.locator('button:has-text("English")'))
          .or(page.locator('button:has-text("中文")'))
          .or(page.locator('.language-selector'));

        if (await languageSwitcher.count() > 0) {
          await languageSwitcher.first().click();
          
          // Select Chinese
          await page.getByText('中文', { exact: false }).or(page.getByText('ZH')).click();
          
          // Wait for language change to take effect
          await page.waitForTimeout(500);
          await page.waitForLoadState('networkidle');

          // Verify Chinese content is displayed
          await expect(page.locator('h1')).toContainText(adminPage.zhTitle);
          
          for (const zhElement of adminPage.zhElements) {
            await expect(page.getByText(zhElement, { exact: false })).toBeVisible();
          }
        }

        // Check for i18n warnings in console
        const i18nWarnings = consoleWarnings.filter(w => 
          w.includes('i18n') || 
          w.includes('translation') || 
          w.includes('locale') ||
          w.includes('missing key')
        );
        
        expect(i18nWarnings).toHaveLength(0);
      });

      test('should persist language preference across navigation', async ({ page }) => {
        // Set language to English
        await page.goto(`${BASE_URL}${adminPage.path}?locale=en`);
        await page.waitForLoadState('networkidle');

        // Verify English content
        await expect(page.locator('h1')).toContainText(adminPage.enTitle);

        // Navigate to another admin page
        const otherPage = adminPages.find(p => p.path !== adminPage.path);
        if (otherPage) {
          await page.goto(`${BASE_URL}${otherPage.path}`);
          await page.waitForLoadState('networkidle');

          // Verify language preference persisted (should still be English)
          await expect(page.locator('h1')).toContainText(otherPage.enTitle);
        }
      });

      test('should have no console errors during language switching', async ({ page }) => {
        // Navigate to page
        await page.goto(`${BASE_URL}${adminPage.path}?locale=zh`);
        await page.waitForLoadState('networkidle');

        // Clear previous console messages
        consoleErrors = [];

        // Switch language
        const languageSwitcher = page.locator('[data-testid="language-switcher"]')
          .or(page.locator('button:has-text("中文")'))
          .or(page.locator('.language-selector'));

        if (await languageSwitcher.count() > 0) {
          await languageSwitcher.first().click();
          await page.getByText('English', { exact: false }).or(page.getByText('EN')).click();
          await page.waitForTimeout(500);
          await page.waitForLoadState('networkidle');
        }

        // Filter out non-critical errors
        const criticalErrors = consoleErrors.filter(e => 
          !e.includes('favicon') && 
          !e.includes('404') &&
          !e.includes('net::ERR_')
        );

        expect(criticalErrors).toHaveLength(0);
      });
    });
  }

  test('should handle rapid language switching', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/console?locale=zh`);
    await page.waitForLoadState('networkidle');

    const languageSwitcher = page.locator('[data-testid="language-switcher"]')
      .or(page.locator('button:has-text("中文")'))
      .or(page.locator('.language-selector'));

    if (await languageSwitcher.count() > 0) {
      // Rapidly switch languages multiple times
      for (let i = 0; i < 3; i++) {
        await languageSwitcher.first().click();
        await page.getByText('English', { exact: false }).or(page.getByText('EN')).click();
        await page.waitForTimeout(200);

        await languageSwitcher.first().click();
        await page.getByText('中文', { exact: false }).or(page.getByText('ZH')).click();
        await page.waitForTimeout(200);
      }

      // Verify page is still functional
      await expect(page.locator('h1')).toBeVisible();
      
      // Check for errors
      const criticalErrors = consoleErrors.filter(e => 
        !e.includes('favicon') && 
        !e.includes('404')
      );
      expect(criticalErrors).toHaveLength(0);
    }
  });
});
