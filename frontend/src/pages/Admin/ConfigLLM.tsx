/**
 * Admin LLM Configuration Page
 * 
 * Provides interface for managing LLM provider configurations including
 * creation, editing, testing connections, and viewing masked API keys.
 * 
 * **Requirement 2.1, 2.2, 2.5, 2.6: LLM Configuration**
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
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeInvisibleOutlined,
  ReloadOutlined,
  StarOutlined,
  StarFilled,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import {
  adminApi,
  LLMConfigResponse,
  LLMConfigCreate,
  LLMConfigUpdate,
  LLMType,
  getLLMTypeName,
  ConnectionTestResult,
} from '@/services/adminApi';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const LLM_TYPES: LLMType[] = ['local_ollama', 'openai', 'qianwen', 'zhipu', 'hunyuan', 'custom'];

const ConfigLLM: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<LLMConfigResponse | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult>>({});
  const [form] = Form.useForm();

  // Fetch LLM configs
  const { data: configs = [], isLoading, refetch } = useQuery({
    queryKey: ['admin-llm-configs'],
    queryFn: () => adminApi.listLLMConfigs(undefined, false),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (config: LLMConfigCreate) => 
      adminApi.createLLMConfig(config, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('llm.configSaveSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-llm-configs'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`${t('llm.configSaveFailed')}: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: LLMConfigUpdate }) =>
      adminApi.updateLLMConfig(id, config, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('llm.configSaveSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-llm-configs'] });
      setModalVisible(false);
      setEditingConfig(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`${t('llm.configSaveFailed')}: ${error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteLLMConfig(id, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success(t('common:deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-llm-configs'] });
    },
    onError: (error: Error) => {
      message.error(`${t('common:deleteFailed')}: ${error.message}`);
    },
  });

  // Test connection
  const handleTestConnection = async (configId: string) => {
    setTestResults(prev => ({ ...prev, [configId]: { success: false, latency_ms: 0, error_message: t('llm.status.testing') } }));
    try {
      const result = await adminApi.testLLMConnection(configId);
      setTestResults(prev => ({ ...prev, [configId]: result }));
      if (result.success) {
        message.success(t('llm.status.connectionSuccess') + ` (${result.latency_ms}ms)`);
      } else {
        message.error(`${t('llm.status.connectionFailed')}: ${result.error_message}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : t('llm.status.connectionFailed');
      setTestResults(prev => ({ ...prev, [configId]: { success: false, latency_ms: 0, error_message: errorMsg } }));
      message.error(errorMsg);
    }
  };

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      temperature: 0.7,
      max_tokens: 2048,
      timeout_seconds: 60,
      is_default: false,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: LLMConfigResponse) => {
    setEditingConfig(record);
    form.setFieldsValue({
      ...record,
      api_key: '', // Don't show encrypted key
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // Remove empty api_key if not changed
      if (!values.api_key) {
        delete values.api_key;
      }

      if (editingConfig) {
        updateMutation.mutate({ id: editingConfig.id, config: values });
      } else {
        createMutation.mutate(values);
      }
    } catch (error) {
      // Form validation error
    }
  };

  const columns = [
    {
      title: t('common:name'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: LLMConfigResponse) => (
        <Space>
          {record.is_default && <StarFilled style={{ color: '#faad14' }} />}
          <Text strong>{text}</Text>
        </Space>
      ),
    },
    {
      title: t('common:type'),
      dataIndex: 'llm_type',
      key: 'llm_type',
      render: (type: LLMType) => <Tag color="blue">{getLLMTypeName(type)}</Tag>,
    },
    {
      title: t('llm.local.defaultModel'),
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (masked: string) => (
        <Tooltip title={t('llm.form.apiKeyMasked')}>
          <Space>
            <EyeInvisibleOutlined />
            <Text code>{masked || t('llm.form.notSet')}</Text>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: t('common:status'),
      key: 'status',
      render: (_: unknown, record: LLMConfigResponse) => {
        const testResult = testResults[record.id];
        if (testResult) {
          return testResult.success ? (
            <Badge status="success" text={`${t('llm.status.online')} (${testResult.latency_ms}ms)`} />
          ) : (
            <Badge status="error" text={testResult.error_message || t('llm.status.offline')} />
          );
        }
        return record.is_active ? (
          <Badge status="default" text={t('llm.form.enabled')} />
        ) : (
          <Badge status="error" text={t('llm.status.disabled')} />
        );
      },
    },
    {
      title: t('common:actions'),
      key: 'actions',
      render: (_: unknown, record: LLMConfigResponse) => (
        <Space>
          <Tooltip title={t('llm.actions.testConnection')}>
            <Button
              type="text"
              icon={<ApiOutlined />}
              onClick={() => handleTestConnection(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('llm.form.confirmDelete')}
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Tooltip title={t('common:delete')}>
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
            <ApiOutlined />
            <span>{t('llm.title')}</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('llm.form.addConfig')}
            </Button>
          </Space>
        }
      >
        <Alert
          message={t('llm.form.configTip')}
          description={t('llm.form.configTipDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingConfig ? t('llm.form.editConfig') : t('llm.form.addConfig')}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingConfig(null);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('llm.form.configName')}
            rules={[{ required: true, message: t('llm.form.configNameRequired') }]}
          >
            <Input placeholder={t('llm.form.configNamePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('common:description')}>
            <TextArea rows={2} placeholder={t('llm.form.descriptionPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="llm_type"
            label={t('llm.form.llmType')}
            rules={[{ required: true, message: t('llm.form.llmTypeRequired') }]}
          >
            <Select placeholder={t('llm.form.llmTypePlaceholder')}>
              {LLM_TYPES.map(type => (
                <Option key={type} value={type}>
                  {getLLMTypeName(type)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="model_name"
            label={t('llm.form.modelName')}
            rules={[{ required: true, message: t('llm.form.modelNameRequired') }]}
          >
            <Input placeholder={t('llm.form.modelNamePlaceholder')} />
          </Form.Item>

          <Form.Item name="api_endpoint" label={t('llm.form.apiEndpoint')}>
            <Input placeholder={t('llm.form.apiEndpointPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            extra={editingConfig ? t('llm.form.apiKeyKeepEmpty') : undefined}
          >
            <Input.Password placeholder={t('llm.form.apiKeyPlaceholder')} />
          </Form.Item>

          <Form.Item name="temperature" label="Temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="max_tokens" label={t('llm.form.maxTokens')}>
            <InputNumber min={1} max={128000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="timeout_seconds" label={t('llm.form.timeout')}>
            <InputNumber min={1} max={600} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="is_default" valuePropName="checked" label={t('llm.form.setAsDefault')}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigLLM;
