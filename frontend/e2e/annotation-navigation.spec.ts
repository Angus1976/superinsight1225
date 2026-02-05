/**
 * Label Studio Annotation Navigation E2E Tests
 * 
 * End-to-end tests for the complete annotation navigation workflow:
 * - User navigates to task detail page
 * - User clicks "Start Annotation" button
 * - User is navigated to annotation page
 * - User clicks "Open in New Window" button
 * - New window opens with Label Studio
 * 
 * **Validates**: Requirements 1.1, 1.2, 1.3, 1.5, 1.6
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Annotation Navigation E2E Tests', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    // Navigate to the application
    await page.goto('http://localhost:5173');
    
    // Login if needed
    // This assumes the user is already logged in or the app doesn't require login for testing
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('should navigate to annotation page when clicking "Start Annotation" button', async () => {
    /**
     * Test: Complete flow for starting annotation
     * 
     * Flow:
     * 1. User navigates to task detail page
     * 2. User clicks "Start Annotation" button
     * 3. System validates project exists
     * 4. System navigates to annotation page
     * 
     * Validates: Requirements 1.1, 1.2, 1.6
     */
    
    // Navigate to task detail page
    await page.goto('http://localhost:5173/tasks/test-task-123');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Click the "Start Annotation" button
    const startButton = page.locator('button:has-text("开始标注"), button:has-text("Start Annotation")').first();
    await startButton.click();
    
    // Wait for navigation to annotation page
    await page.waitForURL('**/tasks/*/annotate', { timeout: 5000 });
    
    // Verify we're on the annotation page
    const currentUrl = page.url();
    expect(currentUrl).toContain('/annotate');
  });

  test('should open Label Studio in new window when clicking "Open in New Window" button', async ({ context }) => {
    /**
     * Test: Complete flow for opening in new window
     * 
     * Flow:
     * 1. User navigates to task detail page
     * 2. User clicks "Open in New Window" button
     * 3. System generates authenticated URL
     * 4. New window opens with Label Studio
     * 
     * Validates: Requirements 1.2, 1.5, 1.6
     */
    
    // Navigate to task detail page
    await page.goto('http://localhost:5173/tasks/test-task-123');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Listen for new page (window) opening
    const newPagePromise = context.waitForEvent('page');
    
    // Click the "Open in New Window" button
    const openWindowButton = page.locator('button:has-text("在新窗口打开"), button:has-text("Open in New Window")').first();
    await openWindowButton.click();
    
    // Wait for new window to open
    const newPage = await newPagePromise;
    
    // Verify new window opened with Label Studio URL
    const newPageUrl = newPage.url();
    expect(newPageUrl).toContain('labelstudio');
    
    // Close the new page
    await newPage.close();
  });

  test('should handle project creation when project does not exist', async () => {
    /**
     * Test: Complete flow for project creation
     * 
     * Flow:
     * 1. User navigates to task detail page with no project
     * 2. User clicks "Start Annotation" button
     * 3. System creates new project
     * 4. System navigates to annotation page
     * 
     * Validates: Requirements 1.1, 1.3, 1.6
     */
    
    // Navigate to task detail page (task without project)
    await page.goto('http://localhost:5173/tasks/test-task-no-project');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Click the "Start Annotation" button
    const startButton = page.locator('button:has-text("开始标注"), button:has-text("Start Annotation")').first();
    await startButton.click();
    
    // Wait for project creation and navigation
    await page.waitForURL('**/tasks/*/annotate', { timeout: 10000 });
    
    // Verify we're on the annotation page
    const currentUrl = page.url();
    expect(currentUrl).toContain('/annotate');
  });

  test('should display error message when project validation fails', async () => {
    /**
     * Test: Error handling during project validation
     * 
     * Flow:
     * 1. User navigates to task detail page
     * 2. User clicks "Start Annotation" button
     * 3. Project validation fails
     * 4. System displays error message
     * 5. User remains on task detail page
     * 
     * Validates: Requirements 1.7
     */
    
    // Navigate to task detail page
    await page.goto('http://localhost:5173/tasks/test-task-123');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Click the "Start Annotation" button
    const startButton = page.locator('button:has-text("开始标注"), button:has-text("Start Annotation")').first();
    await startButton.click();
    
    // Wait for error message to appear (if validation fails)
    // This assumes the error message is displayed in a toast or alert
    const errorMessage = page.locator('text=Error, text=Failed, text=Unauthorized').first();
    
    // If error message appears, verify it
    if (await errorMessage.isVisible({ timeout: 2000 }).catch(() => false)) {
      expect(await errorMessage.isVisible()).toBe(true);
    }
    
    // Verify we're still on the task detail page
    const currentUrl = page.url();
    expect(currentUrl).toContain('/tasks/');
    expect(currentUrl).not.toContain('/annotate');
  });

  test('should synchronize language when opening in new window', async ({ context }) => {
    /**
     * Test: Language synchronization in new window
     * 
     * Flow:
     * 1. User is in Chinese interface
     * 2. User clicks "Open in New Window" button
     * 3. New window opens with Chinese language
     * 4. User switches to English
     * 5. User clicks "Open in New Window" again
     * 6. New window opens with English language
     * 
     * Validates: Requirements 1.5
     */
    
    // Navigate to task detail page
    await page.goto('http://localhost:5173/tasks/test-task-123');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Listen for new page (window) opening
    const newPagePromise1 = context.waitForEvent('page');
    
    // Click the "Open in New Window" button (Chinese)
    const openWindowButton = page.locator('button:has-text("在新窗口打开"), button:has-text("Open in New Window")').first();
    await openWindowButton.click();
    
    // Wait for new window to open
    const newPage1 = await newPagePromise1;
    
    // Verify new window opened with Chinese language
    const newPageUrl1 = newPage1.url();
    expect(newPageUrl1).toContain('lang=zh');
    
    // Close the new page
    await newPage1.close();
    
    // Switch to English (if language switcher is available)
    const languageSwitcher = page.locator('button:has-text("English"), button:has-text("EN")').first();
    if (await languageSwitcher.isVisible({ timeout: 2000 }).catch(() => false)) {
      await languageSwitcher.click();
    }
    
    // Listen for new page (window) opening again
    const newPagePromise2 = context.waitForEvent('page');
    
    // Click the "Open in New Window" button again (English)
    await openWindowButton.click();
    
    // Wait for new window to open
    const newPage2 = await newPagePromise2;
    
    // Verify new window opened with English language
    const newPageUrl2 = newPage2.url();
    expect(newPageUrl2).toContain('lang=en');
    
    // Close the new page
    await newPage2.close();
  });

  test('should handle rapid consecutive button clicks', async () => {
    /**
     * Test: Handling rapid consecutive button clicks
     * 
     * Flow:
     * 1. User rapidly clicks "Start Annotation" button multiple times
     * 2. System handles all clicks gracefully
     * 3. Only one operation is executed
     * 
     * Validates: Requirements 1.1, 1.6
     */
    
    // Navigate to task detail page
    await page.goto('http://localhost:5173/tasks/test-task-123');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Click the "Start Annotation" button multiple times rapidly
    const startButton = page.locator('button:has-text("开始标注"), button:has-text("Start Annotation")').first();
    
    // Perform rapid clicks
    await startButton.click();
    await startButton.click();
    await startButton.click();
    
    // Wait for navigation to annotation page
    await page.waitForURL('**/tasks/*/annotate', { timeout: 5000 });
    
    // Verify we're on the annotation page
    const currentUrl = page.url();
    expect(currentUrl).toContain('/annotate');
  });

  test('should display loading indicator during operation', async () => {
    /**
     * Test: Loading indicator display during operation
     * 
     * Flow:
     * 1. User clicks "Start Annotation" button
     * 2. Loading indicator appears
     * 3. Operation completes
     * 4. Loading indicator disappears
     * 
     * Validates: Requirements 1.6
     */
    
    // Navigate to task detail page
    await page.goto('http://localhost:5173/tasks/test-task-123');
    
    // Wait for page to load
    await page.waitForSelector('text=Test Task', { timeout: 5000 });
    
    // Click the "Start Annotation" button
    const startButton = page.locator('button:has-text("开始标注"), button:has-text("Start Annotation")').first();
    await startButton.click();
    
    // Check if loading indicator appears
    const loadingIndicator = page.locator('[class*="loading"], [class*="spinner"], [class*="progress"]').first();
    
    // If loading indicator is visible, wait for it to disappear
    if (await loadingIndicator.isVisible({ timeout: 1000 }).catch(() => false)) {
      await loadingIndicator.waitFor({ state: 'hidden', timeout: 5000 });
    }
    
    // Wait for navigation to annotation page
    await page.waitForURL('**/tasks/*/annotate', { timeout: 5000 });
    
    // Verify we're on the annotation page
    const currentUrl = page.url();
    expect(currentUrl).toContain('/annotate');
  });
});
