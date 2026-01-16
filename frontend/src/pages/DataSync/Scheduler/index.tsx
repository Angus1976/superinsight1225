import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
  Tooltip,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  HistoryOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;
const { Option } = Select;

interface ScheduledJob {
  id: string;
  name: string;
  sourceId: string;
  sourceName: string;
  cronExpression: string;
  priority: number;
  enabled: boolean;
  status: 'pending' | 'running' | 'completed' | 'failed';
  lastRunAt: string | null;
  nextRunAt: string | null;
  totalRuns: number;
  successfulRuns: number;
  failedRuns: number;
}

interface SyncHistory {
  id: string;
  jobId: string;
  startedAt: string;
  completedAt: string | null;
  status: string;
  rowsSynced: number;
  errorMessage: string | null;
}

const SyncScheduler: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [jobs, setJobs] = useState<ScheduledJob[]>([
    {
      id: 'job_1',
      name: '每日用户数据同步',
      sourceId: 'ds_1',
      sourceName: 'Production DB',
      cronExpression: '0 2 * * *',
      priority: 5,
      enabled: true,
      status: 'completed',
      lastRunAt: '2026-01-13T02:00:00Z',
      nextRunAt: '2026-01-14T02:00:00Z',
      totalRuns: 30,
      successfulRuns: 28,
      failedRuns: 2,
    },
    {
      id: 'job_2',
      name: '实时订单同步',
      sourceId: 'ds_2',
      sourceName: 'Orders DB',
      cronExpression: '*/5 * * * *',
      priority: 8,
      enabled: true,
      status: 'running',
      lastRunAt: '2026-01-13T10:55:00Z',
      nextRunAt: '2026-01-13T11:00:00Z',
      totalRuns: 1440,
      successfulRuns: 1435,
      failedRuns: 5,
    },
  ]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isHistoryVisible, setIsHistoryVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<ScheduledJob | null>(null);
  const [history, setHistory] = useState<SyncHistory[]>([]);
  const [form] = Form.useForm();

  const statusColors: Record<string, string> = {
    pending: 'default',
    running: 'processing',
    completed: 'success',
    failed: 'error',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    pending: <ClockCircleOutlined />,
    running: <SyncOutlined spin />,
    completed: <CheckCircleOutlined />,
    failed: <CloseCircleOutlined />,
  };

  const columns: ColumnsType<ScheduledJob> = [
    {
      title: t('scheduler.taskName'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <Text strong>{text}</Text>
          {record.priority >= 7 && <Tag color="red">{t('scheduler.highPriority')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('scheduler.dataSource'),
      dataIndex: 'sourceName',
      key: 'sourceName',
    },
    {
      title: t('scheduler.cronExpression'),
      dataIndex: 'cronExpression',
      key: 'cronExpression',
      render: (text) => <code>{text}</code>,
    },
    {
      title: t('scheduler.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag icon={statusIcons[status]} color={statusColors[status]}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('scheduler.enabled'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggleEnabled(record.id, checked)}
        />
      ),
    },
    {
      title: t('scheduler.lastRun'),
      dataIndex: 'lastRunAt',
      key: 'lastRunAt',
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: t('scheduler.nextRun'),
      dataIndex: 'nextRunAt',
      key: 'nextRunAt',
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: t('scheduler.successRate'),
      key: 'successRate',
      render: (_, record) => {
        const rate = record.totalRuns > 0
          ? ((record.successfulRuns / record.totalRuns) * 100).toFixed(1)
          : '0';
        return (
          <Text type={parseFloat(rate) >= 95 ? 'success' : 'warning'}>
            {rate}%
          </Text>
        );
      },
    },
    {
      title: t('scheduler.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('scheduler.triggerNow')}>
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => handleTrigger(record.id)}
              disabled={record.status === 'running'}
            />
          </Tooltip>
          <Tooltip title={t('scheduler.viewHistory')}>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => handleViewHistory(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('scheduler.deleteConfirm')}
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const historyColumns: ColumnsType<SyncHistory> = [
    {
      title: t('scheduler.startTime'),
      dataIndex: 'startedAt',
      key: 'startedAt',
      render: (text) => new Date(text).toLocaleString(),
    },
    {
      title: t('scheduler.completedTime'),
      dataIndex: 'completedAt',
      key: 'completedAt',
      render: (text) => text ? new Date(text).toLocaleString() : '-',
    },
    {
      title: t('scheduler.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={statusColors[status]}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: t('scheduler.rowsSynced'),
      dataIndex: 'rowsSynced',
      key: 'rowsSynced',
      render: (count) => count.toLocaleString(),
    },
    {
      title: t('scheduler.errorMessage'),
      dataIndex: 'errorMessage',
      key: 'errorMessage',
      render: (text) => text || '-',
    },
  ];

  const handleToggleEnabled = (jobId: string, enabled: boolean) => {
    setJobs(jobs.map(job =>
      job.id === jobId ? { ...job, enabled } : job
    ));
    message.success(enabled ? t('scheduler.taskEnabled') : t('scheduler.taskDisabled'));
  };

  const handleTrigger = (jobId: string) => {
    message.loading(t('scheduler.triggerStarted'));
    setTimeout(() => {
      message.success(t('scheduler.triggerSuccess'));
    }, 1000);
  };

  const handleViewHistory = (job: ScheduledJob) => {
    setSelectedJob(job);
    setHistory([
      {
        id: 'h1',
        jobId: job.id,
        startedAt: '2026-01-13T02:00:00Z',
        completedAt: '2026-01-13T02:05:30Z',
        status: 'completed',
        rowsSynced: 15000,
        errorMessage: null,
      },
      {
        id: 'h2',
        jobId: job.id,
        startedAt: '2026-01-12T02:00:00Z',
        completedAt: '2026-01-12T02:04:45Z',
        status: 'completed',
        rowsSynced: 14500,
        errorMessage: null,
      },
    ]);
    setIsHistoryVisible(true);
  };

  const handleDelete = (jobId: string) => {
    setJobs(jobs.filter(job => job.id !== jobId));
    message.success(t('scheduler.taskDeleted'));
  };

  const handleCreateJob = (values: any) => {
    const newJob: ScheduledJob = {
      id: `job_${Date.now()}`,
      name: values.name,
      sourceId: values.sourceId,
      sourceName: 'New Source',
      cronExpression: values.cronExpression,
      priority: values.priority,
      enabled: values.enabled,
      status: 'pending',
      lastRunAt: null,
      nextRunAt: new Date(Date.now() + 60000).toISOString(),
      totalRuns: 0,
      successfulRuns: 0,
      failedRuns: 0,
    };
    setJobs([...jobs, newJob]);
    setIsModalVisible(false);
    form.resetFields();
    message.success(t('scheduler.taskCreated'));
  };

  const totalJobs = jobs.length;
  const activeJobs = jobs.filter(j => j.enabled).length;
  const runningJobs = jobs.filter(j => j.status === 'running').length;
  const totalSynced = jobs.reduce((sum, j) => sum + j.successfulRuns, 0);

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>
        <ClockCircleOutlined style={{ marginRight: 8 }} />
        {t('scheduler.title')}
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('scheduler.totalJobs')} value={totalJobs} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('scheduler.activeJobs')} value={activeJobs} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('scheduler.runningJobs')} value={runningJobs} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('scheduler.totalSynced')} value={totalSynced} />
          </Card>
        </Col>
      </Row>

      <Card
        title={t('scheduler.jobList')}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />}>{t('common:refresh')}</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalVisible(true)}>
              {t('scheduler.createJob')}
            </Button>
          </Space>
        }
      >
        <Table columns={columns} dataSource={jobs} rowKey="id" />
      </Card>

      <Modal
        title={t('scheduler.createTitle')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateJob}>
          <Form.Item name="name" label={t('scheduler.taskName')} rules={[{ required: true }]}>
            <Input placeholder={t('scheduler.inputTaskName')} />
          </Form.Item>
          <Form.Item name="sourceId" label={t('scheduler.dataSource')} rules={[{ required: true }]}>
            <Select placeholder={t('scheduler.selectDataSource')}>
              <Option value="ds_1">Production DB</Option>
              <Option value="ds_2">Orders DB</Option>
            </Select>
          </Form.Item>
          <Form.Item name="cronExpression" label={t('scheduler.cronExpression')} rules={[{ required: true }]}>
            <Input placeholder={t('scheduler.cronPlaceholder')} />
          </Form.Item>
          <Form.Item name="priority" label={t('scheduler.priority')} initialValue={5}>
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="enabled" label={t('scheduler.enableNow')} valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">{t('common:actions.create')}</Button>
              <Button onClick={() => setIsModalVisible(false)}>{t('common:cancel')}</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`${t('scheduler.historyTitle')} - ${selectedJob?.name}`}
        open={isHistoryVisible}
        onCancel={() => setIsHistoryVisible(false)}
        footer={null}
        width={800}
      >
        <Table columns={historyColumns} dataSource={history} rowKey="id" pagination={{ pageSize: 10 }} />
      </Modal>
    </div>
  );
};

export default SyncScheduler;
