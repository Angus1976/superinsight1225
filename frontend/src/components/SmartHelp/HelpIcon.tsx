import React, { useCallback } from 'react';
import { QuestionCircleOutlined } from '@ant-design/icons';
import HelpPopover from './HelpPopover';
import { validateHelpKey } from '@/utils/helpUtils';

export interface HelpIconProps {
  helpKey: string;
  size?: 'small' | 'default';
  className?: string;
}

/**
 * 帮助图标按钮 — 点击后通过 HelpPopover 显示对应帮助内容。
 * 键盘可访问：Enter 键触发帮助。
 */
const HelpIcon: React.FC<HelpIconProps> = ({
  helpKey,
  size = 'default',
  className,
}) => {
  const fontSize = size === 'small' ? 12 : 16;

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLSpanElement>) => {
      if (e.key === 'Enter') {
        e.currentTarget.click();
      }
    },
    [],
  );

  // 卫语句：无效 helpKey 不渲染
  if (!helpKey || !validateHelpKey(helpKey)) {
    return null;
  }

  return (
    <HelpPopover helpKey={helpKey} trigger="click">
      <span
        role="button"
        tabIndex={0}
        aria-label="帮助"
        className={className}
        onKeyDown={handleKeyDown}
        style={{
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          color: 'rgba(0, 0, 0, 0.45)',
          lineHeight: 1,
        }}
      >
        <QuestionCircleOutlined style={{ fontSize }} />
      </span>
    </HelpPopover>
  );
};

export default HelpIcon;
