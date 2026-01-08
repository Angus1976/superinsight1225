import React, { useState, useEffect } from 'react';
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
  Tabs,
  Alert,
  Tooltip,
  Progress,
  Typography,
  Row,
  Col,
  Statistic,
  Timeline,
  Badge,
  Drawer,
  Steps,
  Divider,
  InputNumber,
  DatePicker,
  Checkbox,
  Tree,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  SettingOutlined,
  BellOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import type { DataNode } from 'antd/es/tree';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Step } = Steps;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

interface SyncTask {
  id: string;
  name: string;
  description: string;
  sourceId: string;
  sourceName: string;
  targetId: string;
  targetName: string;
  status: 'running' | 'paused' | 'stopped' | 'error' | 'completed';
  strategy: 'full' | 'incremental' | 'realtime';
  schedule: {
    type: 'manual' | 'cron' | 'interval';
    expression?: string;
    interval?: number;
    enabled: boolean;
  };
  mapping: FieldMapping[];
  filters: SyncFilter[];
  monitoring: {
    alertsEnabled: boolean;
    thresholds: {
      errorRate: number;
      latency: number;
      throughput: number;
    };
    notifications: string[];
  };
  lastRun?: Date;
  nextRun?: Date;
  totalRecords: number;
  processedRecords: number;
  errorRecords: number;
  createdAt: Date;
  updatedAt: Date;
}

interface FieldMapping {
  id: string;
  sourceField: string;
  targetField: string;
  transformation?: string;
  required: boolean;
}

interface SyncFilter {
  id: string;
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'like' | 'in' | 'not_in';
  value: any;
  enabled: boolean;
}

interface SyncExecution {
  id: string;
  taskId: string;
  status: 'running' | 'completed' | 'failed';
  startTime: Date;
  endTime?: Date;
  recordsProcessed: number;
  recordsSkipped: number;
  recordsError: number;
  errorMessage?: string;
  logs: string[];
}

const SyncTaskConfig: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [syncTasks, setSyncTasks] = useState<SyncTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingTask, setEditingTask] = useState<SyncTask | null>(null);
  const [selectedTask, setSelectedTask] = useState<SyncTask | null>(null);
  const [executions, setExecutions] = useState<SyncExecution[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();

  // Mock data for demonstration
  useEffect(() => {
    const mockTasks: SyncTask[] = [
      {
        id: '1',
        name: 'User Data Sync',
        description: 'Sync user data from production to analytics',
        sourceId: '1',
        sourceName: 'Production MySQL',
        targetId: '2',
        targetName: 'Analytics PostgreSQL',
        status: 'running',
        strategy: 'incremental',
        schedule: {
          type: 'cron',
          expression: '0 */6 * * *',
          enabled: true,
        },
        mapping: [
          {
            id: '1',
            sourceField: 'user_id',
            targetField: 'id',
            required: true,
          },
          {
            id: '2',
            sourceField: 'username',
            targetField: 'name',
            required: true,
          },
          {
            id: '3',
            sourceField: 'email',
            targetField: 'email_address',
            transformation: 'LOWER(email)',
            required: false,
          },
        ],
        filters: [
          {
            id: '1',
            field: 'status',
            operator: 'eq',
            value: 'active',
            enabled: true,
          },
        ],
        monitoring: {
          alertsEnabled: true,
          thresholds: {
            errorRate: 5,
            latency: 30000,
            throughput: 1000,
          },
          notifications: ['admin@company.com'],
        },
        lastRun: new Date(Date.now() - 1000 * 60 * 60 * 2),
        nextRun: new Date(Date.now() + 1000 * 60 * 60 * 4),
        totalRecords: 50000,
        processedRecords: 48500,
        errorRecords: 25,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 1),
      },
      {
        id: '2',
        name: 'Order Data Sync',
        description: 'Real-time order synchronization',
        sourceId: '1',
        sourceName: 'Production MySQL',
        targetId: '3',
        targetName: 'Cache Redis',
        status: 'paused',
        strategy: 'realtime',
        schedule: {
          type: 'manual',
          enabled: false,
        },
        mapping: [
          {
            id: '4',
            sourceField: 'order_id',
            targetField: 'id',
            required: true,
          },
          {
            id: '5',
            sourceField: 'customer_id',
            targetField: 'customer',
            required: true,
          },
        ],
        filters: [],
        monitoring: {
          alertsEnabled: false,
          thresholds: {
            errorRate: 10,
            latency: 5000,
            throughput: 500,
          },
          notifications: [],
        },
        lastRun: new Date(Date.now() - 1000 * 60 * 60 * 24),
        totalRecords: 25000,
        processedRecords: 25000,
        errorRecords: 0,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 12),
      },
    ];
    setSyncTasks(mockTasks);

    const mockExecutions: SyncExecution[] = [
      {
        id: '1',
        taskId: '1',
        status: 'completed',
        startTime: new Date(Date.now() - 1000 * 60 * 60 * 2),
        endTime: new Date(Date.now() - 1000 * 60 * 60 * 2 + 1000 * 60 * 15),
        recordsProcessed: 1250,
        recordsSkipped: 5,
        recordsError: 2,
        logs: [
          'Starting sync task execution',
          'Connected to source database',
          'Connected to target database',
          'Processing batch 1/10',
          'Processing batch 2/10',
          '...',
          'Sync completed successfully',
        ],
      },
    ];
    setExecutions(mockExecutions);
  }, []);

  const getStatusColor = (status: SyncTask['status']) => {
    switch (status) {
      case 'running':
        return 'processing';
      case 'paused':
        return 'warning';
      case 'stopped':
        return 'default';
      case 'error':
        return 'error';
      case 'completed':
        return 'success';
      default:
        return 'default';
    }
  };

  const getStrategyColor = (strategy: SyncTask['strategy']) => {
    switch (strategy) {
      case 'full':
        return 'blue';
      case 'incremental':
        return 'green';
      case 'realtime':
        return 'orange';
      default:
        return 'default';
    }
  };

  const handleStartTask = (task: SyncTask) => {
    setSyncTasks(prev =>
      prev.map(t =>
        t.id === task.id
          ? { ...t, status: 'running', lastRun: new Date() }
          : t
      )
    );
  };

  const handlePauseTask = (task: SyncTask) => {
    setSyncTasks(prev =>
      prev.map(t =>
        t.id === task.id ? { ...t, status: 'paused' } : t
      )
    );
  };

  const handleStopTask = (task: SyncTask) => {
    setSyncTasks(prev =>
      prev.map(t =>
        t.id === task.id ? { ...t, status: 'stopped' } : t
      )
    );
  };

  const handleCreateOrUpdate = async (values: any) => {
    setLoading(true);
    try {
      if (editingTask) {
        setSyncTasks(prev =>
          prev.map(task =>
            task.id === editingTask.id
              ? { ...task, ...values, updatedAt: new Date() }
              : task
          )
        );
      } else {
        const newTask: SyncTask = {
          id: Date.now().toString(),
          ...values,
          status: 'stopped' as const,
          totalRecords: 0,
          processedRecords: 0,
          errorRecords: 0,
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        setSyncTasks(prev => [...prev, newTask]);
      }
      setModalVisible(false);
      setEditingTask(null);
      form.resetFields();
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (task: SyncTask) => {
    Modal.confirm({
      title: t('dataSync:syncTask.deleteConfirm'),
      content: t('dataSync:syncTask.deleteWarning', { name: task.name }),
      onOk: () => {
        setSyncTasks(prev => prev.filter(t => t.id !== task.id));
      },
    });
  };

  const columns: ColumnsType<SyncTask> = [
    {
      title: t('dataSync:syncTask.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.description}
          </Text>
        </Space>
      ),
    },
    {
      title: t('dataSync:syncTask.source'),
      key: 'source',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text>{record.sourceName}</Text>
          <Text type="secondary">→ {record.targetName}</Text>
        </Space>
      ),
    },
    {
      title: t('dataSync:syncTask.strategy'),
      dataIndex: 'strategy',
      key: 'strategy',
      render: (strategy) => (
        <Tag color={getStrategyColor(strategy)}>
          {t(`dataSync:strategy.${strategy}`)}
        </Tag>
      ),
    },
    {
      title: t('dataSync:syncTask.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge
          status={getStatusColor(status)}
          text={t(`dataSync:status.${status}`)}
        />
      ),
    },
    {
      title: t('dataSync:syncTask.schedule'),
      key: 'schedule',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.schedule.enabled ? (
            <>
              <Tag color="green">{t(`dataSync:schedule.${record.schedule.type}`)}</Tag>
              {record.schedule.expression && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {record.schedule.expression}
                </Text>
              )}
            </>
          ) : (
            <Tag>{t('dataSync:schedule.disabled')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('dataSync:syncTask.progress'),
      key: 'progress',
      render: (_, record) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Progress
            percent={Math.round((record.processedRecords / record.totalRecords) * 100) || 0}
            size="small"
            status={record.errorRecords > 0 ? 'exception' : 'normal'}
          />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.processedRecords.toLocaleString()} / {record.totalRecords.toLocaleString()}
          </Text>
        </Space>
      ),
    },
    {
      title: t('dataSync:syncTask.lastRun'),
      dataIndex: 'lastRun',
      key: 'lastRun',
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: t('common:actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'stopped' || record.status === 'paused' ? (
            <Tooltip title={t('dataSync:syncTask.start')}>
              <Button
                type="text"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStartTask(record)}
              />
            </Tooltip>
          ) : (
            <Tooltip title={t('dataSync:syncTask.pause')}>
              <Button
                type="text"
                icon={<PauseCircleOutlined />}
                onClick={() => handlePauseTask(record)}
              />
            </Tooltip>
          )}
          <Tooltip title={t('dataSync:syncTask.stop')}>
            <Button
              type="text"
              icon={<StopOutlined />}
              onClick={() => handleStopTask(record)}
              disabled={record.status === 'stopped'}
            />
          </Tooltip>
          <Tooltip title={t('dataSync:syncTask.viewDetails')}>
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedTask(record);
                setDrawerVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingTask(record);
                form.setFieldsValue(record);
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('common:delete')}>
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const renderConfigStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="name"
                  label={t('dataSync:syncTask.name')}
                  rules={[{ required: true, message: t('common:validation.required') }]}
                >
                  <Input placeholder={t('dataSync:syncTask.namePlaceholder')} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="strategy"
                  label={t('dataSync:syncTask.strategy')}
                  rules={[{ required: true, message: t('common:validation.required') }]}
                >
                  <Select placeholder={t('dataSync:syncTask.strategyPlaceholder')}>
                    <Select.Option value="full">{t('dataSync:strategy.full')}</Select.Option>
                    <Select.Option value="incremental">{t('dataSync:strategy.incremental')}</Select.Option>
                    <Select.Option value="realtime">{t('dataSync:strategy.realtime')}</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name="description"
              label={t('dataSync:syncTask.description')}
            >
              <TextArea rows={3} placeholder={t('dataSync:syncTask.descriptionPlaceholder')} />
            </Form.Item>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="sourceId"
                  label={t('dataSync:syncTask.source')}
                  rules={[{ required: true, message: t('common:validation.required') }]}
                >
                  <Select placeholder={t('dataSync:syncTask.sourcePlaceholder')}>
                    <Select.Option value="1">Production MySQL</Select.Option>
                    <Select.Option value="2">Analytics PostgreSQL</Select.Option>
                    <Select.Option value="3">Cache Redis</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="targetId"
                  label={t('dataSync:syncTask.target')}
                  rules={[{ required: true, message: t('common:validation.required') }]}
                >
                  <Select placeholder={t('dataSync:syncTask.targetPlaceholder')}>
                    <Select.Option value="1">Production MySQL</Select.Option>
                    <Select.Option value="2">Analytics PostgreSQL</Select.Option>
                    <Select.Option value="3">Cache Redis</Select.Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          </>
        );
      case 1:
        return (
          <>
            <Form.Item label={t('dataSync:syncTask.fieldMapping')}>
              <Table
                size="small"
                columns={[
                  {
                    title: t('dataSync:mapping.sourceField'),
                    dataIndex: 'sourceField',
                    render: (_, __, index) => (
                      <Form.Item
                        name={['mapping', index, 'sourceField']}
                        style={{ margin: 0 }}
                      >
                        <Input placeholder="source_field" />
                      </Form.Item>
                    ),
                  },
                  {
                    title: t('dataSync:mapping.targetField'),
                    dataIndex: 'targetField',
                    render: (_, __, index) => (
                      <Form.Item
                        name={['mapping', index, 'targetField']}
                        style={{ margin: 0 }}
                      >
                        <Input placeholder="target_field" />
                      </Form.Item>
                    ),
                  },
                  {
                    title: t('dataSync:mapping.transformation'),
                    dataIndex: 'transformation',
                    render: (_, __, index) => (
                      <Form.Item
                        name={['mapping', index, 'transformation']}
                        style={{ margin: 0 }}
                      >
                        <Input placeholder="UPPER(field)" />
                      </Form.Item>
                    ),
                  },
                  {
                    title: t('dataSync:mapping.required'),
                    dataIndex: 'required',
                    render: (_, __, index) => (
                      <Form.Item
                        name={['mapping', index, 'required']}
                        valuePropName="checked"
                        style={{ margin: 0 }}
                      >
                        <Checkbox />
                      </Form.Item>
                    ),
                  },
                ]}
                dataSource={[{}, {}, {}]}
                pagination={false}
              />
            </Form.Item>
          </>
        );
      case 2:
        return (
          <>
            <Form.Item label={t('dataSync:syncTask.scheduleType')}>
              <Form.Item name={['schedule', 'type']} style={{ display: 'inline-block', width: '200px' }}>
                <Select>
                  <Select.Option value="manual">{t('dataSync:schedule.manual')}</Select.Option>
                  <Select.Option value="cron">{t('dataSync:schedule.cron')}</Select.Option>
                  <Select.Option value="interval">{t('dataSync:schedule.interval')}</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                name={['schedule', 'enabled']}
                valuePropName="checked"
                style={{ display: 'inline-block', marginLeft: '16px' }}
              >
                <Checkbox>{t('dataSync:schedule.enabled')}</Checkbox>
              </Form.Item>
            </Form.Item>
            <Form.Item
              name={['schedule', 'expression']}
              label={t('dataSync:schedule.expression')}
            >
              <Input placeholder="0 */6 * * *" />
            </Form.Item>
          </>
        );
      case 3:
        return (
          <>
            <Form.Item
              name={['monitoring', 'alertsEnabled']}
              valuePropName="checked"
            >
              <Checkbox>{t('dataSync:monitoring.alertsEnabled')}</Checkbox>
            </Form.Item>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name={['monitoring', 'thresholds', 'errorRate']}
                  label={t('dataSync:monitoring.errorRate')}
                >
                  <InputNumber
                    min={0}
                    max={100}
                    formatter={value => `${value}%`}
                    parser={value => value!.replace('%', '')}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name={['monitoring', 'thresholds', 'latency']}
                  label={t('dataSync:monitoring.latency')}
                >
                  <InputNumber
                    min={0}
                    formatter={value => `${value}ms`}
                    parser={value => value!.replace('ms', '')}
                  />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name={['monitoring', 'thresholds', 'throughput']}
                  label={t('dataSync:monitoring.throughput')}
                >
                  <InputNumber min={0} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name={['monitoring', 'notifications']}
              label={t('dataSync:monitoring.notifications')}
            >
              <Select mode="tags" placeholder={t('dataSync:monitoring.notificationsPlaceholder')}>
                <Select.Option value="admin@company.com">admin@company.com</Select.Option>
                <Select.Option value="ops@company.com">ops@company.com</Select.Option>
              </Select>
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:syncTask.totalTasks')}
              value={syncTasks.length}
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:syncTask.runningTasks')}
              value={syncTasks.filter(task => task.status === 'running').length}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:syncTask.errorTasks')}
              value={syncTasks.filter(task => task.status === 'error').length}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('dataSync:syncTask.totalRecords')}
              value={syncTasks.reduce((sum, task) => sum + task.totalRecords, 0)}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={t('dataSync:syncTask.title')}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingTask(null);
              form.resetFields();
              setCurrentStep(0);
              setModalVisible(true);
            }}
          >
            {t('dataSync:syncTask.create')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={syncTasks}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => t('common:pagination.total', { total }),
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingTask ? t('dataSync:syncTask.edit') : t('dataSync:syncTask.create')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingTask(null);
          form.resetFields();
          setCurrentStep(0);
        }}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            {t('common:cancel')}
          </Button>,
          currentStep > 0 && (
            <Button key="prev" onClick={() => setCurrentStep(currentStep - 1)}>
              {t('common:previous')}
            </Button>
          ),
          currentStep < 3 ? (
            <Button key="next" type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
              {t('common:next')}
            </Button>
          ) : (
            <Button key="submit" type="primary" loading={loading} onClick={() => form.submit()}>
              {t('common:submit')}
            </Button>
          ),
        ]}
        width={800}
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title={t('dataSync:steps.basic')} />
          <Step title={t('dataSync:steps.mapping')} />
          <Step title={t('dataSync:steps.schedule')} />
          <Step title={t('dataSync:steps.monitoring')} />
        </Steps>

        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrUpdate}
        >
          {renderConfigStep()}
        </Form>
      </Modal>

      {/* Task Details Drawer */}
      <Drawer
        title={selectedTask?.name}
        placement="right"
        size="large"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedTask && (
          <Tabs defaultActiveKey="overview">
            <TabPane tab={t('dataSync:tabs.overview')} key="overview">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card size="small" title={t('dataSync:syncTask.basicInfo')}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Text type="secondary">{t('dataSync:syncTask.strategy')}: </Text>
                      <Tag color={getStrategyColor(selectedTask.strategy)}>
                        {t(`dataSync:strategy.${selectedTask.strategy}`)}
                      </Tag>
                    </Col>
                    <Col span={12}>
                      <Text type="secondary">{t('dataSync:syncTask.status')}: </Text>
                      <Badge
                        status={getStatusColor(selectedTask.status)}
                        text={t(`dataSync:status.${selectedTask.status}`)}
                      />
                    </Col>
                  </Row>
                </Card>

                <Card size="small" title={t('dataSync:syncTask.progress')}>
                  <Progress
                    percent={Math.round((selectedTask.processedRecords / selectedTask.totalRecords) * 100) || 0}
                    status={selectedTask.errorRecords > 0 ? 'exception' : 'normal'}
                  />
                  <Row gutter={16} style={{ marginTop: 16 }}>
                    <Col span={8}>
                      <Statistic
                        title={t('dataSync:syncTask.totalRecords')}
                        value={selectedTask.totalRecords}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title={t('dataSync:syncTask.processedRecords')}
                        value={selectedTask.processedRecords}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title={t('dataSync:syncTask.errorRecords')}
                        value={selectedTask.errorRecords}
                        valueStyle={{ color: selectedTask.errorRecords > 0 ? '#cf1322' : undefined }}
                      />
                    </Col>
                  </Row>
                </Card>
              </Space>
            </TabPane>

            <TabPane tab={t('dataSync:tabs.executions')} key="executions">
              <Timeline>
                {executions
                  .filter(exec => exec.taskId === selectedTask.id)
                  .map(exec => (
                    <Timeline.Item
                      key={exec.id}
                      color={exec.status === 'completed' ? 'green' : exec.status === 'failed' ? 'red' : 'blue'}
                    >
                      <div>
                        <Text strong>{t(`dataSync:execution.${exec.status}`)}</Text>
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                          {dayjs(exec.startTime).format('YYYY-MM-DD HH:mm:ss')}
                        </Text>
                      </div>
                      <div>
                        <Text type="secondary">
                          {t('dataSync:execution.processed')}: {exec.recordsProcessed.toLocaleString()}
                        </Text>
                        {exec.recordsError > 0 && (
                          <Text type="danger" style={{ marginLeft: 16 }}>
                            {t('dataSync:execution.errors')}: {exec.recordsError}
                          </Text>
                        )}
                      </div>
                      {exec.errorMessage && (
                        <Alert
                          message={exec.errorMessage}
                          type="error"
                          size="small"
                          style={{ marginTop: 8 }}
                        />
                      )}
                    </Timeline.Item>
                  ))}
              </Timeline>
            </TabPane>

            <TabPane tab={t('dataSync:tabs.monitoring')} key="monitoring">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card size="small" title={t('dataSync:monitoring.alerts')}>
                  <Switch
                    checked={selectedTask.monitoring.alertsEnabled}
                    checkedChildren={t('common:enabled')}
                    unCheckedChildren={t('common:disabled')}
                  />
                </Card>

                <Card size="small" title={t('dataSync:monitoring.thresholds')}>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title={t('dataSync:monitoring.errorRate')}
                        value={selectedTask.monitoring.thresholds.errorRate}
                        suffix="%"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title={t('dataSync:monitoring.latency')}
                        value={selectedTask.monitoring.thresholds.latency}
                        suffix="ms"
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title={t('dataSync:monitoring.throughput')}
                        value={selectedTask.monitoring.thresholds.throughput}
                        suffix="/min"
                      />
                    </Col>
                  </Row>
                </Card>
              </Space>
            </TabPane>
          </Tabs>
        )}
      </Drawer>
    </div>
  );
};

export default SyncTaskConfig;