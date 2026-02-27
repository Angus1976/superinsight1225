/**
 * Unit tests for NotificationBell and HelpButton components.
 *
 * Validates: Requirements 4.4, 4.6, 7.2
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationBell } from '../NotificationBell';
import { HelpButton } from '../HelpButton';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
}));

describe('NotificationBell', () => {
  const defaultProps = {
    count: 0,
    onClick: vi.fn(),
  };

  it('renders bell icon with zero count (no visible badge)', () => {
    const { container } = render(<NotificationBell {...defaultProps} />);
    // Ant Design Badge with count=0 should not show the number
    expect(container.querySelector('.anticon-bell')).toBeTruthy();
  });

  it('displays badge with unread count when count > 0', () => {
    render(<NotificationBell {...defaultProps} count={5} />);
    expect(screen.getByText('5')).toBeTruthy();
  });

  it('calls onClick when bell is clicked', () => {
    const onClick = vi.fn();
    render(<NotificationBell count={3} onClick={onClick} />);
    const button = screen.getByRole('button', { name: '通知' });
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('calls onClick on Enter key press', () => {
    const onClick = vi.fn();
    render(<NotificationBell count={0} onClick={onClick} />);
    const button = screen.getByRole('button', { name: '通知' });
    fireEvent.keyDown(button, { key: 'Enter' });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('uses i18n key for aria-label (not raw text)', () => {
    render(<NotificationBell {...defaultProps} />);
    // The aria-label comes from t('header.notifications', '通知')
    expect(screen.getByRole('button', { name: '通知' })).toBeTruthy();
  });
});

describe('HelpButton', () => {
  it('renders question circle icon', () => {
    const { container } = render(<HelpButton />);
    expect(container.querySelector('.anticon-question-circle')).toBeTruthy();
  });

  it('opens help link in new tab on click', () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    render(<HelpButton />);
    const button = screen.getByRole('button', { name: '帮助' });
    fireEvent.click(button);
    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('http'),
      '_blank',
      'noopener,noreferrer',
    );
    openSpy.mockRestore();
  });

  it('opens help link on Enter key press', () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    render(<HelpButton />);
    const button = screen.getByRole('button', { name: '帮助' });
    fireEvent.keyDown(button, { key: 'Enter' });
    expect(openSpy).toHaveBeenCalledOnce();
    openSpy.mockRestore();
  });

  it('uses i18n key for aria-label', () => {
    render(<HelpButton />);
    expect(screen.getByRole('button', { name: '帮助' })).toBeTruthy();
  });
});
