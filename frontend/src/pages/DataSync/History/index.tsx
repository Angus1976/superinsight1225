import React, { useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  DatePicker,
  Select,
  Button,
  Typography,
  Row,
  Col,
  Statistic,
  Timeline,
  Drawer,
  Descriptions,
  message,
} from 'antd';
import {
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ExportOutlined,
  ImportOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { TransferButton } from '@/components/DataLifecycle/TransferButton';
import type { TransferRecord } from '@/api/dataLifecycleAPI';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface SyncHistoryRecord {
  id: string;
  jobId: string;
  jobName: string;
  sourceName: string;
  startedAt: string;
  completedAt: string | null;
  status: 'running' | 'completed' | 'failed';
  rowsSynced: number;
  bytesProcessed: number;
  durationMs: number;
  errorMessage: string | null;
  checkpointValue: string | null;
  syncDirection?: 'input' | 'output' | 'bidirectional';
  rowsWritten?: number;
  writeErrors?: Record<string, any>;
}

const SyncHistory: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [history, setHistory] = useState<SyncHistoryRecord[]>([
    {
      id: 'h1',
      jobId: 'job_1',
      jobName: '每日用户数据同步',
      sourceName: 'Production DB',
      startedAt: '2026-01-13T02:00:00Z',
      completedAt: '2026-01-13T02:05:30Z',
      status: 'completed',
      rowsSynced: 15000,
      bytesProcessed: 5242880,
      durationMs: 330000,
      errorMessage: null,
      checkpointValue: '2026-01-13T01:59:59Z',
    },
    {
      id: 'h2',
      jobId: 'job_2',
      jobName: '实时订单同步',
      sourceName: 'Orders DB',
      startedAt: '2026-01-13T10:55:00Z',
      completedAt: '2026-01-13T10:55:45Z',
      status: 'completed',
      rowsSynced: 250,
      bytesProcessed: 102400,
      durationMs: 45000,
      errorMessage: null,
      checkpointValue: '2026-01-13T10:54:59Z',
    },
    {
      id: 'h3',
      jobId: 'job_1',
      jobName: '每日用户数据同步',
      sourceName: 'Production DB',
      startedAt: '2026-01-12T02:00:00Z',
      completedAt: '2026-01-12T02:03:15Z',
      status: 'failed',
      rowsSynced: 8500,
      bytesProcessed: 2621440,
      durationMs: 195000,
      errorMessage: 'Connection timeout after 3 retries',
      checkpointValue: '2026-01-12T01:30:00Z',
      syncDirection: 'input',
    },
    {
      id: 'h4',
      jobId: 'job_2',
      jobName: '实时订单同步',
      sourceName: 'Orders DB',
      startedAt: '2026-01-13T10:50:00Z',
      completedAt: '2026-01-13T10:50:30Z',
      status: 'completed',
      rowsSynced: 180,
      bytesProcessed: 73728,
      durationMs: 30000,
      errorMessage: null,
      checkpointValue: '2026-01-13T10:49:59Z',
      syncDirection: 'input',
    },
    {
      id: 'h5',
      jobId: 'job_3',
      jobName: 'AI 数据输出同步',
      sourceName: 'Target DB',
      startedAt: '2026-01-13T14:00:00Z',
      completedAt: '2026-01-13T14:02:15Z',
      status: 'completed',
      rowsSynced: 0,
      bytesProcessed: 0,
      durationMs: 135000,
      errorMessage: null,
      checkpointValue: null,
      syncDirection: 'output',
      rowsWritten: 5000,
      writeErrors: {},
    },
    {
      id: 'h6',
      jobId: 'job_3',
      jobName: 'AI 数据输出同步',
      sourceName: 'Target DB',
      startedAt: '2026-01-12T14:00:00Z',
      completedAt: '2026-01-12T14:01:45Z',
      status: 'failed',
      rowsSynced: 0,
      bytesProcessed: 0,
      durationMs: 105000,
      errorMessage: 'Target database connection failed',
      checkpointValue: null,
      syncDirection: 'output',
      rowsWritten: 2300,
      writeErrors: { failed_rows: 150, error_details: 'Schema mismatch on field "updated_at"' },
    },
  ]);
  const [selectedRecord, setSelectedRecord] = useState<SyncHistoryRecord | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const statusColors: Record<string, string> = {
    running: 'processing',
    completed: 'success',
    failed: 'error',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    running: <SyncOutlined spin />,
    completed: <CheckCircleOutlined />,
    failed: <CloseCircleOutlined />,
  };

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}min`;
  };

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let size = bytes;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(2)} ${units[i]}`;
  };

  const columns: ColumnsType<SyncHistoryRecord> = [
    {
      title: t('history.taskName'),
      dataIndex: 'jobName',
      key: 'jobName',
      render: (text, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.sourceName}</Text>
        </Space>
      ),
    },
    {
      title: t('history.syncDirection'),
      dataIndex: 'syncDirection',
      key: 'syncDirection',
      render: (direction) => {
        if (!direction) return '-';
        const directionConfig = {
          input: { icon: <ImportOutlined />, color: 'blue', text: t('history.directionInput') },
          output: { icon: <ExportOutlined />, color: 'green', text: t('history.directionOutput') },
          bidirectional: { icon: <SwapOutlined />, color: 'purple', text: t('history.directionBidirectional') },
        };
        const config = directionConfig[direction as keyof typeof directionConfig];
        return config ? (
          <Tag icon={config.icon} color={config.color}>
            {config.text}
          </Tag>
        ) : '-';
      },
      filters: [
        { text: t('history.directionInput'), value: 'input' },
        { text: t('history.directionOutput'), value: 'output' },
        { text: t('history.directionBidirectional'), value: 'bidirectional' },
      ],
      onFilter: (value, record) => record.syncDirection === value,
    },
    {
      title: t('history.startTime'),
      dataIndex: 'startedAt',
      key: 'startedAt',
      render: (text) => new Date(text).toLocaleString(),
      sorter: (a, b) => new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: t('history.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag icon={statusIcons[status]} color={statusColors[status]}>
          {status.toUpperCase()}
        </Tag>
      ),
      filters: [
        { text: t('history.success'), value: 'completed' },
        { text: t('history.failed'), value: 'failed' },
        { text: t('history.running'), value: 'running' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: t('history.rowsSynced'),
      dataIndex: 'rowsSynced',
      key: 'rowsSynced',
      render: (count, record) => {
        // For output sync, show rows written instead
        if (record.syncDirection === 'output' && record.rowsWritten !== undefined) {
          return (
            <Space direction="vertical" size="small">
              <Text>{t('history.written')}: {record.rowsWritten.toLocaleString()}</Text>
            </Space>
          );
        }
        return count.toLocaleString();
      },
      sorter: (a, b) => a.rowsSynced - b.rowsSynced,
    },
    {
      title: t('history.dataSize'),
      dataIndex: 'bytesProcessed',
      key: 'bytesProcessed',
      render: formatSize,
    },
    {
      title: t('history.duration'),
      dataIndex: 'durationMs',
      key: 'durationMs',
      render: formatDuration,
      sorter: (a, b) => a.durationMs - b.durationMs,
    },
    {
      title: t('history.actions'),
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          icon={<InfoCircleOutlined />}
          onClick={() => {
            setSelectedRecord(record);
            setDrawerVisible(true);
          }}
        >
          {t('history.details')}
        </Button>
      ),
    },
  ];

  const filteredHistory = statusFilter
    ? history.filter(h => h.status === statusFilter)
    : history;

  const totalSyncs = history.length;
  const successfulSyncs = history.filter(h => h.status === 'completed').length;
  const failedSyncs = history.filter(h => h.status === 'failed').length;
  const totalRows = history.reduce((sum, h) => sum + h.rowsSynced, 0);
  
  // Output sync statistics
  const outputSyncs = history.filter(h => h.syncDirection === 'output' || h.syncDirection === 'bidirectional');
  const outputSuccessful = outputSyncs.filter(h => h.status === 'completed').length;
  const outputFailed = outputSyncs.filter(h => h.status === 'failed').length;
  const totalRowsWritten = outputSyncs.reduce((sum, h) => sum + (h.rowsWritten || 0), 0);

  // Row selection configuration
  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
    getCheckboxProps: (record: SyncHistoryRecord) => ({
      disabled: record.status !== 'completed',
      title: record.status !== 'completed' ? t('history.transfer.onlyCompleted') : '',
    }),
  };

  // Get selected completed records for transfer
  const selectedRecords = history.filter(
    h => selectedRowKeys.includes(h.id) && h.status === 'completed'
  );

  // Convert sync records to transfer format
  const transferRecords: TransferRecord[] = selectedRecords.map(record => ({
    id: record.id,
    content: {
      job_id: record.jobId,
      job_name: record.jobName,
      source_name: record.sourceName,
      rows_synced: record.rowsSynced,
      bytes_processed: record.bytesProcessed,
      started_at: record.startedAt,
      completed_at: record.completedAt,
    },
    metadata: {
      source_name: record.sourceName,
      sync_time: record.completedAt,
      rows_synced: record.rowsSynced,
      checkpoint_value: record.checkpointValue,
      duration_ms: record.durationMs,
    },
  }));

  const handleTransferComplete = (result: any) => {
    message.success(t('history.transfer.success', { count: result.transferred_count }));
    setSelectedRowKeys([]);
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>
        <HistoryOutlined style={{ marginRight: 8 }} />
        {t('history.title')}
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('history.totalSyncs')} value={totalSyncs} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('history.successCount')}
              value={successfulSyncs}
              valueStyle={{ color: '#3f8600' }}
              suffix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('history.failedCount')}
              value={failedSyncs}
              valueStyle={{ color: '#cf1322' }}
              suffix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('history.totalRowsSynced')} value={totalRows} />
          </Card>
        </Col>
      </Row>

      {/* Output Sync Statistics */}
      {outputSyncs.length > 0 && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic 
                title={t('history.outputSyncs')} 
                value={outputSyncs.length}
                prefix={<ExportOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('history.outputSuccessful')}
                value={outputSuccessful}
                valueStyle={{ color: '#3f8600' }}
                suffix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('history.outputFailed')}
                value={outputFailed}
                valueStyle={{ color: '#cf1322' }}
                suffix={<CloseCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title={t('history.totalRowsWritten')} 
                value={totalRowsWritten}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card
        title={t('history.records')}
        extra={
          <Space>
            {selectedRowKeys.length > 0 && (
              <TransferButton
                sourceType="sync"
                sourceId={`batch-${Date.now()}`}
                records={transferRecords}
                onTransferComplete={handleTransferComplete}
              />
            )}
            <RangePicker />
            <Select
              placeholder={t('history.statusFilter')}
              allowClear
              style={{ width: 120 }}
              onChange={setStatusFilter}
            >
              <Option value="completed">{t('history.success')}</Option>
              <Option value="failed">{t('history.failed')}</Option>
              <Option value="running">{t('history.running')}</Option>
            </Select>
            <Button icon={<ReloadOutlined />}>{t('common:refresh')}</Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredHistory}
          rowKey="id"
          rowSelection={rowSelection}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Drawer
        title={t('history.detailTitle')}
        placement="right"
        width={500}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedRecord && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label={t('history.taskName')}>{selectedRecord.jobName}</Descriptions.Item>
              <Descriptions.Item label={t('history.sourceName')}>{selectedRecord.sourceName}</Descriptions.Item>
              <Descriptions.Item label={t('history.syncDirection')}>
                {selectedRecord.syncDirection ? (
                  <Tag 
                    icon={
                      selectedRecord.syncDirection === 'input' ? <ImportOutlined /> :
                      selectedRecord.syncDirection === 'output' ? <ExportOutlined /> :
                      <SwapOutlined />
                    }
                    color={
                      selectedRecord.syncDirection === 'input' ? 'blue' :
                      selectedRecord.syncDirection === 'output' ? 'green' :
                      'purple'
                    }
                  >
                    {selectedRecord.syncDirection === 'input' ? t('history.directionInput') :
                     selectedRecord.syncDirection === 'output' ? t('history.directionOutput') :
                     t('history.directionBidirectional')}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('history.status')}>
                <Tag icon={statusIcons[selectedRecord.status]} color={statusColors[selectedRecord.status]}>
                  {selectedRecord.status.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('history.startTime')}>
                {new Date(selectedRecord.startedAt).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('history.completedAt')}>
                {selectedRecord.completedAt
                  ? new Date(selectedRecord.completedAt).toLocaleString()
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('history.duration')}>
                {formatDuration(selectedRecord.durationMs)}
              </Descriptions.Item>
              {selectedRecord.syncDirection !== 'output' && (
                <Descriptions.Item label={t('history.rowsSynced')}>
                  {selectedRecord.rowsSynced.toLocaleString()}
                </Descriptions.Item>
              )}
              {(selectedRecord.syncDirection === 'output' || selectedRecord.syncDirection === 'bidirectional') && selectedRecord.rowsWritten !== undefined && (
                <Descriptions.Item label={t('history.rowsWritten')}>
                  {selectedRecord.rowsWritten.toLocaleString()}
                </Descriptions.Item>
              )}
              <Descriptions.Item label={t('history.dataSize')}>
                {formatSize(selectedRecord.bytesProcessed)}
              </Descriptions.Item>
              <Descriptions.Item label={t('history.checkpoint')}>
                <code>{selectedRecord.checkpointValue || '-'}</code>
              </Descriptions.Item>
            </Descriptions>

            {selectedRecord.errorMessage && (
              <Card title={t('history.errorInfo')} size="small" type="inner">
                <Text type="danger">{selectedRecord.errorMessage}</Text>
              </Card>
            )}

            {selectedRecord.writeErrors && Object.keys(selectedRecord.writeErrors).length > 0 && (
              <Card title={t('history.writeErrors')} size="small" type="inner">
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(selectedRecord.writeErrors, null, 2)}
                </pre>
              </Card>
            )}

            <Card title={t('history.timeline')} size="small" type="inner">
              <Timeline
                items={[
                  {
                    color: 'blue',
                    children: `${t('history.timelineStart')} - ${new Date(selectedRecord.startedAt).toLocaleTimeString()}`,
                  },
                  {
                    color: 'blue',
                    children: t('history.timelineConnect'),
                  },
                  selectedRecord.syncDirection !== 'output' && {
                    color: 'blue',
                    children: `${t('history.timelineRead')} - ${selectedRecord.rowsSynced.toLocaleString()} rows`,
                  },
                  (selectedRecord.syncDirection === 'output' || selectedRecord.syncDirection === 'bidirectional') && selectedRecord.rowsWritten !== undefined && {
                    color: 'blue',
                    children: `${t('history.timelineWrite')} - ${selectedRecord.rowsWritten.toLocaleString()} rows`,
                  },
                  {
                    color: selectedRecord.status === 'completed' ? 'green' : 'red',
                    children: selectedRecord.status === 'completed'
                      ? `${t('history.timelineComplete')} - ${selectedRecord.completedAt ? new Date(selectedRecord.completedAt).toLocaleTimeString() : ''}`
                      : `${t('history.timelineFailed')} - ${selectedRecord.errorMessage}`,
                  },
                ].filter(Boolean)}
              />
            </Card>
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default SyncHistory;
