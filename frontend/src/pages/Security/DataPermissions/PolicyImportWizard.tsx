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
      message.error('LDAP import failed');
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
      message.error('OAuth import failed');
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
      message.error('Custom policy import failed');
    },
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: (sourceId: string) => dataPermissionApi.syncPolicies(sourceId),
    onSuccess: () => {
      message.success('Sync completed');
      queryClient.invalidateQueries({ queryKey: ['policySources'] });
    },
    onError: () => {
      message.error('Sync failed');
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
      title: 'Type',
      dataIndex: 'conflict_type',
      key: 'conflict_type',
      render: (type) => <Tag color="warning">{type}</Tag>,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Suggested Resolution',
      dataIndex: 'suggested_resolution',
      key: 'suggested_resolution',
    },
  ];

  const sourceColumns: ColumnsType<PolicySource> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Type',
      dataIndex: 'source_type',
      key: 'source_type',
      render: (type) => (
        <Tag color={type === 'ldap' ? 'blue' : type === 'oauth' ? 'green' : 'purple'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Tag color={active ? 'success' : 'default'}>{active ? 'Active' : 'Inactive'}</Tag>
      ),
    },
    {
      title: 'Last Sync',
      dataIndex: 'last_sync_at',
      key: 'last_sync_at',
      render: (date) => (date ? new Date(date).toLocaleString() : 'Never'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          icon={<SyncOutlined />}
          onClick={() => syncMutation.mutate(record.id)}
          loading={syncMutation.isPending}
        >
          Sync
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
          <h3>LDAP / Active Directory</h3>
          <p>Import users and groups from LDAP or Active Directory</p>
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card
          hoverable
          onClick={() => handleSelectType('oauth')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <ApiOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          <h3>OAuth / OIDC</h3>
          <p>Import permissions from OAuth or OpenID Connect provider</p>
        </Card>
      </Col>
      <Col xs={24} md={8}>
        <Card
          hoverable
          onClick={() => handleSelectType('custom')}
          style={{ textAlign: 'center', cursor: 'pointer' }}
        >
          <FileTextOutlined style={{ fontSize: 48, color: '#722ed1' }} />
          <h3>Custom Policy</h3>
          <p>Import from JSON or YAML policy files</p>
        </Card>
      </Col>
    </Row>
  );

  const renderLDAPConfig = () => (
    <Form form={ldapForm} layout="vertical">
      <Form.Item
        name="url"
        label="LDAP URL"
        rules={[{ required: true, message: 'Please enter LDAP URL' }]}
      >
        <Input placeholder="ldap://ldap.example.com:389" />
      </Form.Item>
      <Form.Item
        name="base_dn"
        label="Base DN"
        rules={[{ required: true, message: 'Please enter Base DN' }]}
      >
        <Input placeholder="dc=example,dc=com" />
      </Form.Item>
      <Form.Item
        name="bind_dn"
        label="Bind DN"
        rules={[{ required: true, message: 'Please enter Bind DN' }]}
      >
        <Input placeholder="cn=admin,dc=example,dc=com" />
      </Form.Item>
      <Form.Item
        name="bind_password"
        label="Bind Password"
        rules={[{ required: true, message: 'Please enter password' }]}
      >
        <Input.Password placeholder="Password" />
      </Form.Item>
      <Form.Item name="user_filter" label="User Filter">
        <Input placeholder="(objectClass=person)" />
      </Form.Item>
      <Form.Item name="group_filter" label="Group Filter">
        <Input placeholder="(objectClass=group)" />
      </Form.Item>
      <Form.Item name="use_ssl" label="Use SSL" valuePropName="checked" initialValue={true}>
        <Switch />
      </Form.Item>
      <Form.Item name="timeout" label="Timeout (seconds)" initialValue={30}>
        <Input type="number" />
      </Form.Item>
    </Form>
  );

  const renderOAuthConfig = () => (
    <Form form={oauthForm} layout="vertical">
      <Form.Item
        name="provider_url"
        label="Provider URL"
        rules={[{ required: true, message: 'Please enter provider URL' }]}
      >
        <Input placeholder="https://auth.example.com" />
      </Form.Item>
      <Form.Item
        name="client_id"
        label="Client ID"
        rules={[{ required: true, message: 'Please enter client ID' }]}
      >
        <Input placeholder="Client ID" />
      </Form.Item>
      <Form.Item
        name="client_secret"
        label="Client Secret"
        rules={[{ required: true, message: 'Please enter client secret' }]}
      >
        <Input.Password placeholder="Client Secret" />
      </Form.Item>
      <Form.Item name="scopes" label="Scopes">
        <Select mode="tags" placeholder="Add scopes">
          <Option value="openid">openid</Option>
          <Option value="profile">profile</Option>
          <Option value="email">email</Option>
          <Option value="groups">groups</Option>
        </Select>
      </Form.Item>
      <Form.Item name="use_pkce" label="Use PKCE" valuePropName="checked" initialValue={true}>
        <Switch />
      </Form.Item>
    </Form>
  );

  const renderCustomConfig = () => (
    <Form form={customForm} layout="vertical">
      <Form.Item
        name="format"
        label="Format"
        rules={[{ required: true, message: 'Please select format' }]}
        initialValue="json"
      >
        <Select>
          <Option value="json">JSON</Option>
          <Option value="yaml">YAML</Option>
        </Select>
      </Form.Item>
      <Form.Item
        name="content"
        label="Policy Content"
        rules={[{ required: true, message: 'Please enter policy content' }]}
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
          message="Review Configuration"
          description="Please review your configuration before importing."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Card title="Configuration Summary">
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
        title={importResult.success ? 'Import Successful' : 'Import Completed with Issues'}
        subTitle={`Imported: ${importResult.imported_count}, Updated: ${importResult.updated_count}, Skipped: ${importResult.skipped_count}`}
        extra={[
          <Button type="primary" key="new" onClick={handleReset}>
            Import Another
          </Button>,
        ]}
      >
        {importResult.conflicts.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <Divider>Conflicts ({importResult.conflicts.length})</Divider>
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
            <Divider>Errors ({importResult.errors.length})</Divider>
            {importResult.errors.map((error, index) => (
              <Alert key={index} message={error} type="error" style={{ marginBottom: 8 }} />
            ))}
          </div>
        )}
      </Result>
    );
  };

  const steps = [
    { title: 'Select Type', icon: <FileTextOutlined /> },
    { title: 'Configure', icon: <CloudServerOutlined /> },
    { title: 'Preview', icon: <CheckCircleOutlined /> },
    { title: 'Result', icon: <CheckCircleOutlined /> },
  ];

  const isImporting =
    ldapImportMutation.isPending ||
    oauthImportMutation.isPending ||
    customImportMutation.isPending;

  return (
    <div>
      {/* Existing Sources */}
      <Card title="Existing Policy Sources" style={{ marginBottom: 24 }}>
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
      <Card title="Import New Policy Source">
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
              <Button onClick={() => setCurrentStep(currentStep - 1)}>Previous</Button>
              {currentStep === 1 && (
                <Button type="primary" onClick={handleConfigSubmit}>
                  Next
                </Button>
              )}
              {currentStep === 2 && (
                <Button type="primary" onClick={handleImport} loading={isImporting}>
                  Import
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
