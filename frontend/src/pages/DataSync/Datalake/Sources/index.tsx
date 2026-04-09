import React, { useState, useRef } from 'react';
import { ProTable, type ProColumns, type ActionType } from '@ant-design/pro-components';
import {
  Button, Space, Tag, Modal, Form, Input, Select, Switch,
  message, Popconfirm, Tooltip,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ApiOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { usePermissions } from '@/hooks/usePermissions';
import {
  useDatalakeSources,
  useCreateDatalakeSource,
  useUpdateDatalakeSource,
  useDeleteDatalakeSource,
  useTestDatalakeConnection,
} from '@/hooks/useDatalake';
import {
  DatalakeSourceType,
  DataSourceStatus,
  type DatalakeSourceResponse,
} from '@/types/datalake';

const SOURCE_TYPE_OPTIONS = Object.values(DatalakeSourceType);

const STATUS_COLOR_MAP: Record<DataSourceStatus, string> = {
  [DataSourceStatus.ACTIVE]: 'success',
  [DataSourceStatus.INACTIVE]: 'default',
  [DataSourceStatus.ERROR]: 'error',
  [DataSourceStatus.TESTING]: 'processing',
};

const HEALTH_COLOR_MAP: Record<string, string> = {
  connected: 'success',
  healthy: 'success',
  degraded: 'warning',
  error: 'error',
  down: 'error',
};

const canManageSources = (role: string): boolean => {
  const upper = role.toUpperCase();
  return upper === 'ADMIN' || upper === 'TECHNICAL_EXPERT';
};

const DatalakeSourcesPage: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const { userRole } = usePermissions();
  const actionRef = useRef<ActionType | undefined>(undefined);
  const [form] = Form.useForm();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingSource, setEditingSource] = useState<DatalakeSourceResponse | null>(null);

  const { data: sourcesData, isLoading } = useDatalakeSources();
  const createMutation = useCreateDatalakeSource();
  const updateMutation = useUpdateDatalakeSource();
  const deleteMutation = useDeleteDatalakeSource();
  const testMutation = useTestDatalakeConnection();

  const canManage = canManageSources(userRole || '');

  const handleCreate = () => {
    setEditingSource(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: DatalakeSourceResponse) => {
    setEditingSource(record);
    form.setFieldsValue({
      name: record.name,
      source_type: record.source_type,
      connection_config: record.connection_config,
      is_active: record.is_active,
      description: record.description,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success(t('dataSync:datalake.sources.deleteSuccess', '删除成功'));
      actionRef.current?.reload();
    } catch (error) {
      message.error(t('dataSync:datalake.sources.deleteFailed', '删除失败'));
    }
  };

  const handleTest = async (id: string) => {
    try {
      await testMutation.mutateAsync(id);
      message.success(t('dataSync:datalake.sources.testSuccess', '连接测试成功'));
      actionRef.current?.reload();
    } catch (error) {
      message.error(t('dataSync:datalake.sources.testFailed', '连接测试失败'));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingSource) {
        await updateMutation.mutateAsync({
          id: editingSource.id,
          data: values,
        });
        message.success(t('dataSync:datalake.sources.updateSuccess', '更新成功'));
      } else {
        await createMutation.mutateAsync(values);
        message.success(t('dataSync:datalake.sources.createSuccess', '创建成功'));
      }
      
      setModalVisible(false);
      actionRef.current?.reload();
    } catch (error) {
      message.error(
        editingSource
          ? t('dataSync:datalake.sources.updateFailed', '更新失败')
          : t('dataSync:datalake.sources.createFailed', '创建失败')
      );
    }
  };

  const columns: ProColumns<DatalakeSourceResponse>[] = [
    {
      title: t('dataSync:datalake.sources.name', '数据源名称'),
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text) => (
        <Space>
          <DatabaseOutlined />
          <span>{String(text)}</span>
        </Space>
      ),
    },
    {
      title: t('dataSync:datalake.sources.type', '类型'),
      dataIndex: 'source_type',
      key: 'source_type',
      width: 120,
      render: (text) => <Tag color="blue">{String(text)}</Tag>,
    },
    {
      title: t('dataSync:datalake.sources.status', '状态'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (_, record) => {
        const status = record.status;
        return (
          <Tag color={STATUS_COLOR_MAP[status] || 'default'}>
            {String(status)}
          </Tag>
        );
      },
    },
    {
      title: t('dataSync:datalake.sources.health', '健康状态'),
      dataIndex: ['health_status', 'status'],
      key: 'health',
      width: 120,
      render: (_, record) => {
        const healthStatus = record.health_status?.status || 'unknown';
        return (
          <Tooltip title={record.health_status?.message || ''}>
            <Tag color={HEALTH_COLOR_MAP[healthStatus] || 'default'}>
              {String(healthStatus)}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: t('dataSync:datalake.sources.description', '描述'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text ? String(text) : '-',
    },
    {
      title: t('common:actions.label', '操作'),
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('dataSync:datalake.sources.testConnection', '测试连接')}>
            <Button
              type="link"
              size="small"
              icon={<ApiOutlined />}
              onClick={() => handleTest(record.id)}
              loading={testMutation.isPending}
            />
          </Tooltip>
          {canManage && (
            <>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              >
                {t('common:edit', '编辑')}
              </Button>
              <Popconfirm
                title={t('common:confirmDelete', '确认删除？')}
                onConfirm={() => handleDelete(record.id)}
              >
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                >
                  {t('common:delete', '删除')}
                </Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      <ProTable<DatalakeSourceResponse>
        actionRef={actionRef}
        columns={columns}
        dataSource={sourcesData ?? []}
        loading={isLoading}
        rowKey="id"
        search={false}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
        }}
        toolBarRender={() => [
          canManage && (
            <Button
              key="create"
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              {t('dataSync:datalake.sources.create', '新建数据源')}
            </Button>
          ),
        ]}
      />

      <Modal
        title={
          editingSource
            ? t('dataSync:datalake.sources.edit', '编辑数据源')
            : t('dataSync:datalake.sources.create', '新建数据源')
        }
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('dataSync:datalake.sources.name', '数据源名称')}
            rules={[{ required: true, message: t('common:required', '必填项') }]}
          >
            <Input placeholder={t('dataSync:datalake.sources.namePlaceholder', '请输入数据源名称')} />
          </Form.Item>

          <Form.Item
            name="source_type"
            label={t('dataSync:datalake.sources.type', '类型')}
            rules={[{ required: true, message: t('common:required', '必填项') }]}
          >
            <Select
              placeholder={t('dataSync:datalake.sources.typePlaceholder', '请选择数据源类型')}
              options={SOURCE_TYPE_OPTIONS.map((type) => ({
                label: String(type),
                value: type,
              }))}
            />
          </Form.Item>

          <Form.Item
            name="connection_config"
            label={t('dataSync:datalake.sources.connectionConfig', '连接配置')}
            rules={[{ required: true, message: t('common:required', '必填项') }]}
          >
            <Input.TextArea
              rows={4}
              placeholder={t('dataSync:datalake.sources.connectionConfigPlaceholder', '请输入JSON格式的连接配置')}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('dataSync:datalake.sources.description', '描述')}
          >
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item
            name="is_active"
            label={t('dataSync:datalake.sources.isActive', '启用')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default DatalakeSourcesPage;
