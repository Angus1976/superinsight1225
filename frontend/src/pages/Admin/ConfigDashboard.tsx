/**
 * Admin Configuration Dashboard
 * 
 * Provides system health overview, key metrics, recent alerts, and quick actions
 * for admin configuration management.
 * 
 * **Requirement 1.1, 1.2, 1.3: Dashboard**
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Badge,
  List,
  Button,
  Space,
  Spin,
  Alert,
  Typography,
  Progress,
  Tag,
  Tooltip,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  DatabaseOutlined,
  ApiOutlined,
  SyncOutlined,
  SettingOutlined,
  HistoryOutlined,
  CloudServerOutlined,
  ReloadOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { adminApi, DashboardData } from '@/services/adminApi';

const { Title, Text } = Typography;

interface HealthItemProps {
  name: string;
  status: string;
}

const HealthItem: React.FC<HealthItemProps> = ({ name, status }) => {
  const isHealthy = status === 'connected' || status === 'healthy' || status === 'ok';
  const isWarning = status === 'degraded' || status === 'slow';
  
  let icon = <CheckCircleOutlined style={{ color: '#52c41a' }} />;
  let badgeStatus: 'success' | 'error' | 'warning' = 'success';
  
  if (!isHealthy && !isWarning) {
    icon = <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    badgeStatus = 'error';
  } else if (isWarning) {
    icon = <WarningOutlined style={{ color: '#faad14' }} />;
    badgeStatus = 'warning';
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' }}>
      <Space>
        {icon}
        <Text>{name}</Text>
      </Space>
      <Badge status={badgeStatus} text={status} />
    </div>
  );
};

const ConfigDashboard: React.FC = () => {
  const navigate = useNavigate();
  
  const { data: dashboard, isLoading, error, refetch } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: () => adminApi.getDashboard(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const quickActions = [
    { name: '配置 LLM', path: '/admin/config/llm', icon: <ApiOutlined /> },
    { name: '添加数据库', path: '/admin/config/databases', icon: <DatabaseOutlined /> },
    { name: '同步策略', path: '/admin/config/sync', icon: <SyncOutlined /> },
    { name: 'SQL 构建器', path: '/admin/config/sql-builder', icon: <CloudServerOutlined /> },
    { name: '配置历史', path: '/admin/config/history', icon: <HistoryOutlined /> },
    { name: '第三方工具', path: '/admin/config/third-party', icon: <SettingOutlined /> },
  ];

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载仪表盘数据...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description="无法加载仪表盘数据，请稍后重试。"
        action={
          <Button size="small" onClick={() => refetch()}>
            重试
          </Button>
        }
      />
    );
  }

  const systemHealth = dashboard?.system_health || {};
  const keyMetrics = dashboard?.key_metrics || {};
  const configSummary = dashboard?.config_summary || {};
  const recentAlerts = dashboard?.recent_alerts || [];

  // Calculate overall health
  const healthValues = Object.values(systemHealth);
  const healthyCount = healthValues.filter(v => v === 'connected' || v === 'healthy' || v === 'ok').length;
  const healthPercent = healthValues.length > 0 ? Math.round((healthyCount / healthValues.length) * 100) : 100;

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>
          <SettingOutlined /> 管理员配置中心
        </Title>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          刷新
        </Button>
      </div>

      {/* System Health Overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title="系统健康状态" extra={<Progress type="circle" percent={healthPercent} size={50} />}>
            {Object.entries(systemHealth).map(([key, value]) => (
              <HealthItem key={key} name={key} status={value as string} />
            ))}
          </Card>
        </Col>

        {/* Key Metrics */}
        <Col xs={24} lg={16}>
          <Card title="关键指标">
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Statistic
                  title="总标注数"
                  value={keyMetrics.total_annotations || 0}
                  prefix={<CheckCircleOutlined />}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="活跃用户"
                  value={keyMetrics.active_users || 0}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="待处理任务"
                  value={keyMetrics.pending_tasks || 0}
                  valueStyle={{ color: keyMetrics.pending_tasks > 0 ? '#cf1322' : undefined }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="今日同步"
                  value={keyMetrics.sync_jobs_today || 0}
                  prefix={<SyncOutlined />}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Configuration Summary & Quick Actions */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="配置概览">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card size="small" hoverable onClick={() => navigate('/admin/config/llm')}>
                  <Statistic
                    title="LLM 配置"
                    value={configSummary.llm_configs || 0}
                    prefix={<ApiOutlined />}
                    suffix="个"
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" hoverable onClick={() => navigate('/admin/config/databases')}>
                  <Statistic
                    title="数据库连接"
                    value={configSummary.db_connections || 0}
                    prefix={<DatabaseOutlined />}
                    suffix="个"
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" hoverable onClick={() => navigate('/admin/config/sync')}>
                  <Statistic
                    title="同步策略"
                    value={configSummary.sync_strategies || 0}
                    prefix={<SyncOutlined />}
                    suffix="个"
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" hoverable onClick={() => navigate('/admin/config/third-party')}>
                  <Statistic
                    title="第三方工具"
                    value={configSummary.third_party_tools || 0}
                    prefix={<SettingOutlined />}
                    suffix="个"
                  />
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="快捷操作">
            <List
              grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 2, xl: 3 }}
              dataSource={quickActions}
              renderItem={(item) => (
                <List.Item>
                  <Button
                    type="default"
                    icon={item.icon}
                    onClick={() => navigate(item.path)}
                    style={{ width: '100%', textAlign: 'left' }}
                  >
                    {item.name}
                    <RightOutlined style={{ float: 'right', marginTop: 4 }} />
                  </Button>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Alerts */}
      {recentAlerts.length > 0 && (
        <Card title="最近告警" style={{ marginTop: 16 }}>
          <List
            dataSource={recentAlerts}
            renderItem={(alert: Record<string, unknown>) => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    <Badge
                      status={alert.severity === 'error' ? 'error' : alert.severity === 'warning' ? 'warning' : 'default'}
                    />
                  }
                  title={alert.title as string}
                  description={
                    <Space>
                      <Text type="secondary">{alert.message as string}</Text>
                      <Tag>{alert.time as string}</Tag>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
};

export default ConfigDashboard;
