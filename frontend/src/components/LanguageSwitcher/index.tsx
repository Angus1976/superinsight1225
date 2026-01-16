/**
 * Language Switcher Component
 * 
 * Unified language switching component that:
 * 1. Updates Zustand language store
 * 2. Syncs with react-i18next
 * 3. Syncs to Label Studio iframe via postMessage
 * 4. Persists to localStorage
 */

import React from 'react';
import { Select, Dropdown, Button, Space } from 'antd';
import { GlobalOutlined, CheckOutlined } from '@ant-design/icons';
import { useLanguageStore } from '@/stores/languageStore';
import { useTranslation } from 'react-i18next';
import type { SupportedLanguage } from '@/constants';

interface LanguageSwitcherProps {
  /** Display mode: 'select' for dropdown select, 'dropdown' for menu dropdown, 'toggle' for simple toggle */
  mode?: 'select' | 'dropdown' | 'toggle';
  /** Size of the component */
  size?: 'small' | 'middle' | 'large';
  /** Show language icon */
  showIcon?: boolean;
  /** Show full language name or just code */
  showFullName?: boolean;
  /** Custom class name */
  className?: string;
  /** Custom style */
  style?: React.CSSProperties;
}

const LANGUAGE_OPTIONS: { value: SupportedLanguage; label: string; labelEn: string }[] = [
  { value: 'zh', label: '中文', labelEn: 'Chinese' },
  { value: 'en', label: 'English', labelEn: 'English' },
];

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  mode = 'select',
  size = 'middle',
  showIcon = true,
  showFullName = true,
  className,
  style,
}) => {
  const { language, setLanguage } = useLanguageStore();
  const { t } = useTranslation();

  const handleChange = (value: SupportedLanguage) => {
    setLanguage(value);
  };

  const getCurrentLabel = () => {
    const option = LANGUAGE_OPTIONS.find(opt => opt.value === language);
    return showFullName ? option?.label : language.toUpperCase();
  };

  // Select mode - standard dropdown select
  if (mode === 'select') {
    return (
      <Select
        value={language}
        onChange={handleChange}
        size={size}
        className={className}
        style={{ minWidth: 100, ...style }}
        suffixIcon={showIcon ? <GlobalOutlined /> : undefined}
        options={LANGUAGE_OPTIONS.map(opt => ({
          value: opt.value,
          label: opt.label,
        }))}
      />
    );
  }

  // Dropdown mode - menu style dropdown
  if (mode === 'dropdown') {
    const menuItems = LANGUAGE_OPTIONS.map(opt => ({
      key: opt.value,
      label: (
        <Space>
          {opt.label}
          {language === opt.value && <CheckOutlined style={{ color: '#1890ff' }} />}
        </Space>
      ),
      onClick: () => handleChange(opt.value),
    }));

    return (
      <Dropdown
        menu={{ items: menuItems }}
        trigger={['click']}
        placement="bottomRight"
      >
        <Button
          type="text"
          size={size}
          className={className}
          style={style}
          icon={showIcon ? <GlobalOutlined /> : undefined}
        >
          {getCurrentLabel()}
        </Button>
      </Dropdown>
    );
  }

  // Toggle mode - simple toggle between languages
  return (
    <Button
      type="text"
      size={size}
      className={className}
      style={style}
      icon={showIcon ? <GlobalOutlined /> : undefined}
      onClick={() => handleChange(language === 'zh' ? 'en' : 'zh')}
      title={t('common.switchLanguage', '切换语言')}
    >
      {getCurrentLabel()}
    </Button>
  );
};

export default LanguageSwitcher;
