// Header content component
import { Dropdown, Space, Button, Avatar, Switch, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import {
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  GlobalOutlined,
  BulbOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/hooks/useAuth';
import { useUIStore } from '@/stores/uiStore';
import { TenantSelector } from '@/components/Auth/TenantSelector';
import { WorkspaceSwitcher } from '@/components/Auth/WorkspaceSwitcher';
import { THEMES } from '@/constants';

export const HeaderContent: React.FC = () => {
  const { t, i18n } = useTranslation('common');
  const { user, logout } = useAuth();
  const { theme, toggleTheme, setLanguage } = useUIStore();

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: t('menu.settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('common:logout', '退出登录'),
      danger: true,
    },
  ];

  const languageMenuItems: MenuProps['items'] = [
    {
      key: 'zh',
      label: (
        <Space>
          <span>🇨🇳</span>
          <span>{t('language.zh')}</span>
        </Space>
      ),
    },
    {
      key: 'en',
      label: (
        <Space>
          <span>🇺🇸</span>
          <span>{t('language.en')}</span>
        </Space>
      ),
    },
  ];

  const handleUserMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') {
      logout();
    }
  };

  const handleLanguageChange: MenuProps['onClick'] = ({ key }) => {
    i18n.changeLanguage(key);
    setLanguage(key as 'zh' | 'en');
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 16,
        paddingRight: 24,
      }}
    >
      {/* Theme switch */}
      <Tooltip title={theme === THEMES.DARK ? t('theme.light') : t('theme.dark')}>
        <Switch
          checkedChildren={<MoonOutlined />}
          unCheckedChildren={<SunOutlined />}
          checked={theme === THEMES.DARK}
          onChange={toggleTheme}
          size="small"
        />
      </Tooltip>

      {/* Language switch */}
      <Dropdown 
        menu={{ items: languageMenuItems, onClick: handleLanguageChange }}
        placement="bottomRight"
        trigger={['click']}
      >
        <Button type="text" icon={<GlobalOutlined />} size="small">
          <Space>
            <span>{i18n.language === 'zh' ? '🇨🇳' : '🇺🇸'}</span>
            <span>{i18n.language === 'zh' ? '中文' : 'EN'}</span>
          </Space>
        </Button>
      </Dropdown>

      {/* Tenant selector */}
      <TenantSelector size="small" />

      {/* Workspace switcher */}
      <WorkspaceSwitcher size="small" />

      {/* User dropdown */}
      <Dropdown 
        menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
        placement="bottomRight"
        trigger={['click']}
      >
        <Space style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: 6 }}>
          <Avatar size="small" icon={<UserOutlined />} src={user?.avatar} />
          <span style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {user?.username || 'User'}
          </span>
        </Space>
      </Dropdown>
    </div>
  );
};
