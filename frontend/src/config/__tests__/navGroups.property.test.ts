/**
 * Property Tests for buildMenuRoutes
 *
 * **Validates: Requirements 2.1, 2.2, 2.3, 2.6**
 *
 * Property 2: buildMenuRoutes produces correct structure with role-based filtering
 * Property 3: buildMenuRoutes does not mutate input
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { buildMenuRoutes, type NavGroup, type MenuItem } from '../navGroups';

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

const pathSegmentArb = fc.stringMatching(/^[a-z][a-z0-9]{0,7}$/);

const pathArb = fc
  .array(pathSegmentArb, { minLength: 1, maxLength: 3 })
  .map((segments) => '/' + segments.join('/'));

const accessArb: fc.Arbitrary<'admin' | undefined> = fc.constantFrom('admin' as const, undefined);

const childMenuItemArb: fc.Arbitrary<MenuItem> = fc.record({
  path: pathArb,
  nameKey: fc.string({ minLength: 1, maxLength: 20 }),
  access: accessArb,
}).map(({ path, nameKey, access }) => {
  const item: MenuItem = { path, nameKey };
  if (access) item.access = access;
  return item;
});

const menuItemArb: fc.Arbitrary<MenuItem> = fc.record({
  path: pathArb,
  nameKey: fc.string({ minLength: 1, maxLength: 20 }),
  access: accessArb,
  children: fc.option(fc.array(childMenuItemArb, { minLength: 1, maxLength: 4 }), { nil: undefined }),
}).map(({ path, nameKey, access, children }) => {
  const item: MenuItem = { path, nameKey };
  if (access) item.access = access;
  if (children) item.children = children;
  return item;
});

const navGroupArb: fc.Arbitrary<NavGroup> = fc.record({
  key: fc.string({ minLength: 1, maxLength: 15 }),
  titleKey: fc.string({ minLength: 1, maxLength: 30 }),
  items: fc.array(menuItemArb, { minLength: 1, maxLength: 6 }),
});

const navGroupsArb = fc.array(navGroupArb, { minLength: 0, maxLength: 5 });

const userRoleArb = fc.constantFrom('admin', 'user');

const mockT = (key: string) => `t(${key})`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Count items visible for a given role within a group. */
function countVisibleItems(group: NavGroup, role: string): number {
  return group.items.filter(
    (item) => item.access !== 'admin' || role === 'admin',
  ).length;
}

// ---------------------------------------------------------------------------
// Property 2: buildMenuRoutes produces correct structure with role-based filtering
// ---------------------------------------------------------------------------

describe('Property 2: buildMenuRoutes produces correct structure with role-based filtering', () => {
  /**
   * **Validates: Requirements 2.1, 2.2, 2.3**
   *
   * (a) Each group with visible items has exactly one group divider followed by its visible items.
   */
  it('each group with visible items has exactly one divider followed by its items', () => {
    fc.assert(
      fc.property(navGroupsArb, userRoleArb, (groups, role) => {
        const routes = buildMenuRoutes(groups, role, mockT);

        let routeIdx = 0;
        for (const group of groups) {
          const visibleCount = countVisibleItems(group, role);
          if (visibleCount === 0) continue;

          // Expect a group divider
          const divider = routes[routeIdx];
          expect(divider).toBeDefined();
          expect(divider.itemType).toBe('group');
          expect(divider.path).toBe(`/_group_${group.key}`);
          routeIdx++;

          // Expect exactly visibleCount item entries after the divider
          for (let i = 0; i < visibleCount; i++) {
            const item = routes[routeIdx];
            expect(item).toBeDefined();
            expect(item.itemType).toBeUndefined();
            routeIdx++;
          }
        }

        // All routes consumed
        expect(routeIdx).toBe(routes.length);
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 2.2**
   *
   * (b) No item with access='admin' appears when userRole is 'user'.
   */
  it('no admin-only item appears when userRole is "user"', () => {
    fc.assert(
      fc.property(navGroupsArb, (groups) => {
        const routes = buildMenuRoutes(groups, 'user', mockT);

        // Build a set of translated names for admin-only items.
        // Using names (not paths) avoids false positives when a
        // non-admin item happens to share the same path as an
        // admin-only item in a different group.
        const adminNames = new Set(
          groups.flatMap((g) =>
            g.items
              .filter((i) => i.access === 'admin')
              .map((i) => mockT(`menu.${i.nameKey}`)),
          ),
        );

        // Also collect names that belong to non-admin items so we
        // can exclude shared names from the check.
        const nonAdminNames = new Set(
          groups.flatMap((g) =>
            g.items
              .filter((i) => i.access !== 'admin')
              .map((i) => mockT(`menu.${i.nameKey}`)),
          ),
        );

        // Names that are exclusively admin-only
        const exclusiveAdminNames = new Set(
          [...adminNames].filter((n) => !nonAdminNames.has(n)),
        );

        // No route should carry an exclusively-admin name
        for (const route of routes) {
          if (route.itemType !== 'group') {
            expect(exclusiveAdminNames.has(route.name)).toBe(false);
          }
        }
      }),
      { numRuns: 200 },
    );
  });

  /**
   * **Validates: Requirement 2.3**
   *
   * (c) Groups with zero visible items after filtering produce no divider entry.
   */
  it('groups with zero visible items produce no divider', () => {
    fc.assert(
      fc.property(navGroupsArb, userRoleArb, (groups, role) => {
        const routes = buildMenuRoutes(groups, role, mockT);

        const dividerKeys = routes
          .filter((r) => r.itemType === 'group')
          .map((r) => r.path.replace('/_group_', ''));

        for (const group of groups) {
          const visibleCount = countVisibleItems(group, role);
          if (visibleCount === 0) {
            expect(dividerKeys).not.toContain(group.key);
          }
        }
      }),
      { numRuns: 200 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 3: buildMenuRoutes does not mutate input
// ---------------------------------------------------------------------------

describe('Property 3: buildMenuRoutes does not mutate input', () => {
  /**
   * **Validates: Requirement 2.6**
   *
   * For any NavGroup[] input, calling buildMenuRoutes SHALL leave the original
   * array deeply equal to its state before the call.
   */
  it('original groups array is deeply unchanged after buildMenuRoutes call', () => {
    fc.assert(
      fc.property(navGroupsArb, userRoleArb, (groups, role) => {
        // Deep snapshot before (strip icon since it's React element / undefined)
        const snapshot = JSON.parse(JSON.stringify(groups));

        buildMenuRoutes(groups, role, mockT);

        // Deep equality check after
        expect(JSON.parse(JSON.stringify(groups))).toEqual(snapshot);
      }),
      { numRuns: 200 },
    );
  });
});
