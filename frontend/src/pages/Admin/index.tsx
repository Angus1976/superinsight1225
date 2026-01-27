// Admin console page
import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Alert, Card, Menu, Dropdown, Space } from 'antd';
import type { MenuProps } from 'antd';
import { 
  SecurityScanOutlined, TeamOutlined, DatabaseOutlined, SettingOutlined, 
  DashboardOutlined, ApiOutlined, SafetyOutlined, CloudOutlined, DollarOutlined,
  AppstoreOutlined, SyncOutlined, HistoryOutlined, CodeOutlined, ToolOutlined,
  DownOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import SystemPage from '@/pages/System';
import { useAuthStore } from '@/stores/authStore';

const AdminPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const location = useLocation();

  // Check admin access
  if (user?.role !== 'admin') {
    return (
      <Alert
        type="error"
        message="Access Denied"
        description="You don't have permission to access the admin console."
        showIcon
        icon={<SecurityScanOutlined />}
        style={{ margin: 24 }}
      />
    );
  }

  // Check if we're on a sub-route
  const isSubRoute = location.pathname !== '/admin';

  // Get current menu key
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.includes('/console')) return 'console';
    if (path.includes('/tenants')) return 'tenants';
    if (path.includes('/workspaces')) return 'workspaces';
    if (path.includes('/members')) return 'members';
    if (path.includes('/permissions')) return 'permissions';
    if (path.includes('/quotas')) return 'quotas';
    if (path.includes('/billing')) return 'billing';
    if (path.includes('/users')) return 'users';
    if (path.includes('/system')) return 'system';
    if (path.includes('/llm-config')) return 'llm-config';
    // Admin Configuration Module
    if (path.includes('/config/llm')) return 'config-llm';
    if (path.includes('/config/databases')) return 'config-db';
    if (path.includes('/config/sync')) return 'config-sync';
    if (path.includes('/config/sql-builder')) return 'config-sql';
    if (path.includes('/config/history')) return 'config-history';
    if (path.includes('/config/third-party')) return 'config-third-party';
    if (path.includes('/config')) return 'config';
    return 'admin';
  };

  // Config submenu items
  const configMenuItems: MenuProps['items'] = [
    {
      key: 'config',
      label: <Link to="/admin/config">{t('admin:nav.configCenter')}</Link>,
      icon: <DashboardOutlined />,
    },
    {
      key: 'config-llm',
      label: <Link to="/admin/config/llm">{t('admin:nav.llmConfig')}</Link>,
      icon: <ApiOutlined />,
    },
    {
      key: 'config-db',
      label: <Link to="/admin/config/databases">{t('admin:nav.databaseConfig')}</Link>,
      icon: <DatabaseOutlined />,
    },
    {
      key: 'config-sync',
      label: <Link to="/admin/config/sync">{t('admin:nav.syncStrategy')}</Link>,
      icon: <SyncOutlined />,
    },
    {
      key: 'config-sql',
      label: <Link to="/admin/config/sql-builder">{t('admin:nav.sqlBuilder')}</Link>,
      icon: <CodeOutlined />,
    },
    {
      key: 'config-history',
      label: <Link to="/admin/config/history">{t('admin:nav.configHistory')}</Link>,
      icon: <HistoryOutlined />,
    },
    {
      key: 'config-third-party',
      label: <Link to="/admin/config/third-party">{t('admin:nav.thirdPartyTools')}</Link>,
      icon: <ToolOutlined />,
    },
  ];

  const selectedKey = getSelectedKey();
  const isConfigSelected = selectedKey.startsWith('config');

  // If on sub-route, render the child component
  if (isSubRoute) {
    return (
      <div>
        <Card style={{ marginBottom: 16 }}>
          <Menu mode="horizontal" selectedKeys={[selectedKey]}>
            <Menu.Item key="admin">
              <Link to="/admin">
                <DashboardOutlined /> {t('admin:nav.overview')}
              </Link>
            </Menu.Item>
            <Menu.Item key="console">
              <Link to="/admin/console">
                <AppstoreOutlined /> {t('admin:nav.console')}
              </Link>
            </Menu.Item>
            <Menu.Item key="tenants">
              <Link to="/admin/tenants">
                <DatabaseOutlined /> {t('admin:nav.tenants')}
              </Link>
            </Menu.Item>
            <Menu.Item key="workspaces">
              <Link to="/admin/workspaces">
                <AppstoreOutlined /> {t('admin:nav.workspaces')}
              </Link>
            </Menu.Item>
            <Menu.Item key="members">
              <Link to="/admin/members">
                <TeamOutlined /> {t('admin:nav.members')}
              </Link>
            </Menu.Item>
            <Menu.Item key="permissions">
              <Link to="/admin/permissions">
                <SafetyOutlined /> {t('admin:nav.permissions')}
              </Link>
            </Menu.Item>
            <Menu.Item key="quotas">
              <Link to="/admin/quotas">
                <CloudOutlined /> {t('admin:nav.quotas')}
              </Link>
            </Menu.Item>
            <Menu.Item key="billing">
              <Link to="/admin/billing">
                <DollarOutlined /> {t('admin:nav.billing')}
              </Link>
            </Menu.Item>
            <Menu.Item key="system">
              <Link to="/admin/system">
                <SettingOutlined /> {t('admin:nav.system')}
              </Link>
            </Menu.Item>
            <Menu.Item key="llm-config">
              <Link to="/admin/llm-config">
                <ApiOutlined /> {t('admin:nav.llm')}
              </Link>
            </Menu.Item>
            <Menu.Item key="config-menu" style={{ padding: 0 }}>
              <Dropdown menu={{ items: configMenuItems, selectedKeys: isConfigSelected ? [selectedKey] : [] }} placement="bottomLeft">
                <Space style={{ padding: '0 16px', color: isConfigSelected ? '#1890ff' : undefined }}>
                  <SettingOutlined /> {t('admin:nav.configManagement')} <DownOutlined />
                </Space>
              </Dropdown>
            </Menu.Item>
          </Menu>
        </Card>
        <Outlet />
      </div>
    );
  }

  return <SystemPage />;
};

export default AdminPage;
