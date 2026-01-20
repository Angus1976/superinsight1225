/**
 * Policy Import Wizard
 * 
 * Step-by-step wizard for importing external permission policies (LDAP/OAuth/Custom).
 */

import React, { useState } from 'react';
import {
  Card,
  Steps,
  Button,
  Form,
  Input,
  Select,
  Switch,
  Space,
  Alert,
  Table,
  Tag,
  Result,
  message,
  Divider,
  Typography,
  Row,
  Col,
} from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  dataPermissionApi,
  LDAPConfig,
  OAuthConfig,
  CustomPolicyConfig,
  ImportResult,
  PolicyConflict,
  PolicySource,
} from '@/services/dataPermissionApi';

const { Step } = Steps;
const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

type PolicyType = 'ldap' | 'oauth' | 'custom';

const PolicyImportWizard: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [currentStep, setCurrentStep] = useState(0);
  const [policyType, setPolicyType] = useState<PolicyType | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const [ldapForm] = Form.useForm();
  const [oauthForm] = Form.useForm();
  const [customForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch existing policy sources
  const { data: policySources, isLoading: sourcesLoading } = useQuery({
    queryKey: ['policySources'],
    queryFn: () => dataPermissionApi.listPolicySources(),
  });

  // Import mutations
  const ldapImportMutation = useMutation({
    mutationFn: (config: LDAPConfig) => dataPermissionApi.importLDAPPolicies(config),
    onSuccess: (result) => {
      setImportResult(result);
      setCurrentStep(3);
      queryClient.invalidateQueries({ queryKey: ['policySources'] });
    },
    onError: () => {
      message.error(t('dataPermissions.policyImport.ldapImportFailed'));
    },
  });

  const oauthImportMutation = useMutation({
    mutationFn: (config: OAuthConfig) => dataPermissionApi.importOAuthPolicies(config),
    onSuccess: (result) => {
      setImportResult(result);
      setCurrentStep(3);
      queryClient.invalidateQueries({ queryKey: ['policySources'] });
    },
    onError: () => {
      message.error(t('dataPermissions.policyImport.oauthImportFailed'));
    },
  });

  const customImportMutation = useMutation({
    mutationFn: (config: CustomPolicyConfig) => dataPermissionApi.importCustomPolicies(config),
    onSuccess: (result) => {
      setImportResult(result);
      setCurrentStep(3);
      queryClient.invalidateQueries({ queryKey: ['policySources'] });
    },
    onError: () => {
      message.error(t('dataPermissions.policyImport.customImportFailed'));
    },
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: (sourceId: string) => dataPermissionApi.syncPolicies(sourceId),
    onSuccess: () => {
      message.success(t('dataPermissions.policyImport.syncSuccess'));
      queryClient.invalidateQueries({ queryKey: ['policySources'] });
    },
    onError: () => {
      message.error(t('dataPermissions.policyImport.syncFailed'));
    },
  });

  const handleSelectType = (type: PolicyType) => {
    setPolicyType(type);
    setCurrentStep(1);
  };

  const handleConfigSubmit = () => {
    if (policyType === 'ldap') {
      ldapForm.validateFields().then((values) => {
        setCurrentStep(2);
      });
    } else if (policyType === 'oauth') {
      oauthForm.validateFields().then((values) => {
        setCurrentStep(2);
      });
    } else if (policyType === 'custom') {
      customForm.validateFields().then((values) => {
        setCurrentStep(2);
      });
    }
  };

  const handleImport = () => {
    if (policyType === 'ldap') {
      const values = ldapForm.getFieldsValue();
      ldapImportMutation.mutate(values);
    } else if (policyType === 'oauth') {
      const values = oauthForm.getFieldsValue();
      oauthImportMutation.mutate(values);
    } else if (policyType === 'custom') {
      const values = customForm.getFieldsValue();
      customImportMutation.mutate(values);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setPolicyType(null);
    setImportResult(null);
    ldapForm.resetFields();
    oauthForm.resetFields();
    customForm.resetFields();
  };

  const conflictColumns: ColumnsType<PolicyConflict> = [
    {
      title: t('audit.eventType'),
      dataIndex: 'conflict_type',
      key: 'conflict_type',
      render: (type) => <Tag color="warning">{type}</Tag>,
    },
    {
      title: t('permissions.columns.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('compliance.recommendations'),
      dataIndex: 'suggested_resolution',
      key: 'suggested_resolution',
    },
  ];

  const sourceColumns: ColumnsType<PolicySource> = [
    {
      title: t('sso.providerName'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('audit.eventType'),
      dataIndex: 'source_type',
      key: 'source_type',
      render: (type) => (
        <Tag color={type === 'ldap' ? 'blue' : type === 'oauth' ? 'green' : 'purple'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('sso.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Tag color={active ? 'success' : 'default'}>{active ? t('dataPermissions.masking.active') : t('dataPermissions.masking.inactive')}</Tag>
      ),
    },
    {
      title: t('sessions.columns.lastActivity'),
      dataIndex: 'last_sync_at',
      key: 'last_sync_at',
      render: (date) => (date ? new Date(date).toLocaleString() : t('sessions.neverLoggedIn')),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          icon={<SyncOutlined />}
          onClick={() => syncMutation.mutate(record.id)}
          loading={syncMutation.isPending}
        >
          {t('dataPermissions.policyImport.sync')}
        </Button>
      ),
    },
  ];

  const renderTypeSelection = () => (
    <Row gutter={24}>
      <Col xs={24} md={8}>
        <Card
          hoverable
          onClick={() => handleSelectType('ldap')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <CloudServerOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          <h3>{t('dataPermissions.policyImport.types.ldap')}</h3>
          <p>{t('dataPermissions.policyImport.types.ldapDesc')}</p>
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card
          hoverable
          onClick={() => handleSelectType('oauth')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <ApiOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          <h3>{t('dataPermissions.policyImport.types.oauth')}</h3>
          <p>{t('dataPermissions.policyImport.types.oauthDesc')}</p>
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card
          hoverable
          onClick={() => handleSelectType('custom')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <FileTextOutlined style={{ fontSize: 48, color: '#722ed1' }} />
          <h3>{t('dataPermissions.policyImport.types.custom')}</h3>
          <p>{t('dataPermissions.policyImport.types.customDesc')}</p>
        </Card>
      </Col>
    </Row>
  );

  const renderLDAPConfig = () => (
    <Form form={ldapForm} layout="vertical">
      <Form.Item
        name="url"
        label={t('dataPermissions.policyImport.ldapConfig.url')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.ldapConfig.url') }]}
      >
        <Input placeholder="ldap://ldap.example.com:389" />
      </Form.Item>
      <Form.Item
        name="base_dn"
        label={t('dataPermissions.policyImport.ldapConfig.baseDn')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.ldapConfig.baseDn') }]}
      >
        <Input placeholder="dc=example,dc=com" />
      </Form.Item>
      <Form.Item
        name="bind_dn"
        label={t('dataPermissions.policyImport.ldapConfig.bindDn')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.ldapConfig.bindDn') }]}
      >
        <Input placeholder="cn=admin,dc=example,dc=com" />
      </Form.Item>
      <Form.Item
        name="bind_password"
        label={t('dataPermissions.policyImport.ldapConfig.bindPassword')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.ldapConfig.bindPassword') }]}
      >
        <Input.Password placeholder={t('dataPermissions.policyImport.ldapConfig.bindPassword')} />
      </Form.Item>
      <Form.Item name="user_filter" label={t('dataPermissions.policyImport.ldapConfig.userFilter')}>
        <Input placeholder="(objectClass=person)" />
      </Form.Item>
      <Form.Item name="group_filter" label={t('dataPermissions.policyImport.ldapConfig.groupFilter')}>
        <Input placeholder="(objectClass=group)" />
      </Form.Item>
      <Form.Item name="use_ssl" label={t('dataPermissions.policyImport.ldapConfig.useSsl')} valuePropName="checked" initialValue={true}>
        <Switch />
      </Form.Item>
      <Form.Item name="timeout" label={t('dataPermissions.policyImport.ldapConfig.timeout')} initialValue={30}>
        <Input type="number" />
      </Form.Item>
    </Form>
  );

  const renderOAuthConfig = () => (
    <Form form={oauthForm} layout="vertical">
      <Form.Item
        name="provider_url"
        label={t('dataPermissions.policyImport.oauthConfig.providerUrl')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.oauthConfig.providerUrl') }]}
      >
        <Input placeholder="https://auth.example.com" />
      </Form.Item>
      <Form.Item
        name="client_id"
        label={t('dataPermissions.policyImport.oauthConfig.clientId')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.oauthConfig.clientId') }]}
      >
        <Input placeholder={t('dataPermissions.policyImport.oauthConfig.clientId')} />
      </Form.Item>
      <Form.Item
        name="client_secret"
        label={t('dataPermissions.policyImport.oauthConfig.clientSecret')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.oauthConfig.clientSecret') }]}
      >
        <Input.Password placeholder={t('dataPermissions.policyImport.oauthConfig.clientSecret')} />
      </Form.Item>
      <Form.Item name="scopes" label={t('dataPermissions.policyImport.oauthConfig.scopes')}>
        <Select mode="tags" placeholder={t('dataPermissions.policyImport.oauthConfig.scopes')}>
          <Option value="openid">openid</Option>
          <Option value="profile">profile</Option>
          <Option value="email">email</Option>
          <Option value="groups">groups</Option>
        </Select>
      </Form.Item>
      <Form.Item name="use_pkce" label={t('dataPermissions.policyImport.oauthConfig.usePkce')} valuePropName="checked" initialValue={true}>
        <Switch />
      </Form.Item>
    </Form>
  );

  const renderCustomConfig = () => (
    <Form form={customForm} layout="vertical">
      <Form.Item
        name="format"
        label={t('dataPermissions.policyImport.customConfig.format')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.customConfig.format') }]}
        initialValue="json"
      >
        <Select>
          <Option value="json">JSON</Option>
          <Option value="yaml">YAML</Option>
        </Select>
      </Form.Item>
      <Form.Item
        name="content"
        label={t('dataPermissions.policyImport.customConfig.content')}
        rules={[{ required: true, message: t('dataPermissions.policyImport.customConfig.content') }]}
      >
        <TextArea
          rows={12}
          placeholder={`{
  "policies": [
    {
      "name": "data_reader",
      "permissions": ["read"],
      "resources": ["dataset:*"]
    }
  ]
}`}
        />
      </Form.Item>
    </Form>
  );

  const renderConfigStep = () => {
    if (policyType === 'ldap') return renderLDAPConfig();
    if (policyType === 'oauth') return renderOAuthConfig();
    if (policyType === 'custom') return renderCustomConfig();
    return null;
  };

  const renderPreview = () => {
    const getFormValues = () => {
      if (policyType === 'ldap') return ldapForm.getFieldsValue();
      if (policyType === 'oauth') return oauthForm.getFieldsValue();
      if (policyType === 'custom') return customForm.getFieldsValue();
      return {};
    };

    const values = getFormValues();

    return (
      <div>
        <Alert
          message={t('dataPermissions.policyImport.reviewConfig')}
          description={t('dataPermissions.policyImport.reviewConfigDesc')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Card title={t('dataPermissions.policyImport.configSummary')}>
          <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
            {JSON.stringify(
              { ...values, bind_password: '***', client_secret: '***' },
              null,
              2
            )}
          </pre>
        </Card>
      </div>
    );
  };

  const renderResult = () => {
    if (!importResult) return null;

    return (
      <Result
        status={importResult.success ? 'success' : 'warning'}
        title={importResult.success ? t('dataPermissions.policyImport.importSuccess') : t('dataPermissions.policyImport.importWithIssues')}
        subTitle={t('dataPermissions.policyImport.importStats', { imported: importResult.imported_count, updated: importResult.updated_count, skipped: importResult.skipped_count })}
        extra={[
          <Button type="primary" key="new" onClick={handleReset}>
            {t('dataPermissions.policyImport.importAnother')}
          </Button>,
        ]}
      >
        {importResult.conflicts.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <Divider>{t('dataPermissions.policyImport.conflicts')} ({importResult.conflicts.length})</Divider>
            <Table
              columns={conflictColumns}
              dataSource={importResult.conflicts}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </div>
        )}
        {importResult.errors.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <Divider>{t('dataPermissions.policyImport.errors')} ({importResult.errors.length})</Divider>
            {importResult.errors.map((error, index) => (
              <Alert key={index} message={error} type="error" style={{ marginBottom: 8 }} />
            ))}
          </div>
        )}
      </Result>
    );
  };

  const steps = [
    { title: t('dataPermissions.policyImport.steps.selectType'), icon: <FileTextOutlined /> },
    { title: t('dataPermissions.policyImport.steps.configure'), icon: <CloudServerOutlined /> },
    { title: t('dataPermissions.policyImport.steps.preview'), icon: <CheckCircleOutlined /> },
    { title: t('dataPermissions.policyImport.steps.result'), icon: <CheckCircleOutlined /> },
  ];

  const isImporting =
    ldapImportMutation.isPending ||
    oauthImportMutation.isPending ||
    customImportMutation.isPending;

  return (
    <div>
      {/* Existing Sources */}
      <Card title={t('dataPermissions.policyImport.existingSources')} style={{ marginBottom: 24 }}>
        <Table
          columns={sourceColumns}
          dataSource={policySources || []}
          rowKey="id"
          loading={sourcesLoading}
          size="small"
          pagination={false}
        />
      </Card>

      {/* Import Wizard */}
      <Card title={t('dataPermissions.policyImport.title')}>
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          {steps.map((step) => (
            <Step key={step.title} title={step.title} icon={step.icon} />
          ))}
        </Steps>

        <div style={{ minHeight: 300 }}>
          {currentStep === 0 && renderTypeSelection()}
          {currentStep === 1 && renderConfigStep()}
          {currentStep === 2 && renderPreview()}
          {currentStep === 3 && renderResult()}
        </div>

        {currentStep > 0 && currentStep < 3 && (
          <div style={{ marginTop: 24, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCurrentStep(currentStep - 1)}>{t('common:previous')}</Button>
              {currentStep === 1 && (
                <Button type="primary" onClick={handleConfigSubmit}>
                  {t('common:next')}
                </Button>
              )}
              {currentStep === 2 && (
                <Button type="primary" onClick={handleImport} loading={isImporting}>
                  {t('common:import')}
                </Button>
              )}
            </Space>
          </div>
        )}
      </Card>
    </div>
  );
};

export default PolicyImportWizard;
