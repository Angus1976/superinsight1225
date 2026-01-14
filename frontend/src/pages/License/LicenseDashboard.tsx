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

const licenseTypeLabels: Record<string, string> = {
  trial: '试用版',
  basic: '基础版',
  professional: '专业版',
  enterprise: '企业版',
};

const LicenseDashboard: React.FC = () => {
  const navigate = useNavigate();
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
      setError('无法加载许可证信息');
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
        <div style={{ marginTop: 16 }}>加载许可证信息...</div>
      </div>
    );
  }

  if (error || !licenseStatus) {
    return (
      <Alert
        message="许可证错误"
        description={error || '无法获取许可证状态'}
        type="error"
        showIcon
        action={
          <Space direction="vertical">
            <Button onClick={fetchData}>重试</Button>
            <Button type="primary" onClick={() => navigate('/license/activate')}>
              激活许可证
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
            <SafetyCertificateOutlined /> 许可证管理
          </Title>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              刷新
            </Button>
            <Button type="primary" icon={<KeyOutlined />} onClick={() => navigate('/license/activate')}>
              激活向导
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Warnings */}
      {licenseStatus.warnings.length > 0 && (
        <Alert
          message="许可证警告"
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
      <Card title="许可证状态" style={{ marginBottom: 16 }}>
        <Row gutter={[24, 24]}>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="许可证类型"
              value={licenseTypeLabels[licenseStatus.license_type] || licenseStatus.license_type}
              prefix={<SafetyCertificateOutlined />}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="状态"
              valueRender={() => (
                <Tag color={statusColors[licenseStatus.status]} style={{ fontSize: 16 }}>
                  {licenseStatus.status.toUpperCase()}
                </Tag>
              )}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="有效期状态"
              valueRender={() => (
                <Tag color={validityStatusColors[licenseStatus.validity_status]} style={{ fontSize: 16 }}>
                  {licenseStatus.validity_status === 'active' && '有效'}
                  {licenseStatus.validity_status === 'not_started' && '未开始'}
                  {licenseStatus.validity_status === 'grace_period' && '宽限期'}
                  {licenseStatus.validity_status === 'expired' && '已过期'}
                </Tag>
              )}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="剩余天数"
              value={licenseStatus.days_remaining ?? licenseStatus.days_until_start ?? 0}
              suffix="天"
              prefix={<ClockCircleOutlined />}
              valueStyle={{
                color: (licenseStatus.days_remaining ?? 0) <= 7 ? '#cf1322' : 
                       (licenseStatus.days_remaining ?? 0) <= 30 ? '#faad14' : '#3f8600',
              }}
            />
          </Col>
        </Row>

        <Descriptions style={{ marginTop: 24 }} column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="许可证密钥">
            <Text code copyable={{ text: licenseStatus.license_key }}>
              {licenseStatus.license_key.substring(0, 8)}...
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label="许可证ID">
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
                并发用户
              </Space>
            }
          >
            {concurrentUsage && (
              <>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="当前在线"
                      value={concurrentUsage.current_users}
                      suffix={`/ ${concurrentUsage.max_users}`}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="使用率"
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
                资源使用
              </Space>
            }
          >
            {resourceUsage && (
              <>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="CPU 核心"
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
                      title="存储空间"
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
                已启用功能 ({enabledFeatures.length})
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
                未授权功能 ({disabledFeatures.length})
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
                            试用
                          </Button>,
                        ]
                      : feature.requires_upgrade
                      ? [
                          <Button size="small" type="link">
                            升级
                          </Button>,
                        ]
                      : []
                  }
                >
                  <Space>
                    <Badge status="default" />
                    <Text type="secondary">{feature.name}</Text>
                    {feature.trial_available && feature.trial_days_remaining && (
                      <Tag color="blue">可试用 {feature.trial_days_remaining} 天</Tag>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Card title="快捷操作" style={{ marginTop: 16 }}>
        <Space wrap>
          <Button onClick={() => navigate('/license/usage')}>
            查看使用详情
          </Button>
          <Button onClick={() => navigate('/license/report')}>
            生成使用报告
          </Button>
          <Button onClick={() => navigate('/license/alerts')}>
            告警配置
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default LicenseDashboard;
