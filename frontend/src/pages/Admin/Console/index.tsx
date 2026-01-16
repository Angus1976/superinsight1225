/**
 * Admin Console - System Dashboard
 * 
 * Provides system overview including:
 * - Tenant statistics
 * - Workspace statistics
 * - User statistics
 * - System health status
 * - Service status
 */

import React from 'react';
import { Card, Row, Col, Statistic, Progress, Tag, Table, Spin, Alert, Space, Button } from 'antd';
import {
  TeamOutlined,
  DatabaseOutlined,
  UserOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { adminApi, ServiceStatus } from '@/services/multiTenantApi';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const AdminConsole: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  
  const { data: dashboard, isLoading: dashboardLoading, refetch: refetchDashboard } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: () => adminApi.getDashboard().then(res => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: services, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
    queryKey: ['admin-services'],
    queryFn: () => adminApi.getServices().then(res => res.data),
    refetchInterval: 30000,
  });

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'running':
        return '#52c41a';
      case 'degraded':
        return '#faad14';
      case 'down':
      case 'unhealthy':
        return '#ff4d4f';
      default:
        return '#d9d9d9';
    }
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'running':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'degraded':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'down':
      case 'unhealthy':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <WarningOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const serviceColumns = [
    {
      title: t('console.columns.serviceName'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <CloudServerOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: t('console.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag icon={getHealthIcon(status)} color={status === 'running' ? 'success' : status === 'degraded' ? 'warning' : 'error'}>
          {status === 'running' ? t('console.status.running') : status === 'degraded' ? t('console.status.degraded') : t('console.status.stopped')}
        </Tag>
      ),
    },
    {
      title: t('console.columns.version'),
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => version || '-',
    },
    {
      title: t('console.columns.uptime'),
      dataIndex: 'uptime',
      key: 'uptime',
      render: (uptime: string) => uptime || '-',
    },
    {
      title: t('console.columns.lastCheck'),
      dataIndex: 'last_check',
      key: 'last_check',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
  ];

  if (dashboardLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
        <p>{t('common:status.loading')}</p>
      </div>
    );
  }

  return (
    <div className="admin-console">
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <h2 style={{ margin: 0 }}>
              <SettingOutlined /> {t('console.title')}
            </h2>
            <p style={{ margin: 0, color: '#666' }}>
              {t('console.subtitle')}
            </p>
          </Col>
          <Col>
            <Space>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={() => {
                  refetchDashboard();
                  refetchServices();
                }}
              >
                {t('common:refresh')}
              </Button>
              <Link to="/admin/system">
                <Button type="primary" icon={<SettingOutlined />}>
                  {t('console.systemConfig')}
                </Button>
              </Link>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* System Health Overview */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('console.systemStatus')}
              value={dashboard?.system_health?.overall === 'healthy' ? t('console.healthy') : t('console.unhealthy')}
              valueStyle={{ color: getHealthColor(dashboard?.system_health?.overall || '') }}
              prefix={getHealthIcon(dashboard?.system_health?.overall || '')}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('console.database')}
              value={dashboard?.system_health?.database === 'healthy' ? t('console.normal') : t('console.abnormal')}
              valueStyle={{ color: getHealthColor(dashboard?.system_health?.database || '') }}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('console.cache')}
              value={dashboard?.system_health?.cache === 'healthy' ? t('console.normal') : t('console.abnormal')}
              valueStyle={{ color: getHealthColor(dashboard?.system_health?.cache || '') }}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('console.storage')}
              value={dashboard?.system_health?.storage === 'healthy' ? t('console.normal') : t('console.abnormal')}
              valueStyle={{ color: getHealthColor(dashboard?.system_health?.storage || '') }}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tenant Statistics */}
      <Card title={t('console.tenantStats')} style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title={t('console.totalTenants')}
              value={dashboard?.tenant_stats?.total_tenants || 0}
              prefix={<TeamOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('console.activeTenants')}
              value={dashboard?.tenant_stats?.active_tenants || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('console.suspendedTenants')}
              value={dashboard?.tenant_stats?.suspended_tenants || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('console.disabledTenants')}
              value={dashboard?.tenant_stats?.disabled_tenants || 0}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Col>
        </Row>
        <div style={{ marginTop: 16 }}>
          <Progress
            percent={dashboard?.tenant_stats?.total_tenants ? 
              Math.round((dashboard.tenant_stats.active_tenants / dashboard.tenant_stats.total_tenants) * 100) : 0}
            status="active"
            format={() => `${dashboard?.tenant_stats?.active_tenants || 0} ${t('console.active')}`}
          />
        </div>
      </Card>

      {/* Workspace Statistics */}
      <Card title={t('console.workspaceStats')} style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title={t('console.totalWorkspaces')}
              value={dashboard?.workspace_stats?.total_workspaces || 0}
              prefix={<DatabaseOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('console.activeWorkspaces')}
              value={dashboard?.workspace_stats?.active_workspaces || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('console.archivedWorkspaces')}
              value={dashboard?.workspace_stats?.archived_workspaces || 0}
              valueStyle={{ color: '#666' }}
            />
          </Col>
        </Row>
      </Card>

      {/* User Statistics */}
      <Card title={t('console.userStats')} style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title={t('console.totalUsers')}
              value={dashboard?.user_stats?.total_users || 0}
              prefix={<UserOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('console.activeToday')}
              value={dashboard?.user_stats?.active_users_today || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('console.activeThisWeek')}
              value={dashboard?.user_stats?.active_users_week || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
        </Row>
      </Card>

      {/* Service Status */}
      <Card 
        title={t('console.serviceStatus')} 
        extra={
          <Button 
            size="small" 
            icon={<ReloadOutlined />} 
            onClick={() => refetchServices()}
            loading={servicesLoading}
          >
            {t('common:refresh')}
          </Button>
        }
      >
        <Table
          columns={serviceColumns}
          dataSource={services || []}
          loading={servicesLoading}
          rowKey="name"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Last Updated */}
      {dashboard?.last_updated && (
        <div style={{ textAlign: 'right', marginTop: 16, color: '#666' }}>
          {t('console.lastUpdated')}: {new Date(dashboard.last_updated).toLocaleString()}
        </div>
      )}
    </div>
  );
};

export default AdminConsole;
