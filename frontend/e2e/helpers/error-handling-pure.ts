/** Property 24: HTTP 500 → still show UI shell (modelled as error flag + hasMessage). */
export function gracefulApiFailureState(hasErrorBanner: boolean, routeVisible: boolean): boolean {
  return hasErrorBanner || routeVisible
}

/** Property 25: on network error, draft fields preserved (shallow equality of snapshot). */
export function formDraftPreserved<T extends Record<string, unknown>>(before: T, after: T): boolean {
  return JSON.stringify(before) === JSON.stringify(after)
}

/** Property 26: empty list → zero rows. */
export function emptyStateRowCount(itemCount: number): number {
  return Math.max(0, itemCount)
}
