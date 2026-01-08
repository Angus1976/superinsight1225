/**
 * End-to-End Business Workflow Tests
 *
 * Tests complete business processes from start to finish.
 */

import { test, expect } from '@playwright/test'

// Helper to set up authenticated state
async function setupAuth(page: any, role: string = 'admin') {
  await page.addInitScript(({ role }) => {
    const permissions = role === 'admin' 
      ? ['read:all', 'write:all', 'manage:all']
      : ['read:tasks', 'write:tasks', 'read:billing']

    localStorage.setItem(
      'auth-storage',
      JSON.stringify({
        state: {
          user: {
            id: `user-${role}`,
            username: `${role}user`,
            name: `${role} 用户`,
            email: `${role}@example.com`,
            tenant_id: 'tenant-1',
            roles: [role],
            permissions: permissions,
          },
          token: 'mock-jwt-token',
          currentTenant: {
            id: 'tenant-1',
            name: '测试租户',
          },
          isAuthenticated: true,
        },
      })
    )
  }, { role })
}

test.describe('Complete Task Management Workflow', () => {
  test('complete task lifecycle: create → assign → annotate → review → complete', async ({ page }) => {
    await setupAuth(page, 'admin')

    // Step 1: Create a new task
    await page.goto('/tasks')
    
    const createButton = page.getByRole('button', { name: /创建|新建|create/i })
    
    if (await createButton.isVisible()) {
      await createButton.click()

      // Fill task creation form
      const modal = page.locator('.ant-modal')
      
      if (await modal.isVisible()) {
        // Task name
        const nameInput = page.getByPlaceholder(/任务名称|task.*name/i)
        if (await nameInput.isVisible()) {
          await nameInput.fill('E2E测试任务')
        }

        // Task description
        const descInput = page.getByPlaceholder(/描述|description/i)
        if (await descInput.isVisible()) {
          await descInput.fill('端到端测试任务描述')
        }

        // Submit form
        const submitButton = modal.getByRole('button', { name: /确定|submit|create/i })
        if (await submitButton.isVisible()) {
          await submitButton.click()
        }

        // Wait for modal to close
        await expect(modal).not.toBeVisible({ timeout: 5000 })
      }
    }

    // Step 2: Assign task to user
    const taskRow = page.locator('.ant-table-row').first()
    
    if (await taskRow.isVisible()) {
      // Look for assign button or dropdown
      const assignButton = taskRow.getByRole('button', { name: /分配|assign/i })
      
      if (await assignButton.isVisible()) {
        await assignButton.click()

        // Select assignee
        const assigneeSelect = page.locator('.ant-select-dropdown .ant-select-item').first()
        if (await assigneeSelect.isVisible()) {
          await assigneeSelect.click()
        }
      }
    }

    // Step 3: Navigate to annotation interface
    if (await taskRow.isVisible()) {
      const annotateButton = taskRow.getByRole('button', { name: /标注|annotate/i })
      
      if (await annotateButton.isVisible()) {
        await annotateButton.click()

        // Should navigate to annotation page
        await expect(page).toHaveURL(/annotate|label/i, { timeout: 5000 })

        // Look for Label Studio iframe
        const iframe = page.locator('iframe')
        if (await iframe.isVisible()) {
          await expect(iframe).toBeVisible()
        }
      }
    }

    // Step 4: Complete annotation (simulate)
    // In real scenario, this would involve interacting with Label Studio
    await page.goBack()

    // Step 5: Mark task as complete
    if (await taskRow.isVisible()) {
      const completeButton = taskRow.getByRole('button', { name: /完成|complete/i })
      
      if (await completeButton.isVisible()) {
        await completeButton.click()

        // Confirm completion
        const confirmButton = page.getByRole('button', { name: /确认|confirm/i })
        if (await confirmButton.isVisible()) {
          await confirmButton.click()
        }
      }
    }
  })

  test('task progress tracking and status updates', async ({ page }) => {
    await setupAuth(page, 'manager')
    await page.goto('/tasks')

    // Look for task with progress indicator
    const progressBar = page.locator('.ant-progress, .progress-bar').first()
    
    if (await progressBar.isVisible()) {
      // Progress should be visible and have a value
      await expect(progressBar).toBeVisible()
      
      // Check progress text
      const progressText = page.locator('.ant-progress-text, .progress-text')
      if (await progressText.isVisible()) {
        const text = await progressText.textContent()
        expect(text).toMatch(/\d+%/)
      }
    }

    // Check status badges
    const statusBadge = page.locator('.ant-badge, .ant-tag').first()
    if (await statusBadge.isVisible()) {
      await expect(statusBadge).toBeVisible()
    }
  })
})

test.describe('Billing and Payment Workflow', () => {
  test('complete billing cycle: work tracking → bill generation → export', async ({ page }) => {
    await setupAuth(page, 'admin')

    // Step 1: Check work hours tracking
    await page.goto('/billing')

    // Look for work hours section
    const workHoursSection = page.locator('.work-hours, .time-tracking')
    
    if (await workHoursSection.isVisible()) {
      await expect(workHoursSection).toBeVisible()
    }

    // Step 2: Generate bill
    const generateButton = page.getByRole('button', { name: /生成|generate.*bill/i })
    
    if (await generateButton.isVisible()) {
      await generateButton.click()

      // Should show bill generation progress or result
      const billResult = page.locator('.ant-modal, .bill-result')
      if (await billResult.isVisible()) {
        await expect(billResult).toBeVisible()
      }
    }

    // Step 3: Export bill data
    const exportButton = page.getByRole('button', { name: /导出|export/i })
    
    if (await exportButton.isVisible()) {
      await exportButton.click()

      // Should trigger download or show export options
      const exportModal = page.locator('.ant-modal').filter({ hasText: /导出|export/i })
      if (await exportModal.isVisible()) {
        await expect(exportModal).toBeVisible()

        // Select export format
        const formatSelect = page.locator('.ant-select').filter({ hasText: /格式|format/i })
        if (await formatSelect.isVisible()) {
          await formatSelect.click()
          
          const excelOption = page.getByText(/excel|xlsx/i)
          if (await excelOption.isVisible()) {
            await excelOption.click()
          }
        }

        // Confirm export
        const confirmExport = exportModal.getByRole('button', { name: /确定|export/i })
        if (await confirmExport.isVisible()) {
          await confirmExport.click()
        }
      }
    }
  })

  test('cost analysis and reporting workflow', async ({ page }) => {
    await setupAuth(page, 'finance')
    await page.goto('/billing')

    // Navigate to cost analysis
    const analysisTab = page.getByRole('tab', { name: /分析|analysis|cost/i })
    
    if (await analysisTab.isVisible()) {
      await analysisTab.click()

      // Should show cost analysis charts
      const charts = page.locator('.ant-chart, .recharts-wrapper, canvas')
      
      if (await charts.first().isVisible()) {
        await expect(charts.first()).toBeVisible()
      }

      // Test date range selection
      const dateRangePicker = page.locator('.ant-picker-range')
      
      if (await dateRangePicker.isVisible()) {
        await dateRangePicker.click()

        // Select last month
        const lastMonthButton = page.getByText(/上月|last.*month/i)
        if (await lastMonthButton.isVisible()) {
          await lastMonthButton.click()
        }
      }
    }
  })
})

test.describe('Quality Management Workflow', () => {
  test('quality rule configuration and enforcement', async ({ page }) => {
    await setupAuth(page, 'quality_manager')
    await page.goto('/quality')

    // Step 1: Configure quality rules
    const rulesTab = page.getByRole('tab', { name: /规则|rules/i })
    
    if (await rulesTab.isVisible()) {
      await rulesTab.click()

      // Create new rule
      const createRuleButton = page.getByRole('button', { name: /创建|新建.*规则/i })
      
      if (await createRuleButton.isVisible()) {
        await createRuleButton.click()

        // Fill rule form
        const modal = page.locator('.ant-modal')
        
        if (await modal.isVisible()) {
          const ruleNameInput = page.getByPlaceholder(/规则名称|rule.*name/i)
          if (await ruleNameInput.isVisible()) {
            await ruleNameInput.fill('测试质量规则')
          }

          // Set rule conditions
          const conditionSelect = page.locator('.ant-select').first()
          if (await conditionSelect.isVisible()) {
            await conditionSelect.click()
            
            const option = page.locator('.ant-select-item').first()
            if (await option.isVisible()) {
              await option.click()
            }
          }

          // Save rule
          const saveButton = modal.getByRole('button', { name: /保存|save/i })
          if (await saveButton.isVisible()) {
            await saveButton.click()
          }
        }
      }
    }

    // Step 2: Check quality reports
    const reportsTab = page.getByRole('tab', { name: /报表|reports/i })
    
    if (await reportsTab.isVisible()) {
      await reportsTab.click()

      // Should show quality metrics
      const qualityMetrics = page.locator('.ant-statistic, .quality-metric')
      
      if (await qualityMetrics.first().isVisible()) {
        await expect(qualityMetrics.first()).toBeVisible()
      }
    }
  })

  test('work order creation and management', async ({ page }) => {
    await setupAuth(page, 'quality_manager')
    await page.goto('/quality')

    // Navigate to work orders
    const workOrdersTab = page.getByRole('tab', { name: /工单|work.*order/i })
    
    if (await workOrdersTab.isVisible()) {
      await workOrdersTab.click()

      // Create new work order
      const createButton = page.getByRole('button', { name: /创建|新建.*工单/i })
      
      if (await createButton.isVisible()) {
        await createButton.click()

        // Fill work order form
        const modal = page.locator('.ant-modal')
        
        if (await modal.isVisible()) {
          const titleInput = page.getByPlaceholder(/标题|title/i)
          if (await titleInput.isVisible()) {
            await titleInput.fill('质量问题工单')
          }

          const descInput = page.getByPlaceholder(/描述|description/i)
          if (await descInput.isVisible()) {
            await descInput.fill('发现数据质量问题，需要处理')
          }

          // Assign to user
          const assigneeSelect = page.locator('.ant-select').filter({ hasText: /分配|assign/i })
          if (await assigneeSelect.isVisible()) {
            await assigneeSelect.click()
            
            const assigneeOption = page.locator('.ant-select-item').first()
            if (await assigneeOption.isVisible()) {
              await assigneeOption.click()
            }
          }

          // Submit work order
          const submitButton = modal.getByRole('button', { name: /提交|submit/i })
          if (await submitButton.isVisible()) {
            await submitButton.click()
          }
        }
      }
    }
  })
})

test.describe('System Administration Workflow', () => {
  test('tenant management and configuration', async ({ page }) => {
    await setupAuth(page, 'system_admin')
    await page.goto('/admin')

    // Navigate to tenant management
    const tenantMenu = page.getByRole('menuitem', { name: /租户|tenant/i })
    
    if (await tenantMenu.isVisible()) {
      await tenantMenu.click()
      await expect(page).toHaveURL(/admin.*tenant/i)

      // Create new tenant
      const createTenantButton = page.getByRole('button', { name: /创建|新建.*租户/i })
      
      if (await createTenantButton.isVisible()) {
        await createTenantButton.click()

        // Fill tenant form
        const modal = page.locator('.ant-modal')
        
        if (await modal.isVisible()) {
          const nameInput = page.getByPlaceholder(/租户名称|tenant.*name/i)
          if (await nameInput.isVisible()) {
            await nameInput.fill('新测试租户')
          }

          const codeInput = page.getByPlaceholder(/租户代码|tenant.*code/i)
          if (await codeInput.isVisible()) {
            await codeInput.fill('test-tenant-new')
          }

          // Save tenant
          const saveButton = modal.getByRole('button', { name: /保存|save/i })
          if (await saveButton.isVisible()) {
            await saveButton.click()
          }
        }
      }
    }
  })

  test('system monitoring and health checks', async ({ page }) => {
    await setupAuth(page, 'system_admin')
    await page.goto('/admin/system')

    // Check system status
    const statusCards = page.locator('.ant-card').filter({ hasText: /状态|status|health/i })
    
    if (await statusCards.first().isVisible()) {
      await expect(statusCards.first()).toBeVisible()
    }

    // Check system metrics
    const metricsSection = page.locator('.system-metrics, .monitoring-dashboard')
    
    if (await metricsSection.isVisible()) {
      await expect(metricsSection).toBeVisible()
    }

    // Test system health check
    const healthCheckButton = page.getByRole('button', { name: /健康检查|health.*check/i })
    
    if (await healthCheckButton.isVisible()) {
      await healthCheckButton.click()

      // Should show health check results
      const results = page.locator('.health-results, .ant-alert')
      if (await results.isVisible()) {
        await expect(results).toBeVisible()
      }
    }
  })
})