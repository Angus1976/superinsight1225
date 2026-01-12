/**
 * AccessibilitySettings Component
 * 
 * User interface for customizing accessibility preferences.
 * WCAG 2.1 - Provides user control over accessibility features
 */

import { memo, useCallback, useState, useEffect } from 'react';
import { 
  Modal, 
  Switch, 
  Slider, 
  Radio, 
  Space, 
  Typography, 
  Divider,
  Button,
  Card,
} from 'antd';
import {
  SettingOutlined,
  FontSizeOutlined,
  BgColorsOutlined,
  ThunderboltOutlined,
  SoundOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAccessibilityPreferences, useReducedMotion } from '@/hooks/useAccessibility';
import { useLiveRegion } from './LiveRegion';

const { Title, Text, Paragraph } = Typography;

interface AccessibilitySettingsProps {
  visible: boolean;
  onClose: () => void;
}

interface A11ySettings {
  fontSize: 'normal' | 'large' | 'larger';
  highContrast: boolean;
  reducedMotion: boolean;
  screenReaderOptimized: boolean;
  focusIndicators: 'default' | 'enhanced' | 'high-visibility';
  linkUnderlines: boolean;
  cursorSize: 'default' | 'large';
}

const defaultSettings: A11ySettings = {
  fontSize: 'normal',
  highContrast: false,
  reducedMotion: false,
  screenReaderOptimized: false,
  focusIndicators: 'default',
  linkUnderlines: true,
  cursorSize: 'default',
};

export const AccessibilitySettings = memo<AccessibilitySettingsProps>(({
  visible,
  onClose,
}) => {
  const { t } = useTranslation('common');
  const { announcePolite } = useLiveRegion();
  const systemReducedMotion = useReducedMotion();
  
  const [settings, setSettings] = useState<A11ySettings>(() => {
    const saved = localStorage.getItem('a11y-settings');
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  });

  // Apply settings to document
  useEffect(() => {
    const root = document.documentElement;
    
    // Font size
    const fontSizeMap = { normal: '100%', large: '125%', larger: '150%' };
    root.style.fontSize = fontSizeMap[settings.fontSize];
    root.setAttribute('data-font-size', settings.fontSize);
    
    // High contrast
    root.setAttribute('data-high-contrast', String(settings.highContrast));
    if (settings.highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
    
    // Reduced motion
    root.setAttribute('data-reduced-motion', String(settings.reducedMotion));
    if (settings.reducedMotion) {
      root.classList.add('reduced-motion');
    } else {
      root.classList.remove('reduced-motion');
    }
    
    // Focus indicators
    root.setAttribute('data-focus-indicators', settings.focusIndicators);
    
    // Link underlines
    root.setAttribute('data-link-underlines', String(settings.linkUnderlines));
    
    // Cursor size
    root.setAttribute('data-cursor-size', settings.cursorSize);
    
    // Save to localStorage
    localStorage.setItem('a11y-settings', JSON.stringify(settings));
  }, [settings]);

  const updateSetting = useCallback(<K extends keyof A11ySettings>(
    key: K,
    value: A11ySettings[K]
  ) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    announcePolite(t('accessibility.settingUpdated', 'Setting updated'));
  }, [announcePolite, t]);

  const resetSettings = useCallback(() => {
    setSettings(defaultSettings);
    announcePolite(t('accessibility.settingsReset', 'Settings reset to defaults'));
  }, [announcePolite, t]);

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          {t('accessibility.title', 'Accessibility Settings')}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="reset" onClick={resetSettings}>
          {t('accessibility.reset', 'Reset to Defaults')}
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>
          {t('common.close', 'Close')}
        </Button>,
      ]}
      width={600}
      aria-labelledby="a11y-settings-title"
    >
      <div role="form" aria-label={t('accessibility.title', 'Accessibility Settings')}>
        {/* Font Size */}
        <Card size="small" className="mb-md">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <FontSizeOutlined />
              <Title level={5} style={{ margin: 0 }}>
                {t('accessibility.fontSize', 'Text Size')}
              </Title>
            </Space>
            <Paragraph type="secondary">
              {t('accessibility.fontSizeDesc', 'Adjust the size of text throughout the application')}
            </Paragraph>
            <Radio.Group
              value={settings.fontSize}
              onChange={(e) => updateSetting('fontSize', e.target.value)}
              optionType="button"
              buttonStyle="solid"
            >
              <Radio.Button value="normal">
                {t('accessibility.fontNormal', 'Normal')}
              </Radio.Button>
              <Radio.Button value="large">
                {t('accessibility.fontLarge', 'Large (125%)')}
              </Radio.Button>
              <Radio.Button value="larger">
                {t('accessibility.fontLarger', 'Larger (150%)')}
              </Radio.Button>
            </Radio.Group>
          </Space>
        </Card>

        {/* Visual Settings */}
        <Card size="small" className="mb-md">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <BgColorsOutlined />
              <Title level={5} style={{ margin: 0 }}>
                {t('accessibility.visual', 'Visual Settings')}
              </Title>
            </Space>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Text strong>{t('accessibility.highContrast', 'High Contrast Mode')}</Text>
                <br />
                <Text type="secondary">
                  {t('accessibility.highContrastDesc', 'Increase contrast for better visibility')}
                </Text>
              </div>
              <Switch
                checked={settings.highContrast}
                onChange={(checked) => updateSetting('highContrast', checked)}
                aria-label={t('accessibility.highContrast', 'High Contrast Mode')}
              />
            </div>

            <Divider style={{ margin: '12px 0' }} />

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Text strong>{t('accessibility.linkUnderlines', 'Underline Links')}</Text>
                <br />
                <Text type="secondary">
                  {t('accessibility.linkUnderlinesDesc', 'Always show underlines on links')}
                </Text>
              </div>
              <Switch
                checked={settings.linkUnderlines}
                onChange={(checked) => updateSetting('linkUnderlines', checked)}
                aria-label={t('accessibility.linkUnderlines', 'Underline Links')}
              />
            </div>

            <Divider style={{ margin: '12px 0' }} />

            <div>
              <Text strong>{t('accessibility.focusIndicators', 'Focus Indicators')}</Text>
              <br />
              <Text type="secondary">
                {t('accessibility.focusIndicatorsDesc', 'Visibility of keyboard focus indicators')}
              </Text>
              <Radio.Group
                value={settings.focusIndicators}
                onChange={(e) => updateSetting('focusIndicators', e.target.value)}
                style={{ marginTop: 8 }}
              >
                <Space direction="vertical">
                  <Radio value="default">
                    {t('accessibility.focusDefault', 'Default')}
                  </Radio>
                  <Radio value="enhanced">
                    {t('accessibility.focusEnhanced', 'Enhanced')}
                  </Radio>
                  <Radio value="high-visibility">
                    {t('accessibility.focusHighVisibility', 'High Visibility')}
                  </Radio>
                </Space>
              </Radio.Group>
            </div>
          </Space>
        </Card>

        {/* Motion Settings */}
        <Card size="small" className="mb-md">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <ThunderboltOutlined />
              <Title level={5} style={{ margin: 0 }}>
                {t('accessibility.motion', 'Motion Settings')}
              </Title>
            </Space>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Text strong>{t('accessibility.reducedMotion', 'Reduce Motion')}</Text>
                <br />
                <Text type="secondary">
                  {t('accessibility.reducedMotionDesc', 'Minimize animations and transitions')}
                  {systemReducedMotion && (
                    <span style={{ display: 'block', color: '#1890ff' }}>
                      {t('accessibility.systemPreference', '(System preference detected)')}
                    </span>
                  )}
                </Text>
              </div>
              <Switch
                checked={settings.reducedMotion || systemReducedMotion}
                onChange={(checked) => updateSetting('reducedMotion', checked)}
                disabled={systemReducedMotion}
                aria-label={t('accessibility.reducedMotion', 'Reduce Motion')}
              />
            </div>
          </Space>
        </Card>

        {/* Screen Reader Settings */}
        <Card size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <SoundOutlined />
              <Title level={5} style={{ margin: 0 }}>
                {t('accessibility.screenReader', 'Screen Reader')}
              </Title>
            </Space>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Text strong>{t('accessibility.screenReaderOptimized', 'Screen Reader Optimized')}</Text>
                <br />
                <Text type="secondary">
                  {t('accessibility.screenReaderOptimizedDesc', 'Optimize interface for screen readers')}
                </Text>
              </div>
              <Switch
                checked={settings.screenReaderOptimized}
                onChange={(checked) => updateSetting('screenReaderOptimized', checked)}
                aria-label={t('accessibility.screenReaderOptimized', 'Screen Reader Optimized')}
              />
            </div>
          </Space>
        </Card>
      </div>
    </Modal>
  );
});

AccessibilitySettings.displayName = 'AccessibilitySettings';

// ============================================
// Accessibility Settings Button
// ============================================

interface AccessibilitySettingsButtonProps {
  className?: string;
}

export const AccessibilitySettingsButton = memo<AccessibilitySettingsButtonProps>(({
  className,
}) => {
  const { t } = useTranslation('common');
  const [visible, setVisible] = useState(false);

  return (
    <>
      <Button
        type="text"
        icon={<SettingOutlined />}
        onClick={() => setVisible(true)}
        className={className}
        aria-label={t('accessibility.openSettings', 'Open accessibility settings')}
      >
        {t('accessibility.title', 'Accessibility')}
      </Button>
      <AccessibilitySettings
        visible={visible}
        onClose={() => setVisible(false)}
      />
    </>
  );
});

AccessibilitySettingsButton.displayName = 'AccessibilitySettingsButton';

export default AccessibilitySettings;
