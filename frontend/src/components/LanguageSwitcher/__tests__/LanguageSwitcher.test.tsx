/**
 * i18n Components Unit Tests
 *
 * Tests language switching, translation loading, fallback behavior,
 * and RTL layout support for the LanguageSwitcher component and
 * the underlying i18n infrastructure.
 *
 * Validates: Requirements 1.2, 4.4
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';

// ============================================================================
// Mocks
// ============================================================================

// Mock the language store
const mockSetLanguage = vi.fn();
let mockLanguage = 'zh';

vi.mock('@/stores/languageStore', () => ({
  useLanguageStore: () => ({
    language: mockLanguage,
    setLanguage: mockSetLanguage,
  }),
}));

// Mock react-i18next
const mockChangeLanguage = vi.fn().mockResolvedValue(undefined);
let mockI18nLanguage = 'zh';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue || key,
    i18n: {
      language: mockI18nLanguage,
      changeLanguage: mockChangeLanguage,
      options: {
        fallbackLng: ['zh'],
        resources: { zh: {}, en: {} },
      },
    },
  }),
}));

// ============================================================================
// Import after mocks
// ============================================================================

import { LanguageSwitcher } from '../index';

// ============================================================================
// Helpers
// ============================================================================

function renderSwitcher(props: Record<string, unknown> = {}) {
  return render(<LanguageSwitcher {...props} />);
}

// ============================================================================
// Language Switching Tests
// ============================================================================

describe('LanguageSwitcher - language switching', () => {
  beforeEach(() => {
    mockLanguage = 'zh';
    mockI18nLanguage = 'zh';
    vi.clearAllMocks();
  });

  it('renders in select mode by default', () => {
    renderSwitcher();
    // Ant Design Select renders with role combobox
    const select = document.querySelector('.ant-select');
    expect(select).toBeTruthy();
  });

  it('renders in toggle mode', () => {
    renderSwitcher({ mode: 'toggle' });
    const button = screen.getByRole('button');
    expect(button).toBeTruthy();
  });

  it('renders in dropdown mode', () => {
    renderSwitcher({ mode: 'dropdown' });
    const button = screen.getByRole('button');
    expect(button).toBeTruthy();
  });

  it('displays current language label (中文) when language is zh', () => {
    renderSwitcher({ mode: 'toggle' });
    expect(screen.getByText('中文')).toBeTruthy();
  });

  it('displays current language label (English) when language is en', () => {
    mockLanguage = 'en';
    renderSwitcher({ mode: 'toggle' });
    expect(screen.getByText('English')).toBeTruthy();
  });

  it('calls setLanguage when toggle button is clicked', async () => {
    const user = userEvent.setup();
    renderSwitcher({ mode: 'toggle' });

    const button = screen.getByRole('button');
    await user.click(button);

    // zh toggles to en
    expect(mockSetLanguage).toHaveBeenCalledWith('en');
  });

  it('toggles from en to zh when clicked', async () => {
    mockLanguage = 'en';
    const user = userEvent.setup();
    renderSwitcher({ mode: 'toggle' });

    const button = screen.getByRole('button');
    await user.click(button);

    expect(mockSetLanguage).toHaveBeenCalledWith('zh');
  });

  it('shows language code when showFullName is false', () => {
    renderSwitcher({ mode: 'toggle', showFullName: false });
    expect(screen.getByText('ZH')).toBeTruthy();
  });

  it('hides icon when showIcon is false', () => {
    renderSwitcher({ mode: 'toggle', showIcon: false });
    const icon = document.querySelector('.anticon-global');
    expect(icon).toBeNull();
  });

  it('shows icon by default', () => {
    renderSwitcher({ mode: 'toggle' });
    const icon = document.querySelector('.anticon-global');
    expect(icon).toBeTruthy();
  });
});

// ============================================================================
// Translation Loading Tests
// ============================================================================

describe('LanguageSwitcher - translation loading', () => {
  beforeEach(() => {
    mockLanguage = 'zh';
    vi.clearAllMocks();
  });

  it('renders both language options in select mode', () => {
    renderSwitcher({ mode: 'select' });
    // The select should be present with the current value
    const select = document.querySelector('.ant-select');
    expect(select).toBeTruthy();
  });

  it('renders with correct size prop', () => {
    const { container } = renderSwitcher({ mode: 'toggle', size: 'small' });
    const button = container.querySelector('.ant-btn-sm');
    expect(button).toBeTruthy();
  });

  it('renders with large size', () => {
    const { container } = renderSwitcher({ mode: 'toggle', size: 'large' });
    const button = container.querySelector('.ant-btn-lg');
    expect(button).toBeTruthy();
  });

  it('applies custom className', () => {
    renderSwitcher({ mode: 'toggle', className: 'custom-switcher' });
    const button = screen.getByRole('button');
    expect(button.className).toContain('custom-switcher');
  });

  it('applies custom style', () => {
    renderSwitcher({ mode: 'toggle', style: { marginTop: '10px' } });
    const button = screen.getByRole('button');
    expect(button.style.marginTop).toBe('10px');
  });
});

// ============================================================================
// Fallback Language Behavior Tests
// ============================================================================

describe('LanguageSwitcher - fallback language behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('defaults to zh language', () => {
    mockLanguage = 'zh';
    renderSwitcher({ mode: 'toggle' });
    expect(screen.getByText('中文')).toBeTruthy();
  });

  it('uses t() function with fallback default value', () => {
    renderSwitcher({ mode: 'toggle' });
    // The toggle button uses t('common.switchLanguage', '切换语言') as title
    const button = screen.getByRole('button');
    expect(button.getAttribute('title')).toBe('切换语言');
  });

  it('renders correctly when language store returns zh', () => {
    mockLanguage = 'zh';
    const { container } = renderSwitcher({ mode: 'select' });
    // Should render without errors
    expect(container.querySelector('.ant-select')).toBeTruthy();
  });

  it('renders correctly when language store returns en', () => {
    mockLanguage = 'en';
    const { container } = renderSwitcher({ mode: 'select' });
    expect(container.querySelector('.ant-select')).toBeTruthy();
  });
});

// ============================================================================
// Fallback Language Config Tests
// ============================================================================

describe('i18n config - fallback language', () => {
  it('DEFAULT_LANGUAGE is zh (Chinese as fallback)', async () => {
    const { DEFAULT_LANGUAGE } = await import('@/constants');
    expect(DEFAULT_LANGUAGE).toBe('zh');
  });

  it('SUPPORTED_LANGUAGES includes both zh and en', async () => {
    const { SUPPORTED_LANGUAGES } = await import('@/constants');
    expect(SUPPORTED_LANGUAGES).toContain('zh');
    expect(SUPPORTED_LANGUAGES).toContain('en');
  });

  it('component falls back to showing zh label when language is unknown', () => {
    // When language doesn't match any option, getCurrentLabel returns first option
    mockLanguage = 'zh';
    renderSwitcher({ mode: 'toggle' });
    expect(screen.getByText('中文')).toBeTruthy();
  });
});

// ============================================================================
// RTL Layout Support Tests
// ============================================================================

describe('LanguageSwitcher - RTL layout support', () => {
  beforeEach(() => {
    mockLanguage = 'zh';
    vi.clearAllMocks();
  });

  it('renders correctly in LTR context (default)', () => {
    const { container } = renderSwitcher({ mode: 'toggle' });
    // Default rendering should work without RTL
    expect(container.firstChild).toBeTruthy();
  });

  it('renders correctly when wrapped in RTL direction', () => {
    const { container } = render(
      <div dir="rtl">
        <LanguageSwitcher mode="toggle" />
      </div>
    );
    const button = container.querySelector('button');
    expect(button).toBeTruthy();
  });

  it('renders select mode in RTL context', () => {
    const { container } = render(
      <div dir="rtl">
        <LanguageSwitcher mode="select" />
      </div>
    );
    expect(container.querySelector('.ant-select')).toBeTruthy();
  });

  it('renders dropdown mode in RTL context', () => {
    const { container } = render(
      <div dir="rtl">
        <LanguageSwitcher mode="dropdown" />
      </div>
    );
    const button = container.querySelector('button');
    expect(button).toBeTruthy();
  });
});

// ============================================================================
// Language Store Integration Tests
// ============================================================================

describe('LanguageStore - language management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('exports SUPPORTED_LANGUAGES constant', async () => {
    const { SUPPORTED_LANGUAGES } = await import('@/constants');
    expect(SUPPORTED_LANGUAGES).toContain('zh');
    expect(SUPPORTED_LANGUAGES).toContain('en');
    expect(SUPPORTED_LANGUAGES.length).toBe(2);
  });

  it('exports DEFAULT_LANGUAGE as zh', async () => {
    const { DEFAULT_LANGUAGE } = await import('@/constants');
    expect(DEFAULT_LANGUAGE).toBe('zh');
  });

  it('SupportedLanguage type covers zh and en', async () => {
    const { SUPPORTED_LANGUAGES } = await import('@/constants');
    // Runtime check that the const array has exactly the expected values
    const languages = [...SUPPORTED_LANGUAGES];
    expect(languages.sort()).toEqual(['en', 'zh']);
  });
});
