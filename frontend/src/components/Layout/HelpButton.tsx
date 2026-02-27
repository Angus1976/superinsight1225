/**
 * HelpButton Component
 *
 * Renders a help icon button that opens the help documentation link.
 * All text via i18n keys (Requirement 7.2).
 */

import React from 'react';
import { Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

/** Help documentation URL — can be overridden via environment variable */
const HELP_DOC_URL =
  import.meta.env.VITE_HELP_DOC_URL || 'https://docs.superinsight.ai/help';

export const HelpButton: React.FC = () => {
  const { t } = useTranslation('common');

  const handleClick = () => {
    window.open(HELP_DOC_URL, '_blank', 'noopener,noreferrer');
  };

  return (
    <Tooltip title={t('header.help', '帮助')}>
      <span
        role="button"
        tabIndex={0}
        aria-label={t('header.help', '帮助')}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') handleClick();
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
        <QuestionCircleOutlined />
      </span>
    </Tooltip>
  );
};

export default HelpButton;
