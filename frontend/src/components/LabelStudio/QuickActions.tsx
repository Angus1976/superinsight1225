// Label Studio quick actions and UX optimization component
import { useState, useRef, useEffect } from 'react';
import { Card, Button, Space, Tooltip, Dropdown, Modal, Spin, message, Progress, Badge } from 'antd';
import type { MenuProps } from 'antd';
import {
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  ForwardOutlined,
  BackwardOutlined,
  SettingOutlined,
  KeyOutlined,
  ThunderboltOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  ReloadOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface QuickActionsProps {
  iframeRef?: React.RefObject<HTMLIFrameElement>;
  onFullscreenToggle?: (isFullscreen: boolean) => void;
  onSave?: () => void;
  onSkip?: () => void;
  onPrevious?: () => void;
  onNext?: () => void;
  currentTask?: number;
  totalTasks?: number;
  isLoading?: boolean;
}

interface KeyboardShortcut {
  key: string;
  description: string;
  action: () => void;
}

export const QuickActions: React.FC<QuickActionsProps> = ({
  iframeRef,
  onFullscreenToggle,
  onSave,
  onSkip,
  onPrevious,
  onNext,
  currentTask = 1,
  totalTasks = 100,
  isLoading = false,
}) => {
  const { t } = useTranslation(['labelStudio', 'common']);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Keyboard shortcuts
  const shortcuts: KeyboardShortcut[] = [
    { key: 'Ctrl+S', description: t('shortcuts.save') || 'Save annotation', action: handleSave },
    { key: 'Ctrl+Enter', description: t('shortcuts.submit') || 'Submit and next', action: handleSubmitAndNext },
    { key: 'Ctrl+←', description: t('shortcuts.previous') || 'Previous task', action: () => onPrevious?.() },
    { key: 'Ctrl+→', description: t('shortcuts.next') || 'Next task', action: () => onNext?.() },
    { key: 'Ctrl+Shift+S', description: t('shortcuts.skip') || 'Skip task', action: () => onSkip?.() },
    { key: 'F11', description: t('shortcuts.fullscreen') || 'Toggle fullscreen', action: handleFullscreenToggle },
    { key: 'Ctrl+Z', description: t('shortcuts.undo') || 'Undo', action: handleUndo },
    { key: 'Ctrl+Y', description: t('shortcuts.redo') || 'Redo', action: handleRedo },
  ];

  // Handle save
  function handleSave() {
    setIsSaving(true);
    sendMessageToIframe('labelStudio:saveAnnotation');
    onSave?.();
    setTimeout(() => {
      setIsSaving(false);
      message.success(t('common:save') || 'Annotation saved');
    }, 500);
  }

  // Handle submit and next
  function handleSubmitAndNext() {
    handleSave();
    setTimeout(() => {
      onNext?.();
    }, 600);
  }

  // Handle fullscreen toggle
  function handleFullscreenToggle() {
    const newState = !isFullscreen;
    setIsFullscreen(newState);
    onFullscreenToggle?.(newState);

    if (newState) {
      containerRef.current?.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
  }

  // Handle undo
  function handleUndo() {
    sendMessageToIframe('labelStudio:undo');
  }

  // Handle redo
  function handleRedo() {
    sendMessageToIframe('labelStudio:redo');
  }

  // Send message to iframe
  function sendMessageToIframe(type: string, payload?: unknown) {
    if (iframeRef?.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage({ type, payload, timestamp: Date.now() }, '*');
    }
  }

  // Keyboard event handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S - Save
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
      // Ctrl+Enter - Submit and next
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        handleSubmitAndNext();
      }
      // Ctrl+Left - Previous
      if (e.ctrlKey && e.key === 'ArrowLeft') {
        e.preventDefault();
        onPrevious?.();
      }
      // Ctrl+Right - Next
      if (e.ctrlKey && e.key === 'ArrowRight') {
        e.preventDefault();
        onNext?.();
      }
      // F11 - Fullscreen
      if (e.key === 'F11') {
        e.preventDefault();
        handleFullscreenToggle();
      }
      // Ctrl+Z - Undo
      if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      }
      // Ctrl+Y or Ctrl+Shift+Z - Redo
      if ((e.ctrlKey && e.key === 'y') || (e.ctrlKey && e.shiftKey && e.key === 'z')) {
        e.preventDefault();
        handleRedo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onPrevious, onNext]);

  // Settings menu
  const settingsMenuItems: MenuProps['items'] = [
    {
      key: 'shortcuts',
      icon: <KeyOutlined />,
      label: t('settings.shortcuts') || 'Keyboard Shortcuts',
      onClick: () => setShowShortcuts(true),
    },
    {
      key: 'preload',
      icon: <ThunderboltOutlined />,
      label: t('settings.preload') || 'Enable Preloading',
    },
    {
      key: 'autoSave',
      icon: <SaveOutlined />,
      label: t('settings.autoSave') || 'Auto-save (30s)',
    },
  ];

  const progress = Math.round((currentTask / totalTasks) * 100);

  return (
    <div ref={containerRef}>
      <Card size="small" style={{ marginBottom: 8 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          {/* Navigation */}
          <Space>
            <Tooltip title={t('common:previous') || 'Previous (Ctrl+←)'}>
              <Button
                icon={<BackwardOutlined />}
                onClick={onPrevious}
                disabled={currentTask <= 1 || isLoading}
              />
            </Tooltip>
            
            <Badge count={`${currentTask}/${totalTasks}`} style={{ backgroundColor: '#1890ff' }}>
              <Progress
                type="circle"
                percent={progress}
                size={40}
                format={() => `${progress}%`}
              />
            </Badge>
            
            <Tooltip title={t('common:next') || 'Next (Ctrl+→)'}>
              <Button
                icon={<ForwardOutlined />}
                onClick={onNext}
                disabled={currentTask >= totalTasks || isLoading}
              />
            </Tooltip>
          </Space>

          {/* Actions */}
          <Space>
            <Tooltip title={t('common:undo') || 'Undo (Ctrl+Z)'}>
              <Button icon={<UndoOutlined />} onClick={handleUndo} disabled={isLoading} />
            </Tooltip>
            
            <Tooltip title={t('common:redo') || 'Redo (Ctrl+Y)'}>
              <Button icon={<RedoOutlined />} onClick={handleRedo} disabled={isLoading} />
            </Tooltip>

            <Tooltip title={t('common:save') || 'Save (Ctrl+S)'}>
              <Button
                icon={isSaving ? <Spin size="small" /> : <SaveOutlined />}
                onClick={handleSave}
                disabled={isLoading || isSaving}
              />
            </Tooltip>

            <Tooltip title={t('common:skip') || 'Skip (Ctrl+Shift+S)'}>
              <Button onClick={onSkip} disabled={isLoading}>
                {t('common:skip') || 'Skip'}
              </Button>
            </Tooltip>

            <Tooltip title={t('common:submitNext') || 'Submit & Next (Ctrl+Enter)'}>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={handleSubmitAndNext}
                disabled={isLoading}
              >
                {t('common:submitNext') || 'Submit & Next'}
              </Button>
            </Tooltip>
          </Space>

          {/* Tools */}
          <Space>
            <Tooltip title={t('common:reload') || 'Reload'}>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  sendMessageToIframe('labelStudio:reload');
                  message.info(t('common:reloading') || 'Reloading...');
                }}
                disabled={isLoading}
              />
            </Tooltip>

            <Tooltip title={isFullscreen ? (t('common:exitFullscreen') || 'Exit Fullscreen') : (t('common:fullscreen') || 'Fullscreen (F11)')}>
              <Button
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={handleFullscreenToggle}
              />
            </Tooltip>

            <Dropdown menu={{ items: settingsMenuItems }} placement="bottomRight">
              <Button icon={<SettingOutlined />} />
            </Dropdown>
          </Space>
        </Space>
      </Card>

      {/* Keyboard Shortcuts Modal */}
      <Modal
        title={
          <Space>
            <KeyOutlined />
            {t('shortcuts.title') || 'Keyboard Shortcuts'}
          </Space>
        }
        open={showShortcuts}
        onCancel={() => setShowShortcuts(false)}
        footer={null}
        width={500}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #f0f0f0' }}>
                {t('shortcuts.shortcut') || 'Shortcut'}
              </th>
              <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #f0f0f0' }}>
                {t('shortcuts.action') || 'Action'}
              </th>
            </tr>
          </thead>
          <tbody>
            {shortcuts.map((shortcut, index) => (
              <tr key={index}>
                <td style={{ padding: '8px', borderBottom: '1px solid #f0f0f0' }}>
                  <code style={{ 
                    backgroundColor: '#f5f5f5', 
                    padding: '2px 6px', 
                    borderRadius: 4,
                    fontSize: 12,
                  }}>
                    {shortcut.key}
                  </code>
                </td>
                <td style={{ padding: '8px', borderBottom: '1px solid #f0f0f0' }}>
                  {shortcut.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Modal>
    </div>
  );
};

export default QuickActions;
