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
import { useTranslation } from 'react-i18next';
import { AlertType, AlertConfig as AlertConfigType } from '../../services/licenseApi';

const { Title, Text } = Typography;

interface AlertConfigItem extends AlertConfigType {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const AlertConfig: React.FC = () => {
  const { t } = useTranslation(['license', 'common']);
  
  const defaultConfigs: AlertConfigItem[] = [
    {
      key: 'expiry_warning',
      alert_type: 'expiry_warning' as AlertType,
      name: t('alerts.types.expiryWarning'),
      description: t('alerts.types.expiryWarningDesc'),
      icon: <ClockCircleOutlined style={{ color: '#faad14' }} />,
      enabled: true,
      threshold: 30,
      notification_channels: ['email', 'dashboard'],
      recipients: [],
    },
    {
      key: 'concurrent_limit',
      alert_type: 'concurrent_limit' as AlertType,
      name: t('alerts.types.concurrentLimit'),
      description: t('alerts.types.concurrentLimitDesc'),
      icon: <TeamOutlined style={{ color: '#1890ff' }} />,
      enabled: true,
      threshold: 80,
      notification_channels: ['dashboard'],
      recipients: [],
    },
    {
      key: 'resource_limit',
      alert_type: 'resource_limit' as AlertType,
      name: t('alerts.types.resourceLimit'),
      description: t('alerts.types.resourceLimitDesc'),
      icon: <CloudServerOutlined style={{ color: '#52c41a' }} />,
      enabled: true,
      threshold: 80,
      notification_channels: ['dashboard'],
      recipients: [],
    },
    {
      key: 'license_violation',
      alert_type: 'license_violation' as AlertType,
      name: t('alerts.types.licenseViolation'),
      description: t('alerts.types.licenseViolationDesc'),
      icon: <SafetyCertificateOutlined style={{ color: '#ff4d4f' }} />,
      enabled: true,
      notification_channels: ['email', 'dashboard'],
      recipients: [],
    },
    {
      key: 'activation_failed',
      alert_type: 'activation_failed' as AlertType,
      name: t('alerts.types.activationFailed'),
      description: t('alerts.types.activationFailedDesc'),
      icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
      enabled: true,
      notification_channels: ['email', 'dashboard'],
      recipients: [],
    },
  ];

  const channelOptions = [
    { label: t('alerts.channels.email'), value: 'email' },
    { label: t('alerts.channels.dashboard'), value: 'dashboard' },
    { label: t('alerts.channels.webhook'), value: 'webhook' },
    { label: t('alerts.channels.sms'), value: 'sms' },
  ];

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
      message.success(t('alerts.configSaved'));
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
    message.success(enabled ? t('alerts.alertEnabled') : t('alerts.alertDisabled'));
  };

  const columns: ColumnsType<AlertConfigItem> = [
    {
      title: t('alerts.alertType'),
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
      title: t('dashboard.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggle(record.key, checked)}
          checkedChildren={t('alerts.enabled')}
          unCheckedChildren={t('alerts.disabled')}
        />
      ),
    },
    {
      title: t('alerts.threshold'),
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
                suffix={record.alert_type === 'expiry_warning' ? t('dashboard.days') : '%'}
              />
            </Form.Item>
          );
        }
        return threshold !== undefined ? (
          <Tag>
            {threshold}
            {record.alert_type === 'expiry_warning' ? ` ${t('dashboard.days')}` : '%'}
          </Tag>
        ) : (
          '-'
        );
      },
    },
    {
      title: t('alerts.notificationChannels'),
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
      title: t('alerts.action'),
      key: 'action',
      width: 150,
      render: (_, record) => {
        if (editingKey === record.key) {
          return (
            <Space>
              <Button type="link" onClick={handleSave}>
                {t('alerts.save')}
              </Button>
              <Button type="link" onClick={handleCancel}>
                {t('alerts.cancel')}
              </Button>
            </Space>
          );
        }
        return (
          <Button type="link" onClick={() => handleEdit(record)}>
            {t('alerts.edit')}
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
            <BellOutlined /> {t('alerts.title')}
          </Title>
        </Col>
        <Col>
          <Space>
            <Tag icon={<CheckCircleOutlined />} color="success">
              {enabledCount} {t('alerts.alertsEnabled')}
            </Tag>
          </Space>
        </Col>
      </Row>

      <AntAlert
        message={t('alerts.title')}
        description={t('alerts.description')}
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
      <Card title={t('alerts.globalSettings')} style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item label={t('alerts.defaultEmailRecipients')}>
                <Select
                  mode="tags"
                  placeholder={t('alerts.enterEmailAddress')}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label={t('alerts.webhookUrl')}>
                <Select
                  mode="tags"
                  placeholder={t('alerts.enterWebhookUrl')}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={24}>
            <Col xs={24} md={8}>
              <Form.Item label={t('alerts.silencePeriod')}>
                <InputNumber
                  min={0}
                  max={1440}
                  defaultValue={60}
                  addonAfter={t('alerts.minutes')}
                  style={{ width: '100%' }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('alerts.silencePeriodHint')}
                </Text>
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label={t('alerts.dailyAlertLimit')}>
                <InputNumber
                  min={1}
                  max={100}
                  defaultValue={10}
                  addonAfter={t('alerts.times')}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label={t('alerts.enableAlertAggregation')}>
                <Switch defaultChecked />
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                  {t('alerts.aggregationHint')}
                </Text>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" onClick={() => message.success(t('alerts.settingsSaved'))}>
              {t('alerts.saveGlobalSettings')}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default AlertConfig;
