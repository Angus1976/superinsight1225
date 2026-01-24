/**
 * LanguageSwitcher Component (语言切换器)
 * 
 * Dropdown for language selection with:
 * - Switch all UI text to selected language
 * - Show warning for missing translations
 * - Persist language preference
 * 
 * Requirements: 3.2, 3.3
 */

import React, { useState, useEffect } from 'react';
import {
  Dropdown,
  Button,
  Space,
  Tag,
  Badge,
  Tooltip,
  message,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  GlobalOutlined,
  CheckOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface LanguageInfo {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
  coverage?: number; // Translation coverage percentage
}

const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  { code: 'zh-CN', name: 'Chinese (Simplified)', nativeName: '简体中文', flag: '🇨🇳', coverage: 100 },
  { code: 'en-US', name: 'English', nativeName: 'English', flag: '🇺🇸', coverage: 100 },
  { code: 'zh-TW', name: 'Chinese (Traditional)', nativeName: '繁體中文', flag: '🇹🇼', coverage: 85 },
  { code: 'ja-JP', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵', coverage: 60 },
  { code: 'ko-KR', name: 'Korean', nativeName: '한국어', flag: '🇰🇷', coverage: 50 },
];

const STORAGE_KEY = 'ontology_language_preference';

interface LanguageSwitcherProps {
  showLabel?: boolean;
  size?: 'small' | 'middle' | 'large';
  onLanguageChange?: (language: string) => void;
}

const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  showLabel = true,
  size = 'middle',
  onLanguageChange,
}) => {
  const { t, i18n } = useTranslation('ontology');
  const [currentLanguage, setCurrentLanguage] = useState<string>(
    localStorage.getItem(STORAGE_KEY) || i18n.language || 'zh-CN'
  );

  // Initialize language from storage
  useEffect(() => {
    const savedLanguage = localStorage.getItem(STORAGE_KEY);
    if (savedLanguage && savedLanguage !== i18n.language) {
      i18n.changeLanguage(savedLanguage);
      setCurrentLanguage(savedLanguage);
    }
  }, [i18n]);

  const handleLanguageChange = (languageCode: string) => {
    const language = SUPPORTED_LANGUAGES.find((l) => l.code === languageCode);
    
    if (language && language.coverage && language.coverage < 100) {
      message.warning(t('i18n.warningMissingTranslation'));
    }

    i18n.changeLanguage(languageCode);
    setCurrentLanguage(languageCode);
    localStorage.setItem(STORAGE_KEY, languageCode);
    onLanguageChange?.(languageCode);
  };

  const getCurrentLanguageInfo = () => {
    return SUPPORTED_LANGUAGES.find((l) => l.code === currentLanguage) || SUPPORTED_LANGUAGES[0];
  };

  const menuItems: MenuProps['items'] = SUPPORTED_LANGUAGES.map((language) => ({
    key: language.code,
    label: (
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <span>{language.flag}</span>
          <span>{language.nativeName}</span>
          <span style={{ color: '#999', fontSize: 12 }}>({language.name})</span>
        </Space>
        <Space>
          {language.coverage && language.coverage < 100 && (
            <Tooltip title={t('i18n.translationCoverage') + `: ${language.coverage}%`}>
              <Tag color="warning" icon={<WarningOutlined />}>
                {language.coverage}%
              </Tag>
            </Tooltip>
          )}
          {currentLanguage === language.code && (
            <CheckOutlined style={{ color: '#52c41a' }} />
          )}
        </Space>
      </Space>
    ),
    onClick: () => handleLanguageChange(language.code),
  }));

  const currentLang = getCurrentLanguageInfo();

  return (
    <Dropdown
      menu={{ items: menuItems }}
      trigger={['click']}
      placement="bottomRight"
    >
      <Button size={size}>
        <Space>
          <GlobalOutlined />
          {showLabel && (
            <>
              <span>{currentLang.flag}</span>
              <span>{currentLang.nativeName}</span>
            </>
          )}
          {currentLang.coverage && currentLang.coverage < 100 && (
            <Badge status="warning" />
          )}
        </Space>
      </Button>
    </Dropdown>
  );
};

export default LanguageSwitcher;
