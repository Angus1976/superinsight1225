/**
 * Admin Sync Strategy Configuration Page
 * 
 * Provides interface for managing data synchronization strategies including
 * sync mode selection, scheduling, and sync history viewing.
 * 
 * **Requirement 4.1, 4.2, 4.4, 4.6: Sync Strategy**
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Tag,
  Tooltip,
  message,
  Popconfirm,
  Badge,
  Typography,
  Alert,
  Timeline,
  Drawer,
  Descriptions,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  HistoryOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import {
  adminApi,
  SyncStrategyResponse,
  SyncStrategyCreate,
  SyncStrategyUpdate,
  SyncHistoryResponse,
  SyncMode,
  getSyncModeName,
  DBConfigResponse,
} from '@/services/adminApi';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const SYNC_MODES: SyncMode[] = ['full', 'incremental', 'realtime'];

const ConfigSync: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [historyDrawerVisible, setHistoryDrawerVisible] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<SyncStrategyResponse | null>(null);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [form] = Form.useForm();

  // Fetch sync strategies
  const { data: strategies = [], isLoading, refetch } = useQuery({
    queryKey: ['admin-sync-strategies'],
    queryFn: () => adminApi.listSyncStrategies(),
  });

  // Fetch DB configs for dropdown
  const { data: dbConfigs = [] } = useQuery({
    queryKey: ['admin-db-configs'],
    queryFn: () => adminApi.listDBConfigs(),
  });

  // Fetch sync history
  const { data: syncHistory = [], isLoading: historyLoading } = useQuery({
    queryKey: ['admin-sync-history', selectedStrategyId],
    queryFn: () => selectedStrategyId ? adminApi.getSyncHistory(selectedStrategyId) : Promise.resolve([]),
    enabled: !!selectedStrategyId,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (strategy: SyncStrategyCreate) =>
      adminApi.createSyncStrategy(strategy, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('同步策略创建成功');
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`创建失败: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, strategy }: { id: string; strategy: SyncStrategyUpdate }) =>
      adminApi.updateSyncStrategy(id, strategy, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('同步策略更新成功');
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
      setModalVisible(false);
      setEditingStrategy(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`更新失败: ${error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteSyncStrategy(id, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('同步策略删除成功');
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
    },
    onError: (error: Error) => {
      message.error(`删除失败: ${error.message}`);
    },
  });

  // Trigger sync mutation
  const triggerMutation = useMutation({
    mutationFn: (strategyId: string) => adminApi.triggerSync(strategyId, user?.id || ''),
    onSuccess: (result) => {
      message.success(`同步任务已启动: ${result.job_id}`);
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
    },
    onError: (error: Error) => {
      message.error(`触发同步失败: ${error.message}`);
    },
  });

  const handleCreate = () => {
    setEditingStrategy(null);
    form.resetFields();
    form.setFieldsValue({
      mode: 'full',
      batch_size: 1000,
      enabled: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: SyncStrategyResponse) => {
    setEditingStrategy(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleViewHistory = (strategyId: string) => {
    setSelectedStrategyId(strategyId);
    setHistoryDrawerVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (editingStrategy) {
        updateMutation.mutate({ id: editingStrategy.id, strategy: values });
      } else {
        createMutation.mutate(values);
      }
    } catch (error) {
      // Form validation error
    }
  };

  const getDbConfigName = (dbConfigId: string) => {
    const config = dbConfigs.find((c: DBConfigResponse) => c.id === dbConfigId);
    return config?.name || dbConfigId;
  };

  const getSyncStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: SyncStrategyResponse) => (
        <Text strong>{text || `策略 ${record.id.slice(0, 8)}`}</Text>
      ),
    },
    {
      title: '数据库',
      dataIndex: 'db_config_id',
      key: 'db_config_id',
      render: (id: string) => <Tag>{getDbConfigName(id)}</Tag>,
    },
    {
      title: '同步模式',
      dataIndex: 'mode',
      key: 'mode',
      render: (mode: SyncMode) => {
        const colors: Record<SyncMode, string> = {
          full: 'blue',
          incremental: 'green',
          realtime: 'purple',
        };
        return <Tag color={colors[mode]}>{getSyncModeName(mode)}</Tag>;
      },
    },
    {
      title: '调度',
      dataIndex: 'schedule',
      key: 'schedule',
      render: (schedule: string) => (
        schedule ? <Text code>{schedule}</Text> : <Text type="secondary">手动触发</Text>
      ),
    },
    {
      title: '最后同步',
      key: 'last_sync',
      render: (_: unknown, record: SyncStrategyResponse) => (
        <Space>
          {record.last_sync_status && getSyncStatusIcon(record.last_sync_status)}
          {record.last_sync_at ? (
            <Text>{new Date(record.last_sync_at).toLocaleString()}</Text>
          ) : (
            <Text type="secondary">从未同步</Text>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'enabled',
      render: (_: unknown, record: SyncStrategyResponse) => (
        record.enabled ? (
          <Badge status="success" text="已启用" />
        ) : (
          <Badge status="default" text="已禁用" />
        )
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: SyncStrategyResponse) => (
        <Space>
          <Tooltip title="立即同步">
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => triggerMutation.mutate(record.id)}
              loading={triggerMutation.isPending}
              disabled={!record.enabled}
            />
          </Tooltip>
          <Tooltip title="同步历史">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => handleViewHistory(record.id)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此同步策略？"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <SyncOutlined />
            <span>同步策略管理</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              添加策略
            </Button>
          </Space>
        }
      >
        <Alert
          message="同步说明"
          description="配置数据同步策略，支持全量同步、增量同步和实时同步三种模式。可设置 Cron 表达式进行定时同步。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Table
          columns={columns}
          dataSource={strategies}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingStrategy ? '编辑同步策略' : '添加同步策略'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingStrategy(null);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="策略名称">
            <Input placeholder="例如：每日全量同步" />
          </Form.Item>

          <Form.Item
            name="db_config_id"
            label="数据库连接"
            rules={[{ required: true, message: '请选择数据库连接' }]}
          >
            <Select placeholder="选择数据库连接" disabled={!!editingStrategy}>
              {dbConfigs.map((config: DBConfigResponse) => (
                <Option key={config.id} value={config.id}>
                  {config.name} ({config.db_type})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="mode"
            label="同步模式"
            rules={[{ required: true, message: '请选择同步模式' }]}
          >
            <Select placeholder="选择同步模式">
              {SYNC_MODES.map(mode => (
                <Option key={mode} value={mode}>
                  {getSyncModeName(mode)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.mode !== currentValues.mode}
          >
            {({ getFieldValue }) =>
              getFieldValue('mode') === 'incremental' && (
                <Form.Item
                  name="incremental_field"
                  label="增量字段"
                  rules={[{ required: true, message: '增量同步需要指定增量字段' }]}
                >
                  <Input placeholder="例如：updated_at, id" />
                </Form.Item>
              )
            }
          </Form.Item>

          <Form.Item
            name="schedule"
            label="调度表达式"
            extra="Cron 表达式，留空则手动触发。例如：0 2 * * * (每天凌晨2点)"
          >
            <Input placeholder="例如：0 2 * * *" />
          </Form.Item>

          <Form.Item name="batch_size" label="批次大小">
            <InputNumber min={1} max={100000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="enabled" valuePropName="checked" label="启用策略">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* History Drawer */}
      <Drawer
        title="同步历史"
        placement="right"
        width={500}
        open={historyDrawerVisible}
        onClose={() => {
          setHistoryDrawerVisible(false);
          setSelectedStrategyId(null);
        }}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <LoadingOutlined style={{ fontSize: 24 }} />
          </div>
        ) : syncHistory.length === 0 ? (
          <Empty description="暂无同步记录" />
        ) : (
          <Timeline>
            {syncHistory.map((item: SyncHistoryResponse) => (
              <Timeline.Item
                key={item.id}
                dot={getSyncStatusIcon(item.status)}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="状态">
                    <Tag color={item.status === 'success' ? 'green' : item.status === 'failed' ? 'red' : 'blue'}>
                      {item.status}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="开始时间">
                    {new Date(item.started_at).toLocaleString()}
                  </Descriptions.Item>
                  {item.completed_at && (
                    <Descriptions.Item label="完成时间">
                      {new Date(item.completed_at).toLocaleString()}
                    </Descriptions.Item>
                  )}
                  <Descriptions.Item label="同步记录数">
                    {item.records_synced}
                  </Descriptions.Item>
                  {item.error_message && (
                    <Descriptions.Item label="错误信息">
                      <Text type="danger">{item.error_message}</Text>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Drawer>
    </div>
  );
};

export default ConfigSync;
