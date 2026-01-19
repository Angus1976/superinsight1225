/**
 * Admin Third-Party Tools Configuration Page
 * 
 * Provides interface for managing third-party tool integrations including
 * adding, editing, enabling/disabling, and health checking.
 * 
 * **Requirement 7.1, 7.2, 7.3, 7.5, 7.6: Third-Party Tools**
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
  Progress,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeInvisibleOutlined,
  ReloadOutlined,
  HeartOutlined,
  ApiOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import {
  adminApi,
  ThirdPartyConfigResponse,
  ThirdPartyConfigCreate,
  ThirdPartyConfigUpdate,
  ThirdPartyToolType,
  ConnectionTestResult,
} from '@/services/adminApi';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const TOOL_TYPES: ThirdPartyToolType[] = ['text_to_sql', 'ai_annotation', 'data_processing', 'custom'];

const ThirdPartyConfig: React.FC = () => {
  const { t } = useTranslation('admin');

  const getToolTypeName = (type: ThirdPartyToolType): string => {
    const names: Record<ThirdPartyToolType, string> = {
      text_to_sql: t('thirdPartyConfig.toolTypes.textToSql'),
      ai_annotation: t('thirdPartyConfig.toolTypes.aiAnnotation'),
      data_processing: t('thirdPartyConfig.toolTypes.dataProcessing'),
      custom: t('thirdPartyConfig.toolTypes.custom'),
    };
    return names[type] || type;
  };
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ThirdPartyConfigResponse | null>(null);
  const [healthResults, setHealthResults] = useState<Record<string, ConnectionTestResult>>({});
  const [form] = Form.useForm();

  // Fetch third-party configs
  const { data: configs = [], isLoading, refetch } = useQuery({
    queryKey: ['admin-third-party-configs'],
    queryFn: () => adminApi.listThirdPartyConfigs(),
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (config: ThirdPartyConfigCreate) =>
      adminApi.createThirdPartyConfig(config, user?.id || ''),
    onSuccess: () => {
      message.success(t('thirdPartyConfig.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-third-party-configs'] });
      setModalVisible(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`${t('thirdPartyConfig.updateFailed')}: ${error.message}`);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: ThirdPartyConfigUpdate }) =>
      adminApi.updateThirdPartyConfig(id, config, user?.id || ''),
    onSuccess: () => {
      message.success(t('thirdPartyConfig.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-third-party-configs'] });
      setModalVisible(false);
      setEditingConfig(null);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`${t('thirdPartyConfig.updateFailed')}: ${error.message}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteThirdPartyConfig(id, user?.id || ''),
    onSuccess: () => {
      message.success(t('thirdPartyConfig.deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['admin-third-party-configs'] });
    },
    onError: (error: Error) => {
      message.error(`${t('thirdPartyConfig.deleteFailed')}: ${error.message}`);
    },
  });

  // Toggle enabled mutation
  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      adminApi.updateThirdPartyConfig(id, { enabled }, user?.id || ''),
    onSuccess: (_, variables) => {
      message.success(variables.enabled ? t('thirdPartyConfig.toolEnabled') : t('thirdPartyConfig.toolDisabled'));
      queryClient.invalidateQueries({ queryKey: ['admin-third-party-configs'] });
    },
    onError: (error: Error) => {
      message.error(`${t('thirdPartyConfig.operationFailed')}: ${error.message}`);
    },
  });

  // Health check
  const handleHealthCheck = async (configId: string) => {
    setHealthResults(prev => ({
      ...prev,
      [configId]: { success: false, latency_ms: 0, error_message: t('thirdPartyConfig.checking') },
    }));
    try {
      const result = await adminApi.checkThirdPartyHealth(configId);
      setHealthResults(prev => ({ ...prev, [configId]: result }));
      if (result.success) {
        message.success(t('thirdPartyConfig.healthCheckSuccess', { latency: result.latency_ms }));
      } else {
        message.error(`${t('thirdPartyConfig.healthCheckFailed')}: ${result.error_message}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : t('thirdPartyConfig.checkFailed');
      setHealthResults(prev => ({
        ...prev,
        [configId]: { success: false, latency_ms: 0, error_message: errorMsg },
      }));
      message.error(errorMsg);
    }
  };

  const handleCreate = () => {
    setEditingConfig(null);
    form.resetFields();
    form.setFieldsValue({
      timeout_seconds: 30,
    });
    setModalVisible(true);
  };

  const handleEdit = (record: ThirdPartyConfigResponse) => {
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
      title: t('thirdPartyConfig.toolName'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: t('thirdPartyConfig.toolType'),
      dataIndex: 'tool_type',
      key: 'tool_type',
      render: (type: ThirdPartyToolType) => <Tag color="cyan">{getToolTypeName(type)}</Tag>,
    },
    {
      title: t('thirdPartyConfig.apiEndpoint'),
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
      render: (endpoint: string) => (
        <Tooltip title={endpoint}>
          <Text code style={{ maxWidth: 200 }}>{endpoint}</Text>
        </Tooltip>
      ),
    },
    {
      title: t('thirdPartyConfig.status'),
      key: 'status',
      render: (_: unknown, record: ThirdPartyConfigResponse) => {
        const healthResult = healthResults[record.id];
        if (healthResult) {
          return healthResult.success ? (
            <Badge status="success" text={t('thirdPartyConfig.healthyWithLatency', { latency: healthResult.latency_ms })} />
          ) : (
            <Badge status="error" text={healthResult.error_message || t('thirdPartyConfig.unhealthy')} />
          );
        }
        if (record.health_status) {
          return record.health_status === 'healthy' ? (
            <Badge status="success" text={t('thirdPartyConfig.healthy')} />
          ) : (
            <Badge status="error" text={record.health_status} />
          );
        }
        return <Badge status="default" text={t('thirdPartyConfig.notChecked')} />;
      },
    },
    {
      title: t('thirdPartyConfig.enabledColumn'),
      key: 'enabled',
      render: (_: unknown, record: ThirdPartyConfigResponse) => (
        <Switch
          checked={record.enabled}
          onChange={(checked) => toggleMutation.mutate({ id: record.id, enabled: checked })}
          loading={toggleMutation.isPending}
        />
      ),
    },
    {
      title: t('thirdPartyConfig.callStats'),
      key: 'stats',
      render: (_: unknown, record: ThirdPartyConfigResponse) => (
        <Space direction="vertical" size="small">
          <Text type="secondary">{t('thirdPartyConfig.calls')}: {record.call_count}</Text>
          <Progress
            percent={record.success_rate * 100}
            size="small"
            status={record.success_rate >= 0.9 ? 'success' : record.success_rate >= 0.7 ? 'normal' : 'exception'}
            format={(p) => `${p?.toFixed(0)}%`}
          />
        </Space>
      ),
    },
    {
      title: t('thirdPartyConfig.actions'),
      key: 'actions',
      render: (_: unknown, record: ThirdPartyConfigResponse) => (
        <Space>
          <Tooltip title={t('thirdPartyConfig.healthCheck')}>
            <Button
              type="text"
              icon={<HeartOutlined />}
              onClick={() => handleHealthCheck(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('thirdPartyConfig.edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('thirdPartyConfig.confirmDelete')}
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Tooltip title={t('thirdPartyConfig.delete')}>
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
            <SettingOutlined />
            <span>{t('thirdPartyConfig.title')}</span>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t('common:refresh')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('thirdPartyConfig.addTool')}
            </Button>
          </Space>
        }
      >
        <Alert
          message={t('thirdPartyConfig.infoTitle')}
          description={t('thirdPartyConfig.infoDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* Summary Stats */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic
                title={t('thirdPartyConfig.stats.totalTools')}
                value={configs.length}
                prefix={<SettingOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic
                title={t('thirdPartyConfig.stats.enabled')}
                value={configs.filter((c: ThirdPartyConfigResponse) => c.enabled).length}
                valueStyle={{ color: '#3f8600' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic
                title={t('thirdPartyConfig.stats.totalCalls')}
                value={configs.reduce((sum: number, c: ThirdPartyConfigResponse) => sum + c.call_count, 0)}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic
                title={t('thirdPartyConfig.stats.avgSuccessRate')}
                value={
                  configs.length > 0
                    ? (configs.reduce((sum: number, c: ThirdPartyConfigResponse) => sum + c.success_rate, 0) / configs.length * 100).toFixed(1)
                    : 0
                }
                suffix="%"
                prefix={<ApiOutlined />}
              />
            </Card>
          </Col>
        </Row>

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
        title={editingConfig ? t('thirdPartyConfig.editTool') : t('thirdPartyConfig.addTool')}
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
            label={t('thirdPartyConfig.configName')}
            rules={[{ required: true, message: t('thirdPartyConfig.configNameRequired') }]}
          >
            <Input placeholder={t('thirdPartyConfig.configNamePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('thirdPartyConfig.description')}>
            <TextArea rows={2} placeholder={t('thirdPartyConfig.descriptionPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="tool_type"
            label={t('thirdPartyConfig.toolType')}
            rules={[{ required: true, message: t('thirdPartyConfig.toolTypeRequired') }]}
          >
            <Select placeholder={t('thirdPartyConfig.toolTypePlaceholder')}>
              {TOOL_TYPES.map(type => (
                <Option key={type} value={type}>
                  {getToolTypeName(type)}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="endpoint"
            label={t('thirdPartyConfig.apiEndpoint')}
            rules={[
              { required: true, message: t('thirdPartyConfig.endpointRequired') },
              { type: 'url', message: t('thirdPartyConfig.endpointInvalid') },
            ]}
          >
            <Input placeholder={t('thirdPartyConfig.endpointPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="api_key"
            label={t('thirdPartyConfig.apiKey')}
            extra={editingConfig ? t('thirdPartyConfig.apiKeyKeepEmpty') : undefined}
          >
            <Input.Password placeholder={t('thirdPartyConfig.apiKeyPlaceholder')} />
          </Form.Item>

          <Form.Item name="timeout_seconds" label={t('thirdPartyConfig.timeout')}>
            <InputNumber min={1} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ThirdPartyConfig;
