/**
 * Crowdsource Portal Page (众包门户页面)
 * 
 * Crowdsource management interface including:
 * - Available tasks for annotators
 * - Earnings and statistics
 * - Annotator management (admin)
 * - Platform configuration
 */

import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
  Progress,
  Modal,
  Form,
  Input,
  Select,
  Rate,
  message,
  Avatar,
  Descriptions,
} from 'antd';
import {
  DollarOutlined,
  UserOutlined,
  FileTextOutlined,
  SettingOutlined,
  CloudServerOutlined,
  WalletOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

// Types
interface CrowdsourceTask {
  id: string;
  projectName: string;
  description: string;
  price: number;
  deadline: string;
  claimed: number;
  maxAnnotators: number;
  sensitivityLevel: number;
}

interface Annotator {
  id: string;
  name: string;
  email: string;
  status: 'active' | 'pending_verification' | 'pending_test' | 'suspended';
  starRating: number;
  totalTasks: number;
  totalEarnings: number;
  accuracy: number;
  abilityTags: string[];
}

interface Platform {
  name: string;
  type: 'mturk' | 'scale_ai' | 'custom';
  status: 'connected' | 'disconnected';
  pendingTasks: number;
  completedTasks: number;
}

interface EarningsRecord {
  period: string;
  baseAmount: number;
  qualityBonus: number;
  starBonus: number;
  totalAmount: number;
  taskCount: number;
}

// Mock data
const mockTasks: CrowdsourceTask[] = [
  { id: '1', projectName: '客户评论分类', description: '对客户评论进行情感分类', price: 0.5, deadline: '2026-01-20', claimed: 2, maxAnnotators: 5, sensitivityLevel: 1 },
  { id: '2', projectName: '产品实体识别', description: '识别产品描述中的实体', price: 0.8, deadline: '2026-01-22', claimed: 3, maxAnnotators: 3, sensitivityLevel: 2 },
  { id: '3', projectName: '意图识别', description: '识别用户查询意图', price: 0.6, deadline: '2026-01-25', claimed: 1, maxAnnotators: 5, sensitivityLevel: 1 },
];

const mockAnnotators: Annotator[] = [
  { id: '1', name: '张三', email: 'zhangsan@example.com', status: 'active', starRating: 5, totalTasks: 150, totalEarnings: 1250.50, accuracy: 0.95, abilityTags: ['NER', '情感分析'] },
  { id: '2', name: '李四', email: 'lisi@example.com', status: 'active', starRating: 4, totalTasks: 120, totalEarnings: 980.00, accuracy: 0.92, abilityTags: ['分类', '意图识别'] },
  { id: '3', name: '王五', email: 'wangwu@example.com', status: 'pending_test', starRating: 0, totalTasks: 0, totalEarnings: 0, accuracy: 0, abilityTags: [] },
  { id: '4', name: '赵六', email: 'zhaoliu@example.com', status: 'suspended', starRating: 2, totalTasks: 50, totalEarnings: 320.00, accuracy: 0.65, abilityTags: ['分类'] },
];

const mockPlatforms: Platform[] = [
  { name: 'Amazon MTurk', type: 'mturk', status: 'connected', pendingTasks: 15, completedTasks: 230 },
  { name: 'Scale AI', type: 'scale_ai', status: 'disconnected', pendingTasks: 0, completedTasks: 0 },
  { name: '自定义平台', type: 'custom', status: 'connected', pendingTasks: 8, completedTasks: 45 },
];

const mockEarnings: EarningsRecord[] = [
  { period: '2026-01', baseAmount: 450.00, qualityBonus: 54.00, starBonus: 45.00, totalAmount: 549.00, taskCount: 45 },
  { period: '2025-12', baseAmount: 380.00, qualityBonus: 38.00, starBonus: 38.00, totalAmount: 456.00, taskCount: 38 },
  { period: '2025-11', baseAmount: 420.00, qualityBonus: 50.40, starBonus: 42.00, totalAmount: 512.40, taskCount: 42 },
];

const statusColors = {
  active: 'success',
  pending_verification: 'warning',
  pending_test: 'processing',
  suspended: 'error',
} as const;

const CrowdsourcePage: React.FC = () => {
  const { t } = useTranslation('crowdsource');
  const [claimModalOpen, setClaimModalOpen] = useState(false);
  const [platformModalOpen, setPlatformModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<CrowdsourceTask | null>(null);
  const [platformForm] = Form.useForm();

  const statusKeyMap: Record<string, string> = {
    active: 'annotatorStatus.active',
    pending_verification: 'annotatorStatus.pendingVerification',
    pending_test: 'annotatorStatus.pendingTest',
    suspended: 'annotatorStatus.suspended',
  };

  const sensitivityKeyMap: Record<number, string> = {
    1: 'sensitivity.public',
    2: 'sensitivity.internal',
    3: 'sensitivity.sensitive',
  };

  const handleClaimTask = (task: CrowdsourceTask) => {
    setSelectedTask(task);
    setClaimModalOpen(true);
  };

  const confirmClaim = () => {
    message.success(t('modal.claimSuccess', { name: selectedTask?.projectName }));
    setClaimModalOpen(false);
  };

  const handleAddPlatform = () => {
    platformForm.validateFields().then(values => {
      message.success(t('modal.addPlatformSuccess', { name: values.name }));
      setPlatformModalOpen(false);
      platformForm.resetFields();
    });
  };

  const taskColumns: ColumnsType<CrowdsourceTask> = [
    {
      title: t('tasks.projectName'),
      dataIndex: 'projectName',
      key: 'projectName',
      render: (name) => <a>{name}</a>,
    },
    {
      title: t('tasks.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('tasks.price'),
      dataIndex: 'price',
      key: 'price',
      render: (price) => <span style={{ color: '#52c41a', fontWeight: 'bold' }}>¥{price.toFixed(2)}</span>,
    },
    {
      title: t('tasks.sensitivityLevel'),
      dataIndex: 'sensitivityLevel',
      key: 'sensitivityLevel',
      render: (level) => (
        <Tag color={level === 1 ? 'green' : level === 2 ? 'orange' : 'red'}>
          {t(sensitivityKeyMap[level])}
        </Tag>
      ),
    },
    {
      title: t('tasks.deadline'),
      dataIndex: 'deadline',
      key: 'deadline',
    },
    {
      title: t('tasks.claimed'),
      key: 'claimed',
      render: (_, record) => `${record.claimed}/${record.maxAnnotators}`,
    },
    {
      title: t('tasks.actions'),
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          disabled={record.claimed >= record.maxAnnotators}
          onClick={() => handleClaimTask(record)}
        >
          {t('tasks.claim')}
        </Button>
      ),
    },
  ];

  const annotatorColumns: ColumnsType<Annotator> = [
    {
      title: t('annotators.annotator'),
      key: 'name',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div>{record.name}</div>
            <div style={{ fontSize: 12, color: '#999' }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: t('annotators.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>{t(statusKeyMap[status])}</Tag>
      ),
    },
    {
      title: t('annotators.starRating'),
      dataIndex: 'starRating',
      key: 'starRating',
      render: (rating) => <Rate disabled value={rating} />,
    },
    {
      title: t('annotators.accuracy'),
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (acc) => acc > 0 ? <Progress percent={acc * 100} size="small" style={{ width: 80 }} /> : '-',
    },
    {
      title: t('annotators.completedTasks'),
      dataIndex: 'totalTasks',
      key: 'totalTasks',
    },
    {
      title: t('annotators.totalEarnings'),
      dataIndex: 'totalEarnings',
      key: 'totalEarnings',
      render: (earnings) => <span style={{ color: '#52c41a' }}>¥{earnings.toFixed(2)}</span>,
    },
    {
      title: t('annotators.abilityTags'),
      dataIndex: 'abilityTags',
      key: 'abilityTags',
      render: (tags: string[]) => tags.map(tag => <Tag key={tag}>{tag}</Tag>),
    },
  ];

  const platformColumns: ColumnsType<Platform> = [
    {
      title: t('platforms.platformName'),
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <CloudServerOutlined />
          {name}
          <Tag>{record.type.toUpperCase()}</Tag>
        </Space>
      ),
    },
    {
      title: t('platforms.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge 
          status={status === 'connected' ? 'success' : 'error'} 
          text={status === 'connected' ? t('platforms.connected') : t('platforms.disconnected')} 
        />
      ),
    },
    {
      title: t('platforms.pendingTasks'),
      dataIndex: 'pendingTasks',
      key: 'pendingTasks',
    },
    {
      title: t('platforms.completedTasks'),
      dataIndex: 'completedTasks',
      key: 'completedTasks',
    },
    {
      title: t('platforms.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small">{t('platforms.configure')}</Button>
          <Button type="link" size="small">
            {record.status === 'connected' ? t('platforms.disconnect') : t('platforms.connect')}
          </Button>
        </Space>
      ),
    },
  ];

  const totalEarnings = mockEarnings.reduce((sum, e) => sum + e.totalAmount, 0);
  const activeAnnotators = mockAnnotators.filter(a => a.status === 'active').length;

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>{t('title')}</h2>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.availableTasks')}
              value={mockTasks.filter(t => t.claimed < t.maxAnnotators).length}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.activeAnnotators')}
              value={activeAnnotators}
              suffix={`/ ${mockAnnotators.length}`}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.monthlyEarnings')}
              value={mockEarnings[0]?.totalAmount || 0}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.connectedPlatforms')}
              value={mockPlatforms.filter(p => p.status === 'connected').length}
              suffix={`/ ${mockPlatforms.length}`}
              prefix={<CloudServerOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card>
        <Tabs
          defaultActiveKey="tasks"
          items={[
            {
              key: 'tasks',
              label: <span><FileTextOutlined /> {t('tabs.tasks')}</span>,
              children: (
                <Table
                  columns={taskColumns}
                  dataSource={mockTasks}
                  rowKey="id"
                  pagination={false}
                />
              ),
            },
            {
              key: 'earnings',
              label: <span><WalletOutlined /> {t('tabs.earnings')}</span>,
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={8}>
                      <Card>
                        <Statistic title={t('earnings.totalEarnings')} value={totalEarnings} prefix="¥" precision={2} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card>
                        <Statistic title={t('earnings.totalTasks')} value={mockEarnings.reduce((sum, e) => sum + e.taskCount, 0)} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card>
                        <Statistic title={t('earnings.avgPrice')} value={totalEarnings / mockEarnings.reduce((sum, e) => sum + e.taskCount, 0)} prefix="¥" precision={2} />
                      </Card>
                    </Col>
                  </Row>
                  <Table
                    dataSource={mockEarnings}
                    rowKey="period"
                    pagination={false}
                    columns={[
                      { title: t('earnings.period'), dataIndex: 'period' },
                      { title: t('earnings.baseAmount'), dataIndex: 'baseAmount', render: (v) => `¥${v.toFixed(2)}` },
                      { title: t('earnings.qualityBonus'), dataIndex: 'qualityBonus', render: (v) => `¥${v.toFixed(2)}` },
                      { title: t('earnings.starBonus'), dataIndex: 'starBonus', render: (v) => `¥${v.toFixed(2)}` },
                      { title: t('earnings.totalAmount'), dataIndex: 'totalAmount', render: (v) => <span style={{ color: '#52c41a', fontWeight: 'bold' }}>¥{v.toFixed(2)}</span> },
                      { title: t('earnings.taskCount'), dataIndex: 'taskCount' },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: 'annotators',
              label: <span><UserOutlined /> {t('tabs.annotators')}</span>,
              children: (
                <Table
                  columns={annotatorColumns}
                  dataSource={mockAnnotators}
                  rowKey="id"
                  pagination={false}
                />
              ),
            },
            {
              key: 'platforms',
              label: <span><CloudServerOutlined /> {t('tabs.platforms')}</span>,
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<SettingOutlined />} onClick={() => setPlatformModalOpen(true)}>
                      {t('platforms.addPlatform')}
                    </Button>
                  </div>
                  <Table
                    columns={platformColumns}
                    dataSource={mockPlatforms}
                    rowKey="name"
                    pagination={false}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* Claim Task Modal */}
      <Modal
        title={t('modal.claimTask')}
        open={claimModalOpen}
        onCancel={() => setClaimModalOpen(false)}
        onOk={confirmClaim}
        okText={t('modal.confirmClaim')}
      >
        {selectedTask && (
          <Descriptions column={1}>
            <Descriptions.Item label={t('tasks.projectName')}>{selectedTask.projectName}</Descriptions.Item>
            <Descriptions.Item label={t('tasks.description')}>{selectedTask.description}</Descriptions.Item>
            <Descriptions.Item label={t('tasks.price')}>¥{selectedTask.price.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label={t('tasks.deadline')}>{selectedTask.deadline}</Descriptions.Item>
            <Descriptions.Item label={t('tasks.sensitivityLevel')}>
              <Tag color={selectedTask.sensitivityLevel === 1 ? 'green' : selectedTask.sensitivityLevel === 2 ? 'orange' : 'red'}>
                {t(sensitivityKeyMap[selectedTask.sensitivityLevel])}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* Add Platform Modal */}
      <Modal
        title={t('modal.addPlatform')}
        open={platformModalOpen}
        onCancel={() => setPlatformModalOpen(false)}
        onOk={handleAddPlatform}
      >
        <Form form={platformForm} layout="vertical">
          <Form.Item name="name" label={t('modal.platformName')} rules={[{ required: true }]}>
            <Input placeholder={t('modal.platformNamePlaceholder')} />
          </Form.Item>
          <Form.Item name="type" label={t('modal.platformType')} rules={[{ required: true }]}>
            <Select placeholder={t('modal.platformTypePlaceholder')}>
              <Select.Option value="mturk">Amazon MTurk</Select.Option>
              <Select.Option value="scale_ai">Scale AI</Select.Option>
              <Select.Option value="custom">Custom REST API</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="apiKey" label={t('modal.apiKey')}>
            <Input.Password placeholder={t('modal.apiKeyPlaceholder')} />
          </Form.Item>
          <Form.Item name="endpoint" label={t('modal.apiEndpoint')}>
            <Input placeholder={t('modal.apiEndpointPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CrowdsourcePage;
