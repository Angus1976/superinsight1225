/**
 * DropdownMenu Component
 * 
 * A reusable dropdown menu component with support for
 * nested menus, icons, and keyboard navigation.
 * 
 * @module components/Common/Composable/DropdownMenu
 * @version 1.0.0
 */

import React, { memo, useMemo, useCallback } from 'react';
import { Dropdown, Button, Space, Divider } from 'antd';
import { DownOutlined, EllipsisOutlined } from '@ant-design/icons';
import type { MenuProps, DropdownProps } from 'antd';
import styles from './DropdownMenu.module.scss';

/**
 * Menu item interface
 */
export interface MenuItem {
  /** Unique key */
  key: string;
  /** Item label */
  label: React.ReactNode;
  /** Item icon */
  icon?: React.ReactNode;
  /** Disabled state */
  disabled?: boolean;
  /** Danger style */
  danger?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Nested children */
  children?: MenuItem[];
  /** Divider after this item */
  dividerAfter?: boolean;
  /** Item type */
  type?: 'item' | 'group' | 'divider';
}

/**
 * DropdownMenu component props
 */
export interface DropdownMenuProps {
  /** Menu items */
  items: MenuItem[];
  /** Trigger element */
  trigger?: React.ReactNode;
  /** Trigger type */
  triggerType?: 'button' | 'icon' | 'text' | 'custom';
  /** Button text (for button trigger) */
  buttonText?: string;
  /** Button icon */
  buttonIcon?: React.ReactNode;
  /** Trigger events */
  triggerEvents?: ('click' | 'hover' | 'contextMenu')[];
  /** Placement */
  placement?: DropdownProps['placement'];
  /** Disabled state */
  disabled?: boolean;
  /** Arrow visibility */
  arrow?: boolean;
  /** Custom class name */
  className?: string;
  /** Menu class name */
  menuClassName?: string;
  /** Open state (controlled) */
  open?: boolean;
  /** Open change handler */
  onOpenChange?: (open: boolean) => void;
  /** Item click handler */
  onItemClick?: (key: string) => void;
  /** Destroy popup on hide */
  destroyPopupOnHide?: boolean;
}

/**
 * Convert MenuItem to Ant Design menu item
 */
function convertToAntMenuItem(item: MenuItem, onItemClick?: (key: string) => void): MenuProps['items'][number] {
  if (item.type === 'divider') {
    return { type: 'divider', key: item.key };
  }

  if (item.type === 'group') {
    return {
      type: 'group',
      key: item.key,
      label: item.label,
      children: item.children?.map(child => convertToAntMenuItem(child, onItemClick)),
    };
  }

  const menuItem: MenuProps['items'][number] = {
    key: item.key,
    label: item.label,
    icon: item.icon,
    disabled: item.disabled,
    danger: item.danger,
    onClick: () => {
      item.onClick?.();
      onItemClick?.(item.key);
    },
  };

  if (item.children && item.children.length > 0) {
    (menuItem as { children: MenuProps['items'] }).children = item.children.map(child => 
      convertToAntMenuItem(child, onItemClick)
    );
  }

  return menuItem;
}

/**
 * DropdownMenu component for dropdown menus
 */
export const DropdownMenu = memo(function DropdownMenu({
  items,
  trigger,
  triggerType = 'button',
  buttonText = '更多',
  buttonIcon,
  triggerEvents = ['click'],
  placement = 'bottomLeft',
  disabled = false,
  arrow = false,
  className,
  menuClassName,
  open,
  onOpenChange,
  onItemClick,
  destroyPopupOnHide = true,
}: DropdownMenuProps): React.ReactElement {
  // Convert items to Ant Design format
  const menuItems = useMemo<MenuProps['items']>(() => {
    const result: MenuProps['items'] = [];
    
    items.forEach((item, index) => {
      result.push(convertToAntMenuItem(item, onItemClick));
      
      if (item.dividerAfter && index < items.length - 1) {
        result.push({ type: 'divider', key: `divider-${item.key}` });
      }
    });
    
    return result;
  }, [items, onItemClick]);

  // Build menu props
  const menuProps: MenuProps = {
    items: menuItems,
    className: menuClassName,
  };

  // Render trigger element
  const triggerElement = useMemo(() => {
    if (trigger) {
      return trigger;
    }

    switch (triggerType) {
      case 'button':
        return (
          <Button disabled={disabled}>
            <Space>
              {buttonIcon}
              {buttonText}
              <DownOutlined />
            </Space>
          </Button>
        );

      case 'icon':
        return (
          <Button
            type="text"
            icon={buttonIcon || <EllipsisOutlined />}
            disabled={disabled}
          />
        );

      case 'text':
        return (
          <span className={styles.textTrigger}>
            {buttonText}
            <DownOutlined className={styles.arrow} />
          </span>
        );

      default:
        return (
          <Button disabled={disabled}>
            {buttonText}
          </Button>
        );
    }
  }, [trigger, triggerType, buttonText, buttonIcon, disabled]);

  return (
    <Dropdown
      menu={menuProps}
      trigger={triggerEvents}
      placement={placement}
      disabled={disabled}
      arrow={arrow}
      open={open}
      onOpenChange={onOpenChange}
      destroyPopupOnHide={destroyPopupOnHide}
      className={className}
    >
      {triggerElement}
    </Dropdown>
  );
});

/**
 * ActionMenu - A simplified dropdown for action buttons
 */
export interface ActionMenuProps {
  items: MenuItem[];
  onItemClick?: (key: string) => void;
  disabled?: boolean;
  className?: string;
}

export const ActionMenu = memo(function ActionMenu({
  items,
  onItemClick,
  disabled,
  className,
}: ActionMenuProps): React.ReactElement {
  return (
    <DropdownMenu
      items={items}
      triggerType="icon"
      onItemClick={onItemClick}
      disabled={disabled}
      className={className}
    />
  );
});
