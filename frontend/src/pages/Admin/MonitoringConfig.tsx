/**
 * Monitoring Configuration Page
 *
 * Provides alert threshold configuration including:
 * - Alert threshold management
 * - Alert channel configuration (email, webhook, SMS)
 * - Threshold validation
 *
 * **Feature: admin-configuration**
 * **Validates: Requirements 10.1, 10.2**
 */

import React, { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Modal, Form, Input, InputNumber, Select,
  message, Row, Col, Switch, Tabs, Divider, Alert
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, BellOutlined,
  MailOutlined, ApiOutlined, MobileOutlined, SaveOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

// Types
interface AlertThreshold {
  id: string;
  metric_name: string;
  operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq';
  value: number;
  duration_seconds: number;
  severity: 'info' | 'warning' | 'error' | 'critical';
  enabled: boolean;
  channels: ('email' | 'webhook' | 'sms')[];
  tenant_id: string;
  config_id?: string;
  created_at: string;
  updated_at: string;
}

interface EmailConfig {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  from_address: string;
  to_addresses: string[];
  use_tls: boolean;
}

interface WebhookConfig {
  url: string;
  method: string;
  headers: Record<string, string>;
  timeout: number;
  retry_count: number;
}

interface SMSConfig {
  provider: string;
  api_key: string;
  api_secret?: string;
  from_number: string;
  to_numbers: string[];
}

interface ChannelConfig {
  tenant_id: string;
  email?: EmailConfig;
  webhook?: WebhookConfig;
  sms?: SMSConfig;
}

// Mock API functions - replace with actual API calls
const mockThresholds: AlertThreshold[] = [
  {
    id: '1',
    metric_name: 'llm_response_time_ms',
    operator: 'gt',
    value: 5000,
    duration_seconds: 60,
    severity: 'warning',
    enabled: true,
    channels: ['email', 'webhook'],
    tenant_id: 'default',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '2',
    metric_name: 'db_connection_failures',
    operator: 'gte',
    value: 3,
    duration_seconds: 300,
    severity: 'error',
    enabled: true,
    channels: ['email', 'webhook', 'sms'],
    tenant_id: 'default',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '3',
    metric_name: 'quota_usage_percent',
    operator: 'gte',
    value: 80,
    duration_seconds: 0,
    severity: 'warning',
    enabled: true,
    channels: ['email'],
    tenant_id: 'default',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const fetchThresholds = async (): Promise<AlertThreshold[]> => {
  // Replace with actual API call
  return mockThresholds;
};

const createThreshold = async (data: Partial<AlertThreshold>): Promise<AlertThreshold> => {
  // Replace with actual API call
  return { ...data, id: Date.now().toString() } as AlertThreshold;
};

const updateThreshold = async (id: string, data: Partial<AlertThreshold>): Promise<AlertThreshold> => {
  // Replace with actual API call
  return { ...data, id } as AlertThreshold;
};

const deleteThreshold = async (id: string): Promise<void> => {
  // Replace with actual API call
};

const MonitoringConfig: React.FC = () => {
  const { t } = useTranslation('admin');
  const [isThresholdModalVisible, setIsThresholdModalVisible] = useState(false);
  const [isChannelModalVisible, setIsChannelModalVisible] = useState(false);
  const [editingThreshold, setEditingThreshold] = useState<AlertThreshold | null>(null);
  const [activeChannelTab, setActiveChannelTab] = useState('email');
  const [thresholdForm] = Form.useForm();
  const [emailForm] = Form.useForm();
  const [webhookForm] = Form.useForm();
  const [smsForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch thresholds
  const { data: thresholds, isLoading } = useQuery({
    queryKey: ['alert-thresholds'],
    queryFn: fetchThresholds,
  });

  // Create threshold mutation
  const createMutation = useMutation({
    mutationFn: createThreshold,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-thresholds'] });
      setIsThresholdModalVisible(false);
      thresholdForm.resetFields();
      message.success(t('monitoring.thresholdCreated', 'Alert threshold created successfully'));
    },
    onError: (error: any) => {
      message.error(error.message || t('monitoring.createFailed', 'Failed to create threshold'));
    },
  });

  // Update threshold mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AlertThreshold> }) =>
      updateThreshold(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-thresholds'] });
      setIsThresholdModalVisible(false);
      setEditingThreshold(null);
      thresholdForm.resetFields();
      message.success(t('monitoring.thresholdUpdated', 'Alert threshold updated successfully'));
    },
    onError: (error: any) => {
      message.error(error.message || t('monitoring.updateFailed', 'Failed to update threshold'));
    },
  });

  // Delete threshold mutation
  const deleteMutation = useMutation({
    mutationFn: deleteThreshold,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert-thresholds'] });
      message.success(t('monitoring.thresholdDeleted', 'Alert threshold deleted'));
    },
    onError: (error: any) => {
      message.error(error.message || t('monitoring.deleteFailed', 'Failed to delete threshold'));
    },
  });

  const handleCreateThreshold = () => {
    setEditingThreshold(null);
    thresholdForm.resetFields();
    thresholdForm.setFieldsValue({
      duration_seconds: 60,
      severity: 'warning',
      enabled: true,
      channels: ['email'],
    });
    setIsThresholdModalVisible(true);
  };

  const handleEditThreshold = (record: AlertThreshold) => {
    setEditingThreshold(record);
    thresholdForm.setFieldsValue(record);
    setIsThresholdModalVisible(true);
  };

  const handleDeleteThreshold = (id: string) => {
    Modal.confirm({
      title: t('monitoring.confirmDelete', 'Confirm Delete'),
      content: t('monitoring.deleteConfirmContent', 'Are you sure you want to delete this alert threshold?'),
      onOk: () => deleteMutation.mutate(id),
    });
  };

  const handleThresholdSubmit = (values: any) => {
    const data = {
      ...values,
      tenant_id: 'default', // Get from context in real app
    };

    if (editingThreshold) {
      updateMutation.mutate({ id: editingThreshold.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'error': return 'orange';
      case 'warning': return 'gold';
      case 'info': return 'blue';
      default: return 'default';
    }
  };

  const getOperatorLabel = (operator: string) => {
    const labels: Record<string, string> = {
      gt: '>',
      gte: '>=',
      lt: '<',
      lte: '<=',
      eq: '=',
      neq: '!=',
    };
    return labels[operator] || operator;
  };

  const columns: ColumnsType<AlertThreshold> = [
    {
      title: t('monitoring.columns.metric', 'Metric'),
      dataIndex: 'metric_name',
      key: 'metric_name',
      render: (text) => <code>{text}</code>,
    },
    {
      title: t('monitoring.columns.condition', 'Condition'),
      key: 'condition',
      render: (_, record) => (
        <span>
          {getOperatorLabel(record.operator)} {record.value}
          {record.duration_seconds > 0 && (
            <span style={{ color: '#666', marginLeft: 8 }}>
              ({record.duration_seconds}s)
            </span>
          )}
        </span>
      ),
    },
    {
      title: t('monitoring.columns.severity', 'Severity'),
      dataIndex: 'severity',
      key: 'severity',
      render: (severity) => (
        <Tag color={getSeverityColor(severity)}>
          {severity.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('monitoring.columns.channels', 'Channels'),
      dataIndex: 'channels',
      key: 'channels',
      render: (channels: string[]) => (
        <Space size={4}>
          {channels.includes('email') && <MailOutlined title="Email" />}
          {channels.includes('webhook') && <ApiOutlined title="Webhook" />}
          {channels.includes('sms') && <MobileOutlined title="SMS" />}
        </Space>
      ),
    },
    {
      title: t('monitoring.columns.enabled', 'Enabled'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled) => (
        <Tag color={enabled ? 'green' : 'default'}>
          {enabled ? t('monitoring.enabled', 'Enabled') : t('monitoring.disabled', 'Disabled')}
        </Tag>
      ),
    },
    {
      title: t('monitoring.columns.actions', 'Actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditThreshold(record)}
          >
            {t('monitoring.edit', 'Edit')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteThreshold(record.id)}
          >
            {t('monitoring.delete', 'Delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const metricOptions = [
    { value: 'llm_response_time_ms', label: 'LLM Response Time (ms)' },
    { value: 'llm_error_rate', label: 'LLM Error Rate (%)' },
    { value: 'db_connection_failures', label: 'DB Connection Failures' },
    { value: 'db_query_time_ms', label: 'DB Query Time (ms)' },
    { value: 'sync_failure_count', label: 'Sync Failure Count' },
    { value: 'quota_usage_percent', label: 'Quota Usage (%)' },
    { value: 'api_latency_ms', label: 'API Latency (ms)' },
    { value: 'memory_usage_percent', label: 'Memory Usage (%)' },
  ];

  return (
    <div className="monitoring-config">
      <Row gutter={16}>
        <Col span={24}>
          {/* Alert Thresholds Card */}
          <Card
            title={
              <Space>
                <BellOutlined />
                {t('monitoring.alertThresholds', 'Alert Thresholds')}
              </Space>
            }
            extra={
              <Space>
                <Button
                  icon={<MailOutlined />}
                  onClick={() => setIsChannelModalVisible(true)}
                >
                  {t('monitoring.configureChannels', 'Configure Channels')}
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreateThreshold}
                >
                  {t('monitoring.addThreshold', 'Add Threshold')}
                </Button>
              </Space>
            }
          >
            <Alert
              message={t('monitoring.thresholdInfo', 'Alert thresholds define conditions that trigger notifications')}
              description={t(
                'monitoring.thresholdDescription',
                'Configure metrics, comparison operators, and threshold values. When conditions are met for the specified duration, alerts will be sent through the configured channels.'
              )}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Table
              columns={columns}
              dataSource={thresholds}
              loading={isLoading}
              rowKey="id"
              pagination={{
                showSizeChanger: true,
                showTotal: (total) => t('monitoring.totalThresholds', { total }),
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Threshold Modal */}
      <Modal
        title={editingThreshold
          ? t('monitoring.editThreshold', 'Edit Alert Threshold')
          : t('monitoring.createThreshold', 'Create Alert Threshold')
        }
        open={isThresholdModalVisible}
        onCancel={() => {
          setIsThresholdModalVisible(false);
          setEditingThreshold(null);
          thresholdForm.resetFields();
        }}
        onOk={() => thresholdForm.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form
          form={thresholdForm}
          layout="vertical"
          onFinish={handleThresholdSubmit}
        >
          <Form.Item
            name="metric_name"
            label={t('monitoring.form.metric', 'Metric')}
            rules={[{ required: true, message: t('monitoring.form.metricRequired', 'Please select a metric') }]}
          >
            <Select
              placeholder={t('monitoring.form.selectMetric', 'Select a metric')}
              options={metricOptions}
              showSearch
              allowClear
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="operator"
                label={t('monitoring.form.operator', 'Operator')}
                rules={[{ required: true, message: t('monitoring.form.operatorRequired', 'Please select an operator') }]}
              >
                <Select
                  placeholder={t('monitoring.form.selectOperator', 'Select operator')}
                  options={[
                    { value: 'gt', label: '> (Greater Than)' },
                    { value: 'gte', label: '>= (Greater Than or Equal)' },
                    { value: 'lt', label: '< (Less Than)' },
                    { value: 'lte', label: '<= (Less Than or Equal)' },
                    { value: 'eq', label: '= (Equal)' },
                    { value: 'neq', label: '!= (Not Equal)' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="value"
                label={t('monitoring.form.value', 'Threshold Value')}
                rules={[{ required: true, message: t('monitoring.form.valueRequired', 'Please enter a value') }]}
              >
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="duration_seconds"
                label={t('monitoring.form.duration', 'Duration (seconds)')}
                tooltip={t('monitoring.form.durationTooltip', 'How long the condition must be true before alerting. Set to 0 for immediate alerts.')}
              >
                <InputNumber style={{ width: '100%' }} min={0} max={3600} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="severity"
                label={t('monitoring.form.severity', 'Severity')}
                rules={[{ required: true, message: t('monitoring.form.severityRequired', 'Please select severity') }]}
              >
                <Select
                  options={[
                    { value: 'info', label: 'Info' },
                    { value: 'warning', label: 'Warning' },
                    { value: 'error', label: 'Error' },
                    { value: 'critical', label: 'Critical' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="channels"
            label={t('monitoring.form.channels', 'Notification Channels')}
            rules={[{ required: true, message: t('monitoring.form.channelsRequired', 'Please select at least one channel') }]}
          >
            <Select
              mode="multiple"
              placeholder={t('monitoring.form.selectChannels', 'Select channels')}
              options={[
                { value: 'email', label: 'Email' },
                { value: 'webhook', label: 'Webhook' },
                { value: 'sms', label: 'SMS' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="enabled"
            label={t('monitoring.form.enabled', 'Enabled')}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Channel Configuration Modal */}
      <Modal
        title={t('monitoring.channelConfig', 'Alert Channel Configuration')}
        open={isChannelModalVisible}
        onCancel={() => setIsChannelModalVisible(false)}
        footer={null}
        width={700}
      >
        <Tabs
          activeKey={activeChannelTab}
          onChange={setActiveChannelTab}
          items={[
            {
              key: 'email',
              label: (
                <span>
                  <MailOutlined />
                  {t('monitoring.channels.email', 'Email')}
                </span>
              ),
              children: (
                <Form form={emailForm} layout="vertical">
                  <Row gutter={16}>
                    <Col span={16}>
                      <Form.Item
                        name="smtp_host"
                        label={t('monitoring.email.smtpHost', 'SMTP Host')}
                        rules={[{ required: true }]}
                      >
                        <Input placeholder="smtp.example.com" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        name="smtp_port"
                        label={t('monitoring.email.smtpPort', 'SMTP Port')}
                        rules={[{ required: true }]}
                      >
                        <InputNumber style={{ width: '100%' }} placeholder="587" />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="smtp_user"
                        label={t('monitoring.email.username', 'Username')}
                        rules={[{ required: true }]}
                      >
                        <Input placeholder="user@example.com" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="smtp_password"
                        label={t('monitoring.email.password', 'Password')}
                        rules={[{ required: true }]}
                      >
                        <Input.Password />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item
                    name="from_address"
                    label={t('monitoring.email.fromAddress', 'From Address')}
                    rules={[{ required: true, type: 'email' }]}
                  >
                    <Input placeholder="alerts@example.com" />
                  </Form.Item>
                  <Form.Item
                    name="to_addresses"
                    label={t('monitoring.email.toAddresses', 'To Addresses')}
                    rules={[{ required: true }]}
                  >
                    <Select
                      mode="tags"
                      placeholder={t('monitoring.email.toAddressesPlaceholder', 'Enter email addresses')}
                    />
                  </Form.Item>
                  <Form.Item
                    name="use_tls"
                    label={t('monitoring.email.useTls', 'Use TLS')}
                    valuePropName="checked"
                    initialValue={true}
                  >
                    <Switch />
                  </Form.Item>
                  <Button type="primary" icon={<SaveOutlined />}>
                    {t('monitoring.saveConfig', 'Save Configuration')}
                  </Button>
                </Form>
              ),
            },
            {
              key: 'webhook',
              label: (
                <span>
                  <ApiOutlined />
                  {t('monitoring.channels.webhook', 'Webhook')}
                </span>
              ),
              children: (
                <Form form={webhookForm} layout="vertical">
                  <Form.Item
                    name="url"
                    label={t('monitoring.webhook.url', 'Webhook URL')}
                    rules={[{ required: true, type: 'url' }]}
                  >
                    <Input placeholder="https://example.com/webhook" />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Form.Item
                        name="method"
                        label={t('monitoring.webhook.method', 'HTTP Method')}
                        initialValue="POST"
                      >
                        <Select
                          options={[
                            { value: 'POST', label: 'POST' },
                            { value: 'PUT', label: 'PUT' },
                          ]}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        name="timeout"
                        label={t('monitoring.webhook.timeout', 'Timeout (s)')}
                        initialValue={30}
                      >
                        <InputNumber style={{ width: '100%' }} min={1} max={120} />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        name="retry_count"
                        label={t('monitoring.webhook.retryCount', 'Retries')}
                        initialValue={3}
                      >
                        <InputNumber style={{ width: '100%' }} min={0} max={5} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item
                    name="headers"
                    label={t('monitoring.webhook.headers', 'Custom Headers (JSON)')}
                  >
                    <Input.TextArea
                      rows={3}
                      placeholder='{"Authorization": "Bearer token"}'
                    />
                  </Form.Item>
                  <Button type="primary" icon={<SaveOutlined />}>
                    {t('monitoring.saveConfig', 'Save Configuration')}
                  </Button>
                </Form>
              ),
            },
            {
              key: 'sms',
              label: (
                <span>
                  <MobileOutlined />
                  {t('monitoring.channels.sms', 'SMS')}
                </span>
              ),
              children: (
                <Form form={smsForm} layout="vertical">
                  <Form.Item
                    name="provider"
                    label={t('monitoring.sms.provider', 'SMS Provider')}
                    rules={[{ required: true }]}
                  >
                    <Select
                      placeholder={t('monitoring.sms.selectProvider', 'Select provider')}
                      options={[
                        { value: 'twilio', label: 'Twilio' },
                        { value: 'alibaba', label: 'Alibaba Cloud SMS' },
                        { value: 'tencent', label: 'Tencent Cloud SMS' },
                      ]}
                    />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name="api_key"
                        label={t('monitoring.sms.apiKey', 'API Key')}
                        rules={[{ required: true }]}
                      >
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="api_secret"
                        label={t('monitoring.sms.apiSecret', 'API Secret')}
                      >
                        <Input.Password />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item
                    name="from_number"
                    label={t('monitoring.sms.fromNumber', 'From Number')}
                    rules={[{ required: true }]}
                  >
                    <Input placeholder="+1234567890" />
                  </Form.Item>
                  <Form.Item
                    name="to_numbers"
                    label={t('monitoring.sms.toNumbers', 'To Numbers')}
                    rules={[{ required: true }]}
                  >
                    <Select
                      mode="tags"
                      placeholder={t('monitoring.sms.toNumbersPlaceholder', 'Enter phone numbers')}
                    />
                  </Form.Item>
                  <Button type="primary" icon={<SaveOutlined />}>
                    {t('monitoring.saveConfig', 'Save Configuration')}
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
};

export default MonitoringConfig;
