/**
 * License Dashboard Page
 * 
 * Displays license status overview, validity, features, and usage information.
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Alert,
  Button,
  Descriptions,
  List,
  Space,
  Spin,
  Typography,
  Tooltip,
  Badge,
} from 'antd';
import {
  SafetyCertificateOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  KeyOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  licenseApi,
  usageApi,
  LicenseStatusResponse,
  ConcurrentUsageInfo,
  ResourceUsageInfo,
  FeatureInfo,
} from '../../services/licenseApi';

const { Title, Text } = Typography;

const statusColors: Record<string, string> = {
  active: 'green',
  pending: 'orange',
  expired: 'red',
  suspended: 'gold',
  revoked: 'default',
};

const validityStatusColors: Record<string, string> = {
  active: 'green',
  not_started: 'blue',
  grace_period: 'orange',
  expired: 'red',
};

const LicenseDashboard: React.FC = () => {
  const { t } = useTranslation(['license', 'common']);
  const navigate = useNavigate();

  const licenseTypeLabels: Record<string, string> = {
    trial: t('types.trial'),
    basic: t('types.basic'),
    professional: t('types.professional'),
    enterprise: t('types.enterprise'),
  };

  const validityStatusLabels: Record<string, string> = {
    active: t('status.active'),
    not_started: t('status.notStarted'),
    grace_period: t('status.gracePeriod'),
    expired: t('status.expired'),
  };
  const [loading, setLoading] = useState(true);
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatusResponse | null>(null);
  const [concurrentUsage, setConcurrentUsage] = useState<ConcurrentUsageInfo | null>(null);
  const [resourceUsage, setResourceUsage] = useState<ResourceUsageInfo | null>(null);
  const [features, setFeatures] = useState<FeatureInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [status, concurrent, resources, featureList] = await Promise.all([
        licenseApi.getStatus(),
        usageApi.getConcurrentUsage(),
        usageApi.getResourceUsage(),
        licenseApi.getFeatures(),
      ]);
      setLicenseStatus(status);
      setConcurrentUsage(concurrent);
      setResourceUsage(resources);
      setFeatures(featureList);
    } catch (err) {
      setError(t('dashboard.cannotLoadInfo'));
      console.error('Failed to fetch license data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>{t('dashboard.loadingInfo')}</div>
      </div>
    );
  }

  if (error || !licenseStatus) {
    return (
      <Alert
        message={t('dashboard.error')}
        description={error || t('dashboard.cannotGetStatus')}
        type="error"
        showIcon
        action={
          <Space direction="vertical">
            <Button onClick={fetchData}>{t('dashboard.retry')}</Button>
            <Button type="primary" onClick={() => navigate('/license/activate')}>
              {t('dashboard.activateLicense')}
            </Button>
          </Space>
        }
      />
    );
  }

  const enabledFeatures = features.filter(f => f.enabled);
  const disabledFeatures = features.filter(f => !f.enabled);

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 24 }}>
        <Col flex="auto">
          <Title level={2} style={{ margin: 0 }}>
            <SafetyCertificateOutlined /> {t('dashboard.title')}
          </Title>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              {t('dashboard.refresh')}
            </Button>
            <Button type="primary" icon={<KeyOutlined />} onClick={() => navigate('/license/activate')}>
              {t('dashboard.activationWizard')}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Warnings */}
      {licenseStatus.warnings.length > 0 && (
        <Alert
          message={t('dashboard.warnings')}
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {licenseStatus.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          }
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* License Status Card */}
      <Card title={t('dashboard.licenseStatus')} style={{ marginBottom: 16 }}>
        <Row gutter={[24, 24]}>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title={t('dashboard.licenseType')}
              value={licenseTypeLabels[licenseStatus.license_type] || licenseStatus.license_type}
              prefix={<SafetyCertificateOutlined />}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title={t('dashboard.status')}
              valueRender={() => (
                <Tag color={statusColors[licenseStatus.status]} style={{ fontSize: 16 }}>
                  {licenseStatus.status.toUpperCase()}
                </Tag>
              )}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title={t('dashboard.validityStatus')}
              valueRender={() => (
                <Tag color={validityStatusColors[licenseStatus.validity_status]} style={{ fontSize: 16 }}>
                  {validityStatusLabels[licenseStatus.validity_status] || licenseStatus.validity_status}
                </Tag>
              )}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title={t('dashboard.daysRemaining')}
              value={licenseStatus.days_remaining ?? licenseStatus.days_until_start ?? 0}
              suffix={t('dashboard.days')}
              prefix={<ClockCircleOutlined />}
              valueStyle={{
                color: (licenseStatus.days_remaining ?? 0) <= 7 ? '#cf1322' : 
                       (licenseStatus.days_remaining ?? 0) <= 30 ? '#faad14' : '#3f8600',
              }}
            />
          </Col>
        </Row>

        <Descriptions style={{ marginTop: 24 }} column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label={t('dashboard.licenseKey')}>
            <Text code copyable={{ text: licenseStatus.license_key }}>
              {licenseStatus.license_key.substring(0, 8)}...
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('dashboard.licenseId')}>
            <Text copyable={{ text: licenseStatus.license_id }}>
              {licenseStatus.license_id.substring(0, 8)}...
            </Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Usage Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {/* Concurrent Users */}
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                {t('usage.concurrentUsers')}
              </Space>
            }
          >
            {concurrentUsage && (
              <>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title={t('usage.currentOnline')}
                      value={concurrentUsage.current_users}
                      suffix={`/ ${concurrentUsage.max_users}`}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t('usage.utilizationRate')}
                      value={concurrentUsage.utilization_percent}
                      suffix="%"
                      valueStyle={{
                        color: concurrentUsage.utilization_percent >= 90 ? '#cf1322' :
                               concurrentUsage.utilization_percent >= 70 ? '#faad14' : '#3f8600',
                      }}
                    />
                  </Col>
                </Row>
                <Progress
                  percent={concurrentUsage.utilization_percent}
                  status={concurrentUsage.utilization_percent >= 100 ? 'exception' : 'active'}
                  style={{ marginTop: 16 }}
                />
              </>
            )}
          </Card>
        </Col>

        {/* Resources */}
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <CloudServerOutlined />
                {t('usage.resourceUsage')}
              </Space>
            }
          >
            {resourceUsage && (
              <>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title={t('usage.cpuCores')}
                      value={resourceUsage.cpu_cores}
                      suffix={`/ ${resourceUsage.max_cpu_cores}`}
                    />
                    <Progress
                      percent={resourceUsage.cpu_utilization_percent}
                      size="small"
                      status={resourceUsage.cpu_utilization_percent >= 100 ? 'exception' : 'normal'}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t('usage.storageSpace')}
                      value={resourceUsage.storage_gb.toFixed(1)}
                      suffix={`/ ${resourceUsage.max_storage_gb} GB`}
                    />
                    <Progress
                      percent={resourceUsage.storage_utilization_percent}
                      size="small"
                      status={resourceUsage.storage_utilization_percent >= 100 ? 'exception' : 'normal'}
                    />
                  </Col>
                </Row>
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* Features */}
      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <CheckCircleOutlined style={{ color: '#52c41a' }} />
                {t('features.enabledFeatures')} ({enabledFeatures.length})
              </Space>
            }
          >
            <List
              size="small"
              dataSource={enabledFeatures}
              renderItem={(feature) => (
                <List.Item>
                  <Space>
                    <Badge status="success" />
                    <Text>{feature.name}</Text>
                    {feature.description && (
                      <Tooltip title={feature.description}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          ({feature.description})
                        </Text>
                      </Tooltip>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                {t('features.disabledFeatures')} ({disabledFeatures.length})
              </Space>
            }
          >
            <List
              size="small"
              dataSource={disabledFeatures}
              renderItem={(feature) => (
                <List.Item
                  actions={
                    feature.trial_available
                      ? [
                          <Button size="small" type="link">
                            {t('features.trial')}
                          </Button>,
                        ]
                      : feature.requires_upgrade
                      ? [
                          <Button size="small" type="link">
                            {t('features.upgrade')}
                          </Button>,
                        ]
                      : []
                  }
                >
                  <Space>
                    <Badge status="default" />
                    <Text type="secondary">{feature.name}</Text>
                    {feature.trial_available && feature.trial_days_remaining && (
                      <Tag color="blue">{t('features.trialAvailable', { days: feature.trial_days_remaining })}</Tag>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Card title={t('dashboard.quickActions')} style={{ marginTop: 16 }}>
        <Space wrap>
          <Button onClick={() => navigate('/license/usage')}>
            {t('dashboard.viewUsageDetails')}
          </Button>
          <Button onClick={() => navigate('/license/report')}>
            {t('dashboard.generateReport')}
          </Button>
          <Button onClick={() => navigate('/license/alerts')}>
            {t('dashboard.alertConfig')}
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default LicenseDashboard;
