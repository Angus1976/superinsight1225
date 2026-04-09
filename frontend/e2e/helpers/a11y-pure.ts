/** Property 27: focus order indices strictly increase along tab order (0-based positions). */
export function isStrictlyIncreasingOrder(positions: readonly number[]): boolean {
  for (let i = 1; i < positions.length; i++) {
    if (positions[i]! <= positions[i - 1]!) return false
  }
  return true
}

/** Property 28: visible focus ring — modelled as non-zero outline width (px). */
export function hasVisibleFocusIndicator(outlineWidthPx: number): boolean {
  return outlineWidthPx > 0
}

/** Property 29: modal trap — focus stays within [first, last] while open. */
export function focusInModalTrap(focusIndex: number, first: number, last: number): boolean {
  return focusIndex >= first && focusIndex <= last
}

/** Property 30: every control has label id or aria (model: boolean per control). */
export function allControlsHaveAccessibleName(flags: readonly boolean[]): boolean {
  return flags.length > 0 && flags.every(Boolean)
}

/** Property 31: escape closes top overlay. */
export type Overlay = 'none' | 'modal' | 'dropdown'

export function afterEscape(top: Overlay): Overlay {
  if (top === 'none') return 'none'
  return 'none'
}
