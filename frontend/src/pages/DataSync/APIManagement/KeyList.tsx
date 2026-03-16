import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  InputNumber,
  Checkbox,
  message,
  Tooltip,
  Typography,
  Alert,
  Popconfirm,
  Badge,
  Divider
} from 'antd';
import {
  PlusOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  EyeOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

const { Text, Paragraph } = Typography;

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  raw_key?: string;
  scopes: Record<string, boolean>;
  status: string;
  rate_limit_per_minute: number;
  rate_limit_per_day: number;
  expires_at?: string;
  created_at: string;
  last_used_at?: string;
  total_calls: number;
  allowed_request_types?: string[];
  skill_whitelist?: string[];
  webhook_config?: {
    webhook_url: string;
    webhook_secret: string;
    webhook_events: string[];
  } | null;
}

const KeyList: React.FC = () => {
  const { t } = useTranslation('dataSync');
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [keyCreatedModalVisible, setKeyCreatedModalVisible] = useState(false);
  const [createdKey, setCreatedKey] = useState<APIKey | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const response = await axios.get('/api/v1/sync/api-keys/');
      setKeys(response.data);
    } catch (error) {
      message.error(t('apiManagement.createError'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (values: any) => {
    try {
      const scopes: Record<string, boolean> = {
        annotations: values.scopes?.includes('annotations') || false,
        augmented_data: values.scopes?.includes('augmented_data') || false,
        quality_reports: values.scopes?.includes('quality_reports') || false,
        experiments: values.scopes?.includes('experiments') || false
      };

      const skillWhitelist = values.skill_whitelist
        ? values.skill_whitelist.split(',').map((s: string) => s.trim()).filter(Boolean)
        : [];

      const response = await axios.post('/api/v1/sync/api-keys/', {
        name: values.name,
        description: values.description,
        scopes,
        expires_in_days: values.expires_in_days,
        rate_limit_per_minute: values.rate_limit_per_minute || 60,
        rate_limit_per_day: values.rate_limit_per_day || 10000,
        allowed_request_types: values.allowed_request_types || [],
        skill_whitelist: skillWhitelist,
        webhook_config: null
      });

      setCreatedKey(response.data);
      setCreateModalVisible(false);
      setKeyCreatedModalVisible(true);
      form.resetFields();
      fetchKeys();
      message.success(t('apiManagement.createSuccess'));
    } catch (error) {
      message.error(t('apiManagement.createError'));
    }
  };

  const handleEnableKey = async (keyId: string) => {
    try {
      await axios.post(`/api/v1/sync/api-keys/${keyId}/enable`);
      message.success(t('apiManagement.enableSuccess'));
      fetchKeys();
    } catch (error) {
      message.error(t('apiManagement.enableError'));
    }
  };

  const handleDisableKey = async (keyId: string) => {
    try {
      await axios.post(`/api/v1/sync/api-keys/${keyId}/disable`);
      message.success(t('apiManagement.disableSuccess'));
      fetchKeys();
    } catch (error) {
      message.error(t('apiManagement.disableError'));
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    try {
      await axios.post(`/api/v1/sync/api-keys/${keyId}/revoke`);
      message.success(t('apiManagement.revokeSuccess'));
      fetchKeys();
    } catch (error) {
      message.error(t('apiManagement.revokeError'));
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success(t('apiManagement.keyCopied'));
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      active: { color: 'success', text: t('status.active') },
      disabled: { color: 'default', text: t('status.inactive') },
      revoked: { color: 'error', text: t('status.failed') }
    };
    const config = statusMap[status] || statusMap.active;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const requestTypeNames: Record<string, string> = {
    query: t('apiManagement.requestTypeQuery'),
    chat: t('apiManagement.requestTypeChat'),
    decision: t('apiManagement.requestTypeDecision'),
    skill: t('apiManagement.requestTypeSkill')
  };

  const getRequestTypesList = (types?: string[]) => {
    if (!types?.length) return '-';
    return types.map((type) => (
      <Tag key={type} color="green">
        {requestTypeNames[type] || type}
      </Tag>
    ));
  };

  const getScopesList = (scopes: Record<string, boolean>) => {
    const scopeNames: Record<string, string> = {
      annotations: t('apiManagement.scopeAnnotations'),
      augmented_data: t('apiManagement.scopeAugmentedData'),
      quality_reports: t('apiManagement.scopeQualityReports'),
      experiments: t('apiManagement.scopeExperiments')
    };

    return Object.entries(scopes)
      .filter(([_, enabled]) => enabled)
      .map(([scope, _]) => (
        <Tag key={scope} color="blue">
          {scopeNames[scope] || scope}
        </Tag>
      ));
  };

  const columns = [
    {
      title: t('apiManagement.keyName'),
      dataIndex: 'name',
      key: 'name',
      width: 200
    },
    {
      title: t('apiManagement.keyPrefix'),
      dataIndex: 'key_prefix',
      key: 'key_prefix',
      width: 150,
      render: (prefix: string) => <Text code>{prefix}...</Text>
    },
    {
      title: t('apiManagement.scopes'),
      dataIndex: 'scopes',
      key: 'scopes',
      width: 300,
      render: (scopes: Record<string, boolean>) => getScopesList(scopes)
    },
    {
      title: t('apiManagement.allowedRequestTypes'),
      dataIndex: 'allowed_request_types',
      key: 'allowed_request_types',
      width: 280,
      render: (types: string[]) => getRequestTypesList(types)
    },
    {
      title: t('status.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status)
    },
    {
      title: t('apiManagement.rateLimit'),
      key: 'rate_limit',
      width: 150,
      render: (_: any, record: APIKey) => (
        <Space direction="vertical" size={0}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.rate_limit_per_minute} {t('apiManagement.perMinute')}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.rate_limit_per_day} {t('apiManagement.perDay')}
          </Text>
        </Space>
      )
    },
    {
      title: t('apiManagement.totalCalls'),
      dataIndex: 'total_calls',
      key: 'total_calls',
      width: 120,
      render: (calls: number) => calls.toLocaleString()
    },
    {
      title: t('apiManagement.lastUsed'),
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 180,
      render: (date: string) =>
        date ? new Date(date).toLocaleString() : t('dataSource.neverSynced')
    },
    {
      title: t('apiManagement.actions'),
      key: 'actions',
      width: 200,
      fixed: 'right' as const,
      render: (_: any, record: APIKey) => (
        <Space size="small">
          {record.status === 'active' && (
            <Tooltip title={t('apiManagement.disable')}>
              <Button
                type="text"
                size="small"
                icon={<StopOutlined />}
                onClick={() => handleDisableKey(record.id)}
              />
            </Tooltip>
          )}
          {record.status === 'disabled' && (
            <Tooltip title={t('apiManagement.enable')}>
              <Button
                type="text"
                size="small"
                icon={<CheckCircleOutlined />}
                onClick={() => handleEnableKey(record.id)}
              />
            </Tooltip>
          )}
          {record.status !== 'revoked' && (
            <Popconfirm
              title={t('apiManagement.revokeConfirm')}
              description={t('apiManagement.revokeWarning')}
              onConfirm={() => handleRevokeKey(record.id)}
              okText={t('common:confirm')}
              cancelText={t('common:cancel')}
            >
              <Tooltip title={t('apiManagement.revoke')}>
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ];

  return (
    <div>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Alert
            message={t('apiManagement.description')}
            type="info"
            showIcon
            style={{ flex: 1, marginRight: 16 }}
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            {t('apiManagement.createKey')}
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={keys}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1700 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `${t('common:total')} ${total} ${t('common:items')}`
          }}
        />
      </Space>

      {/* Create Key Modal */}
      <Modal
        title={t('apiManagement.createKeyTitle')}
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateKey}
        >
          <Form.Item
            name="name"
            label={t('apiManagement.keyName')}
            rules={[{ required: true, message: t('apiManagement.keyNamePlaceholder') }]}
          >
            <Input placeholder={t('apiManagement.keyNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('syncTask.description')}
          >
            <Input.TextArea
              rows={3}
              placeholder={t('apiManagement.descriptionPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="scopes"
            label={t('apiManagement.selectScopes')}
            rules={[{ required: true, message: t('apiManagement.selectScopes') }]}
          >
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical">
                <Checkbox value="annotations">{t('apiManagement.scopeAnnotations')}</Checkbox>
                <Checkbox value="augmented_data">{t('apiManagement.scopeAugmentedData')}</Checkbox>
                <Checkbox value="quality_reports">{t('apiManagement.scopeQualityReports')}</Checkbox>
                <Checkbox value="experiments">{t('apiManagement.scopeExperiments')}</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Divider />

          <Form.Item
            name="allowed_request_types"
            label={t('apiManagement.selectRequestTypes')}
          >
            <Checkbox.Group style={{ width: '100%' }}>
              <Space direction="vertical">
                <Checkbox value="query">{t('apiManagement.requestTypeQuery')}</Checkbox>
                <Checkbox value="chat">{t('apiManagement.requestTypeChat')}</Checkbox>
                <Checkbox value="decision">{t('apiManagement.requestTypeDecision')}</Checkbox>
                <Checkbox value="skill">{t('apiManagement.requestTypeSkill')}</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>

          <Form.Item
            name="skill_whitelist"
            label={t('apiManagement.skillWhitelist')}
          >
            <Input
              placeholder={t('apiManagement.skillWhitelistPlaceholder')}
            />
          </Form.Item>

          <Divider />

          <div style={{ position: 'relative', opacity: 0.6 }}>
            <Badge.Ribbon
              text={t('apiManagement.comingSoon')}
              color="orange"
            >
              <div style={{ padding: '12px', border: '1px dashed #d9d9d9', borderRadius: 8 }}>
                <Text strong style={{ display: 'block', marginBottom: 12 }}>
                  {t('apiManagement.webhookConfig')}
                </Text>
                <Form.Item
                  label={t('apiManagement.webhookUrl')}
                  style={{ marginBottom: 8 }}
                >
                  <Input
                    placeholder={t('apiManagement.webhookUrlPlaceholder')}
                    disabled
                  />
                </Form.Item>
                <Form.Item
                  label={t('apiManagement.webhookSecret')}
                  style={{ marginBottom: 8 }}
                >
                  <Input.Password
                    placeholder={t('apiManagement.webhookSecretPlaceholder')}
                    disabled
                  />
                </Form.Item>
                <Form.Item
                  label={t('apiManagement.webhookEvents')}
                  style={{ marginBottom: 0 }}
                >
                  <Checkbox.Group disabled style={{ width: '100%' }}>
                    <Space direction="vertical">
                      <Checkbox value="data_sync">{t('apiManagement.webhookEventDataSync')}</Checkbox>
                      <Checkbox value="data_export">{t('apiManagement.webhookEventExport')}</Checkbox>
                      <Checkbox value="alert">{t('apiManagement.webhookEventAlert')}</Checkbox>
                    </Space>
                  </Checkbox.Group>
                </Form.Item>
              </div>
            </Badge.Ribbon>
          </div>

          <Divider />

          <Form.Item
            name="expires_in_days"
            label={t('apiManagement.expiresInDays')}
          >
            <InputNumber
              min={1}
              style={{ width: '100%' }}
              placeholder={t('apiManagement.expiresInDaysPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="rate_limit_per_minute"
            label={t('apiManagement.rateLimitPerMinute')}
            initialValue={60}
          >
            <InputNumber min={1} max={1000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="rate_limit_per_day"
            label={t('apiManagement.rateLimitPerDay')}
            initialValue={10000}
          >
            <InputNumber min={1} max={1000000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Key Created Modal */}
      <Modal
        title={t('apiManagement.keyCreatedTitle')}
        open={keyCreatedModalVisible}
        onCancel={() => {
          setKeyCreatedModalVisible(false);
          setCreatedKey(null);
        }}
        footer={[
          <Button
            key="close"
            type="primary"
            onClick={() => {
              setKeyCreatedModalVisible(false);
              setCreatedKey(null);
            }}
          >
            {t('common:close')}
          </Button>
        ]}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message={t('apiManagement.keyCreatedMessage')}
            type="success"
            showIcon
          />

          {createdKey?.raw_key && (
            <div>
              <Paragraph
                copyable={{
                  text: createdKey.raw_key,
                  onCopy: () => copyToClipboard(createdKey.raw_key!)
                }}
                code
                style={{
                  padding: 12,
                  backgroundColor: '#f5f5f5',
                  borderRadius: 4,
                  wordBreak: 'break-all'
                }}
              >
                {createdKey.raw_key}
              </Paragraph>
            </div>
          )}

          <Alert
            message={t('apiManagement.keyWarning')}
            type="warning"
            showIcon
          />
        </Space>
      </Modal>
    </div>
  );
};

export default KeyList;
