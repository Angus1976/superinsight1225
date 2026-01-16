// Data augmentation management page
import { useState } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Upload,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Progress,
  Row,
  Col,
  Statistic,
  message,
  Tabs,
  Alert,
  Menu,
} from 'antd';
import {
  UploadOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlusOutlined,
  SettingOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import type { UploadProps } from 'antd';

interface AugmentationJob {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  strategy: string;
  source_count: number;
  output_count: number;
  progress: number;
  created_at: string;
  completed_at?: string;
}

interface SampleData {
  id: string;
  content: string;
  label: string;
  source: 'original' | 'augmented';
  quality_score: number;
  created_at: string;
}

// Mock data
const mockJobs: AugmentationJob[] = [
  {
    id: '1',
    name: 'Customer Review Augmentation',
    status: 'completed',
    strategy: 'back_translation',
    source_count: 1000,
    output_count: 3500,
    progress: 100,
    created_at: '2025-01-15T10:00:00Z',
    completed_at: '2025-01-15T12:30:00Z',
  },
  {
    id: '2',
    name: 'Product Description Enhancement',
    status: 'running',
    strategy: 'paraphrase',
    source_count: 500,
    output_count: 850,
    progress: 68,
    created_at: '2025-01-20T09:00:00Z',
  },
  {
    id: '3',
    name: 'FAQ Expansion',
    status: 'pending',
    strategy: 'synonym_replace',
    source_count: 200,
    output_count: 0,
    progress: 0,
    created_at: '2025-01-20T14:00:00Z',
  },
];

const mockSamples: SampleData[] = [
  {
    id: '1',
    content: 'This product is amazing and works great!',
    label: 'positive',
    source: 'original',
    quality_score: 95,
    created_at: '2025-01-15',
  },
  {
    id: '2',
    content: 'This product is wonderful and functions excellently!',
    label: 'positive',
    source: 'augmented',
    quality_score: 92,
    created_at: '2025-01-15',
  },
  {
    id: '3',
    content: 'The quality is poor and I am disappointed.',
    label: 'negative',
    source: 'original',
    quality_score: 94,
    created_at: '2025-01-15',
  },
];

const statusColors = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
} as const;

const AugmentationPage: React.FC = () => {
  const { t } = useTranslation('augmentation');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [form] = Form.useForm();
  const location = useLocation();

  const strategyKeyMap: Record<string, string> = {
    back_translation: 'strategy.backTranslation',
    paraphrase: 'strategy.paraphrase',
    synonym_replace: 'strategy.synonymReplace',
    noise_injection: 'strategy.noiseInjection',
    eda: 'strategy.eda',
  };

  const statusKeyMap: Record<string, string> = {
    pending: 'status.pending',
    running: 'status.running',
    completed: 'status.completed',
    failed: 'status.failed',
  };

  // Check if we're on a sub-route
  const isSubRoute = location.pathname !== '/augmentation';

  // If on sub-route, render the child component
  if (isSubRoute) {
    return (
      <div>
        <Card style={{ marginBottom: 16 }}>
          <Menu mode="horizontal" selectedKeys={[location.pathname.split('/').pop() || '']}>
            <Menu.Item key="augmentation">
              <Link to="/augmentation">
                <ExperimentOutlined /> {t('nav.overview')}
              </Link>
            </Menu.Item>
            <Menu.Item key="samples">
              <Link to="/augmentation/samples">
                <DatabaseOutlined /> {t('nav.samples')}
              </Link>
            </Menu.Item>
            <Menu.Item key="config">
              <Link to="/augmentation/config">
                <SettingOutlined /> {t('nav.config')}
              </Link>
            </Menu.Item>
          </Menu>
        </Card>
        <Outlet />
      </div>
    );
  }

  const handleCreateJob = async (_values: Record<string, unknown>) => {
    message.success(t('modal.createSuccess'));
    setCreateModalOpen(false);
    form.resetFields();
  };

  const handleUpload: UploadProps['onChange'] = (info) => {
    if (info.file.status === 'done') {
      message.success(`${info.file.name} uploaded successfully`);
      setUploadModalOpen(false);
    } else if (info.file.status === 'error') {
      message.error(`${info.file.name} upload failed`);
    }
  };

  const jobColumns: ColumnsType<AugmentationJob> = [
    {
      title: t('jobs.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name) => <a>{name}</a>,
    },
    {
      title: t('jobs.strategy'),
      dataIndex: 'strategy',
      key: 'strategy',
      render: (strategy) => (
        <Tag color="blue">{t(strategyKeyMap[strategy]) || strategy}</Tag>
      ),
    },
    {
      title: t('jobs.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>{t(statusKeyMap[status])}</Tag>
      ),
    },
    {
      title: t('jobs.progress'),
      key: 'progress',
      width: 200,
      render: (_, record) => (
        <Progress
          percent={record.progress}
          size="small"
          status={record.status === 'failed' ? 'exception' : undefined}
        />
      ),
    },
    {
      title: t('jobs.sourceOutput'),
      key: 'counts',
      render: (_, record) => (
        <span>
          {record.source_count.toLocaleString()} → {record.output_count.toLocaleString()}
        </span>
      ),
    },
    {
      title: t('jobs.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: t('jobs.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'pending' && (
            <Button type="link" size="small" icon={<PlayCircleOutlined />}>
              {t('jobs.start')}
            </Button>
          )}
          {record.status === 'running' && (
            <Button type="link" size="small" icon={<PauseCircleOutlined />}>
              {t('jobs.pause')}
            </Button>
          )}
          <Button type="link" size="small" icon={<EyeOutlined />}>
            {t('jobs.view')}
          </Button>
          <Button type="link" danger size="small" icon={<DeleteOutlined />}>
            {t('jobs.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const sampleColumns: ColumnsType<SampleData> = [
    {
      title: t('samples.content'),
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: t('samples.label'),
      dataIndex: 'label',
      key: 'label',
      width: 100,
      render: (label) => <Tag>{label}</Tag>,
    },
    {
      title: t('samples.source'),
      dataIndex: 'source',
      key: 'source',
      width: 120,
      render: (source) => (
        <Tag color={source === 'original' ? 'blue' : 'green'}>
          {t(`samples.${source}`)}
        </Tag>
      ),
    },
    {
      title: t('samples.quality'),
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 100,
      render: (score) => (
        <Progress
          percent={score}
          size="small"
          status={score >= 90 ? 'success' : 'normal'}
        />
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>{t('title')}</h2>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t('stats.totalSamples')}
              value={25680}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t('stats.augmentedSamples')}
              value={18450}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={t('stats.augmentationRatio')}
              value="3.2x"
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card>
        <Tabs
          defaultActiveKey="jobs"
          items={[
            {
              key: 'jobs',
              label: t('tabs.jobs'),
              children: (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setCreateModalOpen(true)}
                      >
                        {t('jobs.createJob')}
                      </Button>
                      <Button
                        icon={<UploadOutlined />}
                        onClick={() => setUploadModalOpen(true)}
                      >
                        {t('jobs.uploadSamples')}
                      </Button>
                    </Space>
                  </div>
                  <Table
                    columns={jobColumns}
                    dataSource={mockJobs}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                  />
                </>
              ),
            },
            {
              key: 'samples',
              label: t('tabs.samples'),
              children: (
                <>
                  <Alert
                    message={t('samples.preview')}
                    description={t('samples.previewDescription')}
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <Table
                    columns={sampleColumns}
                    dataSource={mockSamples}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* Create Job Modal */}
      <Modal
        title={t('modal.createJob')}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateJob}>
          <Form.Item
            name="name"
            label={t('modal.jobName')}
            rules={[{ required: true, message: t('modal.jobNameRequired') }]}
          >
            <Input placeholder={t('modal.jobNamePlaceholder')} />
          </Form.Item>
          <Form.Item
            name="strategy"
            label={t('modal.strategy')}
            rules={[{ required: true }]}
          >
            <Select placeholder={t('modal.strategyPlaceholder')}>
              <Select.Option value="back_translation">{t('strategy.backTranslation')}</Select.Option>
              <Select.Option value="paraphrase">{t('strategy.paraphrase')}</Select.Option>
              <Select.Option value="synonym_replace">{t('strategy.synonymReplace')}</Select.Option>
              <Select.Option value="eda">{t('strategy.eda')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="multiplier"
            label={t('modal.multiplier')}
            initialValue={3}
          >
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label={t('modal.description')}>
            <Input.TextArea rows={3} placeholder={t('modal.descriptionPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Upload Modal */}
      <Modal
        title={t('modal.uploadSamples')}
        open={uploadModalOpen}
        onCancel={() => setUploadModalOpen(false)}
        footer={null}
      >
        <Upload.Dragger
          name="file"
          accept=".csv,.json,.jsonl"
          onChange={handleUpload}
          action="/api/augmentation/upload"
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">{t('modal.uploadHint')}</p>
          <p className="ant-upload-hint">
            {t('modal.uploadDescription')}
          </p>
        </Upload.Dragger>
      </Modal>
    </div>
  );
};

export default AugmentationPage;
