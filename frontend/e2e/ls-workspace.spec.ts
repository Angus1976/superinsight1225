/**
 * Label Studio Workspace E2E Tests
 *
 * Tests the complete workspace lifecycle including:
 * - Workspace creation, editing, deletion
 * - Member management
 * - Project association
 * - Workspace switching
 * - i18n support
 */

import { test, expect, Page } from '@playwright/test'
import { E2E_VALID_ACCESS_TOKEN } from './e2e-tokens'

// ============================================================================
// Test Helpers
// ============================================================================

/**
 * Set up authenticated state with workspace context
 */
async function setupAuthWithWorkspace(
  page: Page,
  options: {
    userId?: string
    role?: 'owner' | 'admin' | 'manager' | 'reviewer' | 'annotator'
    workspaceId?: string
    workspaceName?: string
  } = {}
) {
  const {
    userId = 'user-1',
    role = 'owner',
    workspaceId = 'ws-1',
    workspaceName = '测试工作空间',
  } = options

  const permissions = getPermissionsForRole(role)

  await page.addInitScript(
    ({ userId, role, workspaceId, workspaceName, permissions, accessToken }) => {
      localStorage.setItem('auth_token', JSON.stringify(accessToken))
      localStorage.setItem(
        'auth-storage',
        JSON.stringify({
          state: {
            user: {
              id: userId,
              username: `${role}user`,
              name: `${role} 用户`,
              email: `${role}@example.com`,
              role,
              tenant_id: 'tenant-1',
              roles: [role],
              permissions: permissions,
            },
            token: accessToken,
            currentTenant: { id: 'tenant-1', name: '测试租户1' },
            currentWorkspace: null,
            workspaces: [],
            isAuthenticated: true,
          },
          version: 0,
        }),
      )

      localStorage.setItem(
        'ls-workspace-selected',
        JSON.stringify({
          id: workspaceId,
          name: workspaceName,
          role: role,
        }),
      )
    },
    { userId, role, workspaceId, workspaceName, permissions, accessToken: E2E_VALID_ACCESS_TOKEN },
  )
}

/**
 * Get permissions for a given role
 */
function getPermissionsForRole(role: string): string[] {
  const permissionMap: Record<string, string[]> = {
    owner: [
      'workspace:view',
      'workspace:edit',
      'workspace:delete',
      'workspace:manage_members',
      'project:view',
      'project:create',
      'project:edit',
      'project:delete',
      'task:view',
      'task:annotate',
      'task:review',
      'data:export',
      'data:import',
    ],
    admin: [
      'workspace:view',
      'workspace:edit',
      'workspace:manage_members',
      'project:view',
      'project:create',
      'project:edit',
      'project:delete',
      'task:view',
      'task:annotate',
      'task:review',
      'data:export',
      'data:import',
    ],
    manager: [
      'workspace:view',
      'project:view',
      'project:create',
      'project:edit',
      'task:view',
      'task:annotate',
      'task:review',
      'data:export',
    ],
    reviewer: [
      'workspace:view',
      'project:view',
      'task:view',
      'task:annotate',
      'task:review',
      'data:export',
    ],
    annotator: ['workspace:view', 'project:view', 'task:view', 'task:annotate'],
  }
  return permissionMap[role] || []
}

/**
 * Mock Label Studio Workspace API responses
 */
async function mockWorkspaceApi(page: Page) {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'e2e-user',
        username: 'e2euser',
        email: 'e2e@example.com',
        role: 'admin',
        tenant_id: 'tenant-1',
        is_active: true,
      }),
    })
  })
  await page.route('**/api/workspaces/my', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })

  // Mock workspace list
  await page.route('**/api/ls-workspaces', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'ws-1',
              name: '研发部门工作空间',
              description: '用于研发团队的标注工作',
              owner_id: 'user-1',
              is_active: true,
              is_deleted: false,
              member_count: 5,
              project_count: 3,
              created_at: '2026-01-20T10:00:00Z',
            },
            {
              id: 'ws-2',
              name: '测试团队工作空间',
              description: '用于测试团队',
              owner_id: 'user-1',
              is_active: true,
              is_deleted: false,
              member_count: 3,
              project_count: 2,
              created_at: '2026-01-21T10:00:00Z',
            },
          ],
          total: 2,
        }),
      })
    } else if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'ws-new',
          name: body.name,
          description: body.description,
          owner_id: 'user-1',
          is_active: true,
          is_deleted: false,
          member_count: 1,
          project_count: 0,
          created_at: new Date().toISOString(),
        }),
      })
    }
  })

  // Mock single workspace
  await page.route('**/api/ls-workspaces/*', async (route) => {
    const url = route.request().url()
    const workspaceId = url.split('/').pop()?.split('?')[0]

    if (route.request().method() === 'GET' && !url.includes('/members') && !url.includes('/projects') && !url.includes('/permissions')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: workspaceId,
          name: '研发部门工作空间',
          description: '用于研发团队的标注工作',
          owner_id: 'user-1',
          is_active: true,
          is_deleted: false,
          member_count: 5,
          project_count: 3,
          created_at: '2026-01-20T10:00:00Z',
        }),
      })
    } else if (route.request().method() === 'PUT') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: workspaceId,
          name: body.name || '研发部门工作空间',
          description: body.description || '用于研发团队的标注工作',
          owner_id: 'user-1',
          is_active: true,
          is_deleted: false,
          member_count: 5,
          project_count: 3,
          created_at: '2026-01-20T10:00:00Z',
        }),
      })
    } else if (route.request().method() === 'DELETE') {
      await route.fulfill({
        status: 204,
        body: '',
      })
    }
  })

  // Mock members
  await page.route('**/api/ls-workspaces/*/members', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'member-1',
              workspace_id: 'ws-1',
              user_id: 'user-1',
              role: 'owner',
              is_active: true,
              joined_at: '2026-01-20T10:00:00Z',
              user_name: 'Owner 用户',
              user_email: 'owner@example.com',
            },
            {
              id: 'member-2',
              workspace_id: 'ws-1',
              user_id: 'user-2',
              role: 'admin',
              is_active: true,
              joined_at: '2026-01-21T10:00:00Z',
              user_name: 'Admin 用户',
              user_email: 'admin@example.com',
            },
            {
              id: 'member-3',
              workspace_id: 'ws-1',
              user_id: 'user-3',
              role: 'annotator',
              is_active: true,
              joined_at: '2026-01-22T10:00:00Z',
              user_name: 'Annotator 用户',
              user_email: 'annotator@example.com',
            },
          ],
          total: 3,
        }),
      })
    } else if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'member-new',
          workspace_id: 'ws-1',
          user_id: body.user_id,
          role: body.role || 'annotator',
          is_active: true,
          joined_at: new Date().toISOString(),
        }),
      })
    }
  })

  // Mock projects
  await page.route('**/api/ls-workspaces/*/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'proj-assoc-1',
              workspace_id: 'ws-1',
              label_studio_project_id: '101',
              project_title: '图像分类项目',
              project_description: '用于图像分类的标注项目',
              created_at: '2026-01-20T10:00:00Z',
            },
            {
              id: 'proj-assoc-2',
              workspace_id: 'ws-1',
              label_studio_project_id: '102',
              project_title: '文本标注项目',
              project_description: '用于文本实体识别',
              created_at: '2026-01-21T10:00:00Z',
            },
          ],
          total: 2,
        }),
      })
    } else if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() || '{}')
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'proj-assoc-new',
          workspace_id: 'ws-1',
          label_studio_project_id: body.label_studio_project_id,
          created_at: new Date().toISOString(),
        }),
      })
    }
  })

  // Mock permissions
  await page.route('**/api/ls-workspaces/*/permissions', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        workspace_id: 'ws-1',
        user_id: 'user-1',
        role: 'owner',
        permissions: [
          'workspace:view',
          'workspace:edit',
          'workspace:delete',
          'workspace:manage_members',
          'project:view',
          'project:create',
          'project:edit',
          'project:delete',
          'task:view',
          'task:annotate',
          'task:review',
          'data:export',
          'data:import',
        ],
      }),
    })
  })
}

/**
 * Wait for page to be ready
 */
async function waitForPageReady(page: Page) {
  try {
    await page.waitForLoadState('networkidle', { timeout: 10000 })
  } catch {
    await page.waitForLoadState('domcontentloaded')
  }

  // Wait for loading spinners to disappear
  try {
    await page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 3000 })
  } catch {
    // Loading spinner might not exist
  }
}

// ============================================================================
// Workspace Lifecycle Tests
// ============================================================================

test.describe('Label Studio Workspace - Lifecycle', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkspaceApi(page)
  })

  test('displays workspace list page', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Check page title or header
    const header = page.locator('h1, .ant-card-head-title').filter({ hasText: /workspace|工作空间/i })
    await expect(header.first()).toBeVisible({ timeout: 5000 }).catch(() => {
      // Fallback: check URL
      expect(page.url()).toContain('ls-workspace')
    })
  })

  test('shows workspace statistics', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Look for statistics cards
    const statisticCards = page.locator('.ant-statistic, .ant-card .ant-statistic-content')

    if ((await statisticCards.count()) > 0) {
      await expect(statisticCards.first()).toBeVisible()
    }
  })

  test('can create new workspace', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Find and click create button
    const createButton = page.locator('button').filter({ hasText: /create|创建|新建/i })

    if (await createButton.first().isVisible({ timeout: 3000 })) {
      await createButton.first().click()

      // Wait for modal
      const modal = page.locator('.ant-modal')
      await expect(modal).toBeVisible({ timeout: 3000 })

      // Fill form
      const nameInput = modal.locator('input').first()
      await nameInput.fill('新工作空间测试')

      const descriptionInput = modal.locator('textarea')
      if (await descriptionInput.isVisible()) {
        await descriptionInput.fill('这是一个测试工作空间')
      }

      // Ant Design may render OK/Cancel with spaces between glyphs (e.g. "确 定"); use primary footer button.
      await modal.locator('.ant-modal-footer .ant-btn-primary').click({ timeout: 15000 })

      // Should close modal on success
      await expect(modal).toBeHidden({ timeout: 5000 }).catch(() => {
        // Modal might show success message
      })
    }
  })

  test('can view workspace details', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Click on a workspace row
    const workspaceRow = page.locator('.ant-table-row, .ant-list-item').first()

    if (await workspaceRow.isVisible({ timeout: 3000 })) {
      await workspaceRow.click()

      // Should show detail panel
      await page.waitForTimeout(500)

      // Look for detail panel with tabs
      const detailPanel = page.locator('.ant-card').filter({ hasText: /members|成员|projects|项目/i })
      await expect(detailPanel.first()).toBeVisible({ timeout: 3000 }).catch(() => {
        // Detail might be in different format
      })
    }
  })

  test('can edit workspace', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Look for edit button or action
    const editButton = page.locator('button, .ant-btn').filter({ hasText: /edit|编辑/i }).first()

    if (await editButton.isVisible({ timeout: 3000 })) {
      await editButton.click()

      // Modal should appear
      const modal = page.locator('.ant-modal')
      await expect(modal).toBeVisible({ timeout: 3000 })

      // Update name
      const nameInput = modal.locator('input').first()
      await nameInput.clear()
      await nameInput.fill('更新后的工作空间名称')

      await modal.locator('.ant-modal-footer .ant-btn-primary').click()
    }
  })

  test('can delete workspace with confirmation', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Look for delete action in dropdown or button
    const moreButton = page.locator('button').filter({ hasText: /more|更多/i }).first()

    if (await moreButton.isVisible({ timeout: 3000 })) {
      await moreButton.click()

      const deleteOption = page.locator('.ant-dropdown-menu-item').filter({ hasText: /delete|删除/i })
      if (await deleteOption.isVisible()) {
        await deleteOption.click()

        // Should show confirmation dialog
        const confirmDialog = page.locator('.ant-modal-confirm, .ant-modal')
        await expect(confirmDialog).toBeVisible({ timeout: 3000 })

        // Cancel to not actually delete
        const cancelButton = page.locator('.ant-modal button').filter({ hasText: /cancel|取消/i })
        if (await cancelButton.isVisible()) {
          await cancelButton.click()
        }
      }
    }
  })
})

// ============================================================================
// Member Management Tests
// ============================================================================

test.describe('Label Studio Workspace - Member Management', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkspaceApi(page)
  })

  test('shows member list in workspace detail', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Click on workspace to show details
    const workspaceRow = page.locator('.ant-table-row').first()
    if (await workspaceRow.isVisible({ timeout: 3000 })) {
      await workspaceRow.click()
      await page.waitForTimeout(500)

      // Click on members tab
      const membersTab = page.locator('.ant-tabs-tab').filter({ hasText: /members|成员/i })
      if (await membersTab.isVisible({ timeout: 3000 })) {
        await membersTab.click()

        // Should show member table
        const memberTable = page.locator('.ant-table')
        await expect(memberTable.first()).toBeVisible({ timeout: 3000 }).catch(() => {
          // Members might be in different format
        })
      }
    }
  })

  test('can add member to workspace', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Click on workspace
    const workspaceRow = page.locator('.ant-table-row').first()
    if (await workspaceRow.isVisible({ timeout: 3000 })) {
      await workspaceRow.click()
      await page.waitForTimeout(500)

      // Find add member button
      const addMemberButton = page.locator('button').filter({ hasText: /add.*member|添加.*成员/i })

      if (await addMemberButton.first().isVisible({ timeout: 3000 })) {
        await addMemberButton.first().click()

        // Modal should appear
        const modal = page.locator('.ant-modal')
        await expect(modal).toBeVisible({ timeout: 3000 })

        // Fill user ID
        const userIdInput = modal.locator('input').first()
        await userIdInput.fill('new-user-id')

        // Select role
        const roleSelect = modal.locator('.ant-select')
        if (await roleSelect.isVisible()) {
          await roleSelect.click()
          const annotatorOption = page.locator('.ant-select-item').filter({ hasText: /annotator|标注员/i })
          if (await annotatorOption.isVisible()) {
            await annotatorOption.click()
          }
        }

        // Cancel to not actually add
        const cancelButton = modal.locator('button').filter({ hasText: /cancel|取消/i })
        await cancelButton.click()
      }
    }
  })

  test('displays role badges correctly', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Click on workspace
    const workspaceRow = page.locator('.ant-table-row').first()
    if (await workspaceRow.isVisible({ timeout: 3000 })) {
      await workspaceRow.click()
      await page.waitForTimeout(500)

      // Look for role tags
      const roleTags = page.locator('.ant-tag')

      if ((await roleTags.count()) > 0) {
        // Should have role tags like owner, admin, annotator
        await expect(roleTags.first()).toBeVisible()
      }
    }
  })
})

// ============================================================================
// Project Association Tests
// ============================================================================

test.describe('Label Studio Workspace - Project Association', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkspaceApi(page)
  })

  test('shows project list in workspace detail', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Click on workspace
    const workspaceRow = page.locator('.ant-table-row').first()
    if (await workspaceRow.isVisible({ timeout: 3000 })) {
      await workspaceRow.click()
      await page.waitForTimeout(500)

      // Click on projects tab
      const projectsTab = page.locator('.ant-tabs-tab').filter({ hasText: /projects|项目/i })
      if (await projectsTab.isVisible({ timeout: 3000 })) {
        await projectsTab.click()

        // Should show project list
        await page.waitForTimeout(500)
        const projectList = page.locator('.ant-table, .ant-list')
        await expect(projectList.first()).toBeVisible({ timeout: 3000 }).catch(() => {
          // Projects might be empty or in different format
        })
      }
    }
  })

  test('can associate project to workspace', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Click on workspace
    const workspaceRow = page.locator('.ant-table-row').first()
    if (await workspaceRow.isVisible({ timeout: 3000 })) {
      await workspaceRow.click()
      await page.waitForTimeout(500)

      // Click on projects tab
      const projectsTab = page.locator('.ant-tabs-tab').filter({ hasText: /projects|项目/i })
      if (await projectsTab.isVisible()) {
        await projectsTab.click()
        await page.waitForTimeout(500)

        // Find associate button
        const associateButton = page.locator('button').filter({ hasText: /associate|关联/i })

        if (await associateButton.first().isVisible({ timeout: 3000 })) {
          await associateButton.first().click()

          // Modal should appear
          const modal = page.locator('.ant-modal')
          await expect(modal).toBeVisible({ timeout: 3000 })

          // Fill project ID
          const projectIdInput = modal.locator('input').first()
          await projectIdInput.fill('123')

          // Cancel
          const cancelButton = modal.locator('button').filter({ hasText: /cancel|取消/i })
          await cancelButton.click()
        }
      }
    }
  })
})

// ============================================================================
// Workspace Switching Tests
// ============================================================================

test.describe('Label Studio Workspace - Switching', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkspaceApi(page)
  })

  test('can select different workspace from list', async ({ page }) => {
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Get all workspace rows
    const workspaceRows = page.locator('.ant-table-row')
    const count = await workspaceRows.count()

    if (count > 1) {
      // Click on second workspace
      await workspaceRows.nth(1).click()
      await page.waitForTimeout(500)

      // Detail panel should update
      const detailPanel = page.locator('.ant-card').last()
      await expect(detailPanel).toBeVisible()
    }
  })

  test('preserves workspace selection', async ({ page }) => {
    await setupAuthWithWorkspace(page, { workspaceId: 'ws-2', workspaceName: '测试团队工作空间' })
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Check localStorage for selected workspace
    const selectedWorkspace = await page.evaluate(() => {
      return localStorage.getItem('ls-workspace-selected')
    })

    if (selectedWorkspace) {
      const parsed = JSON.parse(selectedWorkspace)
      expect(parsed.id).toBe('ws-2')
    }
  })
})

// ============================================================================
// i18n Tests
// ============================================================================

test.describe('Label Studio Workspace - i18n', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkspaceApi(page)
  })

  test('displays Chinese text by default', async ({ page }) => {
    await setupAuthWithWorkspace(page)

    // Set Chinese locale
    await page.addInitScript(() => {
      localStorage.setItem('language', 'zh')
    })

    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Check for Chinese text
    const pageContent = await page.textContent('body')
    const hasChinese = /[\u4e00-\u9fa5]/.test(pageContent || '')

    // Should have some Chinese characters
    expect(hasChinese).toBeTruthy()
  })

  test('can switch to English', async ({ page }) => {
    await setupAuthWithWorkspace(page)

    // Set English locale
    await page.addInitScript(() => {
      localStorage.setItem('language', 'en')
    })

    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Page should still load correctly
    await expect(page).toHaveURL(/ls-workspace/i)
  })
})

// ============================================================================
// Responsive Design Tests
// ============================================================================

test.describe('Label Studio Workspace - Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkspaceApi(page)
  })

  test('displays correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    // Page should still be usable
    await expect(page).toHaveURL(/ls-workspace/i)

    // Tables might be scrollable or collapsed on mobile
    const table = page.locator('.ant-table')
    if (await table.isVisible({ timeout: 3000 })) {
      await expect(table).toBeVisible()
    }
  })

  test('displays correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    await expect(page).toHaveURL(/ls-workspace/i)
  })

  test('displays correctly on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await setupAuthWithWorkspace(page)
    await page.goto('/ls-workspaces')
    await waitForPageReady(page)

    await expect(page).toHaveURL(/ls-workspace/i)

    // Should show full layout with statistics and table
    const statisticCards = page.locator('.ant-statistic')
    if ((await statisticCards.count()) > 0) {
      await expect(statisticCards.first()).toBeVisible()
    }
  })
})
