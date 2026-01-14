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
import SystemPage from '@/pages/System';
import { useAuthStore } from '@/stores/authStore';

const AdminPage: React.FC = () => {
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
      label: <Link to="/admin/config">配置中心</Link>,
      icon: <DashboardOutlined />,
    },
    {
      key: 'config-llm',
      label: <Link to="/admin/config/llm">LLM 配置</Link>,
      icon: <ApiOutlined />,
    },
    {
      key: 'config-db',
      label: <Link to="/admin/config/databases">数据库配置</Link>,
      icon: <DatabaseOutlined />,
    },
    {
      key: 'config-sync',
      label: <Link to="/admin/config/sync">同步策略</Link>,
      icon: <SyncOutlined />,
    },
    {
      key: 'config-sql',
      label: <Link to="/admin/config/sql-builder">SQL 构建器</Link>,
      icon: <CodeOutlined />,
    },
    {
      key: 'config-history',
      label: <Link to="/admin/config/history">配置历史</Link>,
      icon: <HistoryOutlined />,
    },
    {
      key: 'config-third-party',
      label: <Link to="/admin/config/third-party">第三方工具</Link>,
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
                <DashboardOutlined /> 概览
              </Link>
            </Menu.Item>
            <Menu.Item key="console">
              <Link to="/admin/console">
                <AppstoreOutlined /> 控制台
              </Link>
            </Menu.Item>
            <Menu.Item key="tenants">
              <Link to="/admin/tenants">
                <DatabaseOutlined /> 租户
              </Link>
            </Menu.Item>
            <Menu.Item key="workspaces">
              <Link to="/admin/workspaces">
                <AppstoreOutlined /> 工作空间
              </Link>
            </Menu.Item>
            <Menu.Item key="members">
              <Link to="/admin/members">
                <TeamOutlined /> 成员
              </Link>
            </Menu.Item>
            <Menu.Item key="permissions">
              <Link to="/admin/permissions">
                <SafetyOutlined /> 权限
              </Link>
            </Menu.Item>
            <Menu.Item key="quotas">
              <Link to="/admin/quotas">
                <CloudOutlined /> 配额
              </Link>
            </Menu.Item>
            <Menu.Item key="billing">
              <Link to="/admin/billing">
                <DollarOutlined /> 计费
              </Link>
            </Menu.Item>
            <Menu.Item key="system">
              <Link to="/admin/system">
                <SettingOutlined /> 系统
              </Link>
            </Menu.Item>
            <Menu.Item key="llm-config">
              <Link to="/admin/llm-config">
                <ApiOutlined /> LLM
              </Link>
            </Menu.Item>
            <Menu.Item key="config-menu" style={{ padding: 0 }}>
              <Dropdown menu={{ items: configMenuItems, selectedKeys: isConfigSelected ? [selectedKey] : [] }} placement="bottomLeft">
                <Space style={{ padding: '0 16px', color: isConfigSelected ? '#1890ff' : undefined }}>
                  <SettingOutlined /> 配置管理 <DownOutlined />
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
