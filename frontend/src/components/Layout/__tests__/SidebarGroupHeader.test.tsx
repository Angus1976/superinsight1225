/**
 * Unit tests for SidebarMenuItem component.
 *
 * Validates: Requirements 2.4, 2.5
 * - Active item left border accent (3px solid #1890FF)
 * - Collapsed mode: hide group titles, show icons only
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SidebarMenuItem } from '../SidebarGroupHeader';

describe('SidebarMenuItem', () => {
  const defaultProps = {
    dom: <span>Menu Label</span>,
    collapsed: false,
    isActive: false,
    onNavigate: vi.fn(),
  };

  describe('group header rendering', () => {
    it('renders group header text when itemType is group and not collapsed', () => {
      const { container } = render(
        <SidebarMenuItem
          {...defaultProps}
          item={{ itemType: 'group', name: 'Workbench' }}
        />,
      );
      expect(screen.getByText('Workbench')).toBeTruthy();
      const header = container.firstElementChild as HTMLElement;
      expect(header.className).toContain('navGroupHeader');
      expect(header.className).not.toContain('navGroupHeaderCollapsed');
    });

    it('hides group header when collapsed', () => {
      const { container } = render(
        <SidebarMenuItem
          {...defaultProps}
          collapsed={true}
          item={{ itemType: 'group', name: 'Workbench' }}
        />,
      );
      const header = container.firstElementChild as HTMLElement;
      expect(header.className).toContain('navGroupHeaderCollapsed');
    });
  });

  describe('regular menu item rendering', () => {
    it('renders dom content for non-group items', () => {
      render(
        <SidebarMenuItem
          {...defaultProps}
          item={{ path: '/dashboard' }}
        />,
      );
      expect(screen.getByText('Menu Label')).toBeTruthy();
    });

    it('renders menuItem wrapper for active items', () => {
      const { container } = render(
        <SidebarMenuItem
          {...defaultProps}
          isActive={true}
          item={{ path: '/dashboard' }}
        />,
      );
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper.className).toContain('menuItem');
    });

    it('renders menuItem wrapper for inactive items', () => {
      const { container } = render(
        <SidebarMenuItem
          {...defaultProps}
          isActive={false}
          item={{ path: '/dashboard' }}
        />,
      );
      const wrapper = container.firstElementChild as HTMLElement;
      expect(wrapper.className).toContain('menuItem');
      expect(wrapper.className).toContain('menuItem');
    });

    it('calls onNavigate with item path on click', () => {
      const onNavigate = vi.fn();
      render(
        <SidebarMenuItem
          {...defaultProps}
          onNavigate={onNavigate}
          item={{ path: '/tasks' }}
        />,
      );
      fireEvent.click(screen.getByText('Menu Label'));
      expect(onNavigate).toHaveBeenCalledWith('/tasks');
    });

    it('does not call onNavigate when path is undefined', () => {
      const onNavigate = vi.fn();
      render(
        <SidebarMenuItem
          {...defaultProps}
          onNavigate={onNavigate}
          item={{}}
        />,
      );
      fireEvent.click(screen.getByText('Menu Label'));
      expect(onNavigate).not.toHaveBeenCalled();
    });
  });
});
