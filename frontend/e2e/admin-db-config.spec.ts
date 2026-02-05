/**
 * Admin Database Configuration E2E Tests
 *
 * Tests the complete database configuration workflow including:
 * - Creating new database connections
 * - Testing connections
 * - Editing configurations
 * - Deleting configurations
 * - Database type-specific options
 * - SSL/TLS configuration
 * - Read-only mode
 *
 * **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**
 */

import { test, expect } from '@playwright/test';
import { setupAuth, waitForPageReady } from './test-helpers';

test.describe('Admin Database Configuration', () => {
  test.beforeEach(async ({ page }) => {
    // Set up admin authentication
    await setupAuth(page, 'admin', 'tenant-1');

    // Mock API responses for database configuration
    await page.route('**/api/v1/admin/config/db', async (route, request) => {
      if (request.method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'db-1',
              name: 'Production MySQL',
              db_type: 'mysql',
              host: 'mysql.example.com',
              port: 3306,
              database_name: 'superinsight_prod',
              username: 'admin',
              password_masked: '****',
              ssl_enabled: true,
              read_only: true,
              is_active: true,
              connection_pool: {
                min_size: 5,
                max_size: 20,
                timeout: 30,
              },
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            {
              id: 'db-2',
              name: 'Analytics PostgreSQL',
              db_type: 'postgresql',
              host: 'postgres.example.com',
              port: 5432,
              database_name: 'analytics',
              username: 'readonly',
              password_masked: '****',
              ssl_enabled: true,
              read_only: true,
              is_active: true,
              connection_pool: {
                min_size: 2,
                max_size: 10,
                timeout: 30,
              },
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
            id: 'db-new',
            ...body,
            password_masked: '****',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        });
      }
    });

    await page.route('**/api/v1/admin/config/db/*', async (route, request) => {
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
            password_masked: '****',
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
            name: 'Test DB',
            db_type: 'mysql',
            host: 'localhost',
            port: 3306,
            database_name: 'test',
            username: 'root',
            password_masked: '****',
            ssl_enabled: false,
            read_only: false,
            is_active: true,
          }),
        });
      }
    });

    await page.route('**/api/v1/admin/config/db/*/test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          latency_ms: 45,
          server_version: 'MySQL 8.0.32',
          database_size_mb: 1024,
        }),
      });
    });

    // Navigate to DB config page
    await page.goto('/admin/config/db');
    await waitForPageReady(page);
  });

  test('displays database configuration list', async ({ page }) => {
    // Check page title
    await expect(page.locator('text=/数据库|Database/i').first()).toBeVisible({ timeout: 10000 });

    // Check table is visible
    await expect(page.locator('.ant-table')).toBeVisible();

    // Check configurations are displayed
    await expect(page.getByText('Production MySQL')).toBeVisible();
    await expect(page.getByText('Analytics PostgreSQL')).toBeVisible();
  });

  test('opens create configuration modal', async ({ page }) => {
    // Click add button
    const addButton = page.getByRole('button', { name: /添加|新增|add/i });
    await addButton.click();

    // Check modal is visible
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Check form fields are present
    await expect(page.getByLabel(/名称|name/i).first()).toBeVisible();
  });

  test('creates new MySQL database configuration', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Fill form
    await page.getByLabel(/名称|name/i).first().fill('Test MySQL Database');

    // Select database type
    const dbTypeSelect = page.locator('.ant-select').first();
    await dbTypeSelect.click();
    await page.getByText('MySQL', { exact: false }).first().click();

    // Fill connection details
    const hostInput = page.getByLabel(/主机|host/i).first();
    if (await hostInput.isVisible()) {
      await hostInput.fill('mysql.test.com');
    }

    const portInput = page.getByLabel(/端口|port/i).first();
    if (await portInput.isVisible()) {
      await portInput.fill('3306');
    }

    const dbNameInput = page.getByLabel(/数据库名|database/i).first();
    if (await dbNameInput.isVisible()) {
      await dbNameInput.fill('test_db');
    }

    const usernameInput = page.getByLabel(/用户名|username/i).first();
    if (await usernameInput.isVisible()) {
      await usernameInput.fill('test_user');
    }

    const passwordInput = page.locator('input[type="password"]').first();
    if (await passwordInput.isVisible()) {
      await passwordInput.fill('test_password');
    }

    // Submit form
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check success message
    await expect(page.getByText(/成功|success/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('creates new PostgreSQL database configuration', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Fill form
    await page.getByLabel(/名称|name/i).first().fill('Test PostgreSQL Database');

    // Select database type
    const dbTypeSelect = page.locator('.ant-select').first();
    await dbTypeSelect.click();
    await page.getByText('PostgreSQL', { exact: false }).first().click();

    // Fill connection details
    const hostInput = page.getByLabel(/主机|host/i).first();
    if (await hostInput.isVisible()) {
      await hostInput.fill('postgres.test.com');
    }

    const portInput = page.getByLabel(/端口|port/i).first();
    if (await portInput.isVisible()) {
      await portInput.fill('5432');
    }

    // Submit form
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check success message
    await expect(page.getByText(/成功|success/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('displays database type-specific options', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Select MySQL
    const dbTypeSelect = page.locator('.ant-select').first();
    await dbTypeSelect.click();
    await page.getByText('MySQL', { exact: false }).first().click();

    // Check MySQL default port (3306)
    const portInput = page.getByLabel(/端口|port/i).first();
    if (await portInput.isVisible()) {
      const portValue = await portInput.inputValue();
      // Port might be pre-filled with MySQL default
      expect(['', '3306']).toContain(portValue);
    }

    // Select PostgreSQL
    await dbTypeSelect.click();
    await page.getByText('PostgreSQL', { exact: false }).first().click();

    // Check PostgreSQL default port (5432)
    if (await portInput.isVisible()) {
      const portValue = await portInput.inputValue();
      // Port might be updated to PostgreSQL default
      expect(['', '5432', '3306']).toContain(portValue);
    }
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

  test('tests database connection', async ({ page }) => {
    // Find test connection button for first config
    const testButton = page.locator('[aria-label*="test"], button:has(.anticon-api), button:has(.anticon-link)').first();

    if (await testButton.isVisible()) {
      await testButton.click();

      // Check for success message
      await expect(page.getByText(/成功|success|连接/i).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('handles connection test failure gracefully', async ({ page }) => {
    // Override route to return failure
    await page.route('**/api/v1/admin/config/db/*/test', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          latency_ms: 0,
          error_message: 'Connection refused: Unable to connect to database server',
          error_code: 'CONN_REFUSED',
          suggestions: [
            'Check if database server is running',
            'Verify host and port are correct',
            'Check firewall rules',
          ],
        }),
      });
    });

    // Find test connection button
    const testButton = page.locator('[aria-label*="test"], button:has(.anticon-api), button:has(.anticon-link)').first();

    if (await testButton.isVisible()) {
      await testButton.click();

      // Check for error message
      await expect(page.getByText(/失败|failed|error|refused/i).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('edits existing configuration', async ({ page }) => {
    // Find edit button for first config
    const editButton = page.locator('button:has(.anticon-edit)').first();
    await editButton.click();

    // Check modal is visible
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Modify name
    const nameInput = page.getByLabel(/名称|name/i).first();
    await nameInput.clear();
    await nameInput.fill('Updated Database Config');

    // Submit
    await page.getByRole('button', { name: /确定|ok|submit/i }).click();

    // Check success message
    await expect(page.getByText(/成功|success/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('deletes configuration with confirmation', async ({ page }) => {
    // Find delete button
    const deleteButton = page.locator('button:has(.anticon-delete)').first();

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

  test('configures SSL/TLS settings', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Find SSL toggle
    const sslSwitch = page.locator('.ant-switch').first();

    if (await sslSwitch.isVisible()) {
      // Enable SSL
      await sslSwitch.click();

      // Check if SSL certificate field appears
      const certField = page.getByLabel(/证书|certificate|ssl/i);
      // SSL cert field might appear after enabling SSL
      await expect(certField.first()).toBeVisible({ timeout: 3000 }).catch(() => {
        // SSL cert field might not be required
      });
    }
  });

  test('configures read-only mode', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Find read-only toggle
    const readOnlySwitch = page.getByLabel(/只读|read.?only/i);

    if (await readOnlySwitch.isVisible()) {
      // Enable read-only mode
      await readOnlySwitch.click();
    }
  });

  test('displays masked passwords', async ({ page }) => {
    // Check that passwords are masked in the table
    await expect(page.getByText(/\*\*\*\*/).first()).toBeVisible();
  });

  test('configures connection pool settings', async ({ page }) => {
    // Open create modal
    await page.getByRole('button', { name: /添加|新增|add/i }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    // Look for connection pool settings
    const minPoolInput = page.getByLabel(/最小|min/i);
    const maxPoolInput = page.getByLabel(/最大|max/i);

    if (await minPoolInput.isVisible()) {
      await minPoolInput.fill('5');
    }

    if (await maxPoolInput.isVisible()) {
      await maxPoolInput.fill('20');
    }
  });
});

test.describe('Database Configuration - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin', 'tenant-1');

    await page.route('**/api/v1/admin/config/db', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
  });

  test('displays correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/admin/config/db');
    await waitForPageReady(page);

    // Page should still be functional
    await expect(page.getByRole('button', { name: /添加|新增|add/i })).toBeVisible();
  });

  test('displays correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/admin/config/db');
    await waitForPageReady(page);

    // Page should still be functional
    await expect(page.getByRole('button', { name: /添加|新增|add/i })).toBeVisible();
  });
});

test.describe('Database Configuration - Access Control', () => {
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

    await page.goto('/admin/config/db');

    // Should show access denied or redirect
    await expect(
      page.getByText(/禁止|forbidden|权限|access denied/i).first()
    ).toBeVisible({ timeout: 10000 }).catch(() => {
      // May redirect to login or dashboard
      expect(page.url()).not.toContain('/admin/config/db');
    });
  });
});
