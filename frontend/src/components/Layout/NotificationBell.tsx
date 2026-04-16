/**
 * NotificationBell Component
 *
 * Displays a bell icon with an unread notification count badge.
 * - count > 0 → Badge shows the number
 * - count === 0 → no badge dot
 * All text via i18n keys (Requirement 7.2).
 */

import React from 'react';
import { Badge, Tooltip } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

export interface NotificationBellProps {
  count: number;
  onClick: () => void;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({
  count,
  onClick,
}) => {
  const { t } = useTranslation('common');

  return (
    <Tooltip title={t('header.notifications', '通知')}>
      <Badge count={count} size="small" offset={[-2, 2]}>
        <span
          data-testid="header-notification-bell"
          role="button"
          tabIndex={0}
          aria-label={t('header.notifications', '通知')}
          onClick={onClick}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onClick();
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            fontSize: 16,
            padding: 4,
          }}
        >
          <BellOutlined />
        </span>
      </Badge>
    </Tooltip>
  );
};

export default NotificationBell;
