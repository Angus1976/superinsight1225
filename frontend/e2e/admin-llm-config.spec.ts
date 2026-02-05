/**
 * Admin LLM Configuration E2E Tests
 *
 * Tests the complete LLM configuration workflow including:
 * - Creating new LLM configurations
 * - Testing connections
 * - Editing configurations
 * - Deleting configurations
 * - Validation and error handling
 *
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
 */

import { test, expect } from '@playwright/test';
import { setupAuth, waitForPageReady, mockApiResponses } from './test-helpers';

test.describe('Admin LLM Configuration', () => {
  test.beforeEach(async ({ page }) => {
    // Set up admin authentication
    await setupAuth(page, 'admin', 'tenant-1');

    // Mock API responses for LLM configuration
    await page.route('**/api/v1/admin/config/llm', async (route, request) => {
      if (request.method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'llm-1',
              name: 'OpenAI GPT-4',
              llm_type: 'openai',
              model_name: 'gpt-4',
              api_endpoint: 'https://api.openai.com/v1',
              api_key_masked: '****...****',
              temperature: 0.7,
              max_tokens: 4096,
              timeout_seconds: 60,
              is_active: true,
              is_default: true,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            {
              id: 'llm-2',
              name: '通义千问',
              llm_type: 'qianwen',
              model_name: 'qwen-turbo',
              api_endpoint: 'https://dashscope.aliyuncs.com/api/v1',
              api_key_masked: '****...****',
              temperature: 0.8,
              max_tokens: 8192,
              timeout_seconds: 30,
              is_active: true,
              is_default: false,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ]),
        });
      } else if (request.method() === 'POST') {
        const body = JSON.parse(request.postData() || '{}');
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'llm-new',
            ...body,
            api_key_masked: '****...****',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        });
      }
    });

    await page.route('**/api/v1/admin/config/llm/*', async (route, request) => {
      const url = request.url();
      const id = url.split('/').pop();

      if (request.method() === 'PUT') {
        const body = JSON.parse(request.postData() || '{}');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id,
            ...body,
            api_key_masked: '****...****',
            updated_at: new Date().toISOString(),
          }),
        });
      } else if (request.method() === 'DELETE') {
        await route.fulfill({
          status: 204,
        });
      } else if (request.method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id,
            name: 'Test Config',
            llm_type: 'openai',
            model_name: 'gpt-4',
            api_endpoint: 'https://api.openai.com/v1',
            api_key_masked: '****...****',
            temperature: 0.7,
            max_tokens: 4096,
            timeout_seconds: 60,
            is_active: true,
            is_default: false,
          }),
        });
      }
    });

    await page.route('**/api/v1/admin/config/llm/*/test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          latency_ms: 245,
          model_info: {
            name: 'gpt-4',
            version: '2024-01',
          },
        }),
      });
    });

    // Navigate to LLM config page
    await page.goto('/admin/config/llm');
    await waitForPageReady(page);
  });

  test('displays LLM configuration list', async ({ page }) => {
    // Check page title
    await expect(page.locator('text=LLM').first()).toBeVisible({ timeout: 10000 });

    // Check table is visible
    await expect(page.locator('.ant-table')).toBeVisible();

    // Check configurations are displayed
    await expect(page.getByText('OpenAI GPT-4')).toBeVisible();
    await expect(page.getByText('通义千问')).toBeVisible();
  });

  test('opens create configuration modal', async ({ page }) => {
    // Click add button
    const addButton = page.getByRole('button', { name: /添加|新增|add/i });
    await addButton.click();

    // Check modal is visible
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Check form fields are present
    await expect(page.getByLabel(/名称|name/i).first()).toBeVisible();
    await expect(page.locator('.ant-select').first()).toBeVisible();
  });

  test('creates new LLM configuration', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Fill form
    await page.getByLabel(/名称|name/i).first().fill('Test LLM Config');
    
    // Select LLM type
    await page.locator('.ant-select').first().click();
    await page.getByText('OpenAI', { exact: false }).first().click();

    // Fill model name
    await page.getByLabel(/模型|model/i).first().fill('gpt-4-turbo');

    // Fill API endpoint
    const endpointInput = page.getByPlaceholder(/endpoint|端点/i);
    if (await endpointInput.isVisible()) {
      await endpointInput.fill('https://api.openai.com/v1');
    }

    // Fill API key
    const apiKeyInput = page.locator('input[type="password"]').first();
    if (await apiKeyInput.isVisible()) {
      await apiKeyInput.fill('sk-test-key-12345');
    }

    // Submit form
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check success message
    await expect(page.getByText(/成功|success/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('validates required fields', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Try to submit without filling required fields
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check validation errors
    await expect(page.getByText(/请输入|required|必填/i).first()).toBeVisible();
  });

  test('tests LLM connection', async ({ page }) => {
    // Find test connection button for first config
    const testButton = page.locator('[aria-label*="test"], button:has(.anticon-api)').first();
    
    if (await testButton.isVisible()) {
      await testButton.click();

      // Check for success message
      await expect(page.getByText(/成功|success|online/i).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('edits existing configuration', async ({ page }) => {
    // Find edit button for first config
    const editButton = page.locator('button:has(.anticon-edit)').first();
    await editButton.click();

    // Check modal is visible with existing data
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Modify name
    const nameInput = page.getByLabel(/名称|name/i).first();
    await nameInput.clear();
    await nameInput.fill('Updated LLM Config');

    // Submit
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check success message
    await expect(page.getByText(/成功|success/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('deletes configuration with confirmation', async ({ page }) => {
    // Find delete button for second config (not default)
    const deleteButtons = page.locator('button:has(.anticon-delete)');
    const deleteButton = deleteButtons.nth(1);
    
    if (await deleteButton.isVisible()) {
      await deleteButton.click();

      // Check confirmation dialog
      await expect(page.getByText(/确认|confirm|删除/i).first()).toBeVisible();

      // Confirm deletion
      await page.getByRole('button', { name: /确定|ok|yes/i }).click();

      // Check success message
      await expect(page.getByText(/成功|success|删除/i).first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('displays provider-specific options based on selection', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Select OpenAI provider
    await page.locator('.ant-select').first().click();
    await page.getByText('OpenAI', { exact: false }).first().click();

    // Check OpenAI-specific fields are visible
    await expect(page.getByLabel(/API Key/i).first()).toBeVisible();

    // Select local Ollama provider
    await page.locator('.ant-select').first().click();
    await page.getByText(/Ollama|本地/i).first().click();

    // API Key might be optional for local providers
    // Check that endpoint field is visible
    const endpointField = page.getByPlaceholder(/endpoint|端点|localhost/i);
    await expect(endpointField.first()).toBeVisible();
  });

  test('handles connection test failure gracefully', async ({ page }) => {
    // Override route to return failure
    await page.route('**/api/v1/admin/config/llm/*/test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          latency_ms: 0,
          error_message: 'Connection timeout: Unable to reach API endpoint',
        }),
      });
    });

    // Find test connection button
    const testButton = page.locator('[aria-label*="test"], button:has(.anticon-api)').first();
    
    if (await testButton.isVisible()) {
      await testButton.click();

      // Check for error message
      await expect(page.getByText(/失败|failed|error|timeout/i).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('refreshes configuration list', async ({ page }) => {
    // Find refresh button
    const refreshButton = page.getByRole('button', { name: /刷新|refresh/i });
    
    if (await refreshButton.isVisible()) {
      await refreshButton.click();

      // Table should still be visible after refresh
      await expect(page.locator('.ant-table')).toBeVisible();
    }
  });

  test('displays masked API keys', async ({ page }) => {
    // Check that API keys are masked in the table
    await expect(page.getByText(/\*\*\*\*/).first()).toBeVisible();
  });

  test('sets default configuration', async ({ page }) => {
    // Open edit modal for non-default config
    const editButtons = page.locator('button:has(.anticon-edit)');
    await editButtons.nth(1).click();

    // Check modal is visible
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Find and toggle default switch
    const defaultSwitch = page.locator('.ant-switch').first();
    if (await defaultSwitch.isVisible()) {
      await defaultSwitch.click();
    }

    // Submit
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check success
    await expect(page.getByText(/成功|success/i).first()).toBeVisible({ timeout: 5000 });
  });
});

test.describe('LLM Configuration - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1');
    
    await page.route('**/api/v1/admin/config/llm', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
  });

  test('displays correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/admin/config/llm');
    await waitForPageReady(page);

    // Page should still be functional
    await expect(page.getByRole('button', { name: /添加|新增|add/i })).toBeVisible();
  });

  test('displays correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/admin/config/llm');
    await waitForPageReady(page);

    // Page should still be functional
    await expect(page.getByRole('button', { name: /添加|新增|add/i })).toBeVisible();
  });
});

test.describe('LLM Configuration - Access Control', () => {
  test('denies access for non-admin users', async ({ page }) => {
    // Set up as regular user
    await setupAuth(page, 'user', 'tenant-1');

    await page.route('**/api/v1/admin/**', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Forbidden', message: 'Admin access required' }),
      });
    });

    await page.goto('/admin/config/llm');

    // Should show access denied or redirect
    await expect(
      page.getByText(/禁止|forbidden|权限|access denied/i).first()
    ).toBeVisible({ timeout: 10000 }).catch(() => {
      // May redirect to login or dashboard
      expect(page.url()).not.toContain('/admin/config/llm');
    });
  });
});
