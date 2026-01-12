import React, { useState } from 'react';
import { Card, Form, Input, Select, Switch, Button, Space, message, Tabs, Statistic, Row, Col, Progress, Alert } from 'antd';
import { SaveOutlined, ReloadOutlined, DatabaseOutlined, CloudOutlined, SettingOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

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
      message.success('系统配置保存成功');
    },
    onError: () => {
      message.error('系统配置保存失败');
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: (type: string) => api.post(`/api/v1/admin/system/test/${type}`),
    onSuccess: (data, type) => {
      if (data.data.success) {
        message.success(`${type}连接测试成功`);
      } else {
        message.error(`${type}连接测试失败: ${data.data.error}`);
      }
    },
    onError: (_, type) => {
      message.error(`${type}连接测试失败`);
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
      case 'healthy': return '正常';
      case 'warning': return '警告';
      case 'error': return '错误';
      default: return '未知';
    }
  };

  return (
    <div className="admin-system">
      {/* 系统状态概览 */}
      <Card title="系统状态" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title="数据库"
                value={getStatusText(status?.database?.status || 'unknown')}
                valueStyle={{ color: getStatusColor(status?.database?.status || 'unknown') }}
                prefix={<DatabaseOutlined />}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                连接数: {status?.database?.connections || 0}/{status?.database?.maxConnections || 0}
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                响应时间: {status?.database?.responseTime || 0}ms
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="缓存"
                value={getStatusText(status?.cache?.status || 'unknown')}
                valueStyle={{ color: getStatusColor(status?.cache?.status || 'unknown') }}
                prefix={<CloudOutlined />}
              />
              <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
                内存使用: {((status?.cache?.memoryUsage || 0) / 1024 / 1024).toFixed(2)}MB
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                命中率: {((status?.cache?.hitRate || 0) * 100).toFixed(1)}%
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="存储"
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
                title="系统负载"
                value={`${(status?.system?.cpuUsage || 0).toFixed(1)}%`}
                valueStyle={{ 
                  color: (status?.system?.cpuUsage || 0) > 80 ? '#f5222d' : 
                         (status?.system?.cpuUsage || 0) > 60 ? '#faad14' : '#52c41a'
                }}
              />
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  内存: {(status?.system?.memoryUsage || 0).toFixed(1)}%
                </div>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  磁盘: {(status?.system?.diskUsage || 0).toFixed(1)}%
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 系统配置 */}
      <Card
        title="系统配置"
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['system-config'] });
                queryClient.invalidateQueries({ queryKey: ['system-status'] });
              }}
            >
              刷新
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
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            {/* 基本设置 */}
            <TabPane tab="基本设置" key="general">
              <Form.Item
                name={['general', 'siteName']}
                label="站点名称"
                rules={[{ required: true, message: '请输入站点名称' }]}
              >
                <Input placeholder="SuperInsight AI Platform" />
              </Form.Item>
              
              <Form.Item
                name={['general', 'siteDescription']}
                label="站点描述"
              >
                <Input.TextArea rows={3} placeholder="AI数据治理与标注平台" />
              </Form.Item>
              
              <Form.Item
                name={['general', 'adminEmail']}
                label="管理员邮箱"
                rules={[
                  { required: true, message: '请输入管理员邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' },
                ]}
              >
                <Input placeholder="admin@example.com" />
              </Form.Item>
              
              <Form.Item
                name={['general', 'timezone']}
                label="时区"
                rules={[{ required: true, message: '请选择时区' }]}
              >
                <Select placeholder="请选择时区">
                  <Select.Option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</Select.Option>
                  <Select.Option value="UTC">UTC (UTC+0)</Select.Option>
                  <Select.Option value="America/New_York">America/New_York (UTC-5)</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['general', 'language']}
                label="默认语言"
                rules={[{ required: true, message: '请选择默认语言' }]}
              >
                <Select placeholder="请选择默认语言">
                  <Select.Option value="zh-CN">简体中文</Select.Option>
                  <Select.Option value="en-US">English</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item name={['general', 'maintenanceMode']} valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                <span style={{ marginLeft: 8 }}>维护模式</span>
              </Form.Item>
            </TabPane>

            {/* 数据库设置 */}
            <TabPane tab="数据库" key="database">
              <Alert
                message="数据库配置"
                description="修改数据库配置需要重启系统才能生效，请谨慎操作。"
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
              
              <Form.Item
                name={['database', 'host']}
                label="主机地址"
                rules={[{ required: true, message: '请输入主机地址' }]}
              >
                <Input placeholder="localhost" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'port']}
                label="端口"
                rules={[{ required: true, message: '请输入端口' }]}
              >
                <Input type="number" placeholder="5432" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'name']}
                label="数据库名"
                rules={[{ required: true, message: '请输入数据库名' }]}
              >
                <Input placeholder="superinsight" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'maxConnections']}
                label="最大连接数"
              >
                <Input type="number" placeholder="100" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'connectionTimeout']}
                label="连接超时（秒）"
              >
                <Input type="number" placeholder="30" />
              </Form.Item>
              
              <Form.Item
                name={['database', 'queryTimeout']}
                label="查询超时（秒）"
              >
                <Input type="number" placeholder="60" />
              </Form.Item>
              
              <Button
                onClick={() => testConnectionMutation.mutate('database')}
                loading={testConnectionMutation.isPending}
              >
                测试数据库连接
              </Button>
            </TabPane>

            {/* 缓存设置 */}
            <TabPane tab="缓存" key="cache">
              <Form.Item name={['cache', 'enabled']} valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
                <span style={{ marginLeft: 8 }}>启用缓存</span>
              </Form.Item>
              
              <Form.Item
                name={['cache', 'type']}
                label="缓存类型"
              >
                <Select placeholder="请选择缓存类型">
                  <Select.Option value="redis">Redis</Select.Option>
                  <Select.Option value="memory">内存缓存</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['cache', 'host']}
                label="缓存主机"
              >
                <Input placeholder="localhost" />
              </Form.Item>
              
              <Form.Item
                name={['cache', 'port']}
                label="缓存端口"
              >
                <Input type="number" placeholder="6379" />
              </Form.Item>
              
              <Form.Item
                name={['cache', 'ttl']}
                label="默认TTL（秒）"
              >
                <Input type="number" placeholder="3600" />
              </Form.Item>
              
              <Button
                onClick={() => testConnectionMutation.mutate('cache')}
                loading={testConnectionMutation.isPending}
              >
                测试缓存连接
              </Button>
            </TabPane>

            {/* 安全设置 */}
            <TabPane tab="安全" key="security">
              <Form.Item
                name={['security', 'sessionTimeout']}
                label="会话超时（分钟）"
              >
                <Input type="number" placeholder="30" />
              </Form.Item>
              
              <Form.Item
                name={['security', 'passwordMinLength']}
                label="密码最小长度"
              >
                <Input type="number" placeholder="8" />
              </Form.Item>
              
              <Form.Item name={['security', 'passwordRequireSpecialChars']} valuePropName="checked">
                <Switch checkedChildren="要求" unCheckedChildren="不要求" />
                <span style={{ marginLeft: 8 }}>密码包含特殊字符</span>
              </Form.Item>
              
              <Form.Item
                name={['security', 'maxLoginAttempts']}
                label="最大登录尝试次数"
              >
                <Input type="number" placeholder="5" />
              </Form.Item>
              
              <Form.Item
                name={['security', 'lockoutDuration']}
                label="锁定时长（分钟）"
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