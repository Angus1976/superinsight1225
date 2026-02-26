/**
 * Property Tests: 智能帮助助手
 *
 * **Validates: Requirements 2.A, 2.C, 3.A, 3.B**
 *
 * 属性 1: ∀ context: HelpContext, resolveHelpKey(context) 返回非空字符串
 * 属性 2: helpStore.visible === true ⟹ helpStore.currentHelpKey !== null
 *         helpStore.visible === false ⟹ helpStore.currentHelpKey === null
 * 属性 3: validateHelpKey 只接受 [a-zA-Z0-9._] 格式
 * 属性 4: 任意 helpKey 字符串传入 showHelp 不会抛异常
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { resolveHelpKey, validateHelpKey } from '@/utils/helpUtils';
import { useHelpStore } from '@/stores/helpStore';
import type { HelpContext } from '@/types/help';
import '@/locales/config';

// --- Generators ---

/** 生成合法的页面标识（非空字母数字） */
const pageArb = fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9]{0,19}$/);

/** 生成可选的组件/元素标识 */
const optionalSegmentArb = fc.option(
  fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9]{0,19}$/),
  { nil: undefined },
);

/** 生成任意有效 HelpContext */
const helpContextArb: fc.Arbitrary<HelpContext> = fc.record({
  page: pageArb,
  component: optionalSegmentArb,
  element: optionalSegmentArb,
});

/** 生成符合 [a-zA-Z0-9._] 的字符串 */
const validHelpKeyArb = fc.stringMatching(/^[a-zA-Z0-9._]+$/);

/** 生成包含非法字符的字符串 */
const invalidHelpKeyArb = fc.stringMatching(/^.*[^a-zA-Z0-9._].*$/);

// --- Property Tests ---

describe('SmartHelp property tests', () => {
  beforeEach(() => {
    useHelpStore.setState({
      visible: false,
      currentHelpKey: null,
      position: null,
    });
  });

  /**
   * **Validates: Requirements 2.A**
   * 属性 1: resolveHelpKey always returns non-empty string
   */
  it('resolveHelpKey always returns a non-empty string for any valid HelpContext', () => {
    fc.assert(
      fc.property(helpContextArb, (context) => {
        const result = resolveHelpKey(context);
        expect(typeof result).toBe('string');
        expect(result.length).toBeGreaterThan(0);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 3.A, 3.B**
   * 属性 2a: After showHelp — visible === true ⟹ currentHelpKey !== null
   */
  it('showHelp establishes invariant: visible === true ⟹ currentHelpKey !== null', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 30 }),
        fc.option(
          fc.record({ x: fc.integer({ min: 0, max: 2000 }), y: fc.integer({ min: 0, max: 2000 }) }),
          { nil: undefined },
        ),
        (helpKey, position) => {
          useHelpStore.getState().showHelp(helpKey, position);
          const state = useHelpStore.getState();

          if (state.visible) {
            expect(state.currentHelpKey).not.toBeNull();
          }

          // Reset for next iteration
          useHelpStore.setState({ visible: false, currentHelpKey: null, position: null });
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 3.A, 3.B**
   * 属性 2b: After hideHelp — visible === false ⟹ currentHelpKey === null ∧ position === null
   */
  it('hideHelp establishes invariant: visible === false ⟹ currentHelpKey === null ∧ position === null', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 30 }),
        (helpKey) => {
          useHelpStore.getState().showHelp(helpKey);
          useHelpStore.getState().hideHelp();
          const state = useHelpStore.getState();

          expect(state.visible).toBe(false);
          expect(state.currentHelpKey).toBeNull();
          expect(state.position).toBeNull();
        },
      ),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 3.A, 3.B**
   * 属性 2c: After any sequence of showHelp/hideHelp/toggleHelp, invariant holds
   */
  it('state invariant holds after arbitrary sequences of showHelp/hideHelp/toggleHelp', () => {
    /** Operation model: 0=showHelp, 1=hideHelp, 2=toggleHelp */
    const operationArb = fc.array(
      fc.record({
        op: fc.constantFrom(0, 1, 2),
        key: fc.string({ minLength: 1, maxLength: 20 }),
      }),
      { minLength: 1, maxLength: 20 },
    );

    fc.assert(
      fc.property(operationArb, (operations) => {
        useHelpStore.setState({ visible: false, currentHelpKey: null, position: null });

        for (const { op, key } of operations) {
          const store = useHelpStore.getState();
          if (op === 0) {
            store.showHelp(key);
          } else if (op === 1) {
            store.hideHelp();
          } else {
            store.toggleHelp();
          }
        }

        const state = useHelpStore.getState();
        if (state.visible) {
          expect(state.currentHelpKey).not.toBeNull();
        }
        if (!state.visible) {
          expect(state.currentHelpKey).toBeNull();
        }
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 2.C**
   * 属性 3a: validateHelpKey accepts strings matching [a-zA-Z0-9._]
   */
  it('validateHelpKey accepts any string matching [a-zA-Z0-9._]+', () => {
    fc.assert(
      fc.property(validHelpKeyArb, (key) => {
        expect(validateHelpKey(key)).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 2.C**
   * 属性 3b: validateHelpKey rejects strings with characters outside [a-zA-Z0-9._]
   */
  it('validateHelpKey rejects any string containing characters outside [a-zA-Z0-9._]', () => {
    fc.assert(
      fc.property(invalidHelpKeyArb, (key) => {
        expect(validateHelpKey(key)).toBe(false);
      }),
      { numRuns: 100 },
    );
  });

  /**
   * **Validates: Requirements 3.A**
   * 属性 4: arbitrary helpKey string passed to showHelp does not throw
   */
  it('showHelp does not throw for any arbitrary string', () => {
    fc.assert(
      fc.property(fc.string(), (key) => {
        expect(() => {
          useHelpStore.getState().showHelp(key);
        }).not.toThrow();

        // Reset for next iteration
        useHelpStore.setState({ visible: false, currentHelpKey: null, position: null });
      }),
      { numRuns: 100 },
    );
  });
});
