/**
 * Property Tests for ClientBranding
 *
 * **Validates: Requirements 3.1, 3.2, 3.4, 7.1**
 *
 * Property 4: ClientBranding renders correct visual based on logo presence
 * Property 5: Collapsed mode hides text across branding components
 * Property 8: Client logo URL validation rejects malicious inputs
 */

import { describe, it, expect, afterEach } from 'vitest';
import * as fc from 'fast-check';
import { render } from '@testing-library/react';
import { ClientBranding, isValidLogoUrl } from '../ClientBranding';
import { useUIStore, type ClientCompany } from '@/stores/uiStore';

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Non-empty company name (1-20 chars, no whitespace-only) */
const companyNameArb = fc.string({ minLength: 1, maxLength: 20 }).filter((s) => s.trim().length > 0);

/** Valid http/https logo URL */
const validLogoUrlArb = fc
  .record({
    protocol: fc.constantFrom('http', 'https'),
    domain: fc.stringMatching(/^[a-z][a-z0-9]{1,10}$/),
    tld: fc.constantFrom('com', 'org', 'net', 'io'),
    path: fc.stringMatching(/^[a-z0-9]{1,8}$/),
    ext: fc.constantFrom('png', 'jpg', 'svg', 'webp'),
  })
  .map(({ protocol, domain, tld, path, ext }) => `${protocol}://${domain}.${tld}/${path}.${ext}`);

/** Optional label string */
const labelArb = fc.option(fc.string({ minLength: 1, maxLength: 15 }), { nil: undefined });

/** ClientCompany with a valid logo URL */
const companyWithLogoArb: fc.Arbitrary<ClientCompany> = fc.record({
  name: companyNameArb,
  nameEn: companyNameArb,
  logo: validLogoUrlArb,
  label: labelArb,
});

/** ClientCompany without a logo (undefined or empty string) */
const companyWithoutLogoArb: fc.Arbitrary<ClientCompany> = fc.record({
  name: companyNameArb,
  nameEn: companyNameArb,
  label: labelArb,
}).map(({ name, nameEn, label }) => {
  const c: ClientCompany = { name, nameEn };
  if (label) c.label = label;
  return c;
});

/** Any ClientCompany (with or without logo) */
const anyCompanyArb: fc.Arbitrary<ClientCompany> = fc.oneof(companyWithLogoArb, companyWithoutLogoArb);

/** clientCompany state: company or null */
const clientCompanyStateArb: fc.Arbitrary<ClientCompany | null> = fc.oneof(
  anyCompanyArb,
  fc.constant(null),
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setClientCompany(company: ClientCompany | null) {
  useUIStore.setState({ clientCompany: company });
}

// ---------------------------------------------------------------------------
// Property 4: ClientBranding renders correct visual based on logo presence
// ---------------------------------------------------------------------------

describe('Property 4: ClientBranding renders correct visual based on logo presence', () => {
  afterEach(() => {
    setClientCompany(null);
  });

  /**
   * **Validates: Requirements 3.1**
   *
   * If a valid logo URL is present, the rendered output contains an img element
   * with that URL and the company name text.
   */
  it('renders img with logo URL and company name when logo is present', () => {
    fc.assert(
      fc.property(companyWithLogoArb, (company) => {
        setClientCompany(company);
        const { container, unmount } = render(<ClientBranding collapsed={false} />);

        const img = container.querySelector('img');
        expect(img).not.toBeNull();
        expect(img!.getAttribute('src')).toBe(company.logo);
        expect(img!.getAttribute('alt')).toBe(company.name);

        // Company name text is visible (use container-scoped query to avoid cross-render leaks)
        const nameEl = container.querySelector('[class*="companyName"]');
        expect(nameEl).not.toBeNull();
        expect(nameEl!.textContent).toBe(company.name);

        unmount();
      }),
      { numRuns: 50 },
    );
  });

  /**
   * **Validates: Requirements 3.2**
   *
   * If no logo URL is present, the rendered output contains an Avatar displaying
   * the first character of the company name.
   */
  it('renders Avatar with first character when no logo is present', () => {
    fc.assert(
      fc.property(companyWithoutLogoArb, (company) => {
        setClientCompany(company);
        const { container, unmount } = render(<ClientBranding collapsed={false} />);

        // No img element
        const img = container.querySelector('img');
        expect(img).toBeNull();

        // Avatar with first character of company name
        const avatar = container.querySelector('.ant-avatar');
        expect(avatar).not.toBeNull();
        expect(avatar!.textContent).toContain(company.name.charAt(0));

        unmount();
      }),
      { numRuns: 50 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 5: Collapsed mode hides text across branding components
// ---------------------------------------------------------------------------

describe('Property 5: Collapsed mode hides text across branding components', () => {
  afterEach(() => {
    setClientCompany(null);
  });

  /**
   * **Validates: Requirement 3.4**
   *
   * For any ClientCompany configuration (including null) with collapsed=true,
   * ClientBranding renders no visible text content — only Avatar or Icon element.
   */
  it('renders no text content when collapsed, only Avatar or Icon', () => {
    fc.assert(
      fc.property(clientCompanyStateArb, (company) => {
        setClientCompany(company);
        const { container, unmount } = render(<ClientBranding collapsed={true} />);

        // No company name, brand name, or label text should be rendered
        const spans = container.querySelectorAll('span');
        for (const span of spans) {
          // Ant Design Avatar renders a span — allow avatar content (single char)
          const isAvatarContent = span.closest('.ant-avatar') !== null;
          if (!isAvatarContent) {
            // Non-avatar spans should not exist (brand name, company name, etc.)
            expect(span.className).not.toMatch(/brandName|companyName/);
          }
        }

        // No .info block (company name + label container) should be rendered
        const infoBlocks = container.querySelectorAll('[class*="info"]');
        expect(infoBlocks.length).toBe(0);

        // No brandName text should be rendered (null clientCompany case)
        const brandName = container.querySelector('[class*="brandName"]');
        expect(brandName).toBeNull();

        // Should have either an Avatar, an SVG (LogoIcon), or an img (logo with valid URL)
        const avatar = container.querySelector('.ant-avatar');
        const svg = container.querySelector('svg');
        const img = container.querySelector('img');
        expect(avatar !== null || svg !== null || img !== null).toBe(true);

        unmount();
      }),
      { numRuns: 50 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 8: Client logo URL validation rejects malicious inputs
// ---------------------------------------------------------------------------

describe('Property 8: Client logo URL validation rejects malicious inputs', () => {
  /**
   * **Validates: Requirement 7.1**
   *
   * For any string that is NOT a valid HTTP/HTTPS URL, isValidLogoUrl rejects it.
   * This includes javascript:, data:, blob:, and other dangerous schemes.
   */
  it('rejects non-http/https schemes', () => {
    const maliciousSchemeArb = fc
      .record({
        scheme: fc.constantFrom(
          'javascript',
          'data',
          'blob',
          'vbscript',
          'file',
          'ftp',
          'data:text/html',
        ),
        payload: fc.string({ minLength: 1, maxLength: 30 }),
      })
      .map(({ scheme, payload }) => `${scheme}:${payload}`);

    fc.assert(
      fc.property(maliciousSchemeArb, (url) => {
        expect(isValidLogoUrl(url)).toBe(false);
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 7.1**
   *
   * Empty strings, whitespace-only strings, and non-string-like inputs are rejected.
   */
  it('rejects empty and whitespace-only strings', () => {
    const emptyishArb = fc.constantFrom('', ' ', '  ', '\t', '\n', '   \n  ');

    fc.assert(
      fc.property(emptyishArb, (url) => {
        expect(isValidLogoUrl(url)).toBe(false);
      }),
    );
  });

  /**
   * **Validates: Requirement 7.1**
   *
   * Valid http/https URLs should be accepted.
   */
  it('accepts valid http and https URLs', () => {
    fc.assert(
      fc.property(validLogoUrlArb, (url) => {
        expect(isValidLogoUrl(url)).toBe(true);
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 7.1**
   *
   * Random strings that don't form valid URLs are rejected.
   */
  it('rejects random non-URL strings', () => {
    const nonUrlArb = fc
      .string({ minLength: 1, maxLength: 50 })
      .filter((s) => {
        const trimmed = s.trim();
        // Root-relative paths are now valid
        if (trimmed.startsWith('/')) return false;
        try {
          const parsed = new URL(trimmed);
          return parsed.protocol !== 'http:' && parsed.protocol !== 'https:';
        } catch {
          return true; // not a valid URL at all → should be rejected
        }
      });

    fc.assert(
      fc.property(nonUrlArb, (str) => {
        expect(isValidLogoUrl(str)).toBe(false);
      }),
      { numRuns: 200 },
    );
  });
});
