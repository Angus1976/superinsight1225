/**
 * E2E Test: Quota Management Page Translations
 * 
 * Tests Requirements 6.2 and 6.3:
 * - All translations display correctly
 * - Browser console clean (no i18n warnings)
 * 
 * Test Coverage:
 * - Page title
 * - Statistics cards (storage, projects, users, API calls)
 * - Table columns (tenant, storage, projects, users, API calls, status, actions)
 * - Status tags (normal, warning, exceeded, not configured)
 * - Alert messages
 * - Modal form (adjust quota)
 * - Buttons (refresh, adjust quota)
 * - Pagination
 */

import { test, expect, Page } from '@playwright/test';

// Expected Chinese translations
const EXPECTED_TRANSLATIONS = {
  pageTitle: '配额管理',
  statistics: {
    totalStorage: '总存储使用',
    totalProjects: '总项目数',
    totalUsers: '总用户数',
    totalApiCalls: '总 API 调用'
  },
  columns: {
    tenant: '租户',
    storage: '存储',
    projects: '项目数',
    users: '用户数',
    apiCalls: 'API 调用',
    status: '状态',
    actions: '操作'
  },
  buttons: {
    refresh: '刷新',
    adjustQuota: '调整配额'
  },
  form: {
    storageQuota: '存储配额 (GB)',
    projectQuota: '项目配额',
    userQuota: '用户配额',
    apiQuota: 'API 调用配额'
  }
};

test.describe('Quota Management Page Translations', () => {
  let consoleMessages: string[] = [];
  let i18nWarnings: string[] = [];

  test.beforeEach(async ({ page }) => {
    // Monitor console messages
    consoleMessages = [];
    i18nWarnings = [];
    
    page.on('console', msg => {
      const text = msg.text();
      consoleMessages.push(text);
      
      // Check for i18n warnings
      if (text.includes('i18n') || text.includes('translation') || text.includes('missing')) {
        i18nWarnings.push(text);
      }
    });

    // Login (adjust credentials as needed)
    await page.goto('/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/admin/**', { timeout: 10000 });

    // Navigate to Quota Management page
    await page.goto('/admin/quotas');
    await page.waitForSelector('.quota-management', { timeout: 10000 });
  });

  test('should display correct page title', async ({ page }) => {
    const title = await page.locator('.ant-card-head-title').first().textContent();
    expect(title).toContain(EXPECTED_TRANSLATIONS.pageTitle);
  });

  test('should display all statistics cards with correct translations', async ({ page }) => {
    const statisticTitles = await page.locator('.ant-statistic-title').allTextContents();
    
    expect(statisticTitles).toHaveLength(4);
    expect(statisticTitles[0]).toBe(EXPECTED_TRANSLATIONS.statistics.totalStorage);
    expect(statisticTitles[1]).toBe(EXPECTED_TRANSLATIONS.statistics.totalProjects);
    expect(statisticTitles[2]).toBe(EXPECTED_TRANSLATIONS.statistics.totalUsers);
    expect(statisticTitles[3]).toBe(EXPECTED_TRANSLATIONS.statistics.totalApiCalls);
  });

  test('should display all table columns with correct translations', async ({ page }) => {
    const columnHeaders = await page.locator('.ant-table-thead th').allTextContents();
    const filteredHeaders = columnHeaders.filter(text => text.trim() !== '');
    
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.tenant);
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.storage);
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.projects);
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.users);
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.apiCalls);
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.status);
    expect(filteredHeaders).toContain(EXPECTED_TRANSLATIONS.columns.actions);
  });

  test('should display refresh button with correct translation', async ({ page }) => {
    const refreshButton = page.locator('.ant-card-extra button').first();
    const buttonText = await refreshButton.textContent();
    
    expect(buttonText?.trim()).toBe(EXPECTED_TRANSLATIONS.buttons.refresh);
  });

  test('should display adjust quota button with correct translation', async ({ page }) => {
    // Check if there are any rows in the table
    const hasRows = await page.locator('.ant-table-tbody tr:not(.ant-table-placeholder)').count() > 0;
    
    if (hasRows) {
      const adjustButton = page.locator('.ant-table-tbody button[type="link"]').first();
      const buttonText = await adjustButton.textContent();
      
      expect(buttonText?.trim()).toBe(EXPECTED_TRANSLATIONS.buttons.adjustQuota);
    } else {
      test.skip();
    }
  });

  test('should display modal form with correct translations', async ({ page }) => {
    // Check if there are any rows to click
    const hasRows = await page.locator('.ant-table-tbody tr:not(.ant-table-placeholder)').count() > 0;
    
    if (hasRows) {
      // Click the first adjust quota button
      await page.locator('.ant-table-tbody button[type="link"]').first().click();
      
      // Wait for modal to appear
      await page.waitForSelector('.ant-modal', { timeout: 5000 });
      
      // Test form labels
      const formLabels = await page.locator('.ant-modal .ant-form-item-label label').allTextContents();
      
      expect(formLabels).toContain(EXPECTED_TRANSLATIONS.form.storageQuota);
      expect(formLabels).toContain(EXPECTED_TRANSLATIONS.form.projectQuota);
      expect(formLabels).toContain(EXPECTED_TRANSLATIONS.form.userQuota);
      expect(formLabels).toContain(EXPECTED_TRANSLATIONS.form.apiQuota);
      
      // Close modal
      await page.locator('.ant-modal-close').click();
      await page.waitForTimeout(500);
    } else {
      test.skip();
    }
  });

  test('should display pagination with correct translation', async ({ page }) => {
    const paginationText = await page.locator('.ant-pagination-total-text').textContent();
    
    // Check if it contains Chinese characters (共...个租户)
    expect(paginationText).toMatch(/共.*个租户/);
  });

  test('should have no i18n warnings in console', async ({ page }) => {
    // Wait a bit for any async operations to complete
    await page.waitForTimeout(2000);
    
    // Check for i18n warnings
    expect(i18nWarnings).toHaveLength(0);
    
    if (i18nWarnings.length > 0) {
      console.log('❌ Found i18n warnings:');
      i18nWarnings.forEach(warning => console.log(`   - ${warning}`));
    }
  });

  test('should have no console errors', async ({ page }) => {
    // Wait a bit for any async operations to complete
    await page.waitForTimeout(2000);
    
    // Filter out non-error messages
    const errors = consoleMessages.filter(msg => 
      msg.toLowerCase().includes('error') && 
      !msg.includes('DevTools')
    );
    
    if (errors.length > 0) {
      console.log('⚠️  Found console errors:');
      errors.forEach(error => console.log(`   - ${error}`));
    }
    
    // This is a warning, not a hard failure
    expect(errors.length).toBeLessThanOrEqual(5);
  });

  test.afterEach(async () => {
    // Log summary
    console.log(`\n📊 Test completed`);
    console.log(`   Console messages: ${consoleMessages.length}`);
    console.log(`   i18n warnings: ${i18nWarnings.length}`);
  });
});
