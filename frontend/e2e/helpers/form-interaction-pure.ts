/**
 * Pure predicates and small state machines for form/table/modal semantics.
 * Used by Vitest property tests (`src/__tests__/form-interactions.property.test.ts`)
 * and kept conceptually aligned with `form-interaction.ts` Playwright helpers.
 *
 * Requirements: 2.3–2.10
 */

/** Non-empty trimmed value counts as filled */
export function isEmptyRequiredViolation(required: boolean, value: string): boolean {
  return required && value.trim() === ''
}

/** Number of required fields that are empty (Property 2). */
export function countRequiredEmptyViolations(
  fields: ReadonlyArray<{ required: boolean; value: string }>,
): number {
  return fields.filter((f) => isEmptyRequiredViolation(f.required, f.value)).length
}

/** Simple email shape check for Property 3 (field-level invalid input). */
export function isWellFormedEmail(value: string): boolean {
  if (!value || value !== value.trim()) return false
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(value)
}

/** Ant Design–style sort cycle: none → ascend → descend → ascend … */
export type SortOrder = 'ascend' | 'descend' | null

export function nextTableSortOrder(current: SortOrder): SortOrder {
  if (current === null) return 'ascend'
  if (current === 'ascend') return 'descend'
  return 'ascend'
}

/** Total pages for Ant pagination (Property 6). */
export function paginationTotalPages(total: number, pageSize: number): number {
  if (pageSize <= 0 || total < 0) return 0
  return Math.ceil(total / pageSize)
}

export function paginationOffset(zeroBasedPage: number, pageSize: number): number {
  if (pageSize <= 0) return 0
  return Math.max(0, zeroBasedPage) * pageSize
}

/** Rows visible on a page (0-based page index) — slice must not exceed pageSize (Property 6). */
export function pageSliceLength(
  total: number,
  zeroBasedPage: number,
  pageSize: number,
): number {
  if (pageSize <= 0 || total < 0) return 0
  const offset = paginationOffset(zeroBasedPage, pageSize)
  if (offset >= total) return 0
  return Math.min(pageSize, total - offset)
}

/** Property 7: after toggling sort twice from null, we return to the first order. */
export function sortOrderAfterTwoTogglesFromNull(): SortOrder {
  return nextTableSortOrder(nextTableSortOrder(null))
}

/** Property 8: selected option label is what we store as “display value”. */
export function dropdownRoundTrip(selectedLabel: string): string {
  return selectedLabel
}

/** Property 9: reject disallowed extensions (leading dot, lowercase compare). */
export function isAllowedUploadExtension(
  filename: string,
  allowedExtensions: ReadonlyArray<string>,
): boolean {
  const lower = filename.toLowerCase()
  const dot = lower.lastIndexOf('.')
  if (dot === -1) return false
  const ext = lower.slice(dot)
  return allowedExtensions.includes(ext)
}

/** Modal lifecycle: open → submit|cancel → closed (Property 4). */
export type ModalPhase = 'closed' | 'open'

export function modalAfterPrimaryAction(phase: ModalPhase, action: 'open' | 'submit' | 'cancel'): ModalPhase {
  if (action === 'open') return 'open'
  return 'closed'
}

/** Delete confirmation: idle → confirming → deleted|idle (Property 5). */
export type DeletePhase = 'idle' | 'confirming' | 'done'

export function deleteConfirmationAfter(
  phase: DeletePhase,
  event: 'requestDelete' | 'confirm' | 'cancel',
): DeletePhase {
  if (phase === 'idle' && event === 'requestDelete') return 'confirming'
  if (phase === 'confirming' && event === 'confirm') return 'done'
  if (phase === 'confirming' && event === 'cancel') return 'idle'
  return phase
}
