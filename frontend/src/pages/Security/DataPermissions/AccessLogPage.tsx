/**
 * Access Log Page
 * 
 * Query and export data access logs.
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
  message,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  ExportOutlined,
  EyeOutlined,
  ReloadOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  ApiOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  dataPermissionApi,
  AccessLog,
  AccessLogFilter,
  AccessLogOperation,
  SensitivityLevel,
} from '@/services/dataPermissionApi';

const { RangePicker } = DatePicker;
const { Option } = Select;

const operationColors: Record<AccessLogOperation, string> = {
  read: 'blue',
  modify: 'orange',
  export: 'purple',
  api_call: 'cyan',
};

const operationIcons: Record<AccessLogOperation, React.ReactNode> = {
  read: <EyeOutlined />,
  modify: <FileTextOutlined />,
  export: <DownloadOutlined />,
  api_call: <ApiOutlined />,
};

const sensitivityColors: Record<SensitivityLevel, string> = {
  public: 'green',
  internal: 'blue',
  confidential: 'orange',
  top_secret: 'red',
};

const AccessLogPage: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [filters, setFilters] = useState<AccessLogFilter>({
    limit: 50,
    offset: 0,
  });
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AccessLog | null>(null);

  // Fetch access logs
  const { data: logsResponse, isLoading, refetch } = useQuery({
    queryKey: ['accessLogs', filters],
    queryFn: () => dataPermissionApi.queryAccessLogs(filters),
  });

  // Fetch statistics
  const { data: stats } = useQuery({
    queryKey: ['accessStats', filters.start_time, filters.end_time],
    queryFn: () =>
      dataPermissionApi.getAccessStatistics({
        start_time: filters.start_time,
        end_time: filters.end_time,
      }),
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: (format: 'csv' | 'json') =>
      dataPermissionApi.exportAccessLogs(
        {
          ...filters,
          start_time: filters.start_time || dayjs().subtract(30, 'day').toISOString(),
          end_time: filters.end_time || dayjs().toISOString(),
        },
        format
      ),
    onSuccess: (blob, format) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `access_logs_${dayjs().format('YYYY-MM-DD')}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      message.success(t('dataPermissions.accessLog.exportSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.accessLog.exportFailed'));
    },
  });

  const handleViewDetail = (log: AccessLog) => {
    setSelectedLog(log);
    setDetailModalOpen(true);
  };

  const handleFilterChange = (key: keyof AccessLogFilter, value: unknown) => {
    setFilters((prev) => ({ ...prev, [key]: value, offset: 0 }));
  };

  const handleDateRangeChange = (
    dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null
  ) => {
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

  const columns: ColumnsType<AccessLog> = [
    {
      title: t('dataPermissions.accessLog.columns.timestamp'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
      sorter: true,
    },
    {
      title: t('dataPermissions.accessLog.columns.operation'),
      dataIndex: 'operation_type',
      key: 'operation_type',
      width: 120,
      render: (type: AccessLogOperation) => (
        <Tag icon={operationIcons[type]} color={operationColors[type]}>
          {t(`dataPermissions.accessLog.operations.${type}`)}
        </Tag>
      ),
    },
    {
      title: t('dataPermissions.accessLog.columns.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      width: 150,
      ellipsis: true,
    },
    {
      title: t('dataPermissions.accessLog.columns.resource'),
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource}</div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.resource_type}</div>
        </div>
      ),
    },
    {
      title: t('dataPermissions.accessLog.columns.sensitivity'),
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      width: 120,
      render: (level: SensitivityLevel | undefined) =>
        level ? (
          <Tag color={sensitivityColors[level]}>{t(`sensitivity.${level}`)}</Tag>
        ) : (
          '-'
        ),
    },
    {
      title: t('dataPermissions.accessLog.columns.records'),
      dataIndex: 'record_count',
      key: 'record_count',
      width: 80,
      render: (count) => count || '-',
    },
    {
      title: t('dataPermissions.accessLog.columns.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 130,
    },
    {
      title: t('common:actions'),
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
              title={t('dataPermissions.accessLog.stats.totalAccesses')}
              value={stats?.total_accesses || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.accessLog.stats.readOperations')}
              value={stats?.by_operation?.read || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.accessLog.stats.modifyOperations')}
              value={stats?.by_operation?.modify || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.accessLog.stats.exportOperations')}
              value={stats?.by_operation?.export || 0}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        title={t('dataPermissions.accessLog.title')}
        extra={
          <Space>
            <Button
              icon={<ExportOutlined />}
              onClick={() => exportMutation.mutate('csv')}
              loading={exportMutation.isPending}
            >
              {t('dataPermissions.accessLog.exportCsv')}
            </Button>
            <Button
              icon={<ExportOutlined />}
              onClick={() => exportMutation.mutate('json')}
              loading={exportMutation.isPending}
            >
              {t('dataPermissions.accessLog.exportJson')}
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
              placeholder={t('dataPermissions.accessLog.columns.operation')}
              style={{ width: 150 }}
              allowClear
              onChange={(value) => handleFilterChange('operation_type', value)}
            >
              <Option value="read">{t('dataPermissions.accessLog.operations.read')}</Option>
              <Option value="modify">{t('dataPermissions.accessLog.operations.modify')}</Option>
              <Option value="export">{t('dataPermissions.accessLog.operations.export')}</Option>
              <Option value="api_call">{t('dataPermissions.accessLog.operations.apiCall')}</Option>
            </Select>
            <Select
              placeholder={t('dataPermissions.accessLog.columns.sensitivity')}
              style={{ width: 150 }}
              allowClear
              onChange={(value) => handleFilterChange('sensitivity_level', value)}
            >
              <Option value="public">{t('sensitivity.public')}</Option>
              <Option value="internal">{t('sensitivity.internal')}</Option>
              <Option value="confidential">{t('sensitivity.confidential')}</Option>
              <Option value="top_secret">{t('sensitivity.topSecret')}</Option>
            </Select>
            <Input
              placeholder={t('audit.filters.userId')}
              style={{ width: 150 }}
              allowClear
              onChange={(e) =>
                handleFilterChange('user_id', e.target.value || undefined)
              }
            />
            <Input
              placeholder={t('dataPermissions.accessLog.columns.resource')}
              style={{ width: 150 }}
              allowClear
              onChange={(e) =>
                handleFilterChange('resource', e.target.value || undefined)
              }
            />
            <Input
              placeholder={t('audit.filters.ipAddress')}
              style={{ width: 150 }}
              allowClear
              onChange={(e) =>
                handleFilterChange('ip_address', e.target.value || undefined)
              }
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
            showTotal: (total) => t('common.totalLogs', { total }),
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
        title={t('dataPermissions.accessLog.logDetails')}
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
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.timestamp')}>
              {dayjs(selectedLog.timestamp).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.operation')}>
              <Tag
                icon={operationIcons[selectedLog.operation_type]}
                color={operationColors[selectedLog.operation_type]}
              >
                {t(`dataPermissions.accessLog.operations.${selectedLog.operation_type}`)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.user')}>{selectedLog.user_id}</Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.resource')}>{selectedLog.resource}</Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.form.resourceType')}>
              {selectedLog.resource_type}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.sensitivity')}>
              {selectedLog.sensitivity_level ? (
                <Tag color={sensitivityColors[selectedLog.sensitivity_level]}>
                  {t(`sensitivity.${selectedLog.sensitivity_level}`)}
                </Tag>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.records')}>
              {selectedLog.record_count || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.fieldsAccessed')}>
              {selectedLog.fields_accessed?.map((f) => <Tag key={f}>{f}</Tag>) || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.accessLog.columns.ipAddress')}>
              {selectedLog.ip_address || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('audit.userAgent')}>
              {selectedLog.user_agent || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('audit.details')}>
              <pre style={{ margin: 0, fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default AccessLogPage;
