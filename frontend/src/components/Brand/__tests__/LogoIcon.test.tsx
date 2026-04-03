/**
 * Property-based test: LogoIcon renders at specified size
 *
 * **Validates: Requirements 1.1**
 *
 * LogoIcon 使用 <img width/height>（非内联 SVG）。在成功渲染图片时，
 * width/height 属性应等于传入的 size。
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
          const img = container.querySelector('img');

          expect(img).not.toBeNull();
          expect(img!.getAttribute('width')).toBe(String(size));
          expect(img!.getAttribute('height')).toBe(String(size));
        },
      ),
      { numRuns: 100 },
    );
  });

  it('renders at default size (32) when no size prop is provided', () => {
    const { container } = render(<LogoIcon />);
    const img = container.querySelector('img');

    expect(img).not.toBeNull();
    expect(img!.getAttribute('width')).toBe('32');
    expect(img!.getAttribute('height')).toBe('32');
  });
});
