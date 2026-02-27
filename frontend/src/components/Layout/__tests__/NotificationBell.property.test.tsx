/**
 * Property Tests for NotificationBell
 *
 * **Validates: Requirement 4.4**
 *
 * Property 7: NotificationBell displays correct badge count
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import * as fc from 'fast-check';
import { render, cleanup } from '@testing-library/react';
import { NotificationBell } from '../NotificationBell';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
}));

afterEach(() => {
  cleanup();
});

// ---------------------------------------------------------------------------
// Property 7: NotificationBell displays correct badge count
// ---------------------------------------------------------------------------

describe('Property 7: NotificationBell displays correct badge count', () => {
  const noop = () => {};

  /**
   * **Validates: Requirement 4.4**
   *
   * For any positive integer count, the rendered Badge SHALL carry that
   * exact count in its title attribute (Ant Design Badge stores the real
   * value there regardless of overflow display).
   */
  it('Badge title reflects the exact count for any positive integer', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 9999 }),
        (count) => {
          const { container, unmount } = render(
            <NotificationBell count={count} onClick={noop} />,
          );

          const badge = container.querySelector('.ant-badge-count');
          expect(badge).toBeTruthy();
          expect(badge!.getAttribute('title')).toBe(String(count));

          unmount();
          cleanup();
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirement 4.4**
   *
   * When count is 0, the Badge SHALL not display any visible count.
   */
  it('hides the badge count when count is 0', () => {
    const { container } = render(
      <NotificationBell count={0} onClick={noop} />,
    );

    const badge = container.querySelector('.ant-badge-count');
    const isHidden =
      !badge || badge.classList.contains('ant-badge-count-hidden');
    expect(isHidden).toBe(true);
  });
});
