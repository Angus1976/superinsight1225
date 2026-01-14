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

const statusLabels = {
  active: '活跃',
  pending_verification: '待认证',
  pending_test: '待测试',
  suspended: '已暂停',
};

const sensitivityLabels = ['', '公开', '内部', '敏感'];

const CrowdsourcePage: React.FC = () => {
  const [claimModalOpen, setClaimModalOpen] = useState(false);
  const [platformModalOpen, setPlatformModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<CrowdsourceTask | null>(null);
  const [platformForm] = Form.useForm();

  const handleClaimTask = (task: CrowdsourceTask) => {
    setSelectedTask(task);
    setClaimModalOpen(true);
  };

  const confirmClaim = () => {
    message.success(`已领取任务: ${selectedTask?.projectName}`);
    setClaimModalOpen(false);
  };

  const handleAddPlatform = () => {
    platformForm.validateFields().then(values => {
      message.success(`已添加平台: ${values.name}`);
      setPlatformModalOpen(false);
      platformForm.resetFields();
    });
  };

  const taskColumns: ColumnsType<CrowdsourceTask> = [
    {
      title: '项目名称',
      dataIndex: 'projectName',
      key: 'projectName',
      render: (name) => <a>{name}</a>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '单价',
      dataIndex: 'price',
      key: 'price',
      render: (price) => <span style={{ color: '#52c41a', fontWeight: 'bold' }}>¥{price.toFixed(2)}</span>,
    },
    {
      title: '敏感级别',
      dataIndex: 'sensitivityLevel',
      key: 'sensitivityLevel',
      render: (level) => (
        <Tag color={level === 1 ? 'green' : level === 2 ? 'orange' : 'red'}>
          {sensitivityLabels[level]}
        </Tag>
      ),
    },
    {
      title: '截止日期',
      dataIndex: 'deadline',
      key: 'deadline',
    },
    {
      title: '已领取',
      key: 'claimed',
      render: (_, record) => `${record.claimed}/${record.maxAnnotators}`,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          disabled={record.claimed >= record.maxAnnotators}
          onClick={() => handleClaimTask(record)}
        >
          领取
        </Button>
      ),
    },
  ];

  const annotatorColumns: ColumnsType<Annotator> = [
    {
      title: '标注员',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
      ),
    },
    {
      title: '星级',
      dataIndex: 'starRating',
      key: 'starRating',
      render: (rating) => <Rate disabled value={rating} />,
    },
    {
      title: '准确率',
      dataIndex: 'accuracy',
      key: 'accuracy',
      render: (acc) => acc > 0 ? <Progress percent={acc * 100} size="small" style={{ width: 80 }} /> : '-',
    },
    {
      title: '完成任务',
      dataIndex: 'totalTasks',
      key: 'totalTasks',
    },
    {
      title: '总收益',
      dataIndex: 'totalEarnings',
      key: 'totalEarnings',
      render: (earnings) => <span style={{ color: '#52c41a' }}>¥{earnings.toFixed(2)}</span>,
    },
    {
      title: '能力标签',
      dataIndex: 'abilityTags',
      key: 'abilityTags',
      render: (tags: string[]) => tags.map(tag => <Tag key={tag}>{tag}</Tag>),
    },
  ];

  const platformColumns: ColumnsType<Platform> = [
    {
      title: '平台名称',
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
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge status={status === 'connected' ? 'success' : 'error'} text={status === 'connected' ? '已连接' : '未连接'} />
      ),
    },
    {
      title: '待处理任务',
      dataIndex: 'pendingTasks',
      key: 'pendingTasks',
    },
    {
      title: '已完成任务',
      dataIndex: 'completedTasks',
      key: 'completedTasks',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small">配置</Button>
          <Button type="link" size="small">{record.status === 'connected' ? '断开' : '连接'}</Button>
        </Space>
      ),
    },
  ];

  const totalEarnings = mockEarnings.reduce((sum, e) => sum + e.totalAmount, 0);
  const activeAnnotators = mockAnnotators.filter(a => a.status === 'active').length;

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>众包管理</h2>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="可领取任务"
              value={mockTasks.filter(t => t.claimed < t.maxAnnotators).length}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="活跃标注员"
              value={activeAnnotators}
              suffix={`/ ${mockAnnotators.length}`}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="本月收益"
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
              title="已连接平台"
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
              label: <span><FileTextOutlined /> 可领取任务</span>,
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
              label: <span><WalletOutlined /> 收益统计</span>,
              children: (
                <div>
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={8}>
                      <Card>
                        <Statistic title="累计收益" value={totalEarnings} prefix="¥" precision={2} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card>
                        <Statistic title="累计任务" value={mockEarnings.reduce((sum, e) => sum + e.taskCount, 0)} />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card>
                        <Statistic title="平均单价" value={totalEarnings / mockEarnings.reduce((sum, e) => sum + e.taskCount, 0)} prefix="¥" precision={2} />
                      </Card>
                    </Col>
                  </Row>
                  <Table
                    dataSource={mockEarnings}
                    rowKey="period"
                    pagination={false}
                    columns={[
                      { title: '周期', dataIndex: 'period' },
                      { title: '基础金额', dataIndex: 'baseAmount', render: (v) => `¥${v.toFixed(2)}` },
                      { title: '质量奖励', dataIndex: 'qualityBonus', render: (v) => `¥${v.toFixed(2)}` },
                      { title: '星级奖励', dataIndex: 'starBonus', render: (v) => `¥${v.toFixed(2)}` },
                      { title: '总金额', dataIndex: 'totalAmount', render: (v) => <span style={{ color: '#52c41a', fontWeight: 'bold' }}>¥{v.toFixed(2)}</span> },
                      { title: '任务数', dataIndex: 'taskCount' },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: 'annotators',
              label: <span><UserOutlined /> 标注员管理</span>,
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
              label: <span><CloudServerOutlined /> 第三方平台</span>,
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<SettingOutlined />} onClick={() => setPlatformModalOpen(true)}>
                      添加平台
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
        title="领取任务"
        open={claimModalOpen}
        onCancel={() => setClaimModalOpen(false)}
        onOk={confirmClaim}
        okText="确认领取"
      >
        {selectedTask && (
          <Descriptions column={1}>
            <Descriptions.Item label="项目名称">{selectedTask.projectName}</Descriptions.Item>
            <Descriptions.Item label="描述">{selectedTask.description}</Descriptions.Item>
            <Descriptions.Item label="单价">¥{selectedTask.price.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="截止日期">{selectedTask.deadline}</Descriptions.Item>
            <Descriptions.Item label="敏感级别">
              <Tag color={selectedTask.sensitivityLevel === 1 ? 'green' : selectedTask.sensitivityLevel === 2 ? 'orange' : 'red'}>
                {sensitivityLabels[selectedTask.sensitivityLevel]}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* Add Platform Modal */}
      <Modal
        title="添加第三方平台"
        open={platformModalOpen}
        onCancel={() => setPlatformModalOpen(false)}
        onOk={handleAddPlatform}
      >
        <Form form={platformForm} layout="vertical">
          <Form.Item name="name" label="平台名称" rules={[{ required: true }]}>
            <Input placeholder="输入平台名称" />
          </Form.Item>
          <Form.Item name="type" label="平台类型" rules={[{ required: true }]}>
            <Select placeholder="选择平台类型">
              <Select.Option value="mturk">Amazon MTurk</Select.Option>
              <Select.Option value="scale_ai">Scale AI</Select.Option>
              <Select.Option value="custom">自定义 REST API</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="apiKey" label="API Key">
            <Input.Password placeholder="输入 API Key" />
          </Form.Item>
          <Form.Item name="endpoint" label="API Endpoint">
            <Input placeholder="输入 API Endpoint (自定义平台)" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CrowdsourcePage;
