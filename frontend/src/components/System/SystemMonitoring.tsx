// System monitoring dashboard component
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Button,
  Space,
  Select,
  DatePicker,
  Tooltip,
  Badge,
  List,
  Typography,
  Divider,
} from 'antd';
import {
  DashboardOutlined,
  DatabaseOutlined,
  CloudOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import {
  useSystemMetrics,
  useSystemHealth,
  useSystemAlerts,
  useAcknowledgeAlert,
  useResolveAlert,
  useRestartService,
} from '@/hooks';
import type { SystemAlert, ServiceHealth } from '@/types';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const SystemMonitoring: React.FC = () => {
  const { t } = useTranslation('admin');
  const [timeRange, setTimeRange] = useState<[string, string]>([
    dayjs().subtract(24, 'hour').toISOString(),
    dayjs().toISOString(),
  ]);
  const [refreshInterval, setRefreshInterval] = useState(30);

  const { data: systemHealth } = useSystemHealth();
  const { data: systemAlerts = [] } = useSystemAlerts({ limit: 10 });
  const { data: systemMetrics = [] } = useSystemMetrics({
    start_time: timeRange[0],
    end_time: timeRange[1],
    interval: '5m',
  });

  const acknowledgeAlertMutation = useAcknowledgeAlert();
  const resolveAlertMutation = useResolveAlert();
  const restartServiceMutation = useRestartService();

  // Auto refresh
  useEffect(() => {
    const interval = setInterval(() => {
      // Queries will auto-refresh due to refetchInterval in hooks
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const handleAcknowledgeAlert = (id: string) => {
    acknowledgeAlertMutation.mutate(id);
  };

  const handleResolveAlert = (id: string) => {
    resolveAlertMutation.mutate(id);
  };

  const handleRestartService = (serviceName: string) => {
    restartServiceMutation.mutate(serviceName);
  };

  // Prepare chart data
  const metricsChartData = systemMetrics.map(metric => ({
    time: new Date(metric.timestamp).toLocaleTimeString(),
    cpu: metric.cpu_usage,
    memory: metric.memory_usage,
    disk: metric.disk_usage,
  }));

  const serviceStatusData = systemHealth?.services?.map(service => ({
    name: service.name,
    value: service.status === 'healthy' ? 1 : 0,
    status: service.status,
  })) || [];

  // Service health columns
  const serviceColumns: ColumnsType<ServiceHealth> = [
    {
      title: t('systemMonitoring.services.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name) => (
        <Space>
          <DashboardOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: t('systemMonitoring.services.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig = {
          healthy: { color: 'success', icon: <CheckCircleOutlined />, text: t('systemMonitoring.services.healthy') },
          degraded: { color: 'warning', icon: <ExclamationCircleOutlined />, text: t('systemMonitoring.services.degraded') },
          unhealthy: { color: 'error', icon: <CloseCircleOutlined />, text: t('systemMonitoring.services.unhealthy') },
        };
        const config = statusConfig[status as keyof typeof statusConfig];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: t('systemMonitoring.services.uptime'),
      dataIndex: 'uptime',
      key: 'uptime',
      render: (uptime) => {
        const hours = Math.floor(uptime / 3600);
        const minutes = Math.floor((uptime % 3600) / 60);
        return `${hours}h ${minutes}m`;
      },
    },
    {
      title: t('systemMonitoring.services.responseTime'),
      dataIndex: 'response_time',
      key: 'response_time',
      render: (time) => `${time}ms`,
    },
    {
      title: t('systemMonitoring.services.errorRate'),
      dataIndex: 'error_rate',
      key: 'error_rate',
      render: (rate) => (
        <Progress
          percent={rate * 100}
          size="small"
          status={rate > 0.05 ? 'exception' : 'success'}
          format={(percent) => `${percent?.toFixed(1)}%`}
        />
      ),
    },
    {
      title: t('systemMonitoring.services.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('systemMonitoring.services.restartService')}>
            <Button
              type="link"
              icon={<ReloadOutlined />}
              size="small"
              onClick={() => handleRestartService(record.name)}
              loading={restartServiceMutation.isPending}
            />
          </Tooltip>
          <Tooltip title={t('systemMonitoring.services.serviceSettings')}>
            <Button
              type="link"
              icon={<SettingOutlined />}
              size="small"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Alert columns
  const alertColumns: ColumnsType<SystemAlert> = [
    {
      title: t('systemMonitoring.alerts.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        const typeConfig = {
          info: { color: 'blue', icon: <ExclamationCircleOutlined />, text: t('systemMonitoring.alerts.types.info') },
          warning: { color: 'orange', icon: <WarningOutlined />, text: t('systemMonitoring.alerts.types.warning') },
          error: { color: 'red', icon: <CloseCircleOutlined />, text: t('systemMonitoring.alerts.types.error') },
          critical: { color: 'red', icon: <ExclamationCircleOutlined />, text: t('systemMonitoring.alerts.types.critical') },
        };
        const config = typeConfig[type as keyof typeof typeConfig];
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: t('systemMonitoring.alerts.message'),
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: t('systemMonitoring.alerts.source'),
      dataIndex: 'source',
      key: 'source',
    },
    {
      title: t('systemMonitoring.alerts.time'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time) => new Date(time).toLocaleString(),
    },
    {
      title: t('systemMonitoring.alerts.status'),
      key: 'status',
      render: (_, record) => {
        if (record.resolved) {
          return <Tag color="success">{t('systemMonitoring.alerts.statuses.resolved')}</Tag>;
        }
        if (record.acknowledged) {
          return <Tag color="processing">{t('systemMonitoring.alerts.statuses.acknowledged')}</Tag>;
        }
        return <Tag color="error">{t('systemMonitoring.alerts.statuses.new')}</Tag>;
      },
    },
    {
      title: t('systemMonitoring.alerts.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          {!record.acknowledged && (
            <Button
              type="link"
              size="small"
              onClick={() => handleAcknowledgeAlert(record.id)}
              loading={acknowledgeAlertMutation.isPending}
            >
              {t('systemMonitoring.alerts.acknowledge')}
            </Button>
          )}
          {!record.resolved && (
            <Button
              type="link"
              size="small"
              onClick={() => handleResolveAlert(record.id)}
              loading={resolveAlertMutation.isPending}
            >
              {t('systemMonitoring.alerts.resolve')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const criticalAlerts = systemAlerts.filter(alert => 
    alert.type === 'critical' && !alert.resolved
  ).length;

  const warningAlerts = systemAlerts.filter(alert => 
    alert.type === 'warning' && !alert.resolved
  ).length;

  return (
    <div>
      {/* Controls */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <Text strong>{t('systemMonitoring.timeRange')}:</Text>
              <RangePicker
                showTime
                value={[
                  dayjs(timeRange[0]),
                  dayjs(timeRange[1]),
                ]}
                onChange={(dates) => {
                  if (dates && dates[0] && dates[1]) {
                    setTimeRange([
                      dates[0].toISOString(),
                      dates[1].toISOString(),
                    ]);
                  }
                }}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Text strong>{t('systemMonitoring.refresh')}:</Text>
              <Select
                value={refreshInterval}
                onChange={setRefreshInterval}
                style={{ width: 120 }}
              >
                <Select.Option value={10}>10s</Select.Option>
                <Select.Option value={30}>30s</Select.Option>
                <Select.Option value={60}>1m</Select.Option>
                <Select.Option value={300}>5m</Select.Option>
              </Select>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* System Overview */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('systemMonitoring.overview.systemStatus')}
              value={systemHealth?.status || 'Unknown'}
              valueStyle={{
                color: systemHealth?.status === 'healthy' ? '#52c41a' : '#f5222d',
              }}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('systemMonitoring.overview.uptime')}
              value={systemHealth?.uptime ? Math.floor(systemHealth.uptime / 3600) : 0}
              suffix={t('systemMonitoring.overview.hours')}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Badge count={criticalAlerts} offset={[10, 0]}>
              <Statistic
                title={t('systemMonitoring.overview.criticalAlerts')}
                value={criticalAlerts}
                valueStyle={{ color: criticalAlerts > 0 ? '#f5222d' : '#52c41a' }}
                prefix={<WarningOutlined />}
              />
            </Badge>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Badge count={warningAlerts} offset={[10, 0]}>
              <Statistic
                title={t('systemMonitoring.overview.warnings')}
                value={warningAlerts}
                valueStyle={{ color: warningAlerts > 0 ? '#fa8c16' : '#52c41a' }}
                prefix={<ExclamationCircleOutlined />}
              />
            </Badge>
          </Card>
        </Col>
      </Row>

      {/* System Metrics Charts */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={16}>
          <Card title={t('systemMonitoring.charts.systemPerformance')} style={{ height: 400 }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metricsChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <RechartsTooltip />
                <Line
                  type="monotone"
                  dataKey="cpu"
                  stroke="#8884d8"
                  name={t('systemMonitoring.charts.cpuUsage')}
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  stroke="#82ca9d"
                  name={t('systemMonitoring.charts.memoryUsage')}
                />
                <Line
                  type="monotone"
                  dataKey="disk"
                  stroke="#ffc658"
                  name={t('systemMonitoring.charts.diskUsage')}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t('systemMonitoring.charts.serviceStatus')} style={{ height: 400 }}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={serviceStatusData}
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  fill="#8884d8"
                  dataKey="value"
                  label={(entry: any) => `${entry.name}: ${entry.status}`}
                >
                  {serviceStatusData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.status === 'healthy' ? '#52c41a' : '#f5222d'}
                    />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
            <Divider />
            <List
              size="small"
              dataSource={systemHealth?.services?.slice(0, 5) || []}
              renderItem={(service) => (
                <List.Item>
                  <Space>
                    <Badge
                      status={
                        service.status === 'healthy'
                          ? 'success'
                          : service.status === 'degraded'
                          ? 'warning'
                          : 'error'
                      }
                    />
                    <Text>{service.name}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Service Health Table */}
      <Card title={t('systemMonitoring.services.title')} style={{ marginBottom: 16 }}>
        <Table
          columns={serviceColumns}
          dataSource={systemHealth?.services || []}
          rowKey="name"
          pagination={false}
          size="small"
        />
      </Card>

      {/* System Alerts */}
      <Card title={t('systemMonitoring.alerts.title')}>
        <Table
          columns={alertColumns}
          dataSource={systemAlerts}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
          size="small"
        />
      </Card>
    </div>
  );
};

export default SystemMonitoring;