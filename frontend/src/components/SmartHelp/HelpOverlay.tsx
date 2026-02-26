import React, { useCallback, useEffect, useRef } from 'react';
import { Card, Typography, Tag } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useHelpStore } from '@/stores/helpStore';
import { validateHelpKey } from '@/utils/helpUtils';

const { Text } = Typography;

/** 默认位置：屏幕右下角 */
const DEFAULT_OFFSET = { right: 24, bottom: 24 };

/** 计算浮层位置样式 */
function computePositionStyle(
  position: { x: number; y: number } | null,
): React.CSSProperties {
  if (!position) {
    return { position: 'fixed', right: DEFAULT_OFFSET.right, bottom: DEFAULT_OFFSET.bottom };
  }

  return {
    position: 'fixed',
    left: Math.max(8, Math.min(position.x - 140, window.innerWidth - 300)),
    top: Math.max(8, position.y - 10),
  };
}

/**
 * 全局帮助浮层 — 由快捷键触发，从 helpStore 读取状态。
 * 支持 Esc 关闭、Tab 键盘导航、ARIA 无障碍属性。
 * 帮助内容为纯文本，防止 XSS。
 */
const HelpOverlay: React.FC = () => {
  const { t } = useTranslation('help');
  const visible = useHelpStore((s) => s.visible);
  const currentHelpKey = useHelpStore((s) => s.currentHelpKey);
  const position = useHelpStore((s) => s.position);
  const hideHelp = useHelpStore((s) => s.hideHelp);

  const overlayRef = useRef<HTMLDivElement>(null);

  // Esc 关闭
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        hideHelp();
      }
    },
    [hideHelp],
  );

  useEffect(() => {
    if (!visible) return;

    document.addEventListener('keydown', handleKeyDown);
    // 聚焦浮层以支持键盘导航
    overlayRef.current?.focus();

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [visible, handleKeyDown]);

  // 卫语句：不可见或无帮助键时不渲染
  if (!visible || !currentHelpKey) return null;

  const safeKey = validateHelpKey(currentHelpKey) ? currentHelpKey : 'general';

  const title = String(t(`${safeKey}.title`, { defaultValue: '' }));
  const description = String(t(`${safeKey}.description`, { defaultValue: '' }));
  const shortcut = String(t(`${safeKey}.shortcut`, { defaultValue: '' }));

  const positionStyle = computePositionStyle(position);

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="false"
      aria-label={title || t('general.title')}
      tabIndex={-1}
      style={{
        ...positionStyle,
        zIndex: 1050,
        outline: 'none',
        maxWidth: 320,
      }}
    >
      <Card
        size="small"
        title={title || undefined}
        extra={
          <CloseOutlined
            role="button"
            tabIndex={0}
            aria-label="关闭帮助"
            onClick={hideHelp}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                hideHelp();
              }
            }}
            style={{ cursor: 'pointer', fontSize: 12 }}
          />
        }
        style={{ boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
      >
        {description && (
          <Text
            type="secondary"
            style={{ display: 'block', fontSize: 13, marginBottom: shortcut ? 8 : 0 }}
          >
            {description}
          </Text>
        )}
        {shortcut && <Tag>{shortcut}</Tag>}
      </Card>
    </div>
  );
};

export default HelpOverlay;
