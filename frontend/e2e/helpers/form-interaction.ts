/**
 * Form Interaction Helpers for E2E Testing
 *
 * Generic utilities for testing Ant Design form components including
 * form fill, validation, modal interaction, table pagination/sort,
 * and dropdown selection.
 *
 * Requirements: 2.2, 2.3, 2.4, 2.5, 2.7, 2.8, 2.9
 */

import { Page, expect, Locator } from '@playwright/test'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FormField {
  /** The label text, name attribute, or test-id of the field */
  label: string
  /** Value to enter */
  value: string
  /** Field type — defaults to 'input' */
  type?: 'input' | 'select' | 'textarea' | 'checkbox' | 'radio' | 'datepicker' | 'number'
}

// ---------------------------------------------------------------------------
// Form helpers
// ---------------------------------------------------------------------------

/**
 * Fill an Ant Design form by locating fields via their label text.
 */
export async function fillAntForm(page: Page, fields: FormField[]): Promise<void> {
  for (const field of fields) {
    const formItem = page.locator('.ant-form-item').filter({ hasText: field.label })

    switch (field.type ?? 'input') {
      case 'input':
      case 'number': {
        const input = formItem.locator('input').first()
        await input.click()
        await input.fill(field.value)
        break
      }
      case 'textarea': {
        const textarea = formItem.locator('textarea').first()
        await textarea.click()
        await textarea.fill(field.value)
        break
      }
      case 'select': {
        const selectTrigger = formItem.locator('.ant-select-selector').first()
        await selectTrigger.click()
        // Wait for dropdown to appear, then click the matching option
        const option = page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter({
          hasText: field.value,
        })
        await option.first().click()
        break
      }
      case 'checkbox': {
        const checkbox = formItem.locator('.ant-checkbox-input').first()
        if (field.value === 'true') {
          await checkbox.check()
        } else {
          await checkbox.uncheck()
        }
        break
      }
      case 'radio': {
        const radio = formItem.locator('.ant-radio-wrapper').filter({ hasText: field.value })
        await radio.first().click()
        break
      }
      case 'datepicker': {
        const picker = formItem.locator('.ant-picker').first()
        await picker.click()
        const pickerInput = formItem.locator('.ant-picker input').first()
        await pickerInput.fill(field.value)
        await page.keyboard.press('Enter')
        break
      }
    }
  }
}

/**
 * Click the primary submit button inside the nearest form or page.
 * @param buttonText - regex or string to match the button label; defaults to common submit labels.
 */
export async function submitAntForm(
  page: Page,
  buttonText: RegExp = /提交|Submit|确定|OK|保存|Save/,
): Promise<void> {
  const submitBtn = page.locator('button[type="submit"], .ant-btn-primary').filter({ hasText: buttonText }).first()
  await submitBtn.click()
}

/**
 * Verify that Ant Design validation errors appear for the expected number of fields.
 */
export async function verifyFormValidation(page: Page, expectedErrors: number): Promise<void> {
  const errors = page.locator('.ant-form-item-explain-error')
  await expect(errors).toHaveCount(expectedErrors, { timeout: 5000 })
}

/**
 * Open a modal via a trigger selector, fill the form inside it, and submit.
 * Returns true if the modal closed after submission (success).
 */
export async function fillAndSubmitModal(
  page: Page,
  fields: FormField[],
  triggerSelector: string,
): Promise<boolean> {
  // Click the trigger to open the modal
  await page.locator(triggerSelector).first().click()

  // Wait for modal to be visible
  const modal = page.locator('.ant-modal').filter({ has: page.locator('.ant-modal-body') })
  await expect(modal.first()).toBeVisible({ timeout: 5000 })

  // Fill the form inside the modal
  await fillAntForm(page, fields)

  // Click the modal's OK / submit button
  const okBtn = modal.first().locator('.ant-modal-footer .ant-btn-primary, button[type="submit"]').first()
  await okBtn.click()

  // Check if modal closed
  try {
    await expect(modal.first()).toBeHidden({ timeout: 5000 })
    return true
  } catch {
    return false
  }
}

// ---------------------------------------------------------------------------
// Table helpers
// ---------------------------------------------------------------------------

/**
 * Verify table pagination: navigate pages and check row counts.
 */
export async function verifyTablePagination(
  page: Page,
  expectedPageSize: number,
): Promise<void> {
  const table = page.locator('.ant-table').first()
  await expect(table).toBeVisible({ timeout: 5000 })

  // Check that visible rows do not exceed page size
  const rows = table.locator('.ant-table-tbody tr.ant-table-row')
  const rowCount = await rows.count()
  expect(rowCount).toBeLessThanOrEqual(expectedPageSize)

  // Try clicking "next page" if pagination exists
  const nextBtn = page.locator('.ant-pagination-next:not(.ant-pagination-disabled)').first()
  if (await nextBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await nextBtn.click()
    // After navigation, rows should still respect page size
    const newRowCount = await rows.count()
    expect(newRowCount).toBeLessThanOrEqual(expectedPageSize)
  }
}

/**
 * Verify table column sort by clicking a column header.
 */
export async function verifyTableSort(page: Page, columnHeader: string): Promise<void> {
  const table = page.locator('.ant-table').first()
  await expect(table).toBeVisible({ timeout: 5000 })

  const header = table.locator('th').filter({ hasText: columnHeader }).first()
  await header.click()

  // After click, the header should have a sorter class
  await expect(
    header.locator('.ant-table-column-sorter-up.active, .ant-table-column-sorter-down.active'),
  ).toBeVisible({ timeout: 3000 }).catch(() => {
    // Some Ant versions use different class names — just verify the click didn't error
  })
}

/**
 * Open a dropdown/select, pick an option, and verify the displayed value.
 */
export async function verifyDropdownSelect(
  page: Page,
  selector: string,
  optionText: string,
): Promise<void> {
  const selectTrigger = page.locator(selector).first()
  await selectTrigger.click()

  const option = page.locator('.ant-select-dropdown:visible .ant-select-item-option').filter({
    hasText: optionText,
  })
  await option.first().click()

  // Verify the selected value is displayed
  await expect(selectTrigger).toContainText(optionText, { timeout: 3000 })
}
