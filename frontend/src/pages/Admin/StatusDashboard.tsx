/**
 * Status Dashboard Page
 *
 * Real-time status dashboard displaying:
 * - LLM configuration health status
 * - Database connection health status
 * - Sync pipeline health status
 * - Quota usage for LLM providers
 * - Auto-refresh every 30 seconds
 *
 * **Feature: admin-configuration**
 * **Validates: Requirements 10.6**
 */

import React, { useState, useEffect } from 'react';
import {
  Card, Row, Col, Tag, Progress, Statistic, Table, Space, Button,
  Alert, Tooltip, Badge, Spin, Switch, Typography
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
  QuestionCircleOutlined, ReloadOutlined, CloudOutlined, DatabaseOutlined,
  SyncOutlined, ApiOutlined, ClockCircleOutlined, WarningOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;

// Types
interface ServiceHealth {
  service_id: string;
  service_name: string;
  service_type: 'llm_api' | 'database' | 'sync_pipeline';
  tenant_id: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  last_check?: string;
  last_success?: string;
  last_failure?: string;
  consecutive_failures: number;
  latency_ms?: number;
  error_message?: string;
  details: Record<string, any>;
}

interface QuotaStatus {
  config_id: string;
  quota_type: string;
  provider_name: string;
  current_usage: number;
  limit: number;
  usage_percent: number;
  remaining: number;
  status: 'healthy' | 'warning' | 'critical';
  period_end: string;
  estimated_exhaustion?: string;
  last_updated: string;
}

interface DashboardStatus {
  tenant_id: string;
  llm_services: ServiceHealth[];
  database_services: ServiceHealth[];
  sync_pipelines: ServiceHealth[];
  overall_status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  healthy_count: number;
  degraded_count: number;
  unhealthy_count: number;
  last_updated: string;
}

interface QuotaDashboard {
  tenant_id: string;
  quotas: QuotaStatus[];
  summary: {
    total: number;
    healthy: number;
    warning: number;
    critical: number;
  };
  last_updated: string;
}

// Mock data - replace with actual API calls
const mockDashboardStatus: DashboardStatus = {
  tenant_id: 'default',
  llm_services: [
    {
      service_id: 'llm-openai-1',
      service_name: 'OpenAI GPT-4',
      service_type: 'llm_api',
      tenant_id: 'default',
      status: 'healthy',
      last_check: new Date().toISOString(),
      last_success: new Date().toISOString(),
      consecutive_failures: 0,
      latency_ms: 245,
      details: { model: 'gpt-4', endpoint: 'api.openai.com' },
    },
    {
      service_id: 'llm-anthropic-1',
      service_name: 'Anthropic Claude',
      service_type: 'llm_api',
      tenant_id: 'default',
      status: 'healthy',
      last_check: new Date().toISOString(),
      last_success: new Date().toISOString(),
      consecutive_failures: 0,
      latency_ms: 312,
      details: { model: 'claude-3', endpoint: 'api.anthropic.com' },
    },
  ],
  database_services: [
    {
      service_id: 'db-postgres-1',
      service_name: 'Primary PostgreSQL',
      service_type: 'database',
      tenant_id: 'default',
      status: 'healthy',
      last_check: new Date().toISOString(),
      last_success: new Date().toISOString(),
      consecutive_failures: 0,
      latency_ms: 15,
      details: { db_type: 'postgresql', version: '15.2' },
    },
    {
      service_id: 'db-mysql-1',
      service_name: 'Analytics MySQL',
      service_type: 'database',
      tenant_id: 'default',
      status: 'degraded',
      last_check: new Date().toISOString(),
      last_success: new Date(Date.now() - 60000).toISOString(),
      last_failure: new Date().toISOString(),
      consecutive_failures: 1,
      latency_ms: 850,
      error_message: 'Connection timeout',
      details: { db_type: 'mysql', version: '8.0' },
    },
  ],
  sync_pipelines: [
    {
      service_id: 'sync-crm-1',
      service_name: 'CRM Data Sync',
      service_type: 'sync_pipeline',
      tenant_id: 'default',
      status: 'healthy',
      last_check: new Date().toISOString(),
      last_success: new Date().toISOString(),
      consecutive_failures: 0,
      details: { last_sync_records: 1250, interval: '1h' },
    },
  ],
  overall_status: 'degraded',
  healthy_count: 4,
  degraded_count: 1,
  unhealthy_count: 0,
  last_updated: new Date().toISOString(),
};

const mockQuotaDashboard: QuotaDashboard = {
  tenant_id: 'default',
  quotas: [
    {
      config_id: 'llm-openai-1',
      quota_type: 'tokens',
      provider_name: 'OpenAI',
      current_usage: 850000,
      limit: 1000000,
      usage_percent: 85,
      remaining: 150000,
      status: 'warning',
      period_end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      estimated_exhaustion: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      last_updated: new Date().toISOString(),
    },
    {
      config_id: 'llm-anthropic-1',
      quota_type: 'tokens',
      provider_name: 'Anthropic',
      current_usage: 320000,
      limit: 500000,
      usage_percent: 64,
      remaining: 180000,
      status: 'healthy',
      period_end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      last_updated: new Date().toISOString(),
    },
  ],
  summary: {
    total: 2,
    healthy: 1,
    warning: 1,
    critical: 0,
  },
  last_updated: new Date().toISOString(),
};

const fetchDashboardStatus = async (): Promise<DashboardStatus> => {
  // Replace with actual API call
  return mockDashboardStatus;
};

const fetchQuotaDashboard = async (): Promise<QuotaDashboard> => {
  // Replace with actual API call
  return mockQuotaDashboard;
};

const StatusDashboard: React.FC = () => {
  const { t } = useTranslation('admin');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const REFRESH_INTERVAL = 30000; // 30 seconds

  // Fetch dashboard status
  const {
    data: dashboardStatus,
    isLoading: statusLoading,
    refetch: refetchStatus,
    dataUpdatedAt: statusUpdatedAt,
  } = useQuery({
    queryKey: ['dashboard-status'],
    queryFn: fetchDashboardStatus,
    refetchInterval: autoRefresh ? REFRESH_INTERVAL : false,
  });

  // Fetch quota dashboard
  const {
    data: quotaDashboard,
    isLoading: quotaLoading,
    refetch: refetchQuota,
  } = useQuery({
    queryKey: ['quota-dashboard'],
    queryFn: fetchQuotaDashboard,
    refetchInterval: autoRefresh ? REFRESH_INTERVAL : false,
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'degraded':
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      case 'unhealthy':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <QuestionCircleOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'unhealthy':
        return 'error';
      default:
        return 'default';
    }
  };

  const getProgressStatus = (percent: number): 'success' | 'normal' | 'exception' => {
    if (percent >= 95) return 'exception';
    if (percent >= 80) return 'normal';
    return 'success';
  };

  const formatLatency = (ms?: number) => {
    if (ms === undefined) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const serviceColumns: ColumnsType<ServiceHealth> = [
    {
      title: t('status.columns.service', 'Service'),
      key: 'service',
      render: (_, record) => (
        <Space>
          {getStatusIcon(record.status)}
          <div>
            <div style={{ fontWeight: 500 }}>{record.service_name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.service_id}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: t('status.columns.status', 'Status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('status.columns.latency', 'Latency'),
      dataIndex: 'latency_ms',
      key: 'latency',
      width: 100,
      render: (latency) => formatLatency(latency),
    },
    {
      title: t('status.columns.lastCheck', 'Last Check'),
      dataIndex: 'last_check',
      key: 'last_check',
      width: 180,
      render: (timestamp) => timestamp ? (
        <Tooltip title={new Date(timestamp).toLocaleString()}>
          <ClockCircleOutlined style={{ marginRight: 4 }} />
          {new Date(timestamp).toLocaleTimeString()}
        </Tooltip>
      ) : '-',
    },
    {
      title: t('status.columns.failures', 'Failures'),
      dataIndex: 'consecutive_failures',
      key: 'failures',
      width: 80,
      render: (failures) => failures > 0 ? (
        <Badge count={failures} style={{ backgroundColor: failures >= 3 ? '#ff4d4f' : '#faad14' }} />
      ) : (
        <Text type="secondary">0</Text>
      ),
    },
    {
      title: t('status.columns.details', 'Details'),
      key: 'details',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.error_message && (
            <Text type="danger" style={{ fontSize: 12 }}>
              {record.error_message}
            </Text>
          )}
          {record.details && Object.entries(record.details).slice(0, 2).map(([key, value]) => (
            <Text type="secondary" key={key} style={{ fontSize: 11 }}>
              {key}: {String(value)}
            </Text>
          ))}
        </Space>
      ),
    },
  ];

  const quotaColumns: ColumnsType<QuotaStatus> = [
    {
      title: t('status.quota.provider', 'Provider'),
      dataIndex: 'provider_name',
      key: 'provider',
      width: 150,
    },
    {
      title: t('status.quota.type', 'Type'),
      dataIndex: 'quota_type',
      key: 'type',
      width: 100,
      render: (type) => <Tag>{type}</Tag>,
    },
    {
      title: t('status.quota.usage', 'Usage'),
      key: 'usage',
      width: 200,
      render: (_, record) => (
        <div style={{ width: 150 }}>
          <Progress
            percent={Math.round(record.usage_percent)}
            size="small"
            status={getProgressStatus(record.usage_percent)}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {formatNumber(record.current_usage)} / {formatNumber(record.limit)}
          </Text>
        </div>
      ),
    },
    {
      title: t('status.quota.remaining', 'Remaining'),
      dataIndex: 'remaining',
      key: 'remaining',
      width: 100,
      render: (remaining) => formatNumber(remaining),
    },
    {
      title: t('status.quota.status', 'Status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('status.quota.periodEnd', 'Period End'),
      dataIndex: 'period_end',
      key: 'period_end',
      width: 150,
      render: (timestamp) => new Date(timestamp).toLocaleDateString(),
    },
    {
      title: t('status.quota.exhaustion', 'Est. Exhaustion'),
      dataIndex: 'estimated_exhaustion',
      key: 'exhaustion',
      width: 150,
      render: (timestamp) => timestamp ? (
        <Text type={new Date(timestamp) < new Date(Date.now() + 3 * 24 * 60 * 60 * 1000) ? 'danger' : 'secondary'}>
          {new Date(timestamp).toLocaleDateString()}
        </Text>
      ) : '-',
    },
  ];

  const handleRefresh = () => {
    refetchStatus();
    refetchQuota();
  };

  const isLoading = statusLoading || quotaLoading;

  return (
    <div className="status-dashboard">
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Text strong style={{ fontSize: 18 }}>
                {t('status.title', 'System Status Dashboard')}
              </Text>
              {dashboardStatus && (
                <Tag color={getStatusColor(dashboardStatus.overall_status)} style={{ marginLeft: 8 }}>
                  {getStatusIcon(dashboardStatus.overall_status)}
                  <span style={{ marginLeft: 4 }}>
                    {dashboardStatus.overall_status.toUpperCase()}
                  </span>
                </Tag>
              )}
            </Space>
          </Col>
          <Col>
            <Space>
              <Text type="secondary">
                {t('status.lastUpdated', 'Last updated')}: {new Date(statusUpdatedAt || Date.now()).toLocaleTimeString()}
              </Text>
              <Switch
                checked={autoRefresh}
                onChange={setAutoRefresh}
                checkedChildren={t('status.autoRefresh', 'Auto')}
                unCheckedChildren={t('status.manual', 'Manual')}
              />
              <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={isLoading}>
                {t('status.refresh', 'Refresh')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Summary Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('status.stats.totalServices', 'Total Services')}
              value={(dashboardStatus?.healthy_count || 0) +
                (dashboardStatus?.degraded_count || 0) +
                (dashboardStatus?.unhealthy_count || 0)}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('status.stats.healthy', 'Healthy')}
              value={dashboardStatus?.healthy_count || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('status.stats.degraded', 'Degraded')}
              value={dashboardStatus?.degraded_count || 0}
              valueStyle={{ color: '#faad14' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('status.stats.unhealthy', 'Unhealthy')}
              value={dashboardStatus?.unhealthy_count || 0}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Alerts */}
      {dashboardStatus?.degraded_count || dashboardStatus?.unhealthy_count ? (
        <Alert
          message={t('status.alert.issuesDetected', 'Service Issues Detected')}
          description={
            <Space>
              {(dashboardStatus?.degraded_count || 0) > 0 && (
                <Tag color="warning">
                  {dashboardStatus?.degraded_count} {t('status.alert.degraded', 'degraded')}
                </Tag>
              )}
              {(dashboardStatus?.unhealthy_count || 0) > 0 && (
                <Tag color="error">
                  {dashboardStatus?.unhealthy_count} {t('status.alert.unhealthy', 'unhealthy')}
                </Tag>
              )}
            </Space>
          }
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      ) : null}

      {/* LLM Services */}
      <Card
        title={
          <Space>
            <CloudOutlined />
            {t('status.llmServices', 'LLM Services')}
            <Tag>{dashboardStatus?.llm_services?.length || 0}</Tag>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Spin spinning={statusLoading}>
          <Table
            columns={serviceColumns}
            dataSource={dashboardStatus?.llm_services || []}
            rowKey="service_id"
            pagination={false}
            size="small"
          />
        </Spin>
      </Card>

      {/* Database Services */}
      <Card
        title={
          <Space>
            <DatabaseOutlined />
            {t('status.databaseServices', 'Database Connections')}
            <Tag>{dashboardStatus?.database_services?.length || 0}</Tag>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Spin spinning={statusLoading}>
          <Table
            columns={serviceColumns}
            dataSource={dashboardStatus?.database_services || []}
            rowKey="service_id"
            pagination={false}
            size="small"
          />
        </Spin>
      </Card>

      {/* Sync Pipelines */}
      <Card
        title={
          <Space>
            <SyncOutlined />
            {t('status.syncPipelines', 'Sync Pipelines')}
            <Tag>{dashboardStatus?.sync_pipelines?.length || 0}</Tag>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Spin spinning={statusLoading}>
          <Table
            columns={serviceColumns}
            dataSource={dashboardStatus?.sync_pipelines || []}
            rowKey="service_id"
            pagination={false}
            size="small"
          />
        </Spin>
      </Card>

      {/* Quota Usage */}
      <Card
        title={
          <Space>
            <ApiOutlined />
            {t('status.quotaUsage', 'LLM Quota Usage')}
            {quotaDashboard?.summary && (
              <>
                <Tag color="success">{quotaDashboard.summary.healthy} {t('status.quota.healthy', 'healthy')}</Tag>
                {quotaDashboard.summary.warning > 0 && (
                  <Tag color="warning">{quotaDashboard.summary.warning} {t('status.quota.warning', 'warning')}</Tag>
                )}
                {quotaDashboard.summary.critical > 0 && (
                  <Tag color="error">{quotaDashboard.summary.critical} {t('status.quota.critical', 'critical')}</Tag>
                )}
              </>
            )}
          </Space>
        }
      >
        <Spin spinning={quotaLoading}>
          <Table
            columns={quotaColumns}
            dataSource={quotaDashboard?.quotas || []}
            rowKey="config_id"
            pagination={false}
            size="small"
          />
        </Spin>
      </Card>
    </div>
  );
};

export default StatusDashboard;
