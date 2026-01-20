/**
 * SSO Configuration Page
 */

import React, { useState } from 'react';
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
  message,
  Popconfirm,
  Typography,
  Tabs,
  Alert,
  Descriptions,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  ApiOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  ssoApi,
  SSOProvider,
  SSOProtocol,
  CreateSSOProviderRequest,
  SSOProviderConfig,
} from '@/services/ssoApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const protocolLabels: Record<SSOProtocol, string> = {
  saml: 'SAML 2.0',
  oauth2: 'OAuth 2.0',
  oidc: 'OpenID Connect',
  ldap: 'LDAP/AD',
};

const protocolColors: Record<SSOProtocol, string> = {
  saml: 'purple',
  oauth2: 'blue',
  oidc: 'cyan',
  ldap: 'orange',
};

const SSOConfig: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<SSOProvider | null>(null);
  const [selectedProtocol, setSelectedProtocol] = useState<SSOProtocol>('oidc');
  const [testResult, setTestResult] = useState<{ success: boolean; message?: string } | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch providers
  const { data: providers = [], isLoading } = useQuery({
    queryKey: ['ssoProviders'],
    queryFn: () => ssoApi.listProviders(),
  });

  // Create provider mutation
  const createMutation = useMutation({
    mutationFn: (data: CreateSSOProviderRequest) => ssoApi.createProvider(data),
    onSuccess: () => {
      message.success(t('sso.createSuccess'));
      queryClient.invalidateQueries({ queryKey: ['ssoProviders'] });
      handleCloseModal();
    },
    onError: () => {
      message.error(t('sso.createFailed'));
    },
  });

  // Update provider mutation
  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: Partial<CreateSSOProviderRequest> }) =>
      ssoApi.updateProvider(name, data),
    onSuccess: () => {
      message.success(t('sso.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['ssoProviders'] });
      handleCloseModal();
    },
    onError: () => {
      message.error(t('sso.updateFailed'));
    },
  });

  // Delete provider mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) => ssoApi.deleteProvider(name),
    onSuccess: () => {
      message.success(t('sso.deleteSuccess'));
      queryClient.invalidateQueries({ queryKey: ['ssoProviders'] });
    },
    onError: () => {
      message.error(t('sso.deleteFailed'));
    },
  });

  // Toggle provider mutation
  const toggleMutation = useMutation({
    mutationFn: ({ name, enable }: { name: string; enable: boolean }) =>
      enable ? ssoApi.enableProvider(name) : ssoApi.disableProvider(name),
    onSuccess: () => {
      message.success(t('sso.statusUpdated'));
      queryClient.invalidateQueries({ queryKey: ['ssoProviders'] });
    },
    onError: () => {
      message.error(t('sso.statusUpdateFailed'));
    },
  });

  // Test provider mutation
  const testMutation = useMutation({
    mutationFn: (name: string) => ssoApi.testProvider(name),
    onSuccess: (result) => {
      setTestResult(result);
      if (result.success) {
        message.success(t('sso.testPassed'));
      } else {
        message.error(`${t('sso.testFailed')}: ${result.error}`);
      }
    },
    onError: () => {
      message.error(t('sso.testFailed'));
    },
  });

  const handleOpenModal = (provider?: SSOProvider) => {
    if (provider) {
      setEditingProvider(provider);
      setSelectedProtocol(provider.protocol);
      form.setFieldsValue({
        name: provider.name,
        protocol: provider.protocol,
        enabled: provider.enabled,
      });
    } else {
      setEditingProvider(null);
      setSelectedProtocol('oidc');
      form.resetFields();
    }
    setTestResult(null);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditingProvider(null);
    setTestResult(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      const config: SSOProviderConfig = {};
      
      // Build config based on protocol
      if (selectedProtocol === 'saml') {
        config.entity_id = values.entity_id;
        config.idp_metadata_url = values.idp_metadata_url;
        config.idp_sso_url = values.idp_sso_url;
        config.idp_certificate = values.idp_certificate;
      } else if (selectedProtocol === 'oauth2' || selectedProtocol === 'oidc') {
        config.client_id = values.client_id;
        config.client_secret = values.client_secret;
        config.authorization_url = values.authorization_url;
        config.token_url = values.token_url;
        config.userinfo_url = values.userinfo_url;
        config.scopes = values.scopes?.split(',').map((s: string) => s.trim());
      } else if (selectedProtocol === 'ldap') {
        config.server_url = values.server_url;
        config.bind_dn = values.bind_dn;
        config.bind_password = values.bind_password;
        config.base_dn = values.base_dn;
        config.user_search_filter = values.user_search_filter;
      }

      const data: CreateSSOProviderRequest = {
        name: values.name,
        protocol: selectedProtocol,
        config,
        enabled: values.enabled ?? true,
      };

      if (editingProvider) {
        updateMutation.mutate({ name: editingProvider.name, data });
      } else {
        createMutation.mutate(data);
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const columns: ColumnsType<SSOProvider> = [
    {
      title: t('sso.providerName'),
      dataIndex: 'name',
      key: 'name',
      render: (name) => (
        <Space>
          <SafetyCertificateOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: t('sso.protocol'),
      dataIndex: 'protocol',
      key: 'protocol',
      render: (protocol: SSOProtocol) => (
        <Tag color={protocolColors[protocol]}>{t(`sso.protocols.${protocol}`)}</Tag>
      ),
    },
    {
      title: t('sso.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) =>
            toggleMutation.mutate({ name: record.name, enable: checked })
          }
          checkedChildren={<CheckCircleOutlined />}
          unCheckedChildren={<CloseCircleOutlined />}
        />
      ),
    },
    {
      title: t('common:createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('sso.testConnection')}>
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => testMutation.mutate(record.name)}
              loading={testMutation.isPending}
            />
          </Tooltip>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          />
          <Popconfirm
            title={t('sso.deleteConfirm')}
            onConfirm={() => deleteMutation.mutate(record.name)}
            okText={t('common:delete')}
            cancelText={t('common:cancel')}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const renderConfigFields = () => {
    switch (selectedProtocol) {
      case 'saml':
        return (
          <>
            <Form.Item name="entity_id" label={t('sso.form.entityId')} rules={[{ required: true }]}>
              <Input placeholder="https://your-app.com/saml/metadata" />
            </Form.Item>
            <Form.Item name="idp_metadata_url" label={t('sso.form.idpMetadataUrl')}>
              <Input placeholder="https://idp.example.com/metadata" />
            </Form.Item>
            <Form.Item name="idp_sso_url" label={t('sso.form.idpSsoUrl')} rules={[{ required: true }]}>
              <Input placeholder="https://idp.example.com/sso" />
            </Form.Item>
            <Form.Item name="idp_certificate" label={t('sso.form.idpCertificate')}>
              <TextArea rows={4} placeholder="-----BEGIN CERTIFICATE-----..." />
            </Form.Item>
          </>
        );
      case 'oauth2':
      case 'oidc':
        return (
          <>
            <Form.Item name="client_id" label={t('sso.form.clientId')} rules={[{ required: true }]}>
              <Input placeholder="your-client-id" />
            </Form.Item>
            <Form.Item name="client_secret" label={t('sso.form.clientSecret')} rules={[{ required: true }]}>
              <Input.Password placeholder="your-client-secret" />
            </Form.Item>
            <Form.Item name="authorization_url" label={t('sso.form.authorizationUrl')} rules={[{ required: true }]}>
              <Input placeholder="https://provider.com/oauth/authorize" />
            </Form.Item>
            <Form.Item name="token_url" label={t('sso.form.tokenUrl')} rules={[{ required: true }]}>
              <Input placeholder="https://provider.com/oauth/token" />
            </Form.Item>
            <Form.Item name="userinfo_url" label={t('sso.form.userinfoUrl')}>
              <Input placeholder="https://provider.com/oauth/userinfo" />
            </Form.Item>
            <Form.Item name="scopes" label={t('sso.form.scopes')}>
              <Input placeholder="openid, profile, email" />
            </Form.Item>
          </>
        );
      case 'ldap':
        return (
          <>
            <Form.Item name="server_url" label={t('sso.form.serverUrl')} rules={[{ required: true }]}>
              <Input placeholder="ldap://ldap.example.com:389" />
            </Form.Item>
            <Form.Item name="bind_dn" label={t('sso.form.bindDn')} rules={[{ required: true }]}>
              <Input placeholder="cn=admin,dc=example,dc=com" />
            </Form.Item>
            <Form.Item name="bind_password" label={t('sso.form.bindPassword')} rules={[{ required: true }]}>
              <Input.Password placeholder="password" />
            </Form.Item>
            <Form.Item name="base_dn" label={t('sso.form.baseDn')} rules={[{ required: true }]}>
              <Input placeholder="dc=example,dc=com" />
            </Form.Item>
            <Form.Item name="user_search_filter" label={t('sso.form.userSearchFilter')}>
              <Input placeholder="(uid={username})" />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SafetyCertificateOutlined /> {t('sso.title')}
      </Title>

      <Alert
        message={t('sso.title')}
        description={t('sso.description')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
            {t('sso.addProvider')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={providers}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showTotal: (total) => t('common.totalProviders', { total }),
          }}
        />
      </Card>

      <Modal
        title={editingProvider ? t('sso.editProvider') : t('sso.addProvider')}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleCloseModal}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('sso.providerName')}
            rules={[{ required: true, message: t('common:pleaseInput', { field: t('sso.providerName') }) }]}
          >
            <Input placeholder={t('sso.form.namePlaceholder')} disabled={!!editingProvider} />
          </Form.Item>

          <Form.Item name="protocol" label={t('sso.protocol')} initialValue="oidc">
            <Select
              value={selectedProtocol}
              onChange={setSelectedProtocol}
              disabled={!!editingProvider}
              options={[
                { label: `${t('sso.protocols.oidc')} (Recommended)`, value: 'oidc' },
                { label: t('sso.protocols.oauth2'), value: 'oauth2' },
                { label: t('sso.protocols.saml'), value: 'saml' },
                { label: t('sso.protocols.ldap'), value: 'ldap' },
              ]}
            />
          </Form.Item>

          <Form.Item name="enabled" label={t('permissions.enabled')} valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>

          {renderConfigFields()}

          {testResult && (
            <Alert
              message={testResult.success ? t('sso.testPassed') : t('sso.testFailed')}
              description={testResult.message}
              type={testResult.success ? 'success' : 'error'}
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default SSOConfig;
