/**
 * Property-based test: LogoIcon renders at specified size
 *
 * **Validates: Requirements 1.1**
 *
 * For any valid size value passed to LogoIcon, the rendered SVG element's
 * width and height attributes SHALL equal that size value.
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import * as fc from 'fast-check';
import { LogoIcon } from '../LogoIcon';

describe('LogoIcon - Property Tests', () => {
  it('Property 1: renders SVG at specified size for any positive integer', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 512 }),
        (size) => {
          const { container } = render(<LogoIcon size={size} />);
          const svg = container.querySelector('svg');

          expect(svg).not.toBeNull();
          expect(svg!.getAttribute('width')).toBe(String(size));
          expect(svg!.getAttribute('height')).toBe(String(size));
        },
      ),
      { numRuns: 100 },
    );
  });

  it('renders at default size (32) when no size prop is provided', () => {
    const { container } = render(<LogoIcon />);
    const svg = container.querySelector('svg');

    expect(svg).not.toBeNull();
    expect(svg!.getAttribute('width')).toBe('32');
    expect(svg!.getAttribute('height')).toBe('32');
  });
});
