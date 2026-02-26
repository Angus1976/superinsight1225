# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** — 品牌替换不完全
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope to concrete failing cases — the 4 known hardcoded "Label Studio" locations
  - Test file: `frontend/src/components/LabelStudio/__tests__/brand-replacement.test.ts`
  - Test 1a: Read `deploy/label-studio/branding.css` content, assert it contains sidebar-related selectors (e.g. `sidebar`, `logo` hiding in sidebar context, footer link hiding). Currently missing → FAIL
  - Test 1b: Read `deploy/label-studio/i18n-inject.js` TRANSLATIONS object or source, assert it contains sidebar link text entries (e.g. "API", "Documentation") or DOM hiding logic for sidebar footer. Currently missing → FAIL
  - Test 1c: Parse `IframeContainer.tsx` source, assert Card title, Spin tip, Alert message do NOT contain hardcoded `"Label Studio"` string — use `t()` i18n calls instead. Currently hardcoded → FAIL
  - Test 1d: Parse `LabelStudioEmbed.tsx` source, assert Card title `<span>` does NOT contain hardcoded `"Label Studio"` — uses `t()` instead. Currently hardcoded → FAIL
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (confirms bug exists in all 4 files)
  - Document counterexamples found
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** — 现有品牌替换和标注功能不受影响
  - **IMPORTANT**: Follow observation-first methodology
  - Test file: `frontend/src/components/LabelStudio/__tests__/brand-preservation.test.ts`
  - Observe on UNFIXED code:
    - `branding.css` contains `.ls-header__logo img { display: none }` (existing header logo hiding)
    - `branding.css` contains `content: "问视间"` (existing brand text replacement)
    - `branding.css` contains `--ls-brand-primary: #1890ff` (existing theme color)
    - `i18n-inject.js` TRANSLATIONS contains `'Label Studio': '问视间'` (existing brand translation)
    - `i18n-inject.js` exports `translateText`, `switchLanguage` functions (existing API)
    - `LabelStudioEmbed.tsx` uses `useTranslation` hook (existing i18n integration)
    - `LabelStudioEmbed.tsx` error alert uses `t('labelStudio.loadErrorTitle')` (existing i18n usage)
  - Write property-based tests asserting these observed behaviors are preserved:
    - Test 2a: `branding.css` MUST contain existing header logo selectors and brand text `::after` rules
    - Test 2b: `branding.css` MUST contain theme color CSS variables
    - Test 2c: `i18n-inject.js` TRANSLATIONS MUST contain all existing translation entries (snapshot key count ≥ current)
    - Test 2d: `i18n-inject.js` MUST export `translateText` and `switchLanguage` for test/integration use
    - Test 2e: `LabelStudioEmbed.tsx` MUST import and use `useTranslation` hook
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for 品牌替换不完全

  - [x] 3.1 Implement CSS fixes in `deploy/label-studio/branding.css`
    - Add sidebar logo area hiding rules: `[class*="sidebar"] [class*="logo"] img { display: none }` and similar selectors
    - Add sidebar footer links hiding rules: `[class*="sidebar"] [class*="footer"]`, `[class*="sidebar"] a[href*="github"]`, `[class*="sidebar"] a[href*="slack"]` etc.
    - Add version number hiding rule: `[class*="sidebar"] [class*="version"]`
    - _Bug_Condition: branding.css lacks sidebar-related selectors_
    - _Expected_Behavior: sidebar brand elements hidden via CSS_
    - _Preservation: existing header logo, theme color, brand text rules unchanged_
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Implement i18n-inject.js enhancements in `deploy/label-studio/i18n-inject.js`
    - Add sidebar link text translations to TRANSLATIONS dict: "API", "Documentation", "Docs", "GitHub", "Slack Community"
    - Add DOM hiding logic in `translatePage()` for sidebar footer links and version number as CSS backup
    - _Bug_Condition: i18n-inject.js lacks sidebar text translations and DOM hiding_
    - _Expected_Behavior: sidebar text translated, external links and version hidden_
    - _Preservation: existing TRANSLATIONS entries and translateText/switchLanguage API unchanged_
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Replace hardcoded strings in `IframeContainer.tsx`
    - Import `useTranslation` from `react-i18next`
    - Add `const { t } = useTranslation();` in component
    - `title="Label Studio"` → `title={t('labelStudio.title', '标注系统')}`
    - `tip="Loading Label Studio..."` → `tip={t('labelStudio.loading', '正在加载标注系统...')}`
    - `message="Label Studio Error"` → `message={t('labelStudio.loadErrorTitle', '标注系统加载错误')}`
    - _Bug_Condition: IframeContainer contains hardcoded "Label Studio" strings_
    - _Expected_Behavior: all user-facing strings use t() i18n calls_
    - _Preservation: component rendering behavior and props unchanged_
    - _Requirements: 2.3_

  - [x] 3.4 Replace hardcoded string in `LabelStudioEmbed.tsx`
    - `<span>Label Studio</span>` → `<span>{t('labelStudio.title', '标注系统')}</span>`
    - _Bug_Condition: LabelStudioEmbed Card title contains hardcoded "Label Studio"_
    - _Expected_Behavior: Card title uses t() i18n call_
    - _Preservation: component already uses useTranslation, no new imports needed_
    - _Requirements: 2.3_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** — 品牌替换完成
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** — 现有品牌替换和标注功能不受影响
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint — Ensure all tests pass
  - Run `cd frontend && npx vitest run src/components/LabelStudio/__tests__/brand-replacement.test.ts src/components/LabelStudio/__tests__/brand-preservation.test.ts`
  - Ensure all tests pass, ask the user if questions arise.
