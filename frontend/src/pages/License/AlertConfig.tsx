/**
 * Alert Configuration Page
 * 
 * Configures license-related alerts and notifications.
 */

import React, { useState } from 'react';
import {
  Card,
  Form,
  Switch,
  InputNumber,
  Select,
  Button,
  Table,
  Tag,
  Space,
  message,
  Typography,
  Divider,
  Row,
  Col,
  Alert as AntAlert,
} from 'antd';
import {
  BellOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  CloudServerOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { AlertType, AlertConfig as AlertConfigType } from '../../services/licenseApi';

const { Title, Text } = Typography;

interface AlertConfigItem extends AlertConfigType {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const defaultConfigs: AlertConfigItem[] = [
  {
    key: 'expiry_warning',
    alert_type: 'expiry_warning' as AlertType,
    name: '许可证过期提醒',
    description: '在许可证即将过期时发送提醒',
    icon: <ClockCircleOutlined style={{ color: '#faad14' }} />,
    enabled: true,
    threshold: 30,
    notification_channels: ['email', 'dashboard'],
    recipients: [],
  },
  {
    key: 'concurrent_limit',
    alert_type: 'concurrent_limit' as AlertType,
    name: '并发用户限制告警',
    description: '当并发用户接近或达到限制时告警',
    icon: <TeamOutlined style={{ color: '#1890ff' }} />,
    enabled: true,
    threshold: 80,
    notification_channels: ['dashboard'],
    recipients: [],
  },
  {
    key: 'resource_limit',
    alert_type: 'resource_limit' as AlertType,
    name: '资源限制告警',
    description: '当资源使用接近或达到限制时告警',
    icon: <CloudServerOutlined style={{ color: '#52c41a' }} />,
    enabled: true,
    threshold: 80,
    notification_channels: ['dashboard'],
    recipients: [],
  },
  {
    key: 'license_violation',
    alert_type: 'license_violation' as AlertType,
    name: '许可证违规告警',
    description: '检测到许可证违规行为时告警',
    icon: <SafetyCertificateOutlined style={{ color: '#ff4d4f' }} />,
    enabled: true,
    notification_channels: ['email', 'dashboard'],
    recipients: [],
  },
  {
    key: 'activation_failed',
    alert_type: 'activation_failed' as AlertType,
    name: '激活失败告警',
    description: '许可证激活失败时告警',
    icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
    enabled: true,
    notification_channels: ['email', 'dashboard'],
    recipients: [],
  },
];

const channelOptions = [
  { label: '邮件', value: 'email' },
  { label: '仪表板', value: 'dashboard' },
  { label: 'Webhook', value: 'webhook' },
  { label: '短信', value: 'sms' },
];

const AlertConfig: React.FC = () => {
  const [configs, setConfigs] = useState<AlertConfigItem[]>(defaultConfigs);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [form] = Form.useForm();

  const handleEdit = (record: AlertConfigItem) => {
    form.setFieldsValue(record);
    setEditingKey(record.key);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const newConfigs = configs.map((config) =>
        config.key === editingKey ? { ...config, ...values } : config
      );
      setConfigs(newConfigs);
      setEditingKey(null);
      message.success('配置已保存');
    } catch (err) {
      console.error('Validation failed:', err);
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    form.resetFields();
  };

  const handleToggle = (key: string, enabled: boolean) => {
    const newConfigs = configs.map((config) =>
      config.key === key ? { ...config, enabled } : config
    );
    setConfigs(newConfigs);
    message.success(`告警已${enabled ? '启用' : '禁用'}`);
  };

  const columns: ColumnsType<AlertConfigItem> = [
    {
      title: '告警类型',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          {record.icon}
          <div>
            <Text strong>{name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggle(record.key, checked)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      width: 120,
      render: (threshold: number | undefined, record) => {
        if (editingKey === record.key) {
          return (
            <Form.Item name="threshold" style={{ margin: 0 }}>
              <InputNumber
                min={1}
                max={100}
                suffix={record.alert_type === 'expiry_warning' ? '天' : '%'}
              />
            </Form.Item>
          );
        }
        return threshold !== undefined ? (
          <Tag>
            {threshold}
            {record.alert_type === 'expiry_warning' ? ' 天' : '%'}
          </Tag>
        ) : (
          '-'
        );
      },
    },
    {
      title: '通知渠道',
      dataIndex: 'notification_channels',
      key: 'notification_channels',
      width: 200,
      render: (channels: string[], record) => {
        if (editingKey === record.key) {
          return (
            <Form.Item name="notification_channels" style={{ margin: 0 }}>
              <Select
                mode="multiple"
                options={channelOptions}
                style={{ minWidth: 150 }}
              />
            </Form.Item>
          );
        }
        return (
          <Space wrap>
            {channels.map((channel) => (
              <Tag key={channel} color="blue">
                {channelOptions.find((o) => o.value === channel)?.label || channel}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => {
        if (editingKey === record.key) {
          return (
            <Space>
              <Button type="link" onClick={handleSave}>
                保存
              </Button>
              <Button type="link" onClick={handleCancel}>
                取消
              </Button>
            </Space>
          );
        }
        return (
          <Button type="link" onClick={() => handleEdit(record)}>
            编辑
          </Button>
        );
      },
    },
  ];

  const enabledCount = configs.filter((c) => c.enabled).length;

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 24 }}>
        <Col flex="auto">
          <Title level={2} style={{ margin: 0 }}>
            <BellOutlined /> 告警配置
          </Title>
        </Col>
        <Col>
          <Space>
            <Tag icon={<CheckCircleOutlined />} color="success">
              {enabledCount} 个告警已启用
            </Tag>
          </Space>
        </Col>
      </Row>

      <AntAlert
        message="告警说明"
        description="配置许可证相关的告警规则，当触发条件满足时，系统将通过配置的渠道发送通知。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card>
        <Form form={form} component={false}>
          <Table
            columns={columns}
            dataSource={configs}
            rowKey="key"
            pagination={false}
          />
        </Form>
      </Card>

      <Divider />

      {/* Global Settings */}
      <Card title="全局设置" style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item label="默认邮件接收人">
                <Select
                  mode="tags"
                  placeholder="输入邮箱地址"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="Webhook URL">
                <Select
                  mode="tags"
                  placeholder="输入 Webhook URL"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={24}>
            <Col xs={24} md={8}>
              <Form.Item label="告警静默时间">
                <InputNumber
                  min={0}
                  max={1440}
                  defaultValue={60}
                  addonAfter="分钟"
                  style={{ width: '100%' }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  同一告警在静默时间内不会重复发送
                </Text>
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="每日告警上限">
                <InputNumber
                  min={1}
                  max={100}
                  defaultValue={10}
                  addonAfter="次"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="启用告警聚合">
                <Switch defaultChecked />
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                  将相似告警合并发送
                </Text>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" onClick={() => message.success('设置已保存')}>
              保存全局设置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default AlertConfig;
