/**
 * NotificationBanner Component
 * 
 * A reusable notification banner component for displaying
 * alerts, announcements, and messages.
 * 
 * @module components/Common/Composable/NotificationBanner
 * @version 1.0.0
 */

import React, { useState, useCallback, memo } from 'react';
import { Alert, Button, Space } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AlertProps } from 'antd';
import styles from './NotificationBanner.module.scss';

/**
 * NotificationBanner component props
 */
export interface NotificationBannerProps {
  /** Banner type */
  type?: 'success' | 'info' | 'warning' | 'error';
  /** Banner message */
  message: React.ReactNode;
  /** Banner description */
  description?: React.ReactNode;
  /** Show icon */
  showIcon?: boolean;
  /** Custom icon */
  icon?: React.ReactNode;
  /** Closable */
  closable?: boolean;
  /** Close handler */
  onClose?: () => void;
  /** Action button text */
  actionText?: string;
  /** Action button handler */
  onAction?: () => void;
  /** Secondary action text */
  secondaryActionText?: string;
  /** Secondary action handler */
  onSecondaryAction?: () => void;
  /** Banner style */
  variant?: 'filled' | 'outlined' | 'borderless';
  /** Full width */
  fullWidth?: boolean;
  /** Custom class name */
  className?: string;
  /** Sticky position */
  sticky?: boolean;
  /** Sticky position offset */
  stickyOffset?: number;
  /** Auto dismiss after ms */
  autoDismiss?: number;
  /** Banner ID for persistence */
  bannerId?: string;
}

/**
 * NotificationBanner component for displaying notifications
 */
export const NotificationBanner = memo(function NotificationBanner({
  type = 'info',
  message,
  description,
  showIcon = true,
  icon,
  closable = true,
  onClose,
  actionText,
  onAction,
  secondaryActionText,
  onSecondaryAction,
  variant = 'filled',
  fullWidth = true,
  className,
  sticky = false,
  stickyOffset = 0,
  autoDismiss,
  bannerId,
}: NotificationBannerProps): React.ReactElement | null {
  const [visible, setVisible] = useState(true);

  // Handle close
  const handleClose = useCallback(() => {
    setVisible(false);
    onClose?.();
    
    // Persist dismissal if bannerId provided
    if (bannerId) {
      localStorage.setItem(`banner-dismissed-${bannerId}`, 'true');
    }
  }, [onClose, bannerId]);

  // Auto dismiss
  React.useEffect(() => {
    if (autoDismiss && autoDismiss > 0) {
      const timer = setTimeout(handleClose, autoDismiss);
      return () => clearTimeout(timer);
    }
  }, [autoDismiss, handleClose]);

  // Check if banner was previously dismissed
  React.useEffect(() => {
    if (bannerId) {
      const dismissed = localStorage.getItem(`banner-dismissed-${bannerId}`);
      if (dismissed === 'true') {
        setVisible(false);
      }
    }
  }, [bannerId]);

  if (!visible) {
    return null;
  }

  // Build action buttons
  const actions = (
    <Space>
      {secondaryActionText && onSecondaryAction && (
        <Button size="small" onClick={onSecondaryAction}>
          {secondaryActionText}
        </Button>
      )}
      {actionText && onAction && (
        <Button type="primary" size="small" onClick={onAction}>
          {actionText}
        </Button>
      )}
    </Space>
  );

  // Build alert props
  const alertProps: AlertProps = {
    type,
    message,
    description,
    showIcon,
    icon,
    closable,
    onClose: handleClose,
    action: (actionText || secondaryActionText) ? actions : undefined,
  };

  // Apply variant styles
  const variantClass = styles[variant];

  // Apply sticky styles
  const stickyStyle: React.CSSProperties = sticky
    ? { position: 'sticky', top: stickyOffset, zIndex: 100 }
    : {};

  return (
    <div
      className={`${styles.notificationBanner} ${variantClass} ${fullWidth ? styles.fullWidth : ''} ${className || ''}`}
      style={stickyStyle}
    >
      <Alert {...alertProps} />
    </div>
  );
});

/**
 * Announcement banner for important announcements
 */
export interface AnnouncementBannerProps {
  message: React.ReactNode;
  link?: string;
  linkText?: string;
  onDismiss?: () => void;
  className?: string;
}

export const AnnouncementBanner = memo(function AnnouncementBanner({
  message,
  link,
  linkText,
  onDismiss,
  className,
}: AnnouncementBannerProps): React.ReactElement {
  const { t } = useTranslation('common');
  const [visible, setVisible] = useState(true);

  const handleDismiss = useCallback(() => {
    setVisible(false);
    onDismiss?.();
  }, [onDismiss]);

  if (!visible) {
    return <></>;
  }

  return (
    <div className={`${styles.announcementBanner} ${className || ''}`}>
      <div className={styles.content}>
        <span className={styles.message}>{message}</span>
        {link && (
          <a href={link} target="_blank" rel="noopener noreferrer" className={styles.link}>
            {linkText || t('banner.learnMore')}
          </a>
        )}
      </div>
      <button className={styles.closeButton} onClick={handleDismiss} aria-label={t('common.close')}>
        <CloseOutlined />
      </button>
    </div>
  );
});
