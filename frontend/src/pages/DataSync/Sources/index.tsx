import React, { useState, useMemo } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Progress, Tooltip, Alert } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SyncOutlined, InboxOutlined, StarOutlined, ThunderboltOutlined, FileTextOutlined, ExperimentOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import {
  normalizeDataSource,
  toCreateSourceRequestBody,
  type DataSyncSource as DataSource,
} from '@/utils/dataSyncApiNormalize';

type SourceType = DataSource['type'];

/** 数据流转类型与所需权限的映射 */
const LIFECYCLE_TYPE_PERMISSIONS: Record<string, string> = {
  lifecycle_temp_data: 'dataLifecycle.create',
  lifecycle_sample: 'dataLifecycle.create',
  lifecycle_enhancement: 'enhancement.create',
  lifecycle_annotation: 'annotationTask.create',
  lifecycle_ai_trial: 'aiTrial.view',
};

/** 判断是否为数据流转类型 */
const isLifecycleType = (type: string): boolean => type.startsWith('lifecycle_');

const DataSyncSources: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuthStore();

  /** 根据用户权限过滤可用的数据流转类型 */
  const availableLifecycleTypes = useMemo(() => {
    return Object.entries(LIFECYCLE_TYPE_PERMISSIONS)
      .filter(([, permission]) => hasPermission(permission))
      .map(([type]) => type);
  }, [hasPermission]);

  const { data: sources = [], isLoading } = useQuery<DataSource[]>({
    queryKey: ['data-sources'],
    queryFn: async () => {
      const res = await api.get('/api/v1/data-sync/sources');
      const list = res.data as Record<string, unknown>[];
      return Array.isArray(list) ? list.map(normalizeDataSource) : [];
    },
  });

  const createSourceMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/api/v1/data-sync/sources', toCreateSourceRequestBody(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('dataSource.createSuccess'));
    },
    onError: () => {
      message.error(t('dataSource.createError'));
    },
  });

  const updateSourceMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/api/v1/data-sync/sources/${id}`, toCreateSourceRequestBody(data)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('dataSource.updateSuccess'));
    },
    onError: () => {
      message.error(t('dataSource.updateError'));
    },
  });

  const deleteSourceMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/data-sync/sources/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      message.success(t('dataSource.deleteSuccess'));
    },
    onError: () => {
      message.error(t('dataSource.deleteError'));
    },
  });

  const syncSourceMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/data-sync/sources/${id}/sync`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      message.success(t('dataSource.syncStarted'));
    },
    onError: () => {
      message.error(t('dataSource.syncError'));
    },
  });

  const toggleSourceMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      api.patch(`/api/v1/data-sync/sources/${id}/toggle`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      message.success(t('dataSource.statusUpdateSuccess'));
    },
    onError: () => {
      message.error(t('dataSource.statusUpdateError'));
    },
  });

  const columns: ColumnsType<DataSource> = [
    {
      title: t('dataSource.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record) => (
        <div>
          <div>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.connectionString && record.connectionString.length > 50 
              ? `${record.connectionString.substring(0, 50)}...` 
              : record.connectionString || '-'}
          </div>
        </div>
      ),
    },
    {
      title: t('dataSource.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          database: 'blue',
          file: 'green',
          api: 'orange',
          stream: 'purple',
          lifecycle_temp_data: 'cyan',
          lifecycle_sample: 'gold',
          lifecycle_enhancement: 'magenta',
          lifecycle_annotation: 'geekblue',
          lifecycle_ai_trial: 'volcano',
        };
        return <Tag color={colors[type] || 'default'}>{t(`sourceTypes.${type}`)}</Tag>;
      },
    },
    {
      title: t('dataSource.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          active: 'success',
          inactive: 'default',
          error: 'error',
          syncing: 'processing',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{t(`status.${status}`)}</Tag>;
      },
    },
    {
      title: t('dataSource.syncProgress'),
      key: 'progress',
      render: (_, record) => {
        const totalRecords = record.totalRecords || 0;
        const syncedRecords = record.syncedRecords || 0;
        const errorCount = record.errorCount || 0;
        const progress = totalRecords > 0 ? (syncedRecords / totalRecords) * 100 : 0;
        return (
          <div>
            <Progress 
              percent={Math.round(progress)} 
              size="small" 
              showInfo={false}
              status={errorCount > 0 ? 'exception' : 'normal'}
            />
            <div style={{ fontSize: '12px', color: '#666' }}>
              {syncedRecords}/{totalRecords} {t('dataSource.records')}
            </div>
          </div>
        );
      },
    },
    {
      title: t('dataSource.syncInterval'),
      dataIndex: 'syncInterval',
      key: 'syncInterval',
      render: (interval: number) =>
        interval > 0 ? `${interval} ${t('dataSource.minutes')}` : '-',
    },
    {
      title: t('dataSource.lastSync'),
      dataIndex: 'lastSyncTime',
      key: 'lastSyncTime',
      render: (time: string) => time ? new Date(time).toLocaleString() : t('dataSource.neverSynced'),
    },
    {
      title: t('dataSource.nextSync'),
      dataIndex: 'nextSyncTime',
      key: 'nextSyncTime',
      render: (time: string) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: t('form.enableStatus'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => toggleSourceMutation.mutate({ id: record.id, enabled: checked })}
          checkedChildren={t('schedule.enabled')}
          unCheckedChildren={t('schedule.disabled')}
        />
      ),
    },
    {
      title: t('common:actions.label'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title={t('dataSource.syncNow')}>
            <Button
              type="link"
              icon={<SyncOutlined />}
              onClick={() => syncSourceMutation.mutate(record.id)}
              loading={syncSourceMutation.isPending}
            />
          </Tooltip>
          <Tooltip title={t('dataSource.edit')}>
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingSource(record);
                form.setFieldsValue(record);
                setIsModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('dataSource.delete')}>
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: t('dataSource.deleteConfirm'),
                  content: t('dataSource.deleteWarning', { name: record.name }),
                  onOk: () => deleteSourceMutation.mutate(record.id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    if (editingSource) {
      updateSourceMutation.mutate({ id: editingSource.id, data: values });
    } else {
      createSourceMutation.mutate(values);
    }
  };

  const renderConfigForm = (type: string) => {
    // 数据流转类型：显示说明和可选的状态过滤
    if (isLifecycleType(type)) {
      return (
        <>
          <Alert
            type="info"
            showIcon
            message={t('lifecycleSource.hint')}
            description={t(`lifecycleSource.${type}_desc`)}
            style={{ marginBottom: 16 }}
          />
          <Form.Item
            name={['config', 'state_filter']}
            label={t('lifecycleSource.stateFilter')}
          >
            <Select
              mode="multiple"
              allowClear
              placeholder={t('lifecycleSource.stateFilterPlaceholder')}
            >
              {type === 'lifecycle_temp_data' && (
                <>
                  <Select.Option value="temp_stored">{t('lifecycleSource.states.temp_stored')}</Select.Option>
                  <Select.Option value="approved">{t('lifecycleSource.states.approved')}</Select.Option>
                  <Select.Option value="ready">{t('lifecycleSource.states.ready')}</Select.Option>
                </>
              )}
              {type === 'lifecycle_sample' && (
                <>
                  <Select.Option value="active">{t('lifecycleSource.states.active')}</Select.Option>
                  <Select.Option value="archived">{t('lifecycleSource.states.archived')}</Select.Option>
                </>
              )}
              {type === 'lifecycle_enhancement' && (
                <>
                  <Select.Option value="completed">{t('lifecycleSource.states.completed')}</Select.Option>
                  <Select.Option value="running">{t('lifecycleSource.states.running')}</Select.Option>
                </>
              )}
              {type === 'lifecycle_annotation' && (
                <>
                  <Select.Option value="completed">{t('lifecycleSource.states.completed')}</Select.Option>
                  <Select.Option value="in_progress">{t('lifecycleSource.states.in_progress')}</Select.Option>
                </>
              )}
              {type === 'lifecycle_ai_trial' && (
                <>
                  <Select.Option value="completed">{t('lifecycleSource.states.completed')}</Select.Option>
                  <Select.Option value="running">{t('lifecycleSource.states.running')}</Select.Option>
                </>
              )}
            </Select>
          </Form.Item>
          <Form.Item
            name={['config', 'auto_sync_new']}
            label={t('lifecycleSource.autoSyncNew')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch
              checkedChildren={t('schedule.enabled')}
              unCheckedChildren={t('schedule.disabled')}
            />
          </Form.Item>
        </>
      );
    }

    switch (type) {
      case 'database':
        return (
          <>
            <Form.Item
              name={['config', 'host']}
              label={t('form.hostAddress')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input placeholder={t('form.hostPlaceholder')} />
            </Form.Item>
            <Form.Item
              name={['config', 'port']}
              label={t('form.port')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input placeholder={t('form.portPlaceholder')} />
            </Form.Item>
            <Form.Item
              name={['config', 'database']}
              label={t('form.databaseName')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input placeholder={t('form.databasePlaceholder')} />
            </Form.Item>
            <Form.Item
              name={['config', 'username']}
              label={t('form.username')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input placeholder={t('form.usernamePlaceholder')} />
            </Form.Item>
            <Form.Item
              name={['config', 'password']}
              label={t('form.password')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input.Password placeholder={t('form.passwordPlaceholder')} />
            </Form.Item>
          </>
        );
      case 'file':
        return (
          <>
            <Form.Item
              name={['config', 'path']}
              label={t('form.filePath')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input placeholder={t('form.filePathPlaceholder')} />
            </Form.Item>
            <Form.Item
              name={['config', 'format']}
              label={t('form.fileFormat')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Select placeholder={t('form.fileFormatPlaceholder')}>
                <Select.Option value="csv">CSV</Select.Option>
                <Select.Option value="json">JSON</Select.Option>
                <Select.Option value="xml">XML</Select.Option>
                <Select.Option value="excel">Excel</Select.Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'api':
        return (
          <>
            <Form.Item
              name={['config', 'url']}
              label={t('form.apiUrl')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Input placeholder={t('form.apiUrlPlaceholder')} />
            </Form.Item>
            <Form.Item
              name={['config', 'method']}
              label={t('form.requestMethod')}
              rules={[{ required: true, message: t('common:validation.required') }]}
            >
              <Select placeholder={t('form.requestMethodPlaceholder')}>
                <Select.Option value="GET">GET</Select.Option>
                <Select.Option value="POST">POST</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name={['config', 'headers']}
              label={t('form.requestHeaders')}
            >
              <Input.TextArea rows={3} placeholder='{"Authorization": "Bearer token"}' />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div className="data-sync-sources">
      <Card
        title={t('dataSource.title')}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingSource(null);
              form.resetFields();
              setIsModalVisible(true);
            }}
          >
            {t('dataSource.create')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={sources}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => t('common.totalRecords', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      <Modal
        title={editingSource ? t('dataSource.edit') : t('dataSource.create')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createSourceMutation.isPending || updateSourceMutation.isPending}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label={t('dataSource.name')}
            rules={[{ required: true, message: t('dataSource.namePlaceholder') }]}
          >
            <Input placeholder={t('dataSource.namePlaceholder')} />
          </Form.Item>
          
          <Form.Item
            name="type"
            label={t('dataSource.type')}
            rules={[{ required: true, message: t('dataSource.typePlaceholder') }]}
          >
            <Select placeholder={t('dataSource.typePlaceholder')}>
              <Select.OptGroup label={t('sourceTypes.groupExternal')}>
                <Select.Option value="database">{t('sourceTypes.database')}</Select.Option>
                <Select.Option value="file">{t('sourceTypes.file')}</Select.Option>
                <Select.Option value="api">{t('sourceTypes.api')}</Select.Option>
                <Select.Option value="stream">{t('sourceTypes.stream')}</Select.Option>
              </Select.OptGroup>
              {availableLifecycleTypes.length > 0 && (
                <Select.OptGroup label={t('sourceTypes.groupLifecycle')}>
                  {availableLifecycleTypes.includes('lifecycle_temp_data') && (
                    <Select.Option value="lifecycle_temp_data">
                      <Space><InboxOutlined />{t('sourceTypes.lifecycle_temp_data')}</Space>
                    </Select.Option>
                  )}
                  {availableLifecycleTypes.includes('lifecycle_sample') && (
                    <Select.Option value="lifecycle_sample">
                      <Space><StarOutlined />{t('sourceTypes.lifecycle_sample')}</Space>
                    </Select.Option>
                  )}
                  {availableLifecycleTypes.includes('lifecycle_enhancement') && (
                    <Select.Option value="lifecycle_enhancement">
                      <Space><ThunderboltOutlined />{t('sourceTypes.lifecycle_enhancement')}</Space>
                    </Select.Option>
                  )}
                  {availableLifecycleTypes.includes('lifecycle_annotation') && (
                    <Select.Option value="lifecycle_annotation">
                      <Space><FileTextOutlined />{t('sourceTypes.lifecycle_annotation')}</Space>
                    </Select.Option>
                  )}
                  {availableLifecycleTypes.includes('lifecycle_ai_trial') && (
                    <Select.Option value="lifecycle_ai_trial">
                      <Space><ExperimentOutlined />{t('sourceTypes.lifecycle_ai_trial')}</Space>
                    </Select.Option>
                  )}
                </Select.OptGroup>
              )}
            </Select>
          </Form.Item>

          <Form.Item
            name="syncInterval"
            label={t('form.syncIntervalLabel')}
            rules={[{ required: true, message: t('common:validation.required') }]}
          >
            <Input type="number" min={1} placeholder="60" />
          </Form.Item>

          <Form.Item dependencies={['type']}>
            {({ getFieldValue }) => {
              const type = getFieldValue('type');
              return type ? renderConfigForm(type) : null;
            }}
          </Form.Item>

          <Form.Item
            name="enabled"
            label={t('form.enableStatus')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren={t('schedule.enabled')} unCheckedChildren={t('schedule.disabled')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DataSyncSources;