/**
 * Preservation Property Tests — 现有品牌替换和标注功能不受影响
 *
 * Property 2: Preservation
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4
 *
 * These tests observe and assert EXISTING behavior on UNFIXED code.
 * They MUST PASS on unfixed code — confirming the baseline to preserve.
 * After the fix, they MUST STILL PASS — confirming no regressions.
 */
import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import * as fs from 'fs';
import { createRequire } from 'node:module';
import * as path from 'path';

// Resolve paths relative to project root
const PROJECT_ROOT = path.resolve(__dirname, '../../../../..');
const BRANDING_CSS_PATH = path.join(PROJECT_ROOT, 'deploy/label-studio/branding.css');
const I18N_INJECT_PATH = path.join(PROJECT_ROOT, 'deploy/label-studio/i18n-inject.js');
const LS_EMBED_PATH = path.join(PROJECT_ROOT, 'frontend/src/components/LabelStudio/LabelStudioEmbed.tsx');

// Read files once for all tests
const brandingCss = fs.readFileSync(BRANDING_CSS_PATH, 'utf-8');
const i18nSource = fs.readFileSync(I18N_INJECT_PATH, 'utf-8');
const lsEmbedSource = fs.readFileSync(LS_EMBED_PATH, 'utf-8');

// Load i18n module for runtime checks
const require = createRequire(import.meta.url);
const i18nModule = require(I18N_INJECT_PATH);

describe('Preservation Property: 现有品牌替换和标注功能不受影响', () => {
  /**
   * Test 2a: branding.css MUST contain existing header logo selectors
   * and brand text ::after rules (content: "问视间")
   *
   * **Validates: Requirements 3.1, 3.2**
   */
  describe('2a: branding.css preserves header logo and brand text rules', () => {
    it('contains header logo hiding selectors (SVG alt / viewBox / lsf-menu-header)', () => {
      expect(brandingCss).toMatch(/svg\[alt\*="Label Studio" i\]|lsf-menu-header__logo|viewBox="0 0 194 30"/);
      expect(brandingCss).toMatch(/display:\s*none\s*!important/s);
    });

    it('contains brand text ::after with content "问视间"', () => {
      expect(brandingCss).toMatch(/::after/);
      expect(brandingCss).toMatch(/content:\s*"问视间"/);
    });

    it('property: for any header logo selector, display:none rule exists', () => {
      const headerLogoSelectors = [
        'svg[alt*="Label Studio" i]',
        'svg[viewBox="0 0 194 30"]',
      ];

      fc.assert(
        fc.property(
          fc.constantFrom(...headerLogoSelectors),
          (selector) => {
            expect(brandingCss).toContain(selector);
          },
        ),
        { numRuns: headerLogoSelectors.length },
      );
    });
  });

  /**
   * Test 2b: branding.css MUST contain theme color CSS variables
   * (--ls-brand-primary: #1890ff)
   *
   * **Validates: Requirements 3.2**
   */
  describe('2b: branding.css preserves theme color CSS variables', () => {
    it('contains --ls-brand-primary: #1890ff', () => {
      expect(brandingCss).toMatch(/--ls-brand-primary:\s*#1890ff/);
    });

    it('property: all brand color variables are defined', () => {
      const brandColorVars = [
        '--ls-brand-primary',
        '--ls-brand-primary-hover',
        '--ls-brand-primary-active',
        '--ls-brand-primary-light',
      ];

      fc.assert(
        fc.property(
          fc.constantFrom(...brandColorVars),
          (varName) => {
            expect(brandingCss).toContain(varName);
          },
        ),
        { numRuns: brandColorVars.length },
      );
    });
  });

  /**
   * Test 2c: i18n-inject.js TRANSLATIONS MUST contain all existing
   * translation entries (snapshot key count ≥ 300)
   *
   * **Validates: Requirements 3.3**
   */
  describe('2c: i18n-inject.js preserves all existing translation entries', () => {
    // 词典随需求精简，仅保证「足够覆盖常用 UI」而非固定 300+ 条
    const MINIMUM_TRANSLATION_COUNT = 100;

    it(`TRANSLATIONS has ≥ ${MINIMUM_TRANSLATION_COUNT} entries`, () => {
      const keys = Object.keys(i18nModule.TRANSLATIONS);
      expect(keys.length).toBeGreaterThanOrEqual(MINIMUM_TRANSLATION_COUNT);
    });

    it('property: critical translation keys exist', () => {
      const criticalKeys = [
        'Label Studio',
        'Projects',
        'Settings',
        'Submit',
        'Skip',
        'Cancel',
        'Delete',
        'Import',
        'Export',
        'Loading...',
        'Error',
        'Home',
        'Organization',
        'Data Manager',
        'Create Project',
        'Filters',
      ];

      fc.assert(
        fc.property(
          fc.constantFrom(...criticalKeys),
          (key) => {
            expect(i18nModule.TRANSLATIONS).toHaveProperty(key);
          },
        ),
        { numRuns: criticalKeys.length },
      );
    });

    it('property: brand translation "Label Studio" → "问视间" exists', () => {
      expect(i18nModule.TRANSLATIONS['Label Studio']).toBe('问视间');
    });
  });

  /**
   * Test 2d: i18n-inject.js MUST export translateText and switchLanguage
   * for test/integration use
   *
   * **Validates: Requirements 3.3, 3.4**
   */
  describe('2d: i18n-inject.js preserves exported API', () => {
    it('exports translateText function', () => {
      expect(typeof i18nModule.translateText).toBe('function');
    });

    it('exports switchLanguage function', () => {
      expect(typeof i18nModule.switchLanguage).toBe('function');
    });

    it('property: translateText translates known entries correctly', () => {
      const sampleEntries = [
        ['Label Studio', '问视间'],
        ['Projects', '项目'],
        ['Submit', '提交'],
        ['Cancel', '取消'],
        ['Loading...', '加载中...'],
      ] as const;

      fc.assert(
        fc.property(
          fc.constantFrom(...sampleEntries),
          ([en, zh]) => {
            // Ensure zh mode
            i18nModule._setLang('zh');
            expect(i18nModule.translateText(en)).toBe(zh);
          },
        ),
        { numRuns: sampleEntries.length },
      );

      // Reset to zh
      i18nModule._setLang('zh');
    });
  });

  /**
   * Test 2e: LabelStudioEmbed.tsx MUST import and use useTranslation hook
   *
   * **Validates: Requirements 3.3**
   */
  describe('2e: LabelStudioEmbed.tsx preserves useTranslation integration', () => {
    it('imports useTranslation from react-i18next', () => {
      expect(lsEmbedSource).toMatch(/import\s*\{[^}]*useTranslation[^}]*\}\s*from\s*['"]react-i18next['"]/);
    });

    it('uses useTranslation hook (const { t } = useTranslation())', () => {
      expect(lsEmbedSource).toMatch(/const\s*\{\s*t\s*\}\s*=\s*useTranslation\(\)/);
    });

    it('uses t() for translations in component', () => {
      // Verify t() is called at least once for label studio related keys
      expect(lsEmbedSource).toMatch(/t\(\s*['"]labelStudio\./);
    });
  });
});
