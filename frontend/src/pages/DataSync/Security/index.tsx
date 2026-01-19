import React, { useState } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, message, Divider, Alert, Table, Tag } from 'antd';
import { SaveOutlined, ReloadOutlined, SafetyOutlined, KeyOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '@/services/api';

interface SecurityConfig {
  encryption: {
    enabled: boolean;
    algorithm: string;
    keyRotationInterval: number;
  };
  authentication: {
    required: boolean;
    method: string;
    tokenExpiration: number;
  };
  authorization: {
    enabled: boolean;
    defaultRole: string;
    strictMode: boolean;
  };
  audit: {
    enabled: boolean;
    logLevel: string;
    retentionDays: number;
  };
  dataProtection: {
    piiDetection: boolean;
    autoDesensitization: boolean;
    complianceMode: string;
  };
}

interface SecurityRule {
  id: string;
  name: string;
  type: 'encryption' | 'access' | 'audit' | 'compliance';
  enabled: boolean;
  description: string;
  conditions: string[];
  actions: string[];
  priority: number;
  createdAt: string;
}

const DataSyncSecurity: React.FC = () => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { t } = useTranslation(['dataSync', 'common']);

  const { data: config, isLoading } = useQuery({
    queryKey: ['data-sync-security-config'],
    queryFn: () => api.get('/api/v1/data-sync/security/config').then(res => res.data),
  });

  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ['data-sync-security-rules'],
    queryFn: () => api.get('/api/v1/data-sync/security/rules').then(res => res.data),
  });

  const updateConfigMutation = useMutation({
    mutationFn: (data: SecurityConfig) => api.put('/api/v1/data-sync/security/config', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sync-security-config'] });
      message.success(t('security.saveSuccess'));
    },
    onError: () => {
      message.error(t('security.saveError'));
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: () => api.post('/api/v1/data-sync/security/test'),
    onSuccess: (data) => {
      if (data.data.success) {
        message.success(t('security.testSuccess'));
      } else {
        message.error(`${t('security.testFailed')}: ${data.data.error}`);
      }
    },
    onError: () => {
      message.error(t('security.testFailed'));
    },
  });

  const handleSubmit = (values: SecurityConfig) => {
    updateConfigMutation.mutate(values);
  };

  const handleTest = () => {
    testConnectionMutation.mutate();
  };

  const ruleColumns: ColumnsType<SecurityRule> = [
    {
      title: t('security.rules.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('security.rules.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          encryption: 'blue',
          access: 'green',
          audit: 'orange',
          compliance: 'purple',
        };
        const labelKeys: Record<string, string> = {
          encryption: 'security.rules.encryption',
          access: 'security.rules.access',
          audit: 'security.rules.audit',
          compliance: 'security.rules.compliance',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{t(labelKeys[type])}</Tag>;
      },
    },
    {
      title: t('security.rules.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? t('common:enabled') : t('common:disabled')}
        </Tag>
      ),
    },
    {
      title: t('security.rules.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: number) => (
        <Tag color={priority >= 8 ? 'error' : priority >= 5 ? 'warning' : 'default'}>
          {priority}
        </Tag>
      ),
    },
    {
      title: t('security.rules.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('security.rules.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ];

  React.useEffect(() => {
    if (config) {
      form.setFieldsValue(config);
    }
  }, [config, form]);

  return (
    <div className="data-sync-security">
      <Alert
        message={t('security.configTitle')}
        description={t('security.configDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card
        title={t('security.title')}
        extra={
          <Space>
            <Button
              icon={<SafetyOutlined />}
              onClick={handleTest}
              loading={testConnectionMutation.isPending}
            >
              {t('security.testConnection')}
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['data-sync-security-config'] });
              }}
            >
              {t('security.reload')}
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => form.submit()}
              loading={updateConfigMutation.isPending}
            >
              {t('security.saveConfig')}
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          loading={isLoading}
        >
          {/* 加密配置 */}
          <Card type="inner" title={t('security.encryption.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['encryption', 'enabled']} valuePropName="checked">
              <Switch checkedChildren={t('common:enabled')} unCheckedChildren={t('common:disabled')} />
              <span style={{ marginLeft: 8 }}>{t('security.encryption.enabled')}</span>
            </Form.Item>
            
            <Form.Item
              name={['encryption', 'algorithm']}
              label={t('security.encryption.algorithm')}
            >
              <Select placeholder={t('security.encryption.algorithmPlaceholder')}>
                <Select.Option value="AES-256-GCM">AES-256-GCM</Select.Option>
                <Select.Option value="AES-128-GCM">AES-128-GCM</Select.Option>
                <Select.Option value="ChaCha20-Poly1305">ChaCha20-Poly1305</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name={['encryption', 'keyRotationInterval']}
              label={t('security.encryption.keyRotation')}
            >
              <Input type="number" min={1} max={365} placeholder="30" />
            </Form.Item>
          </Card>

          {/* 认证配置 */}
          <Card type="inner" title={t('security.authentication.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['authentication', 'required']} valuePropName="checked">
              <Switch checkedChildren={t('common:required')} unCheckedChildren={t('common:optional')} />
              <span style={{ marginLeft: 8 }}>{t('security.authentication.required')}</span>
            </Form.Item>
            
            <Form.Item
              name={['authentication', 'method']}
              label={t('security.authentication.method')}
            >
              <Select placeholder={t('security.authentication.methodPlaceholder')}>
                <Select.Option value="jwt">JWT Token</Select.Option>
                <Select.Option value="oauth2">OAuth 2.0</Select.Option>
                <Select.Option value="basic">Basic Auth</Select.Option>
                <Select.Option value="apikey">API Key</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name={['authentication', 'tokenExpiration']}
              label={t('security.authentication.tokenExpiration')}
            >
              <Input type="number" min={1} max={168} placeholder="24" />
            </Form.Item>
          </Card>

          {/* 授权配置 */}
          <Card type="inner" title={t('security.authorization.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['authorization', 'enabled']} valuePropName="checked">
              <Switch checkedChildren={t('common:enabled')} unCheckedChildren={t('common:disabled')} />
              <span style={{ marginLeft: 8 }}>{t('security.authorization.enabled')}</span>
            </Form.Item>
            
            <Form.Item
              name={['authorization', 'defaultRole']}
              label={t('security.authorization.defaultRole')}
            >
              <Select placeholder={t('security.authorization.defaultRolePlaceholder')}>
                <Select.Option value="viewer">{t('security.authorization.viewer')}</Select.Option>
                <Select.Option value="editor">{t('security.authorization.editor')}</Select.Option>
                <Select.Option value="admin">{t('security.authorization.admin')}</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item name={['authorization', 'strictMode']} valuePropName="checked">
              <Switch checkedChildren={t('common:strict')} unCheckedChildren={t('common:loose')} />
              <span style={{ marginLeft: 8 }}>{t('security.authorization.strictMode')}</span>
            </Form.Item>
          </Card>

          {/* 审计配置 */}
          <Card type="inner" title={t('security.audit.title')} style={{ marginBottom: 16 }}>
            <Form.Item name={['audit', 'enabled']} valuePropName="checked">
              <Switch checkedChildren={t('common:enabled')} unCheckedChildren={t('common:disabled')} />
              <span style={{ marginLeft: 8 }}>{t('security.audit.enabled')}</span>
            </Form.Item>
            
            <Form.Item
              name={['audit', 'logLevel']}
              label={t('security.audit.logLevel')}
            >
              <Select placeholder={t('security.audit.logLevelPlaceholder')}>
                <Select.Option value="debug">{t('security.audit.debug')}</Select.Option>
                <Select.Option value="info">{t('security.audit.info')}</Select.Option>
                <Select.Option value="warning">{t('security.audit.warning')}</Select.Option>
                <Select.Option value="error">{t('security.audit.error')}</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name={['audit', 'retentionDays']}
              label={t('security.audit.retentionDays')}
            >
              <Input type="number" min={1} max={3650} placeholder="90" />
            </Form.Item>
          </Card>

          {/* 数据保护配置 */}
          <Card type="inner" title={t('security.dataProtection.title')}>
            <Form.Item name={['dataProtection', 'piiDetection']} valuePropName="checked">
              <Switch checkedChildren={t('common:enabled')} unCheckedChildren={t('common:disabled')} />
              <span style={{ marginLeft: 8 }}>{t('security.dataProtection.piiDetection')}</span>
            </Form.Item>
            
            <Form.Item name={['dataProtection', 'autoDesensitization']} valuePropName="checked">
              <Switch checkedChildren={t('common:enabled')} unCheckedChildren={t('common:disabled')} />
              <span style={{ marginLeft: 8 }}>{t('security.dataProtection.autoDesensitization')}</span>
            </Form.Item>
            
            <Form.Item
              name={['dataProtection', 'complianceMode']}
              label={t('security.dataProtection.complianceMode')}
            >
              <Select placeholder={t('security.dataProtection.compliancePlaceholder')}>
                <Select.Option value="gdpr">{t('security.dataProtection.gdpr')}</Select.Option>
                <Select.Option value="ccpa">{t('security.dataProtection.ccpa')}</Select.Option>
                <Select.Option value="pipl">{t('security.dataProtection.pipl')}</Select.Option>
                <Select.Option value="custom">{t('security.dataProtection.custom')}</Select.Option>
              </Select>
            </Form.Item>
          </Card>
        </Form>
      </Card>

      {/* 安全规则 */}
      <Card title={t('security.rules.title')} style={{ marginTop: 16 }}>
        <Table
          columns={ruleColumns}
          dataSource={rules}
          loading={rulesLoading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => t('common.totalRecords', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>
    </div>
  );
};

export default DataSyncSecurity;