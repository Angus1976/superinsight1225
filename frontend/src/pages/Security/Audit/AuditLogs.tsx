/**
 * Audit Logs Page
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  DatePicker,
  Input,
  Select,
  Row,
  Col,
  Statistic,
  Modal,
  Descriptions,
  Typography,
  message,
  Tooltip,
  Alert,
} from 'antd';
import {
  SearchOutlined,
  ExportOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyOutlined,
  FilterOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { auditApi, AuditLog, AuditLogQueryParams } from '@/services/auditApi';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const eventTypeColors: Record<string, string> = {
  login_attempt: 'blue',
  data_access: 'cyan',
  permission_change: 'orange',
  session_created: 'green',
  session_destroyed: 'red',
  security_event: 'purple',
  config_change: 'gold',
};

const AuditLogs: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [filters, setFilters] = useState<AuditLogQueryParams>({
    limit: 50,
    offset: 0,
  });
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);

  // Fetch audit logs
  const { data: logsResponse, isLoading, refetch } = useQuery({
    queryKey: ['auditLogs', filters],
    queryFn: () => auditApi.queryLogs(filters),
  });

  // Fetch statistics
  const { data: stats } = useQuery({
    queryKey: ['auditStats'],
    queryFn: () => auditApi.getStatistics(),
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: (format: 'json' | 'csv') =>
      auditApi.exportLogs({
        start_time: filters.start_time || dayjs().subtract(30, 'day').toISOString(),
        end_time: filters.end_time || dayjs().toISOString(),
        format,
        user_id: filters.user_id,
        event_type: filters.event_type,
      }),
    onSuccess: (blob, format) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${dayjs().format('YYYY-MM-DD')}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success(t('audit.stats.exportSuccess'));
    },
    onError: () => {
      message.error(t('audit.stats.exportFailed'));
    },
  });

  // Verify integrity mutation
  const verifyMutation = useMutation({
    mutationFn: () =>
      auditApi.verifyIntegrity({
        start_time: filters.start_time,
        end_time: filters.end_time,
      }),
    onSuccess: (result) => {
      if (result.valid) {
        message.success(t('audit.verifySuccess', { count: result.verified_count }));
      } else {
        message.error(t('audit.verifyFailed', { error: result.error }));
      }
    },
    onError: () => {
      message.error(t('audit.verifyError'));
    },
  });

  const handleViewDetail = (log: AuditLog) => {
    setSelectedLog(log);
    setDetailModalOpen(true);
  };

  const handleFilterChange = (key: keyof AuditLogQueryParams, value: unknown) => {
    setFilters((prev) => ({ ...prev, [key]: value, offset: 0 }));
  };

  const handleDateRangeChange = (dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setFilters((prev) => ({
        ...prev,
        start_time: dates[0]!.toISOString(),
        end_time: dates[1]!.toISOString(),
        offset: 0,
      }));
    } else {
      setFilters((prev) => ({
        ...prev,
        start_time: undefined,
        end_time: undefined,
        offset: 0,
      }));
    }
  };

  const columns: ColumnsType<AuditLog> = [
    {
      title: t('audit.columns.timestamp'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
      sorter: true,
    },
    {
      title: t('audit.columns.eventType'),
      dataIndex: 'event_type',
      key: 'event_type',
      width: 150,
      render: (type) => (
        <Tag color={eventTypeColors[type] || 'default'}>
          {type.replace(/_/g, ' ').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('audit.columns.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
      ellipsis: true,
    },
    {
      title: t('audit.columns.resource'),
      dataIndex: 'resource',
      key: 'resource',
      ellipsis: true,
    },
    {
      title: t('audit.columns.action'),
      dataIndex: 'action',
      key: 'action',
      width: 100,
    },
    {
      title: t('audit.columns.result'),
      dataIndex: 'result',
      key: 'result',
      width: 80,
      render: (result) =>
        result === true ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            {t('audit.results.success')}
          </Tag>
        ) : result === false ? (
          <Tag icon={<CloseCircleOutlined />} color="error">
            {t('audit.results.failed')}
          </Tag>
        ) : (
          <Tag>-</Tag>
        ),
    },
    {
      title: t('audit.columns.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        />
      ),
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('audit.stats.totalLogs')}
              value={stats?.total_logs || 0}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('audit.stats.eventTypes')}
              value={Object.keys(stats?.event_types || {}).length}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('audit.stats.successRate')}
              value={
                stats?.results
                  ? (
                      ((stats.results['True'] || 0) /
                        (Object.values(stats.results).reduce((a, b) => a + b, 0) || 1)) *
                      100
                    ).toFixed(1)
                  : 0
              }
              suffix="%"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('audit.stats.failedOperations')}
              value={stats?.results?.['False'] || 0}
              valueStyle={{ color: stats?.results?.['False'] ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        title={t('audit.logs')}
        extra={
          <Space>
            <Tooltip title={t('audit.verifyIntegrity')}>
              <Button
                icon={<SafetyOutlined />}
                onClick={() => verifyMutation.mutate()}
                loading={verifyMutation.isPending}
              >
                {t('audit.verifyIntegrity')}
              </Button>
            </Tooltip>
            <Button
              icon={<ExportOutlined />}
              onClick={() => exportMutation.mutate('csv')}
              loading={exportMutation.isPending}
            >
              {t('audit.exportCsv')}
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <RangePicker
              showTime
              onChange={handleDateRangeChange}
              placeholder={[t('audit.filters.startTime'), t('audit.filters.endTime')]}
            />
            <Select
              placeholder={t('audit.filters.eventType')}
              style={{ width: 150 }}
              allowClear
              onChange={(value) => handleFilterChange('event_type', value)}
              options={[
                { label: t('audit.eventTypes.loginAttempt'), value: 'login_attempt' },
                { label: t('audit.eventTypes.dataAccess'), value: 'data_access' },
                { label: t('audit.eventTypes.permissionChange'), value: 'permission_change' },
                { label: t('audit.eventTypes.sessionCreated'), value: 'session_created' },
                { label: t('audit.eventTypes.securityEvent'), value: 'security_event' },
              ]}
            />
            <Select
              placeholder={t('audit.filters.result')}
              style={{ width: 120 }}
              allowClear
              onChange={(value) => handleFilterChange('result', value)}
              options={[
                { label: t('audit.results.success'), value: true },
                { label: t('audit.results.failed'), value: false },
              ]}
            />
            <Input
              placeholder={t('audit.filters.userId')}
              style={{ width: 150 }}
              allowClear
              onChange={(e) => handleFilterChange('user_id', e.target.value || undefined)}
            />
            <Input
              placeholder={t('audit.filters.ipAddress')}
              style={{ width: 150 }}
              allowClear
              onChange={(e) => handleFilterChange('ip_address', e.target.value || undefined)}
            />
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={logsResponse?.logs || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor((filters.offset || 0) / (filters.limit || 50)) + 1,
            pageSize: filters.limit || 50,
            total: logsResponse?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => t('security:common.totalLogs', { total }),
            onChange: (page, pageSize) => {
              setFilters((prev) => ({
                ...prev,
                offset: (page - 1) * pageSize,
                limit: pageSize,
              }));
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title={t('audit.logDetails')}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {t('common:close')}
          </Button>,
        ]}
        width={700}
      >
        {selectedLog && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{selectedLog.id}</Descriptions.Item>
            <Descriptions.Item label={t('audit.timestamp')}>
              {dayjs(selectedLog.timestamp).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label={t('audit.eventType')}>
              <Tag color={eventTypeColors[selectedLog.event_type] || 'default'}>
                {selectedLog.event_type}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('audit.user')}>{selectedLog.user_id}</Descriptions.Item>
            <Descriptions.Item label={t('audit.resource')}>{selectedLog.resource || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('audit.action')}>{selectedLog.action || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('audit.result')}>
              {selectedLog.result === true ? (
                <Tag color="success">{t('audit.results.success')}</Tag>
              ) : selectedLog.result === false ? (
                <Tag color="error">{t('audit.results.failed')}</Tag>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label={t('audit.ipAddress')}>{selectedLog.ip_address || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('audit.userAgent')}>{selectedLog.user_agent || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('audit.sessionId')}>{selectedLog.session_id || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('audit.details')}>
              <pre style={{ margin: 0, fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label={t('audit.hash')}>
              <Text code style={{ fontSize: 10 }}>
                {selectedLog.hash}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default AuditLogs;
