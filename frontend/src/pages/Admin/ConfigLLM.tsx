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
      message.success('LLM 配置创建成功');
      queryClient.invalidateQueries({ queryKey: ['admin-llm-configs'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`创建失败: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: LLMConfigUpdate }) =>
      adminApi.updateLLMConfig(id, config, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('LLM 配置更新成功');
      queryClient.invalidateQueries({ queryKey: ['admin-llm-configs'] });
      setModalVisible(false);
      setEditingConfig(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`更新失败: ${error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteLLMConfig(id, user?.id || '', user?.username || ''),
    onSuccess: () => {
      message.success('LLM 配置删除成功');
      queryClient.invalidateQueries({ queryKey: ['admin-llm-configs'] });
    },
    onError: (error: Error) => {
      message.error(`删除失败: ${error.message}`);
    },
  });

  // Test connection
  const handleTestConnection = async (configId: string) => {
    setTestResults(prev => ({ ...prev, [configId]: { success: false, latency_ms: 0, error_message: '测试中...' } }));
    try {
      const result = await adminApi.testLLMConnection(configId);
      setTestResults(prev => ({ ...prev, [configId]: result }));
      if (result.success) {
        message.success(`连接成功 (${result.latency_ms}ms)`);
      } else {
        message.error(`连接失败: ${result.error_message}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '测试失败';
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
      title: '名称',
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
      title: '类型',
      dataIndex: 'llm_type',
      key: 'llm_type',
      render: (type: LLMType) => <Tag color="blue">{getLLMTypeName(type)}</Tag>,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
      render: (masked: string) => (
        <Tooltip title="API Key 已脱敏显示">
          <Space>
            <EyeInvisibleOutlined />
            <Text code>{masked || '未设置'}</Text>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: LLMConfigResponse) => {
        const testResult = testResults[record.id];
        if (testResult) {
          return testResult.success ? (
            <Badge status="success" text={`在线 (${testResult.latency_ms}ms)`} />
          ) : (
            <Badge status="error" text={testResult.error_message || '离线'} />
          );
        }
        return record.is_active ? (
          <Badge status="default" text="已启用" />
        ) : (
          <Badge status="error" text="已禁用" />
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: LLMConfigResponse) => (
        <Space>
          <Tooltip title="测试连接">
            <Button
              type="text"
              icon={<ApiOutlined />}
              onClick={() => handleTestConnection(record.id)}
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
            title="确定删除此配置？"
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
            <ApiOutlined />
            <span>LLM 配置管理</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              添加配置
            </Button>
          </Space>
        }
      >
        <Alert
          message="配置说明"
          description="管理 LLM 提供商配置，包括本地 Ollama、OpenAI、通义千问等。API Key 将加密存储并脱敏显示。"
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
        title={editingConfig ? '编辑 LLM 配置' : '添加 LLM 配置'}
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
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="例如：生产环境 OpenAI" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="配置描述（可选）" />
          </Form.Item>

          <Form.Item
            name="llm_type"
            label="LLM 类型"
            rules={[{ required: true, message: '请选择 LLM 类型' }]}
          >
            <Select placeholder="选择 LLM 提供商">
              {LLM_TYPES.map(type => (
                <Option key={type} value={type}>
                  {getLLMTypeName(type)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="例如：gpt-3.5-turbo, qwen-turbo" />
          </Form.Item>

          <Form.Item name="api_endpoint" label="API 端点">
            <Input placeholder="例如：https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            extra={editingConfig ? '留空则保持原有 API Key 不变' : undefined}
          >
            <Input.Password placeholder="输入 API Key（将加密存储）" />
          </Form.Item>

          <Form.Item name="temperature" label="Temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="max_tokens" label="最大 Token 数">
            <InputNumber min={1} max={128000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="timeout_seconds" label="超时时间（秒）">
            <InputNumber min={1} max={600} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="is_default" valuePropName="checked" label="设为默认">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigLLM;
