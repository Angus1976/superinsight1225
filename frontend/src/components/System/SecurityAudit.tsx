// Security audit and logs component
import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  DatePicker,
  Select,
  Input,
  Row,
  Col,
  Statistic,
  Alert,
  Tooltip,
  Modal,
  Descriptions,
  Typography,
  Timeline,
  Badge,
  Tabs,
} from 'antd';
import {
  SearchOutlined,
  EyeOutlined,
  DownloadOutlined,
  SecurityScanOutlined,
  UserOutlined,
  LockOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { useAuditLogs, useSystemLogs } from '@/hooks';
import type { SystemAuditLog } from '@/types';

const { RangePicker } = DatePicker;
const { Search } = Input;
const { Text } = Typography;
const { TabPane } = Tabs;

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const SecurityAudit: React.FC = () => {
  const { t } = useTranslation('admin');
  const [auditFilters, setAuditFilters] = useState({
    tenant_id: undefined as string | undefined,
    user_id: undefined as string | undefined,
    action: undefined as string | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
    limit: 50,
    offset: 0,
  });

  const [systemLogFilters, setSystemLogFilters] = useState({
    service: undefined as string | undefined,
    level: undefined as string | undefined,
    start_time: undefined as string | undefined,
    end_time: undefined as string | undefined,
    limit: 50,
  });

  const [selectedLog, setSelectedLog] = useState<SystemAuditLog | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const { data: auditLogsData } = useAuditLogs(auditFilters);
  const { data: systemLogsData } = useSystemLogs(systemLogFilters);

  const auditLogs = auditLogsData?.logs || [];
  const systemLogs = systemLogsData?.logs || [];

  const handleViewDetails = (log: SystemAuditLog) => {
    setSelectedLog(log);
    setDetailModalOpen(true);
  };

  const handleExportLogs = () => {
    // Export functionality
    console.log('Exporting logs...');
  };

  // Audit log columns
  const auditColumns: ColumnsType<SystemAuditLog> = [
    {
      title: t('securityAudit.columns.time'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (time) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    },
    {
      title: t('securityAudit.columns.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
      render: (userId) => (
        <Space>
          <UserOutlined />
          <Text code>{userId}</Text>
        </Space>
      ),
    },
    {
      title: t('securityAudit.columns.action'),
      dataIndex: 'action',
      key: 'action',
      width: 150,
      render: (action) => {
        const actionColors: Record<string, string> = {
          login: 'blue',
          logout: 'default',
          create: 'green',
          update: 'orange',
          delete: 'red',
          view: 'cyan',
          export: 'purple',
        };
        const color = actionColors[action.toLowerCase()] || 'default';
        const actionKey = action.toLowerCase() as keyof typeof t;
        const actionText = t(`securityAudit.actions.${actionKey}`, { defaultValue: action });
        return <Tag color={color}>{actionText.toUpperCase()}</Tag>;
      },
    },
    {
      title: t('securityAudit.columns.resource'),
      key: 'resource',
      width: 200,
      render: (_, record) => (
        <div>
          <Text strong>{record.resource_type}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            ID: {record.resource_id}
          </Text>
        </div>
      ),
    },
    {
      title: t('securityAudit.columns.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
      render: (ip) => <Text code>{ip}</Text>,
    },
    {
      title: t('securityAudit.columns.status'),
      key: 'status',
      width: 100,
      render: (_, record) => {
        // Determine status based on action or details
        const isSuccess = !record.details?.error;
        return isSuccess ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            {t('securityAudit.status.success')}
          </Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />}>
            {t('securityAudit.status.failed')}
          </Tag>
        );
      },
    },
    {
      title: t('securityAudit.columns.actions'),
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('securityAudit.tooltips.viewDetails')}>
            <Button
              type="link"
              icon={<EyeOutlined />}
              size="small"
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // System log columns
  const systemLogColumns: ColumnsType<any> = [
    {
      title: t('securityAudit.columns.time'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (time) => new Date(time).toLocaleString(),
    },
    {
      title: t('securityAudit.columns.level'),
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level) => {
        const levelColors: Record<string, string> = {
          DEBUG: 'default',
          INFO: 'blue',
          WARN: 'orange',
          ERROR: 'red',
          FATAL: 'red',
        };
        return <Tag color={levelColors[level]}>{level}</Tag>;
      },
    },
    {
      title: t('securityAudit.columns.service'),
      dataIndex: 'service',
      key: 'service',
      width: 120,
      render: (service) => (
        <Space>
          <SecurityScanOutlined />
          {service}
        </Space>
      ),
    },
    {
      title: t('securityAudit.columns.message'),
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
  ];

  // Prepare chart data
  const actionStats = auditLogs.reduce((acc: Record<string, number>, log: SystemAuditLog) => {
    acc[log.action] = (acc[log.action] || 0) + 1;
    return acc;
  }, {});

  const actionChartData = Object.entries(actionStats).map(([action, count]) => ({
    action,
    count,
  }));

  const hourlyStats = auditLogs.reduce((acc: Record<number, number>, log: SystemAuditLog) => {
    const hour = new Date(log.timestamp).getHours();
    acc[hour] = (acc[hour] || 0) + 1;
    return acc;
  }, {});

  const hourlyChartData = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    count: hourlyStats[i] || 0,
  }));

  const riskLevels = auditLogs.reduce((acc: Record<string, number>, log: SystemAuditLog) => {
    const isHighRisk = ['delete', 'export', 'admin'].some(keyword =>
      log.action.toLowerCase().includes(keyword)
    );
    const level = isHighRisk ? 'High' : 'Low';
    acc[level] = (acc[level] || 0) + 1;
    return acc;
  }, {});

  const riskChartData = Object.entries(riskLevels).map(([level, count]) => ({
    level,
    count,
  }));

  return (
    <div>
      {/* Security Overview */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('securityAudit.overview.totalAuditLogs')}
              value={auditLogsData?.total || 0}
              prefix={<SecurityScanOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('securityAudit.overview.highRiskActions')}
              value={riskLevels.High || 0}
              valueStyle={{ color: '#f5222d' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('securityAudit.overview.failedLogins')}
              value={auditLogs.filter((log: SystemAuditLog) => 
                log.action === 'login' && log.details?.error
              ).length}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<LockOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('securityAudit.overview.activeUsers')}
              value={new Set(auditLogs.map((log: SystemAuditLog) => log.user_id)).size}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Security Analytics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title={t('securityAudit.charts.actionDistribution')} style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={actionChartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  fill="#8884d8"
                  dataKey="count"
                  label={(entry: any) => `${entry.action}: ${entry.count}`}
                >
                  {actionChartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t('securityAudit.charts.hourlyActivity')} style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={hourlyChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <RechartsTooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t('securityAudit.charts.riskAssessment')} style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={riskChartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  fill="#8884d8"
                  dataKey="count"
                  label={(entry: any) => `${entry.level}: ${entry.count}`}
                >
                  {riskChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.level === 'High' ? '#f5222d' : '#52c41a'}
                    />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* Logs Tables */}
      <Tabs defaultActiveKey="audit">
        <TabPane tab={t('securityAudit.tabs.audit')} key="audit">
          <Card
            title={t('securityAudit.auditLogs')}
            extra={
              <Space>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={handleExportLogs}
                >
                  {t('securityAudit.export')}
                </Button>
              </Space>
            }
          >
            {/* Filters */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={8}>
                <Search
                  placeholder={t('securityAudit.filters.searchByUserId')}
                  onSearch={(value) =>
                    setAuditFilters(prev => ({ ...prev, user_id: value || undefined }))
                  }
                  allowClear
                />
              </Col>
              <Col xs={24} sm={6}>
                <Select
                  placeholder={t('securityAudit.filters.action')}
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) =>
                    setAuditFilters(prev => ({ ...prev, action: value }))
                  }
                >
                  <Select.Option value="login">{t('securityAudit.actions.login')}</Select.Option>
                  <Select.Option value="logout">{t('securityAudit.actions.logout')}</Select.Option>
                  <Select.Option value="create">{t('securityAudit.actions.create')}</Select.Option>
                  <Select.Option value="update">{t('securityAudit.actions.update')}</Select.Option>
                  <Select.Option value="delete">{t('securityAudit.actions.delete')}</Select.Option>
                  <Select.Option value="view">{t('securityAudit.actions.view')}</Select.Option>
                  <Select.Option value="export">{t('securityAudit.actions.export')}</Select.Option>
                </Select>
              </Col>
              <Col xs={24} sm={10}>
                <RangePicker
                  style={{ width: '100%' }}
                  showTime
                  onChange={(dates) => {
                    setAuditFilters(prev => ({
                      ...prev,
                      start_date: dates?.[0]?.toISOString(),
                      end_date: dates?.[1]?.toISOString(),
                    }));
                  }}
                />
              </Col>
            </Row>

            <Table
              columns={auditColumns}
              dataSource={auditLogs}
              rowKey="id"
              pagination={{
                total: auditLogsData?.total,
                pageSize: auditFilters.limit,
                current: Math.floor(auditFilters.offset / auditFilters.limit) + 1,
                onChange: (page, pageSize) => {
                  setAuditFilters(prev => ({
                    ...prev,
                    limit: pageSize || 50,
                    offset: ((page - 1) * (pageSize || 50)),
                  }));
                },
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) =>
                  t('securityAudit.pagination.range', { start: range[0], end: range[1], total }),
              }}
              size="small"
            />
          </Card>
        </TabPane>

        <TabPane tab={t('securityAudit.tabs.system')} key="system">
          <Card title={t('securityAudit.systemLogs')}>
            {/* System Log Filters */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={6}>
                <Select
                  placeholder={t('securityAudit.filters.service')}
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) =>
                    setSystemLogFilters(prev => ({ ...prev, service: value }))
                  }
                >
                  <Select.Option value="api">{t('securityAudit.services.api')}</Select.Option>
                  <Select.Option value="database">{t('securityAudit.services.database')}</Select.Option>
                  <Select.Option value="auth">{t('securityAudit.services.auth')}</Select.Option>
                  <Select.Option value="sync">{t('securityAudit.services.sync')}</Select.Option>
                </Select>
              </Col>
              <Col xs={24} sm={6}>
                <Select
                  placeholder={t('securityAudit.filters.logLevel')}
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) =>
                    setSystemLogFilters(prev => ({ ...prev, level: value }))
                  }
                >
                  <Select.Option value="DEBUG">{t('securityAudit.logLevels.debug')}</Select.Option>
                  <Select.Option value="INFO">{t('securityAudit.logLevels.info')}</Select.Option>
                  <Select.Option value="WARN">{t('securityAudit.logLevels.warn')}</Select.Option>
                  <Select.Option value="ERROR">{t('securityAudit.logLevels.error')}</Select.Option>
                  <Select.Option value="FATAL">{t('securityAudit.logLevels.fatal')}</Select.Option>
                </Select>
              </Col>
              <Col xs={24} sm={12}>
                <RangePicker
                  style={{ width: '100%' }}
                  showTime
                  onChange={(dates) => {
                    setSystemLogFilters(prev => ({
                      ...prev,
                      start_time: dates?.[0]?.toISOString(),
                      end_time: dates?.[1]?.toISOString(),
                    }));
                  }}
                />
              </Col>
            </Row>

            <Table
              columns={systemLogColumns}
              dataSource={systemLogs}
              rowKey={(record, index) => `${record.timestamp}-${index}`}
              pagination={{
                total: systemLogsData?.total,
                pageSize: systemLogFilters.limit,
                showSizeChanger: true,
                showQuickJumper: true,
              }}
              size="small"
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* Log Detail Modal */}
      <Modal
        title={t('securityAudit.details.title')}
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedLog(null);
        }}
        footer={null}
        width={800}
      >
        {selectedLog && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label={t('securityAudit.details.timestamp')}>
                {new Date(selectedLog.timestamp).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('securityAudit.details.userId')}>
                <Text code>{selectedLog.user_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label={t('securityAudit.details.action')}>
                <Tag>{selectedLog.action}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('securityAudit.details.resourceType')}>
                {selectedLog.resource_type}
              </Descriptions.Item>
              <Descriptions.Item label={t('securityAudit.details.resourceId')}>
                <Text code>{selectedLog.resource_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label={t('securityAudit.details.ipAddress')}>
                <Text code>{selectedLog.ip_address}</Text>
              </Descriptions.Item>
              <Descriptions.Item label={t('securityAudit.details.userAgent')} span={2}>
                <Text code style={{ fontSize: '12px' }}>
                  {selectedLog.user_agent}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            {selectedLog.details && (
              <div style={{ marginTop: 16 }}>
                <Text strong>{t('securityAudit.details.details')}:</Text>
                <pre style={{
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  marginTop: 8,
                  fontSize: '12px',
                  overflow: 'auto',
                }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SecurityAudit;