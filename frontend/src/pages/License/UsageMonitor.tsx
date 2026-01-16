/**
 * Usage Monitor Page
 * 
 * Displays real-time usage monitoring for concurrent users and resources.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Progress,
  Statistic,
  Button,
  Space,
  Tag,
  Modal,
  Input,
  message,
  Typography,
  Tooltip,
  Badge,
} from 'antd';
import {
  TeamOutlined,
  CloudServerOutlined,
  ReloadOutlined,
  DeleteOutlined,
  UserOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import {
  usageApi,
  ConcurrentUsageInfo,
  ResourceUsageInfo,
  UserSession,
} from '../../services/licenseApi';

const { Title, Text } = Typography;

const UsageMonitor: React.FC = () => {
  const { t } = useTranslation(['license', 'common']);
  const [loading, setLoading] = useState(true);
  const [concurrentUsage, setConcurrentUsage] = useState<ConcurrentUsageInfo | null>(null);
  const [resourceUsage, setResourceUsage] = useState<ResourceUsageInfo | null>(null);
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [terminateModalVisible, setTerminateModalVisible] = useState(false);
  const [selectedSession, setSelectedSession] = useState<UserSession | null>(null);
  const [terminateReason, setTerminateReason] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [concurrent, resources, sessionList] = await Promise.all([
        usageApi.getConcurrentUsage(),
        usageApi.getResourceUsage(),
        usageApi.getActiveSessions(),
      ]);
      setConcurrentUsage(concurrent);
      setResourceUsage(resources);
      setSessions(sessionList);
    } catch (err) {
      console.error('Failed to fetch usage data:', err);
      message.error(t('usage.fetchFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, fetchData]);

  const handleTerminateSession = async () => {
    if (!selectedSession) return;
    
    try {
      await usageApi.terminateSession(selectedSession.session_id, terminateReason);
      message.success(t('usage.sessionTerminated'));
      setTerminateModalVisible(false);
      setSelectedSession(null);
      setTerminateReason('');
      fetchData();
    } catch (err) {
      message.error(t('usage.terminateFailed'));
    }
  };

  const sessionColumns: ColumnsType<UserSession> = [
    {
      title: t('usage.columns.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      render: (userId: string) => (
        <Space>
          <UserOutlined />
          <Text>{userId}</Text>
        </Space>
      ),
    },
    {
      title: t('usage.columns.sessionId'),
      dataIndex: 'session_id',
      key: 'session_id',
      render: (sessionId: string) => (
        <Tooltip title={sessionId}>
          <Text code>{sessionId.substring(0, 12)}...</Text>
        </Tooltip>
      ),
    },
    {
      title: t('usage.columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: number) => (
        <Tag color={priority > 5 ? 'gold' : 'default'}>
          {priority}
        </Tag>
      ),
    },
    {
      title: t('usage.columns.loginTime'),
      dataIndex: 'login_time',
      key: 'login_time',
      render: (time: string) => (
        <Space>
          <ClockCircleOutlined />
          {new Date(time).toLocaleString()}
        </Space>
      ),
    },
    {
      title: t('usage.columns.lastActivity'),
      dataIndex: 'last_activity',
      key: 'last_activity',
      render: (time: string) => {
        const diff = Date.now() - new Date(time).getTime();
        const minutes = Math.floor(diff / 60000);
        return (
          <Text type={minutes > 30 ? 'warning' : 'secondary'}>
            {minutes < 1 ? t('usage.justNow') : t('usage.minutesAgo', { minutes })}
          </Text>
        );
      },
    },
    {
      title: t('usage.columns.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (ip: string) => (
        ip ? (
          <Space>
            <GlobalOutlined />
            {ip}
          </Space>
        ) : '-'
      ),
    },
    {
      title: t('usage.columns.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Badge status={active ? 'success' : 'default'} text={active ? t('usage.sessionStatus.active') : t('usage.sessionStatus.offline')} />
      ),
    },
    {
      title: t('usage.columns.action'),
      key: 'action',
      render: (_, record) => (
        <Button
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => {
            setSelectedSession(record);
            setTerminateModalVisible(true);
          }}
        >
          {t('usage.terminate')}
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 24 }}>
        <Col flex="auto">
          <Title level={2} style={{ margin: 0 }}>
            {t('usage.title')}
          </Title>
        </Col>
        <Col>
          <Space>
            <Button
              type={autoRefresh ? 'primary' : 'default'}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? t('usage.stopAutoRefresh') : t('usage.autoRefresh')}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
              {t('usage.refresh')}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Usage Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <TeamOutlined />
                {t('usage.concurrentUsers')}
              </Space>
            }
            loading={loading}
          >
            {concurrentUsage && (
              <>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title={t('usage.currentOnline')}
                      value={concurrentUsage.current_users}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title={t('usage.maxLimit')}
                      value={concurrentUsage.max_users}
                    />
                  </Col>
                  <Col span={8}>
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
                  status={
                    concurrentUsage.utilization_percent >= 100 ? 'exception' :
                    concurrentUsage.utilization_percent >= 80 ? 'active' : 'normal'
                  }
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': concurrentUsage.utilization_percent >= 80 ? '#ff4d4f' : '#87d068',
                  }}
                  style={{ marginTop: 16 }}
                />
              </>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <CloudServerOutlined />
                {t('usage.resourceUsage')}
              </Space>
            }
            loading={loading}
          >
            {resourceUsage && (
              <Row gutter={[16, 16]}>
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
                    suffix={`/ ${resourceUsage.max_storage_gb}`}
                  />
                  <Progress
                    percent={resourceUsage.storage_utilization_percent}
                    size="small"
                    status={resourceUsage.storage_utilization_percent >= 100 ? 'exception' : 'normal'}
                  />
                </Col>
              </Row>
            )}
          </Card>
        </Col>
      </Row>

      {/* Active Sessions Table */}
      <Card
        title={
          <Space>
            <TeamOutlined />
            {t('usage.activeSessions')}
            <Tag color="blue">{sessions.length}</Tag>
          </Space>
        }
      >
        <Table
          columns={sessionColumns}
          dataSource={sessions}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => t('usage.totalSessions', { total }),
          }}
        />
      </Card>

      {/* Terminate Session Modal */}
      <Modal
        title={t('usage.terminateSession')}
        open={terminateModalVisible}
        onOk={handleTerminateSession}
        onCancel={() => {
          setTerminateModalVisible(false);
          setSelectedSession(null);
          setTerminateReason('');
        }}
        okText={t('usage.confirmTerminateBtn')}
        okButtonProps={{ danger: true }}
      >
        <p>
          {t('usage.confirmTerminate', { user: selectedSession?.user_id })}
        </p>
        <Input.TextArea
          placeholder={t('usage.terminateReason')}
          value={terminateReason}
          onChange={(e) => setTerminateReason(e.target.value)}
          rows={3}
        />
      </Modal>
    </div>
  );
};

export default UsageMonitor;
