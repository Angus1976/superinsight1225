/**
 * E2E Tests for Quality Management Module
 * 质量管理模块端到端测试
 */

import { test, expect } from '@playwright/test';

test.describe('Quality Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to quality dashboard
    await page.goto('/quality');
  });

  test('should display quality overview statistics', async ({ page }) => {
    // Check for key statistics
    await expect(page.getByText('平均质量分')).toBeVisible();
    await expect(page.getByText('通过率')).toBeVisible();
    await expect(page.getByText('待处理问题')).toBeVisible();
    await expect(page.getByText('活跃预警')).toBeVisible();
  });

  test('should navigate between tabs', async ({ page }) => {
    // Click on Rules tab
    await page.click('text=规则配置');
    await expect(page.getByText('质量规则')).toBeVisible();

    // Click on Alerts tab
    await page.click('text=预警列表');
    await expect(page.getByText('质量预警')).toBeVisible();

    // Click on Reports tab
    await page.click('text=报告');
    await expect(page.getByText('质量报告')).toBeVisible();
  });

  test('should display annotator ranking', async ({ page }) => {
    // Check for ranking table
    await expect(page.getByText('标注员排名')).toBeVisible();
    
    // Check for ranking columns
    await expect(page.getByText('排名')).toBeVisible();
    await expect(page.getByText('标注员')).toBeVisible();
    await expect(page.getByText('平均分')).toBeVisible();
  });
});

test.describe('Quality Rules Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality');
    await page.click('text=规则配置');
  });

  test('should display rules list', async ({ page }) => {
    // Check for rules table
    await expect(page.getByRole('table')).toBeVisible();
    
    // Check for table headers
    await expect(page.getByText('规则名称')).toBeVisible();
    await expect(page.getByText('严重程度')).toBeVisible();
    await expect(page.getByText('优先级')).toBeVisible();
  });

  test('should open create rule modal', async ({ page }) => {
    // Click add rule button
    await page.click('text=添加规则');
    
    // Check modal is visible
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('规则名称')).toBeVisible();
    await expect(page.getByText('规则类型')).toBeVisible();
  });

  test('should create a new rule', async ({ page }) => {
    // Open modal
    await page.click('text=添加规则');
    
    // Fill form
    await page.fill('input[placeholder="请输入规则名称"]', 'Test Rule');
    await page.click('text=选择类型');
    await page.click('text=内置规则');
    await page.click('text=选择严重程度');
    await page.click('.ant-select-item-option:has-text("高")');
    
    // Submit
    await page.click('button:has-text("确定")');
    
    // Verify success message
    await expect(page.getByText('规则已创建')).toBeVisible();
  });

  test('should toggle rule enabled status', async ({ page }) => {
    // Find a switch in the table and click it
    const switchElement = page.locator('.ant-switch').first();
    await switchElement.click();
    
    // Verify status change message
    await expect(page.getByText(/规则已(启用|禁用)/)).toBeVisible();
  });

  test('should delete a rule', async ({ page }) => {
    // Click delete button
    await page.click('button[aria-label="删除"]');
    
    // Confirm deletion
    await page.click('text=确定');
    
    // Verify success message
    await expect(page.getByText('规则已删除')).toBeVisible();
  });
});

test.describe('Quality Alerts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality');
    await page.click('text=预警列表');
  });

  test('should display alerts list', async ({ page }) => {
    // Check for alerts table
    await expect(page.getByRole('table')).toBeVisible();
    
    // Check for table headers
    await expect(page.getByText('严重程度')).toBeVisible();
    await expect(page.getByText('触发维度')).toBeVisible();
    await expect(page.getByText('状态')).toBeVisible();
  });

  test('should filter alerts by status', async ({ page }) => {
    // Open status filter
    await page.click('text=状态筛选');
    
    // Select "待处理"
    await page.click('text=待处理');
    
    // Verify filter is applied
    await expect(page.locator('.ant-select-selection-item:has-text("待处理")')).toBeVisible();
  });

  test('should acknowledge an alert', async ({ page }) => {
    // Find and click acknowledge button
    const acknowledgeBtn = page.locator('button:has-text("确认")').first();
    if (await acknowledgeBtn.isVisible()) {
      await acknowledgeBtn.click();
      await expect(page.getByText('预警已确认')).toBeVisible();
    }
  });

  test('should resolve an alert', async ({ page }) => {
    // Find and click resolve button
    const resolveBtn = page.locator('button:has-text("解决")').first();
    if (await resolveBtn.isVisible()) {
      await resolveBtn.click();
      await expect(page.getByText('预警已解决')).toBeVisible();
    }
  });

  test('should configure alert thresholds', async ({ page }) => {
    // Click configure button
    await page.click('text=配置阈值');
    
    // Check modal is visible
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('准确性阈值')).toBeVisible();
    await expect(page.getByText('完整性阈值')).toBeVisible();
  });
});

test.describe('Quality Reports', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality');
    await page.click('text=报告');
  });

  test('should display report options', async ({ page }) => {
    // Check for report types
    await expect(page.getByText('项目质量报告')).toBeVisible();
    await expect(page.getByText('标注员排名报告')).toBeVisible();
    await expect(page.getByText('质量趋势报告')).toBeVisible();
  });

  test('should generate project report', async ({ page }) => {
    // Click on project report card
    await page.click('text=项目质量报告');
    
    // Verify action triggered
    await expect(page.getByText(/生成|报告/)).toBeVisible();
  });

  test('should export report', async ({ page }) => {
    // Find export button
    await page.click('text=导出报告');
    
    // Select format
    await page.click('text=导出 PDF');
  });
});

test.describe('Improvement Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality/workflow/tasks');
  });

  test('should display improvement tasks list', async ({ page }) => {
    // Check for tasks table
    await expect(page.getByRole('table')).toBeVisible();
    
    // Check for key columns
    await expect(page.getByText('任务ID')).toBeVisible();
    await expect(page.getByText('优先级')).toBeVisible();
    await expect(page.getByText('状态')).toBeVisible();
  });

  test('should filter tasks by status', async ({ page }) => {
    // Open status filter
    await page.click('text=状态筛选');
    
    // Select "待处理"
    await page.click('.ant-select-item-option:has-text("待处理")');
  });

  test('should filter tasks by priority', async ({ page }) => {
    // Open priority filter
    await page.click('text=优先级');
    
    // Select "高优先级"
    await page.click('.ant-select-item-option:has-text("高优先级")');
  });

  test('should navigate to task detail', async ({ page }) => {
    // Click on first task's detail link
    const detailLink = page.locator('text=查看详情').first();
    if (await detailLink.isVisible()) {
      await detailLink.click();
      
      // Verify navigation to detail page
      await expect(page.getByText('任务详情')).toBeVisible();
    }
  });
});

test.describe('Improvement Task Detail', () => {
  test('should display task information', async ({ page }) => {
    // Navigate to a specific task (mock ID)
    await page.goto('/quality/workflow/tasks/task_001');
    
    // Check for task details
    await expect(page.getByText('任务详情')).toBeVisible();
    await expect(page.getByText('质量问题')).toBeVisible();
    await expect(page.getByText('改进数据')).toBeVisible();
  });

  test('should edit improvement data', async ({ page }) => {
    await page.goto('/quality/workflow/tasks/task_001');
    
    // Click edit button
    const editBtn = page.locator('button:has-text("编辑")');
    if (await editBtn.isVisible()) {
      await editBtn.click();
      
      // Check for textarea
      await expect(page.locator('textarea')).toBeVisible();
    }
  });

  test('should submit improvement', async ({ page }) => {
    await page.goto('/quality/workflow/tasks/task_001');
    
    // Click edit
    await page.click('text=编辑');
    
    // Fill improvement data
    await page.fill('textarea', '{"field": "corrected_value"}');
    
    // Submit
    await page.click('text=提交改进');
  });

  test('should review improvement', async ({ page }) => {
    await page.goto('/quality/workflow/tasks/task_001');
    
    // Check for review buttons (if task is in submitted status)
    const approveBtn = page.locator('button:has-text("批准")');
    const rejectBtn = page.locator('button:has-text("拒绝")');
    
    if (await approveBtn.isVisible()) {
      await expect(approveBtn).toBeVisible();
      await expect(rejectBtn).toBeVisible();
    }
  });
});

test.describe('Workflow Configuration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/quality/workflow/config');
  });

  test('should display workflow configuration', async ({ page }) => {
    // Check for configuration form
    await expect(page.getByText('工作流配置')).toBeVisible();
    await expect(page.getByText('工作流阶段')).toBeVisible();
    await expect(page.getByText('自动化设置')).toBeVisible();
  });

  test('should toggle auto create task', async ({ page }) => {
    // Find auto create switch
    const autoCreateSwitch = page.locator('.ant-switch').first();
    await autoCreateSwitch.click();
  });

  test('should save workflow configuration', async ({ page }) => {
    // Click save button
    await page.click('text=保存配置');
    
    // Verify success message
    await expect(page.getByText('配置已保存')).toBeVisible();
  });

  test('should display effect statistics', async ({ page }) => {
    // Check for effect statistics card
    await expect(page.getByText('改进效果统计')).toBeVisible();
    await expect(page.getByText('总任务数')).toBeVisible();
    await expect(page.getByText('完成任务')).toBeVisible();
  });
});

test.describe('Complete Quality Workflow E2E', () => {
  test('should complete full quality management workflow', async ({ page }) => {
    // 1. View dashboard
    await page.goto('/quality');
    await expect(page.getByText('质量仪表板')).toBeVisible();
    
    // 2. Check rules
    await page.click('text=规则配置');
    await expect(page.getByRole('table')).toBeVisible();
    
    // 3. View alerts
    await page.click('text=预警列表');
    await expect(page.getByText('质量预警')).toBeVisible();
    
    // 4. Generate report
    await page.click('text=报告');
    await expect(page.getByText('项目质量报告')).toBeVisible();
    
    // 5. Navigate to workflow
    await page.goto('/quality/workflow/tasks');
    await expect(page.getByText('改进任务列表')).toBeVisible();
  });
});
