import { describe, it, expect } from 'vitest';
import {
  buildMenuRoutes,
  NAV_GROUPS,
  type NavGroup,
  type MenuItem,
} from '../navGroups';

// Simple identity translator for testing
const mockT = (key: string) => key;

describe('NAV_GROUPS', () => {
  it('defines 5 groups with expected keys', () => {
    const keys = NAV_GROUPS.map((g) => g.key);
    expect(keys).toEqual([
      'workbench',
      'dataManage',
      'aiCapability',
      'qualitySec',
      'system',
    ]);
  });

  it('every group has at least one item', () => {
    for (const group of NAV_GROUPS) {
      expect(group.items.length).toBeGreaterThan(0);
    }
  });
});

describe('buildMenuRoutes', () => {
  const simpleGroups: NavGroup[] = [
    {
      key: 'g1',
      titleKey: 'navGroup.g1',
      items: [
        { path: '/a', nameKey: 'a' },
        { path: '/b', nameKey: 'b', access: 'admin' },
      ],
    },
  ];

  it('produces group divider followed by visible items', () => {
    const routes = buildMenuRoutes(simpleGroups, 'admin', mockT);
    expect(routes[0]).toMatchObject({
      path: '/_group_g1',
      name: 'navGroup.g1',
      itemType: 'group',
    });
    expect(routes[1]).toMatchObject({ path: '/a', name: 'menu.a' });
    expect(routes[2]).toMatchObject({ path: '/b', name: 'menu.b' });
    expect(routes).toHaveLength(3);
  });

  it('filters admin items when userRole is not admin', () => {
    const routes = buildMenuRoutes(simpleGroups, 'user', mockT);
    expect(routes).toHaveLength(2); // divider + /a
    expect(routes.every((r) => r.path !== '/b')).toBe(true);
  });

  it('omits group divider when all items are filtered out', () => {
    const adminOnlyGroup: NavGroup[] = [
      {
        key: 'secret',
        titleKey: 'navGroup.secret',
        items: [{ path: '/x', nameKey: 'x', access: 'admin' }],
      },
    ];
    const routes = buildMenuRoutes(adminOnlyGroup, 'user', mockT);
    expect(routes).toHaveLength(0);
  });

  it('filters admin children within items', () => {
    const groupWithChildren: NavGroup[] = [
      {
        key: 'mixed',
        titleKey: 'navGroup.mixed',
        items: [
          {
            path: '/parent',
            nameKey: 'parent',
            children: [
              { path: '/parent/public', nameKey: 'pub' },
              { path: '/parent/secret', nameKey: 'sec', access: 'admin' },
            ],
          },
        ],
      },
    ];
    const routes = buildMenuRoutes(groupWithChildren, 'user', mockT);
    expect(routes).toHaveLength(2); // divider + parent
    const parentRoute = routes[1];
    expect(parentRoute.routes).toHaveLength(1);
    expect(parentRoute.routes![0].path).toBe('/parent/public');
  });

  it('removes children array when all children are admin-only and user is not admin', () => {
    const groupAllAdminChildren: NavGroup[] = [
      {
        key: 'g',
        titleKey: 'navGroup.g',
        items: [
          {
            path: '/p',
            nameKey: 'p',
            children: [
              { path: '/p/a', nameKey: 'a', access: 'admin' },
            ],
          },
        ],
      },
    ];
    const routes = buildMenuRoutes(groupAllAdminChildren, 'user', mockT);
    expect(routes[1].routes).toBeUndefined();
  });

  it('translates all name fields via t()', () => {
    const t = (key: string) => `[${key}]`;
    const routes = buildMenuRoutes(simpleGroups, 'admin', t);
    expect(routes[0].name).toBe('[navGroup.g1]');
    expect(routes[1].name).toBe('[menu.a]');
  });

  it('does NOT mutate the input groups array', () => {
    const original: NavGroup[] = [
      {
        key: 'test',
        titleKey: 'navGroup.test',
        items: [
          { path: '/x', nameKey: 'x', access: 'admin' },
          { path: '/y', nameKey: 'y' },
        ],
      },
    ];
    const snapshot = JSON.stringify(original);
    buildMenuRoutes(original, 'user', mockT);
    expect(JSON.stringify(original)).toBe(snapshot);
  });

  it('works with the real NAV_GROUPS constant', () => {
    const routes = buildMenuRoutes(NAV_GROUPS, 'admin', mockT);
    // All 5 groups should have dividers
    const dividers = routes.filter((r) => r.itemType === 'group');
    expect(dividers).toHaveLength(5);
  });

  it('filters security and admin groups for regular user', () => {
    const routes = buildMenuRoutes(NAV_GROUPS, 'user', mockT);
    const dividers = routes.filter((r) => r.itemType === 'group');
    // qualitySec group still shows (quality is non-admin), system group still shows (billing + settings)
    // But security item and admin item are removed
    const paths = routes.map((r) => r.path);
    expect(paths).not.toContain('/security');
    expect(paths).not.toContain('/admin');
  });
});
