import React from 'react';
import { Popover, Typography, Tag } from 'antd';
import { useTranslation } from 'react-i18next';
import type { TooltipPlacement } from 'antd/es/tooltip';
import { validateHelpKey } from '@/utils/helpUtils';

const { Text } = Typography;

export interface HelpPopoverProps {
  helpKey: string;
  placement?: TooltipPlacement;
  children: React.ReactNode;
  trigger?: 'hover' | 'click';
}

/**
 * 帮助浮层组件 — 包裹目标元素，悬停或点击时显示 i18n 帮助内容。
 * 帮助内容为纯文本，防止 XSS。
 */
const HelpPopover: React.FC<HelpPopoverProps> = ({
  helpKey,
  placement = 'top',
  children,
  trigger = 'hover',
}) => {
  const { t } = useTranslation('help');

  // 卫语句：无效 helpKey 直接渲染子元素
  if (!helpKey || !validateHelpKey(helpKey)) {
    return <>{children}</>;
  }

  const title = String(t(`${helpKey}.title`, { defaultValue: '' }));
  const description = String(t(`${helpKey}.description`, { defaultValue: '' }));
  const shortcut = String(t(`${helpKey}.shortcut`, { defaultValue: '' }));

  // 无有效内容时不包裹 Popover
  if (!title && !description) {
    return <>{children}</>;
  }

  const content = (
    <div style={{ maxWidth: 260 }}>
      {description && (
        <Text type="secondary" style={{ display: 'block', fontSize: 13 }}>
          {description}
        </Text>
      )}
      {shortcut && (
        <Tag style={{ marginTop: 6 }}>{shortcut}</Tag>
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      title={title || undefined}
      placement={placement}
      trigger={trigger}
      overlayStyle={{ maxWidth: 300 }}
    >
      {children}
    </Popover>
  );
};

export default HelpPopover;
