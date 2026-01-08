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
import { useAuditLogs, useSystemLogs } from '@/hooks';
import type { SystemAuditLog } from '@/types';

const { RangePicker } = DatePicker;
const { Search } = Input;
const { Text } = Typography;
const { TabPane } = Tabs;

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const SecurityAudit: React.FC = () => {
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
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (time) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    },
    {
      title: 'User',
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
      title: 'Action',
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
        return <Tag color={color}>{action.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Resource',
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
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
      render: (ip) => <Text code>{ip}</Text>,
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_, record) => {
        // Determine status based on action or details
        const isSuccess = !record.details?.error;
        return isSuccess ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            Success
          </Tag>
        ) : (
          <Tag color="error" icon={<CloseCircleOutlined />}>
            Failed
          </Tag>
        );
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space>
          <Tooltip title="View Details">
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
      title: 'Time',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (time) => new Date(time).toLocaleString(),
    },
    {
      title: 'Level',
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
      title: 'Service',
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
      title: 'Message',
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
              title="Total Audit Logs"
              value={auditLogsData?.total || 0}
              prefix={<SecurityScanOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="High Risk Actions"
              value={riskLevels.High || 0}
              valueStyle={{ color: '#f5222d' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Failed Logins"
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
              title="Active Users"
              value={new Set(auditLogs.map((log: SystemAuditLog) => log.user_id)).size}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Security Analytics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={8}>
          <Card title="Action Distribution" style={{ height: 300 }}>
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
          <Card title="Hourly Activity" style={{ height: 300 }}>
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
          <Card title="Risk Assessment" style={{ height: 300 }}>
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
        <TabPane tab="Audit Logs" key="audit">
          <Card
            title="Security Audit Logs"
            extra={
              <Space>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={handleExportLogs}
                >
                  Export
                </Button>
              </Space>
            }
          >
            {/* Filters */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={8}>
                <Search
                  placeholder="Search by user ID"
                  onSearch={(value) =>
                    setAuditFilters(prev => ({ ...prev, user_id: value || undefined }))
                  }
                  allowClear
                />
              </Col>
              <Col xs={24} sm={6}>
                <Select
                  placeholder="Action"
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) =>
                    setAuditFilters(prev => ({ ...prev, action: value }))
                  }
                >
                  <Select.Option value="login">Login</Select.Option>
                  <Select.Option value="logout">Logout</Select.Option>
                  <Select.Option value="create">Create</Select.Option>
                  <Select.Option value="update">Update</Select.Option>
                  <Select.Option value="delete">Delete</Select.Option>
                  <Select.Option value="view">View</Select.Option>
                  <Select.Option value="export">Export</Select.Option>
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
                  `${range[0]}-${range[1]} of ${total} logs`,
              }}
              size="small"
            />
          </Card>
        </TabPane>

        <TabPane tab="System Logs" key="system">
          <Card title="System Logs">
            {/* System Log Filters */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={6}>
                <Select
                  placeholder="Service"
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) =>
                    setSystemLogFilters(prev => ({ ...prev, service: value }))
                  }
                >
                  <Select.Option value="api">API Server</Select.Option>
                  <Select.Option value="database">Database</Select.Option>
                  <Select.Option value="auth">Authentication</Select.Option>
                  <Select.Option value="sync">Data Sync</Select.Option>
                </Select>
              </Col>
              <Col xs={24} sm={6}>
                <Select
                  placeholder="Log Level"
                  style={{ width: '100%' }}
                  allowClear
                  onChange={(value) =>
                    setSystemLogFilters(prev => ({ ...prev, level: value }))
                  }
                >
                  <Select.Option value="DEBUG">Debug</Select.Option>
                  <Select.Option value="INFO">Info</Select.Option>
                  <Select.Option value="WARN">Warning</Select.Option>
                  <Select.Option value="ERROR">Error</Select.Option>
                  <Select.Option value="FATAL">Fatal</Select.Option>
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
        title="Audit Log Details"
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
              <Descriptions.Item label="Timestamp">
                {new Date(selectedLog.timestamp).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="User ID">
                <Text code>{selectedLog.user_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Action">
                <Tag>{selectedLog.action}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Resource Type">
                {selectedLog.resource_type}
              </Descriptions.Item>
              <Descriptions.Item label="Resource ID">
                <Text code>{selectedLog.resource_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="IP Address">
                <Text code>{selectedLog.ip_address}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="User Agent" span={2}>
                <Text code style={{ fontSize: '12px' }}>
                  {selectedLog.user_agent}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            {selectedLog.details && (
              <div style={{ marginTop: 16 }}>
                <Text strong>Details:</Text>
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