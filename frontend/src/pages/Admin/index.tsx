// Admin console page
import React from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Alert, Card, Menu } from 'antd';
import { SecurityScanOutlined, TeamOutlined, DatabaseOutlined, SettingOutlined, DashboardOutlined } from '@ant-design/icons';
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

  // If on sub-route, render the child component
  if (isSubRoute) {
    return (
      <div>
        <Card style={{ marginBottom: 16 }}>
          <Menu mode="horizontal" selectedKeys={[location.pathname.split('/').pop() || '']}>
            <Menu.Item key="admin">
              <Link to="/admin">
                <DashboardOutlined /> 管理概览
              </Link>
            </Menu.Item>
            <Menu.Item key="tenants">
              <Link to="/admin/tenants">
                <DatabaseOutlined /> 租户管理
              </Link>
            </Menu.Item>
            <Menu.Item key="users">
              <Link to="/admin/users">
                <TeamOutlined /> 用户管理
              </Link>
            </Menu.Item>
            <Menu.Item key="system">
              <Link to="/admin/system">
                <SettingOutlined /> 系统配置
              </Link>
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
