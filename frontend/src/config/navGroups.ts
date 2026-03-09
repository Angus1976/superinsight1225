/**
 * Sidebar navigation group configuration.
 *
 * Defines business-category groups and the pure function
 * `buildMenuRoutes` that transforms them into ProLayout routes
 * with role-based filtering and i18n translation.
 */
import React from 'react';
import {
  DashboardOutlined,
  RobotOutlined,
  OrderedListOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  AuditOutlined,
  SafetyOutlined,
  DollarOutlined,
  SettingOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { ROUTES } from '@/constants';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MenuItem {
  path: string;
  nameKey: string;
  icon?: React.ReactNode;
  access?: 'admin';
  children?: MenuItem[];
}

export interface NavGroup {
  key: string;
  titleKey: string; // i18n key, e.g. 'navGroup.workbench'
  items: MenuItem[];
}

/** Subset of ProLayout route shape we actually produce. */
export interface ProLayoutRoute {
  path: string;
  name: string;
  icon?: React.ReactNode;
  hideInMenu?: boolean;
  itemType?: 'group';
  routes?: { path: string; name: string }[];
}

// ---------------------------------------------------------------------------
// Menu item definitions (mirrors existing MainLayout menuItems)
// ---------------------------------------------------------------------------

const dashboard: MenuItem = {
  path: ROUTES.DASHBOARD,
  nameKey: 'dashboard',
  icon: React.createElement(DashboardOutlined),
};

const aiAssistant: MenuItem = {
  path: '/ai-assistant',
  nameKey: 'aiAssistant',
  icon: React.createElement(RobotOutlined),
};

const tasks: MenuItem = {
  path: ROUTES.TASKS,
  nameKey: 'tasks',
  icon: React.createElement(OrderedListOutlined),
};

const dataSync: MenuItem = {
  path: ROUTES.DATA_SYNC,
  nameKey: 'dataSync',
  icon: React.createElement(SyncOutlined),
  children: [
    { path: `${ROUTES.DATA_SYNC}/sources`, nameKey: 'dataSources' },
    { path: `${ROUTES.DATA_SYNC}/scheduler`, nameKey: 'syncTasks' },
    { path: `${ROUTES.DATA_SYNC}/security`, nameKey: 'dataSecurity' },
  ],
};

const augmentation: MenuItem = {
  path: ROUTES.AUGMENTATION,
  nameKey: 'augmentation',
  icon: React.createElement(ThunderboltOutlined),
  children: [
    { path: `${ROUTES.AUGMENTATION}/samples`, nameKey: 'samples' },
    { path: `${ROUTES.AUGMENTATION}/config`, nameKey: 'config' },
    {
      path: `${ROUTES.AUGMENTATION}/ai-processing`,
      nameKey: 'dataProcessing',
      access: 'admin',
    },
  ],
};

const quality: MenuItem = {
  path: ROUTES.QUALITY,
  nameKey: 'quality',
  icon: React.createElement(SafetyCertificateOutlined),
  children: [
    { path: `${ROUTES.QUALITY}/rules`, nameKey: 'rules' },
    { path: `${ROUTES.QUALITY}/reports`, nameKey: 'reports' },
  ],
};

const security: MenuItem = {
  path: ROUTES.SECURITY,
  nameKey: 'security',
  icon: React.createElement(AuditOutlined),
  access: 'admin',
  children: [
    { path: `${ROUTES.SECURITY}/audit`, nameKey: 'audit' },
    { path: `${ROUTES.SECURITY}/permissions`, nameKey: 'permissions' },
  ],
};

const admin: MenuItem = {
  path: ROUTES.ADMIN,
  nameKey: 'admin',
  icon: React.createElement(SafetyOutlined),
  access: 'admin',
  children: [
    { path: `${ROUTES.ADMIN}/tenants`, nameKey: 'tenants' },
    { path: `${ROUTES.ADMIN}/users`, nameKey: 'users' },
    { path: `${ROUTES.ADMIN}/system`, nameKey: 'system' },
  ],
};

const billing: MenuItem = {
  path: ROUTES.BILLING,
  nameKey: 'billing',
  icon: React.createElement(DollarOutlined),
  children: [
    { path: `${ROUTES.BILLING}/overview`, nameKey: 'overview' },
    { path: `${ROUTES.BILLING}/reports`, nameKey: 'reports' },
  ],
};

const settings: MenuItem = {
  path: ROUTES.SETTINGS,
  nameKey: 'settings',
  icon: React.createElement(SettingOutlined),
};

const dataLifecycle: MenuItem = {
  path: '/data-lifecycle',
  nameKey: 'dataLifecycle',
  icon: React.createElement(DatabaseOutlined),
};

// ---------------------------------------------------------------------------
// Group definitions
// ---------------------------------------------------------------------------

export const NAV_GROUPS: NavGroup[] = [
  { key: 'workbench', titleKey: 'navGroup.workbench', items: [dashboard, aiAssistant] },
  { key: 'dataManage', titleKey: 'navGroup.dataManage', items: [tasks, dataSync, dataLifecycle] },
  { key: 'aiCapability', titleKey: 'navGroup.aiCapability', items: [augmentation] },
  { key: 'qualitySec', titleKey: 'navGroup.qualitySec', items: [quality, security] },
  { key: 'system', titleKey: 'navGroup.system', items: [admin, billing, settings] },
];

// ---------------------------------------------------------------------------
// buildMenuRoutes – pure function, no mutation
// ---------------------------------------------------------------------------

/** Translation function signature (subset of i18next TFunction). */
type TranslateFn = (key: string) => string;

/**
 * Filter children of a MenuItem by role, returning a new array.
 * If no children exist, returns undefined.
 */
function filterChildren(
  children: MenuItem[] | undefined,
  userRole: string,
): MenuItem[] | undefined {
  if (!children) return undefined;
  const filtered = children.filter(
    (child) => child.access !== 'admin' || userRole === 'admin',
  );
  return filtered.length > 0 ? filtered : undefined;
}

/**
 * Transform NavGroup[] into a flat ProLayout-compatible route array.
 *
 * - Inserts a group divider (itemType='group') before each group's items
 * - Filters out admin-only items (and admin-only children) when userRole !== 'admin'
 * - Omits the group divider entirely when all items are filtered out
 * - Translates all `name` fields via `t()`
 * - Does NOT mutate the input `groups` array
 */
export function buildMenuRoutes(
  groups: readonly NavGroup[],
  userRole: string,
  t: TranslateFn,
): ProLayoutRoute[] {
  const routes: ProLayoutRoute[] = [];

  for (const group of groups) {
    // 1. Filter top-level items by access role
    const visibleItems = group.items.filter(
      (item) => item.access !== 'admin' || userRole === 'admin',
    );

    if (visibleItems.length === 0) continue;

    // 2. Group divider
    routes.push({
      path: `/_group_${group.key}`,
      name: t(group.titleKey),
      hideInMenu: false,
      itemType: 'group',
    });

    // 3. Items under this group
    for (const item of visibleItems) {
      const filteredChildren = filterChildren(item.children, userRole);

      routes.push({
        path: item.path,
        name: t(`menu.${item.nameKey}`),
        icon: item.icon,
        routes: filteredChildren?.map((child) => ({
          path: child.path,
          name: t(`menu.${child.nameKey}`),
        })),
      });
    }
  }

  return routes;
}
