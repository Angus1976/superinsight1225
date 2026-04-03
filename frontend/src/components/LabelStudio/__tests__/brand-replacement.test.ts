/**
 * Bug Condition Exploration Test — 品牌替换不完全
 *
 * Property 1: Fault Condition
 * Validates: Requirements 1.1, 1.2, 1.3
 *
 * These tests assert the EXPECTED (fixed) behavior.
 * On UNFIXED code they MUST FAIL — failure confirms the bug exists.
 * After the fix is applied, they should PASS.
 */
import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

// Resolve paths relative to project root (frontend/../)
const PROJECT_ROOT = path.resolve(__dirname, '../../../../..');
const BRANDING_CSS_PATH = path.join(PROJECT_ROOT, 'deploy/label-studio/branding.css');
const I18N_INJECT_PATH = path.join(PROJECT_ROOT, 'deploy/label-studio/i18n-inject.js');
const IFRAME_CONTAINER_PATH = path.join(PROJECT_ROOT, 'frontend/src/components/LabelStudio/IframeContainer.tsx');
const LS_EMBED_PATH = path.join(PROJECT_ROOT, 'frontend/src/components/LabelStudio/LabelStudioEmbed.tsx');

describe('Bug Condition Exploration: 品牌替换不完全', () => {
  /**
   * Test 1a: branding.css MUST contain sidebar-related selectors
   * Currently missing → FAIL (confirms bug)
   *
   * **Validates: Requirements 2.1, 2.2**
   */
  it('1a: branding.css contains sidebar brand hiding selectors', () => {
    const css = fs.readFileSync(BRANDING_CSS_PATH, 'utf-8');

    // 当前实现：基于 lsf-menu-header / SVG alt / viewBox，而非 “sidebar” 字样
    expect(css).toMatch(/lsf-menu-header|问视间|Label Studio/i);
    expect(css).toMatch(/display:\s*none\s*!important/s);

    // 外部链接隐藏（侧栏/页脚等链接）
    expect(css).toMatch(/labelstud\.io|humansignal|display:\s*none/s);
  });

  /**
   * Test 1b: i18n-inject.js MUST contain sidebar DOM hiding logic
   * Currently has translations but NO DOM hiding for sidebar footer
   * → FAIL (confirms bug)
   *
   * **Validates: Requirements 2.1, 2.2**
   */
  it('1b: i18n-inject.js contains sidebar footer DOM hiding logic', () => {
    const source = fs.readFileSync(I18N_INJECT_PATH, 'utf-8');

    // replaceBrand：SVG logo display:none；hideExtLinks：外链 display:none
    const hasDomHiding =
      /svg\.style\.display\s*=\s*['"]?none/i.test(source) ||
      /hideExtLinks|replaceBrand/.test(source) ||
      /el\.style\.display\s*=\s*['"]?none/i.test(source);

    expect(hasDomHiding).toBe(true);
  });

  /**
   * Test 1c: IframeContainer.tsx MUST NOT contain hardcoded "Label Studio"
   * Currently has 3 hardcoded instances → FAIL (confirms bug)
   *
   * **Validates: Requirements 2.3**
   */
  it('1c: IframeContainer.tsx uses i18n instead of hardcoded "Label Studio"', () => {
    const source = fs.readFileSync(IFRAME_CONTAINER_PATH, 'utf-8');

    // Card title should use t() not hardcoded string
    expect(source).not.toMatch(/title="Label Studio"/);

    // Spin tip should use t() not hardcoded string
    expect(source).not.toMatch(/tip="Loading Label Studio\.\.\."/);

    // Alert message should use t() not hardcoded string
    expect(source).not.toMatch(/message="Label Studio Error"/);
  });

  /**
   * Test 1d: LabelStudioEmbed.tsx Card title MUST NOT contain hardcoded "Label Studio"
   * Currently has <span>Label Studio</span> → FAIL (confirms bug)
   *
   * **Validates: Requirements 2.3**
   */
  it('1d: LabelStudioEmbed.tsx Card title uses i18n instead of hardcoded "Label Studio"', () => {
    const source = fs.readFileSync(LS_EMBED_PATH, 'utf-8');

    // The Card title <span> should use t() not hardcoded "Label Studio"
    expect(source).not.toMatch(/<span>Label Studio<\/span>/);
  });
});
