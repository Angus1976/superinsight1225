// Admin console page
import React, { useEffect, useCallback, useRef } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Alert, Card, Menu, Dropdown, Space } from 'antd';
import type { MenuProps } from 'antd';
import { 
  SecurityScanOutlined, TeamOutlined, DatabaseOutlined, SettingOutlined, 
  DashboardOutlined, ApiOutlined, SafetyOutlined, CloudOutlined, DollarOutlined,
  AppstoreOutlined, SyncOutlined, HistoryOutlined, CodeOutlined, ToolOutlined,
  DownOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { optimizedApiClient } from '@/services/api/client';
import SystemPage from '@/pages/System';
import { useAuthStore } from '@/stores/authStore';

const AdminPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNavigatingRef = useRef(false);

  // Clear caches when route changes to ensure fresh data
  useEffect(() => {
    // Clear React Query cache for admin-related queries
    queryClient.invalidateQueries({ queryKey: ['admin'] });
    // Clear API client cache to prevent stale data
    optimizedApiClient.clearCache();
    // Reset navigation flag when route changes
    isNavigatingRef.current = false;
  }, [location.pathname, queryClient]);

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

  const selectedKey = getSelectedKey();
  const isConfigSelected = selectedKey.startsWith('config');

  // Handle menu click with debounce to prevent rapid navigation
  const handleMenuClick = useCallback((path: string) => {
    // Prevent rapid clicks
    if (isNavigatingRef.current) {
      return;
    }
    // Don't navigate if already on the same path
    if (location.pathname === path) {
      return;
    }
    isNavigatingRef.current = true;
    navigate(path);
  }, [navigate, location.pathname]);

  // Config submenu items
  const configMenuItems: MenuProps['items'] = [
    {
      key: 'config',
      label: t('admin:nav.configCenter'),
      icon: <DashboardOutlined />,
      onClick: () => handleMenuClick('/admin/config'),
    },
    {
      key: 'config-llm',
      label: t('admin:nav.llmConfig'),
      icon: <ApiOutlined />,
      onClick: () => handleMenuClick('/admin/config/llm'),
    },
    {
      key: 'config-db',
      label: t('admin:nav.databaseConfig'),
      icon: <DatabaseOutlined />,
      onClick: () => handleMenuClick('/admin/config/databases'),
    },
    {
      key: 'config-sync',
      label: t('admin:nav.syncStrategy'),
      icon: <SyncOutlined />,
      onClick: () => handleMenuClick('/admin/config/sync'),
    },
    {
      key: 'config-sql',
      label: t('admin:nav.sqlBuilder'),
      icon: <CodeOutlined />,
      onClick: () => handleMenuClick('/admin/config/sql-builder'),
    },
    {
      key: 'config-history',
      label: t('admin:nav.configHistory'),
      icon: <HistoryOutlined />,
      onClick: () => handleMenuClick('/admin/config/history'),
    },
    {
      key: 'config-third-party',
      label: t('admin:nav.thirdPartyTools'),
      icon: <ToolOutlined />,
      onClick: () => handleMenuClick('/admin/config/third-party'),
    },
  ];

  // Menu items configuration
  const menuItems: MenuProps['items'] = [
    {
      key: 'admin',
      label: <><DashboardOutlined /> {t('admin:nav.overview')}</>,
      onClick: () => handleMenuClick('/admin'),
    },
    {
      key: 'console',
      label: <><AppstoreOutlined /> {t('admin:nav.console')}</>,
      onClick: () => handleMenuClick('/admin/console'),
    },
    {
      key: 'tenants',
      label: <><DatabaseOutlined /> {t('admin:nav.tenants')}</>,
      onClick: () => handleMenuClick('/admin/tenants'),
    },
    {
      key: 'workspaces',
      label: <><AppstoreOutlined /> {t('admin:nav.workspaces')}</>,
      onClick: () => handleMenuClick('/admin/workspaces'),
    },
    {
      key: 'members',
      label: <><TeamOutlined /> {t('admin:nav.members')}</>,
      onClick: () => handleMenuClick('/admin/members'),
    },
    {
      key: 'permissions',
      label: <><SafetyOutlined /> {t('admin:nav.permissions')}</>,
      onClick: () => handleMenuClick('/admin/permissions'),
    },
    {
      key: 'quotas',
      label: <><CloudOutlined /> {t('admin:nav.quotas')}</>,
      onClick: () => handleMenuClick('/admin/quotas'),
    },
    {
      key: 'billing',
      label: <><DollarOutlined /> {t('admin:nav.billing')}</>,
      onClick: () => handleMenuClick('/admin/billing'),
    },
    {
      key: 'system',
      label: <><SettingOutlined /> {t('admin:nav.system')}</>,
      onClick: () => handleMenuClick('/admin/system'),
    },
    {
      key: 'llm-config',
      label: <><ApiOutlined /> {t('admin:nav.llm')}</>,
      onClick: () => handleMenuClick('/admin/llm-config'),
    },
    {
      key: 'config-menu',
      label: (
        <Dropdown menu={{ items: configMenuItems, selectedKeys: isConfigSelected ? [selectedKey] : [] }} placement="bottomLeft">
          <Space style={{ color: isConfigSelected ? '#1890ff' : undefined }}>
            <SettingOutlined /> {t('admin:nav.configManagement')} <DownOutlined />
          </Space>
        </Dropdown>
      ),
    },
  ];

  // If on sub-route, render the child component
  if (isSubRoute) {
    return (
      <div key={location.pathname}>
        <Card style={{ marginBottom: 16 }}>
          <Menu 
            mode="horizontal" 
            selectedKeys={[selectedKey]} 
            items={menuItems}
          />
        </Card>
        <Outlet />
      </div>
    );
  }

  return <SystemPage />;
};

export default AdminPage;
