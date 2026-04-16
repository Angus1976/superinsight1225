/**
 * Sidebar group header renderer for ProLayout menuItemRender.
 *
 * Detects `itemType === 'group'` route entries produced by
 * `buildMenuRoutes` and renders them as styled section headers.
 * Regular menu items get an active-state left border accent.
 */
import React from 'react';
import styles from './SidebarStyles.module.scss';

interface MenuItemMeta {
  itemType?: 'group';
  path?: string;
  name?: string;
  [key: string]: unknown;
}

export interface SidebarMenuItemProps {
  /** Route metadata from ProLayout */
  item: MenuItemMeta;
  /** Default DOM rendered by ProLayout */
  dom: React.ReactNode;
  /** Whether the sidebar is collapsed */
  collapsed: boolean;
  /** Whether this item is currently active */
  isActive: boolean;
  /** Click handler for navigation */
  onNavigate: (path: string) => void;
}

/**
 * Render a single sidebar menu entry.
 *
 * - Group dividers → styled section header (hidden when collapsed)
 * - Regular items  → wrapped with active accent border
 */
export const SidebarMenuItem: React.FC<SidebarMenuItemProps> = ({
  item,
  dom,
  collapsed,
  isActive,
  onNavigate,
}) => {
  if (item.itemType === 'group') {
    if (collapsed) {
      return <div className={styles.navGroupHeaderCollapsed} />;
    }
    return <div className={styles.navGroupHeader}>{item.name}</div>;
  }

  return (
    <div
      className={styles.menuItem}
      data-nav-path={item.path}
      onClick={() => item.path && onNavigate(item.path)}
    >
      {dom}
    </div>
  );
};
