import React, { useState } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, message, Divider, Alert, Table, Tag } from 'antd';
import { SaveOutlined, ReloadOutlined, ShieldOutlined, KeyOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

  const { data: config, isLoading } = useQuery({
    queryKey: ['data-sync-security-config'],
    queryFn: () => api.get('/api/v1/data-sync/security/config').then(res => res.data),
  });

  const { data: rules, isLoading: rulesLoading } = useQuery({
    queryKey: ['data-sync-security-rules'],
    queryFn: () => api.get('/api/v1/data-sync/security/rules').then(res => res.data),
  });

  const updateConfigMutation = useMutation({
    mutationFn: (data: SecurityConfig) => api.put('/api/v1/data-sync/security/config', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sync-security-config'] });
      message.success('安全配置保存成功');
    },
    onError: () => {
      message.error('安全配置保存失败');
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: () => api.post('/api/v1/data-sync/security/test'),
    onSuccess: (data) => {
      if (data.data.success) {
        message.success('安全连接测试成功');
      } else {
        message.error(`安全连接测试失败: ${data.data.error}`);
      }
    },
    onError: () => {
      message.error('安全连接测试失败');
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
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          encryption: 'blue',
          access: 'green',
          audit: 'orange',
          compliance: 'purple',
        };
        const labels = {
          encryption: '加密',
          access: '访问控制',
          audit: '审计',
          compliance: '合规',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{labels[type as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: number) => (
        <Tag color={priority >= 8 ? 'error' : priority >= 5 ? 'warning' : 'default'}>
          {priority}
        </Tag>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '创建时间',
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
        message="数据同步安全配置"
        description="配置数据同步过程中的安全策略，包括加密、认证、授权和审计等功能。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card
        title="安全配置"
        extra={
          <Space>
            <Button
              icon={<ShieldOutlined />}
              onClick={handleTest}
              loading={testConnectionMutation.isPending}
            >
              测试安全连接
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['data-sync-security-config'] });
              }}
            >
              重新加载
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => form.submit()}
              loading={updateConfigMutation.isPending}
            >
              保存配置
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
          <Card type="inner" title="数据加密" style={{ marginBottom: 16 }}>
            <Form.Item name={['encryption', 'enabled']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>启用数据传输加密</span>
            </Form.Item>
            
            <Form.Item
              name={['encryption', 'algorithm']}
              label="加密算法"
            >
              <Select placeholder="请选择加密算法">
                <Select.Option value="AES-256-GCM">AES-256-GCM</Select.Option>
                <Select.Option value="AES-128-GCM">AES-128-GCM</Select.Option>
                <Select.Option value="ChaCha20-Poly1305">ChaCha20-Poly1305</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name={['encryption', 'keyRotationInterval']}
              label="密钥轮换间隔（天）"
            >
              <Input type="number" min={1} max={365} placeholder="30" />
            </Form.Item>
          </Card>

          {/* 认证配置 */}
          <Card type="inner" title="身份认证" style={{ marginBottom: 16 }}>
            <Form.Item name={['authentication', 'required']} valuePropName="checked">
              <Switch checkedChildren="必需" unCheckedChildren="可选" />
              <span style={{ marginLeft: 8 }}>要求身份认证</span>
            </Form.Item>
            
            <Form.Item
              name={['authentication', 'method']}
              label="认证方式"
            >
              <Select placeholder="请选择认证方式">
                <Select.Option value="jwt">JWT Token</Select.Option>
                <Select.Option value="oauth2">OAuth 2.0</Select.Option>
                <Select.Option value="basic">Basic Auth</Select.Option>
                <Select.Option value="apikey">API Key</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name={['authentication', 'tokenExpiration']}
              label="Token过期时间（小时）"
            >
              <Input type="number" min={1} max={168} placeholder="24" />
            </Form.Item>
          </Card>

          {/* 授权配置 */}
          <Card type="inner" title="访问授权" style={{ marginBottom: 16 }}>
            <Form.Item name={['authorization', 'enabled']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>启用访问控制</span>
            </Form.Item>
            
            <Form.Item
              name={['authorization', 'defaultRole']}
              label="默认角色"
            >
              <Select placeholder="请选择默认角色">
                <Select.Option value="viewer">查看者</Select.Option>
                <Select.Option value="editor">编辑者</Select.Option>
                <Select.Option value="admin">管理员</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item name={['authorization', 'strictMode']} valuePropName="checked">
              <Switch checkedChildren="严格" unCheckedChildren="宽松" />
              <span style={{ marginLeft: 8 }}>严格模式（拒绝未明确授权的访问）</span>
            </Form.Item>
          </Card>

          {/* 审计配置 */}
          <Card type="inner" title="安全审计" style={{ marginBottom: 16 }}>
            <Form.Item name={['audit', 'enabled']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>启用安全审计</span>
            </Form.Item>
            
            <Form.Item
              name={['audit', 'logLevel']}
              label="日志级别"
            >
              <Select placeholder="请选择日志级别">
                <Select.Option value="debug">调试</Select.Option>
                <Select.Option value="info">信息</Select.Option>
                <Select.Option value="warning">警告</Select.Option>
                <Select.Option value="error">错误</Select.Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name={['audit', 'retentionDays']}
              label="日志保留天数"
            >
              <Input type="number" min={1} max={3650} placeholder="90" />
            </Form.Item>
          </Card>

          {/* 数据保护配置 */}
          <Card type="inner" title="数据保护">
            <Form.Item name={['dataProtection', 'piiDetection']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>PII敏感信息检测</span>
            </Form.Item>
            
            <Form.Item name={['dataProtection', 'autoDesensitization']} valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              <span style={{ marginLeft: 8 }}>自动脱敏处理</span>
            </Form.Item>
            
            <Form.Item
              name={['dataProtection', 'complianceMode']}
              label="合规模式"
            >
              <Select placeholder="请选择合规模式">
                <Select.Option value="gdpr">GDPR</Select.Option>
                <Select.Option value="ccpa">CCPA</Select.Option>
                <Select.Option value="pipl">个人信息保护法</Select.Option>
                <Select.Option value="custom">自定义</Select.Option>
              </Select>
            </Form.Item>
          </Card>
        </Form>
      </Card>

      {/* 安全规则 */}
      <Card title="安全规则" style={{ marginTop: 16 }}>
        <Table
          columns={ruleColumns}
          dataSource={rules}
          loading={rulesLoading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  );
};

export default DataSyncSecurity;