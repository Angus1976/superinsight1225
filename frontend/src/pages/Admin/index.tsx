// Admin console page
import React from 'react';
import { Alert } from 'antd';
import { SecurityScanOutlined } from '@ant-design/icons';
import SystemPage from '@/pages/System';
import { useAuthStore } from '@/stores/authStore';

const AdminPage: React.FC = () => {
  const { user } = useAuthStore();

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

  return <SystemPage />;
};

export default AdminPage;
