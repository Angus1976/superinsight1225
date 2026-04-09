/** Property 32: content width ≤ viewport (no horizontal overflow). */
export function hasNoHorizontalOverflow(contentWidthPx: number, viewportWidthPx: number): boolean {
  return contentWidthPx <= viewportWidthPx
}

/** Property 33: touch target minimum (WCAG 2.5.5 style — 44px). */
export const MIN_TOUCH_TARGET_PX = 44

export function meetsTouchTarget(sizePx: number): boolean {
  return sizePx >= MIN_TOUCH_TARGET_PX
}
