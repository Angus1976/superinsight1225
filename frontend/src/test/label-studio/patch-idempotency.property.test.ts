/**
 * Property 5: 补丁脚本幂等性
 *
 * Feature: label-studio-integration-enhancement
 * Property 5: 补丁脚本幂等性
 *
 * Validates: Requirements 6.2
 *
 * For any 补丁目标文件，连续执行两次补丁操作的结果应与执行一次的结果完全相同
 * （标记检测机制确保不重复应用）。
 *
 * This test simulates the marker-based patch logic used in entrypoint-sso.sh:
 * 1. Check if a marker string exists in the file content (grep -q)
 * 2. If marker NOT found → apply patch content + insert marker
 * 3. If marker found → skip (already patched)
 */
import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

// ---------------------------------------------------------------------------
// Patch logic simulation (mirrors entrypoint-sso.sh marker-based detection)
// ---------------------------------------------------------------------------

interface PatchDef {
  /** Unique marker string, e.g. "# SUPERINSIGHT_I18N_PATCH" */
  marker: string
  /** Content to append/inject when the patch is applied */
  patchContent: string
}

/**
 * Simulates the marker-based patch pattern from entrypoint-sso.sh.
 *
 * Equivalent bash logic:
 *   if ! grep -q "$MARKER" "$FILE"; then
 *       # apply patch and insert marker
 *   fi
 */
function applyPatch(fileContent: string, patch: PatchDef): string {
  if (fileContent.includes(patch.marker)) {
    // Marker found → already patched, skip
    return fileContent
  }
  // Marker not found → apply patch + insert marker
  return fileContent + '\n' + patch.patchContent + ' ' + patch.marker
}

/**
 * Applies multiple patches sequentially (mirrors the entrypoint script
 * which applies i18n, branding CSS, favicon, and title patches in order).
 */
function applyAllPatches(fileContent: string, patches: PatchDef[]): string {
  return patches.reduce((content, patch) => applyPatch(content, patch), fileContent)
}

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Safe characters that won't accidentally form a marker string */
const safeContentArb = fc
  .array(
    fc.constantFrom(
      ...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n<>/'.split(''),
    ),
    { minLength: 0, maxLength: 200 },
  )
  .map((chars) => chars.join(''))

/** Generates a unique marker string (prefixed to avoid collision with content) */
const markerArb = fc
  .tuple(
    fc.constantFrom('SUPERINSIGHT', 'PATCH', 'CUSTOM', 'MARKER'),
    fc
      .array(fc.constantFrom(...'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'.split('')), {
        minLength: 3,
        maxLength: 10,
      })
      .map((chars) => chars.join('')),
  )
  .map(([prefix, suffix]) => `# ${prefix}_${suffix}`)

/** Generates a single patch definition */
const patchDefArb = fc.tuple(markerArb, safeContentArb).map(([marker, content]) => ({
  marker,
  patchContent: content,
}))

/** Generates a list of patches with unique markers (simulating multiple patches in entrypoint) */
const patchListArb = fc
  .array(patchDefArb, { minLength: 1, maxLength: 5 })
  .map((patches) => {
    // Ensure unique markers (each patch in entrypoint-sso.sh has a distinct marker)
    const seen = new Set<string>()
    return patches.filter((p) => {
      if (seen.has(p.marker)) return false
      seen.add(p.marker)
      return true
    })
  })
  .filter((patches) => patches.length > 0)

/**
 * Generates file content that does NOT contain any of the given markers.
 * This simulates a fresh (unpatched) file.
 */
function freshContentArb(patches: PatchDef[]) {
  return safeContentArb.filter((content) => patches.every((p) => !content.includes(p.marker)))
}

// ---------------------------------------------------------------------------
// Property tests
// ---------------------------------------------------------------------------

describe('Feature: label-studio-integration-enhancement, Property 5: 补丁脚本幂等性', () => {
  /**
   * **Validates: Requirements 6.2**
   *
   * Core idempotency: applying a single patch twice yields the same result as once.
   */
  it('单个补丁连续执行两次的结果应与执行一次完全相同', () => {
    fc.assert(
      fc.property(patchDefArb, (patch) => {
        // Generate fresh content without the marker
        fc.assert(
          fc.property(
            safeContentArb.filter((c) => !c.includes(patch.marker)),
            (fileContent) => {
              const afterFirst = applyPatch(fileContent, patch)
              const afterSecond = applyPatch(afterFirst, patch)

              expect(afterSecond).toBe(afterFirst)
            },
          ),
          { numRuns: 10 },
        )
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 6.2**
   *
   * Multiple patches applied twice in sequence yield the same result as once.
   * This mirrors entrypoint-sso.sh applying i18n, CSS, favicon, title patches.
   */
  it('多个补丁连续执行两次的结果应与执行一次完全相同', () => {
    fc.assert(
      fc.property(patchListArb, (patches) => {
        fc.assert(
          fc.property(freshContentArb(patches), (fileContent) => {
            const afterFirst = applyAllPatches(fileContent, patches)
            const afterSecond = applyAllPatches(afterFirst, patches)

            expect(afterSecond).toBe(afterFirst)
          }),
          { numRuns: 10 },
        )
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 6.2**
   *
   * After patching, the marker MUST be present in the result.
   * This ensures the detection mechanism has material to detect.
   */
  it('补丁应用后文件内容应包含标记字符串', () => {
    fc.assert(
      fc.property(patchDefArb, (patch) => {
        fc.assert(
          fc.property(
            safeContentArb.filter((c) => !c.includes(patch.marker)),
            (fileContent) => {
              const result = applyPatch(fileContent, patch)
              expect(result).toContain(patch.marker)
            },
          ),
          { numRuns: 10 },
        )
      }),
      { numRuns: 100 },
    )
  })

  /**
   * **Validates: Requirements 6.2**
   *
   * If the file already contains the marker, applying the patch should be a no-op.
   * This directly tests the "skip if already patched" branch.
   */
  it('已包含标记的文件应用补丁后内容不变', () => {
    fc.assert(
      fc.property(patchDefArb, safeContentArb, (patch, extraContent) => {
        // File that already has the marker
        const alreadyPatched = extraContent + ' ' + patch.marker + ' ' + extraContent

        const result = applyPatch(alreadyPatched, patch)
        expect(result).toBe(alreadyPatched)
      }),
      { numRuns: 100 },
    )
  })
})
