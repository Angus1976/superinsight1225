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
} from 'antd';
import {
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  FilterOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

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
}

const SyncHistory: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
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
      title: '任务名称',
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
      title: '开始时间',
      dataIndex: 'startedAt',
      key: 'startedAt',
      render: (text) => new Date(text).toLocaleString(),
      sorter: (a, b) => new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag icon={statusIcons[status]} color={statusColors[status]}>
          {status.toUpperCase()}
        </Tag>
      ),
      filters: [
        { text: 'Completed', value: 'completed' },
        { text: 'Failed', value: 'failed' },
        { text: 'Running', value: 'running' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '同步行数',
      dataIndex: 'rowsSynced',
      key: 'rowsSynced',
      render: (count) => count.toLocaleString(),
      sorter: (a, b) => a.rowsSynced - b.rowsSynced,
    },
    {
      title: '数据量',
      dataIndex: 'bytesProcessed',
      key: 'bytesProcessed',
      render: formatSize,
    },
    {
      title: '耗时',
      dataIndex: 'durationMs',
      key: 'durationMs',
      render: formatDuration,
      sorter: (a, b) => a.durationMs - b.durationMs,
    },
    {
      title: '操作',
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
          详情
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

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>
        <HistoryOutlined style={{ marginRight: 8 }} />
        同步历史记录
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总同步次数" value={totalSyncs} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功次数"
              value={successfulSyncs}
              valueStyle={{ color: '#3f8600' }}
              suffix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败次数"
              value={failedSyncs}
              valueStyle={{ color: '#cf1322' }}
              suffix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="总同步行数" value={totalRows} />
          </Card>
        </Col>
      </Row>

      <Card
        title="历史记录"
        extra={
          <Space>
            <RangePicker />
            <Select
              placeholder="状态筛选"
              allowClear
              style={{ width: 120 }}
              onChange={setStatusFilter}
            >
              <Option value="completed">成功</Option>
              <Option value="failed">失败</Option>
              <Option value="running">运行中</Option>
            </Select>
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredHistory}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Drawer
        title="同步详情"
        placement="right"
        width={500}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedRecord && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="任务名称">{selectedRecord.jobName}</Descriptions.Item>
              <Descriptions.Item label="数据源">{selectedRecord.sourceName}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag icon={statusIcons[selectedRecord.status]} color={statusColors[selectedRecord.status]}>
                  {selectedRecord.status.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {new Date(selectedRecord.startedAt).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {selectedRecord.completedAt
                  ? new Date(selectedRecord.completedAt).toLocaleString()
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="耗时">
                {formatDuration(selectedRecord.durationMs)}
              </Descriptions.Item>
              <Descriptions.Item label="同步行数">
                {selectedRecord.rowsSynced.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="数据量">
                {formatSize(selectedRecord.bytesProcessed)}
              </Descriptions.Item>
              <Descriptions.Item label="检查点">
                <code>{selectedRecord.checkpointValue || '-'}</code>
              </Descriptions.Item>
            </Descriptions>

            {selectedRecord.errorMessage && (
              <Card title="错误信息" size="small" type="inner">
                <Text type="danger">{selectedRecord.errorMessage}</Text>
              </Card>
            )}

            <Card title="执行时间线" size="small" type="inner">
              <Timeline
                items={[
                  {
                    color: 'blue',
                    children: `开始执行 - ${new Date(selectedRecord.startedAt).toLocaleTimeString()}`,
                  },
                  {
                    color: 'blue',
                    children: `连接数据源`,
                  },
                  {
                    color: 'blue',
                    children: `读取数据 - ${selectedRecord.rowsSynced.toLocaleString()} 行`,
                  },
                  {
                    color: selectedRecord.status === 'completed' ? 'green' : 'red',
                    children: selectedRecord.status === 'completed'
                      ? `完成 - ${selectedRecord.completedAt ? new Date(selectedRecord.completedAt).toLocaleTimeString() : ''}`
                      : `失败 - ${selectedRecord.errorMessage}`,
                  },
                ]}
              />
            </Card>
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default SyncHistory;
