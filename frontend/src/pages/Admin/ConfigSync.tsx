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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['admin', 'common']);
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
      message.success(t('configSync.createSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(t('configSync.createFailed', { error: error.message }));
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, strategy }: { id: string; strategy: SyncStrategyUpdate }) =>
      adminApi.updateSyncStrategy(id, strategy, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('configSync.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
      setModalVisible(false);
      setEditingStrategy(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(t('configSync.updateFailed', { error: error.message }));
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteSyncStrategy(id, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('configSync.deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
    },
    onError: (error: Error) => {
      message.error(t('configSync.deleteFailed', { error: error.message }));
    },
  });

  // Trigger sync mutation
  const triggerMutation = useMutation({
    mutationFn: (strategyId: string) => adminApi.triggerSync(strategyId, user?.id || ''),
    onSuccess: (result) => {
      message.success(t('configSync.triggerSuccess', { jobId: result.job_id }));
      queryClient.invalidateQueries({ queryKey: ['admin-sync-strategies'] });
    },
    onError: (error: Error) => {
      message.error(t('configSync.triggerFailed', { error: error.message }));
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
      title: t('configSync.columns.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: SyncStrategyResponse) => (
        <Text strong>{text || `${t('configSync.strategyPrefix')} ${record.id.slice(0, 8)}`}</Text>
      ),
    },
    {
      title: t('configSync.columns.database'),
      dataIndex: 'db_config_id',
      key: 'db_config_id',
      render: (id: string) => <Tag>{getDbConfigName(id)}</Tag>,
    },
    {
      title: t('configSync.columns.syncMode'),
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
      title: t('configSync.columns.schedule'),
      dataIndex: 'schedule',
      key: 'schedule',
      render: (schedule: string) => (
        schedule ? <Text code>{schedule}</Text> : <Text type="secondary">{t('configSync.manualTrigger')}</Text>
      ),
    },
    {
      title: t('configSync.columns.lastSync'),
      key: 'last_sync',
      render: (_: unknown, record: SyncStrategyResponse) => (
        <Space>
          {record.last_sync_status && getSyncStatusIcon(record.last_sync_status)}
          {record.last_sync_at ? (
            <Text>{new Date(record.last_sync_at).toLocaleString()}</Text>
          ) : (
            <Text type="secondary">{t('configSync.neverSynced')}</Text>
          )}
        </Space>
      ),
    },
    {
      title: t('configSync.columns.status'),
      key: 'enabled',
      render: (_: unknown, record: SyncStrategyResponse) => (
        record.enabled ? (
          <Badge status="success" text={t('configSync.enabled')} />
        ) : (
          <Badge status="default" text={t('configSync.disabled')} />
        )
      ),
    },
    {
      title: t('configSync.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: SyncStrategyResponse) => (
        <Space>
          <Tooltip title={t('configSync.actions.syncNow')}>
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => triggerMutation.mutate(record.id)}
              loading={triggerMutation.isPending}
              disabled={!record.enabled}
            />
          </Tooltip>
          <Tooltip title={t('configSync.actions.syncHistory')}>
            <Button
              type="text"
              icon={<HistoryOutlined />}
              onClick={() => handleViewHistory(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('configSync.actions.edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('configSync.confirmDelete')}
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Tooltip title={t('configSync.actions.delete')}>
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
            <span>{t('configSync.title')}</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('configSync.addStrategy')}
            </Button>
          </Space>
        }
      >
        <Alert
          message={t('configSync.syncDescription')}
          description={t('configSync.syncDescriptionText')}
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
        title={editingStrategy ? t('configSync.editStrategy') : t('configSync.addStrategyTitle')}
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
          <Form.Item name="name" label={t('configSync.form.strategyName')}>
            <Input placeholder={t('configSync.form.strategyNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="db_config_id"
            label={t('configSync.form.dbConnection')}
            rules={[{ required: true, message: t('configSync.form.dbConnectionRequired') }]}
          >
            <Select placeholder={t('configSync.form.dbConnectionPlaceholder')} disabled={!!editingStrategy}>
              {dbConfigs.map((config: DBConfigResponse) => (
                <Option key={config.id} value={config.id}>
                  {config.name} ({config.db_type})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="mode"
            label={t('configSync.form.syncMode')}
            rules={[{ required: true, message: t('configSync.form.syncModeRequired') }]}
          >
            <Select placeholder={t('configSync.form.syncModePlaceholder')}>
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
                  label={t('configSync.form.incrementalField')}
                  rules={[{ required: true, message: t('configSync.form.incrementalFieldRequired') }]}
                >
                  <Input placeholder={t('configSync.form.incrementalFieldPlaceholder')} />
                </Form.Item>
              )
            }
          </Form.Item>

          <Form.Item
            name="schedule"
            label={t('configSync.form.schedule')}
            extra={t('configSync.form.scheduleExtra')}
          >
            <Input placeholder={t('configSync.form.schedulePlaceholder')} />
          </Form.Item>

          <Form.Item name="batch_size" label={t('configSync.form.batchSize')}>
            <InputNumber min={1} max={100000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="enabled" valuePropName="checked" label={t('configSync.form.enableStrategy')}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* History Drawer */}
      <Drawer
        title={t('configSync.history.title')}
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
          <Empty description={t('configSync.noHistory')} />
        ) : (
          <Timeline>
            {syncHistory.map((item: SyncHistoryResponse) => (
              <Timeline.Item
                key={item.id}
                dot={getSyncStatusIcon(item.status)}
              >
                <Descriptions column={1} size="small">
                  <Descriptions.Item label={t('configSync.history.status')}>
                    <Tag color={item.status === 'success' ? 'green' : item.status === 'failed' ? 'red' : 'blue'}>
                      {item.status}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('configSync.history.startTime')}>
                    {new Date(item.started_at).toLocaleString()}
                  </Descriptions.Item>
                  {item.completed_at && (
                    <Descriptions.Item label={t('configSync.history.endTime')}>
                      {new Date(item.completed_at).toLocaleString()}
                    </Descriptions.Item>
                  )}
                  <Descriptions.Item label={t('configSync.history.recordsSynced')}>
                    {item.records_synced}
                  </Descriptions.Item>
                  {item.error_message && (
                    <Descriptions.Item label={t('configSync.history.errorMessage')}>
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
