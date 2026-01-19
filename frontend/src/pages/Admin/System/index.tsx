import React, { useState } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, message, Tabs, Statistic, Row, Col, Progress, Alert } from 'antd';
import { SaveOutlined, ReloadOutlined, DatabaseOutlined, CloudOutlined, SettingOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

interface SystemConfig {
  general: {
    siteName: string;
    siteDescription: string;
    adminEmail: string;
    timezone: string;
    language: string;
    maintenanceMode: boolean;
  };
  database: {
    host: string;
    port: number;
    name: string;
    maxConnections: number;
    connectionTimeout: number;
    queryTimeout: number;
  };
  cache: {
    enabled: boolean;
    type: string;
    host: string;
    port: number;
    ttl: number;
  };
  storage: {
    type: string;
    path: string;
    maxFileSize: number;
    allowedTypes: string[];
  };
  security: {
    sessionTimeout: number;
    passwordMinLength: number;
    passwordRequireSpecialChars: boolean;
    maxLoginAttempts: number;
    lockoutDuration: number;
  };
  email: {
    enabled: boolean;
    provider: string;
    host: string;
    port: number;
    username: string;
    password: string;
    encryption: string;
  };
}

interface SystemStatus {
  database: {
    status: 'healthy' | 'warning' | 'error';
    connections: number;
    maxConnections: number;
    responseTime: number;
  };
  cache: {
    status: 'healthy' | 'warning' | 'error';
    memoryUsage: number;
    hitRate: number;
  };
  storage: {
    status: 'healthy' | 'warning' | 'error';
    totalSpace: number;
    usedSpace: number;
    freeSpace: number;
  };
  system: {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    uptime: number;
  };
}

const AdminSystem: React.FC = () => {
  const { t } = useTranslation(['admin', 'common']);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('general');
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['system-config'],
    queryFn: () => api.get('/api/v1/admin/system/config').then(res => res.data),
  });

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: () => api.get('/api/v1/admin/system/status').then(res => res.data),
    refetchInterval: 30000, // 每30秒刷新一次
  });

  const updateConfigMutation = useMutation({
    mutationFn: (data: SystemConfig) => api.put('/api/v1/admin/system/config', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] });
      message.success(t('system.configSaveSuccess'));
    },
    onError: () => {
      message.error(t('system.configSaveFailed'));
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: (type: string) => api.post(`/api/v1/admin/system/test/${type}`),
    onSuccess: (data, type) => {
      if (data.data.success) {
        message.success(t('system.connectionTestSuccess', { type }));
      } else {
        message.error(t('system.connectionTestFailed', { type, error: data.data.error }));
      }
    },
    onError: (_, type) => {
      message.error(t('system.connectionTestFailed', { type }));
    },
  });

  const handleSubmit = (values: SystemConfig) => {
    updateConfigMutation.mutate(values);
  };

  React.useEffect(() => {
    if (config) {
      form.setFieldsValue(config);
    }
  }, [config, form]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#52c41a';
      case 'warning': return '#faad14';
      case 'error': return '#f5222d';
      default: return '#d9d9d9';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return t('system.status.healthy');
      case 'warning': return t('system.status.warning');
      case 'error': return t('system.status.error');
      default: return t('system.status.unknown');
    }
  };

  return (
    <div className="admin-system">
      {/* 系统状态概览 */}
      <Card title={t('system.statusOverview')} style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('system.database.title')}
                value={getStatusText(status?.database?.status || 'unknown')}
                valueStyle={{ color: getStatusColor(status?.database?.status || 'unknown') }}
                prefix={<DatabaseOutlined />}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                {t('system.database.connections')}: {status?.database?.connections || 0}/{status?.database?.maxConnections || 0}
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {t('system.database.responseTime')}: {status?.database?.responseTime || 0}ms
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('system.cache.title')}
                value={getStatusText(status?.cache?.status || 'unknown')}
                valueStyle={{ color: getStatusColor(status?.cache?.status || 'unknown') }}
                prefix={<CloudOutlined />}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                {t('system.cache.memoryUsage')}: {((status?.cache?.memoryUsage || 0) / 1024 / 1024).toFixed(2)}MB
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {t('system.cache.hitRate')}: {((status?.cache?.hitRate || 0) * 100).toFixed(1)}%
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('system.storage.title')}
                value={getStatusText(status?.storage?.status || 'unknown')}
                valueStyle={{ color: getStatusColor(status?.storage?.status || 'unknown') }}
                prefix={<SettingOutlined />}
              />
              <div style={{ marginTop: 8 }}>
                <Progress
                  percent={status?.storage ? (status.storage.usedSpace / status.storage.totalSpace) * 100 : 0}
                  size="small"
                />
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {((status?.storage?.usedSpace || 0) / 1024 / 1024 / 1024).toFixed(2)}GB / 
                {((status?.storage?.totalSpace || 0) / 1024 / 1024 / 1024).toFixed(2)}GB
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('system.systemLoad')}
                value={`${(status?.system?.cpuUsage || 0).toFixed(1)}%`}
                valueStyle={{ 
                  color: (status?.system?.cpuUsage || 0) > 80 ? '#f5222d' : 
                         (status?.system?.cpuUsage || 0) > 60 ? '#faad14' : '#52c41a'
                }}
              />
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  {t('system.memory')}: {(status?.system?.memoryUsage || 0).toFixed(1)}%
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  {t('system.disk')}: {(status?.system?.diskUsage || 0).toFixed(1)}%
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 系统配置 */}
      <Card
        title={t('system.configTitle')}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['system-config'] });
                queryClient.invalidateQueries({ queryKey: ['system-status'] });
              }}
            >
              {t('common:refresh')}
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => form.submit()}
              loading={updateConfigMutation.isPending}
            >
              {t('system.saveConfig')}
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
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            {/* 基本设置 */}
            <TabPane tab={t('system.general.title')} key="general">
              <Form.Item
                name={['general', 'siteName']}
                label={t('system.general.siteName')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder="SuperInsight AI Platform" />
              </Form.Item>
              
              <Form.Item
                name={['general', 'siteDescription']}
                label={t('system.general.siteDescription')}
              >
                <Input.TextArea rows={3} placeholder={t('common:placeholder.description')} />
              </Form.Item>
              
              <Form.Item
                name={['general', 'adminEmail']}
                label={t('system.general.adminEmail')}
                rules={[
                  { required: true, message: t('common:validation.required') },
                  { type: 'email', message: t('common:validation.email') },
                ]}
              >
                <Input placeholder="admin@example.com" />
              </Form.Item>
              
              <Form.Item
                name={['general', 'timezone']}
                label={t('system.general.timezone')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Select placeholder={t('common:placeholder.select')}>
                  <Select.Option value="Asia/Shanghai">{t('system.general.timezones.shanghai')}</Select.Option>
                  <Select.Option value="UTC">{t('system.general.timezones.utc')}</Select.Option>
                  <Select.Option value="America/New_York">{t('system.general.timezones.newYork')}</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['general', 'language']}
                label={t('system.general.language')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Select placeholder={t('common:placeholder.select')}>
                  <Select.Option value="zh-CN">{t('system.general.languages.zhCN')}</Select.Option>
                  <Select.Option value="en-US">{t('system.general.languages.enUS')}</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item name={['general', 'maintenanceMode']} valuePropName="checked">
                <Switch checkedChildren={t('common:on')} unCheckedChildren={t('common:off')} />
                <span style={{ marginLeft: 8 }}>{t('system.general.maintenanceMode')}</span>
              </Form.Item>
            </TabPane>

            {/* 数据库设置 */}
            <TabPane tab={t('system.database.title')} key="database">
              <Alert
                message={t('system.database.title')}
                description={t('system.database.configWarning')}
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
              
              <Form.Item
                name={['database', 'host']}
                label={t('system.database.host')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder="localhost" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'port']}
                label={t('system.database.port')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input type="number" placeholder="5432" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'name']}
                label={t('system.database.name')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder="superinsight" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'maxConnections']}
                label={t('system.database.maxConnections')}
              >
                <Input type="number" placeholder="100" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'connectionTimeout']}
                label={t('system.database.connectionTimeout')}
              >
                <Input type="number" placeholder="30" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'queryTimeout']}
                label={t('system.database.queryTimeout')}
              >
                <Input type="number" placeholder="60" />
              </Form.Item>
              
              <Button
                onClick={() => testConnectionMutation.mutate('database')}
                loading={testConnectionMutation.isPending}
              >
                {t('system.testDatabaseConnection')}
              </Button>
            </TabPane>

            {/* 缓存设置 */}
            <TabPane tab={t('system.cache.title')} key="cache">
              <Form.Item name={['cache', 'enabled']} valuePropName="checked">
                <Switch checkedChildren={t('common:enabled')} unCheckedChildren={t('common:disabled')} />
                <span style={{ marginLeft: 8 }}>{t('system.cache.enabled')}</span>
              </Form.Item>
              
              <Form.Item
                name={['cache', 'type']}
                label={t('system.cache.type')}
              >
                <Select placeholder={t('common:placeholder.select')}>
                  <Select.Option value="redis">{t('system.cache.types.redis')}</Select.Option>
                  <Select.Option value="memory">{t('system.cache.types.memory')}</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['cache', 'host']}
                label={t('system.cache.host')}
              >
                <Input placeholder="localhost" />
              </Form.Item>
              
              <Form.Item
                name={['cache', 'port']}
                label={t('system.cache.port')}
              >
                <Input type="number" placeholder="6379" />
              </Form.Item>
              
              <Form.Item
                name={['cache', 'ttl']}
                label={t('system.cache.ttl')}
              >
                <Input type="number" placeholder="3600" />
              </Form.Item>
              
              <Button
                onClick={() => testConnectionMutation.mutate('cache')}
                loading={testConnectionMutation.isPending}
              >
                {t('system.testCacheConnection')}
              </Button>
            </TabPane>

            {/* 安全设置 */}
            <TabPane tab={t('system.security.title')} key="security">
              <Form.Item
                name={['security', 'sessionTimeout']}
                label={t('system.security.sessionTimeout')}
              >
                <Input type="number" placeholder="30" />
              </Form.Item>
              
              <Form.Item
                name={['security', 'passwordMinLength']}
                label={t('system.security.passwordMinLength')}
              >
                <Input type="number" placeholder="8" />
              </Form.Item>
              
              <Form.Item name={['security', 'passwordRequireSpecialChars']} valuePropName="checked">
                <Switch checkedChildren={t('common:required')} unCheckedChildren={t('common:optional')} />
                <span style={{ marginLeft: 8 }}>{t('system.security.passwordRequireSpecialChars')}</span>
              </Form.Item>
              
              <Form.Item
                name={['security', 'maxLoginAttempts']}
                label={t('system.security.maxLoginAttempts')}
              >
                <Input type="number" placeholder="5" />
              </Form.Item>
              
              <Form.Item
                name={['security', 'lockoutDuration']}
                label={t('system.security.lockoutDuration')}
              >
                <Input type="number" placeholder="15" />
              </Form.Item>
            </TabPane>
          </Tabs>
        </Form>
      </Card>
    </div>
  );
};

export default AdminSystem;