// System management page
import React from 'react';
import { Tabs, Card } from 'antd';
import {
  TeamOutlined,
  DashboardOutlined,
  SecurityScanOutlined,
} from '@ant-design/icons';
import TenantManager from '@/components/System/TenantManager';
import SystemMonitoring from '@/components/System/SystemMonitoring';
import SecurityAudit from '@/components/System/SecurityAudit';
import { useAuthStore } from '@/stores/authStore';

const SystemPage: React.FC = () => {
  const { user } = useAuthStore();

  // Check admin access
  if (user?.role !== 'admin') {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <SecurityScanOutlined style={{ fontSize: 64, color: '#f5222d' }} />
          <h2 style={{ marginTop: 16 }}>Access Denied</h2>
          <p>You don't have permission to access the system management console.</p>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>System Management</h2>
      
      <Tabs
        defaultActiveKey="tenants"
        size="large"
        items={[
          {
            key: 'tenants',
            label: (
              <span>
                <TeamOutlined />
                Tenant Management
              </span>
            ),
            children: <TenantManager />,
          },
          {
            key: 'monitoring',
            label: (
              <span>
                <DashboardOutlined />
                System Monitoring
              </span>
            ),
            children: <SystemMonitoring />,
          },
          {
            key: 'security',
            label: (
              <span>
                <SecurityScanOutlined />
                Security & Audit
              </span>
            ),
            children: <SecurityAudit />,
          },
        ]}
      />
    </div>
  );
};

export default SystemPage;