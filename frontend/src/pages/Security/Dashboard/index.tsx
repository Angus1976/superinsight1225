/**
 * Security Dashboard Page
 */

import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Progress,
  Timeline,
  Typography,
  Alert,
  Modal,
  Form,
  Input,
  Select,
  message,
  Tooltip,
  Tabs,
} from 'antd';
import {
  SecurityScanOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  securityMonitorApi,
  sessionApi,
  SecurityEvent,
  SecuritySeverity,
  Session,
} from '@/services/securityApi';
import dayjs from 'dayjs';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const severityColors: Record<SecuritySeverity, string> = {
  low: 'default',
  medium: 'warning',
  high: 'orange',
  critical: 'error',
};

const SecurityDashboard: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<SecurityEvent | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch security summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['securitySummary'],
    queryFn: () => securityMonitorApi.getSummary(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch security posture
  const { data: posture } = useQuery({
    queryKey: ['securityPosture'],
    queryFn: () => securityMonitorApi.getPosture(7),
  });

  // Fetch recent security events
  const { data: eventsResponse, isLoading: eventsLoading } = useQuery({
    queryKey: ['securityEvents', { status: 'open', limit: 10 }],
    queryFn: () => securityMonitorApi.listEvents({ status: 'open', limit: 10 }),
  });

  // Fetch active sessions
  const { data: sessionsResponse } = useQuery({
    queryKey: ['activeSessions'],
    queryFn: () => sessionApi.listSessions({ limit: 10 }),
  });

  // Resolve event mutation
  const resolveMutation = useMutation({
    mutationFn: ({ eventId, data }: { eventId: string; data: { resolution_notes: string; resolved_by: string } }) =>
      securityMonitorApi.resolveEvent(eventId, data),
    onSuccess: () => {
      message.success(t('dashboard.eventResolved'));
      queryClient.invalidateQueries({ queryKey: ['securityEvents'] });
      queryClient.invalidateQueries({ queryKey: ['securitySummary'] });
      setResolveModalOpen(false);
      form.resetFields();
    },
    onError: () => {
      message.error(t('dashboard.resolveFailed'));
    },
  });

  // Force logout mutation
  const forceLogoutMutation = useMutation({
    mutationFn: (userId: string) => sessionApi.forceLogout(userId, 'admin'),
    onSuccess: () => {
      message.success(t('sessions.logoutSuccess', { count: 1 }));
      queryClient.invalidateQueries({ queryKey: ['activeSessions'] });
    },
    onError: () => {
      message.error(t('sessions.logoutFailed'));
    },
  });

  const handleResolveEvent = (event: SecurityEvent) => {
    setSelectedEvent(event);
    setResolveModalOpen(true);
  };

  const handleSubmitResolve = async () => {
    try {
      const values = await form.validateFields();
      if (selectedEvent) {
        resolveMutation.mutate({
          eventId: selectedEvent.id,
          data: {
            resolution_notes: values.resolution_notes,
            resolved_by: 'admin', // In production, get from auth context
          },
        });
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'critical':
        return '#ff4d4f';
      case 'high':
        return '#fa8c16';
      case 'medium':
        return '#faad14';
      default:
        return '#52c41a';
    }
  };

  const eventColumns: ColumnsType<SecurityEvent> = [
    {
      title: t('audit.riskLevel'),
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: SecuritySeverity) => (
        <Tag color={severityColors[severity]}>{severity.toUpperCase()}</Tag>
      ),
    },
    {
      title: t('audit.eventType'),
      dataIndex: 'event_type',
      key: 'event_type',
      render: (type) => type.replace(/_/g, ' '),
    },
    {
      title: t('audit.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      width: 120,
      ellipsis: true,
    },
    {
      title: t('audit.timestamp'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).fromNow(),
    },
    {
      title: t('common:actions'),
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => handleResolveEvent(record)}
        >
          {t('common:resolve')}
        </Button>
      ),
    },
  ];

  const sessionColumns: ColumnsType<Session> = [
    {
      title: t('sessions.columns.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      render: (userId) => (
        <Space>
          <UserOutlined />
          <Text>{userId}</Text>
        </Space>
      ),
    },
    {
      title: t('sessions.columns.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: t('sessions.columns.lastActivity'),
      dataIndex: 'last_activity',
      key: 'last_activity',
      render: (date) => dayjs(date).fromNow(),
    },
    {
      title: t('common:actions'),
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          danger
          onClick={() => forceLogoutMutation.mutate(record.user_id)}
        >
          {t('sessions.forceLogout')}
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SecurityScanOutlined /> {t('dashboard.title')}
      </Title>

      {/* Alert Banner */}
      {summary && summary.critical_events_24h > 0 && (
        <Alert
          message={t('dashboard.criticalAlert')}
          description={t('dashboard.criticalAlertDesc', { count: summary.critical_events_24h })}
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
          style={{ marginBottom: 24 }}
          action={
            <Button size="small" danger>
              {t('dashboard.viewEvents')}
            </Button>
          }
        />
      )}

      {/* Summary Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dashboard.stats.riskScore')}
              value={summary?.risk_score || 0}
              suffix="/ 100"
              valueStyle={{ color: getRiskLevelColor(summary?.risk_level || 'low') }}
              prefix={<SecurityScanOutlined />}
            />
            <Progress
              percent={summary?.risk_score || 0}
              showInfo={false}
              strokeColor={getRiskLevelColor(summary?.risk_level || 'low')}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dashboard.stats.openEvents')}
              value={summary?.open_events || 0}
              valueStyle={{ color: summary?.open_events ? '#faad14' : '#52c41a' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dashboard.stats.critical24h')}
              value={summary?.critical_events_24h || 0}
              valueStyle={{ color: summary?.critical_events_24h ? '#ff4d4f' : '#52c41a' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dashboard.stats.events7days')}
              value={summary?.events_last_7_days || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        {/* Security Events */}
        <Col xs={24} lg={14}>
          <Card
            title={t('dashboard.openSecurityEvents')}
            extra={
              <Button
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['securityEvents'] })}
              >
                {t('common:refresh')}
              </Button>
            }
          >
            <Table
              columns={eventColumns}
              dataSource={eventsResponse?.events || []}
              rowKey="id"
              loading={eventsLoading}
              pagination={false}
              size="small"
              locale={{ emptyText: t('dashboard.noOpenEvents') }}
            />
          </Card>
        </Col>

        {/* Recommendations */}
        <Col xs={24} lg={10}>
          <Card title={t('dashboard.securityRecommendations')}>
            {posture?.recommendations && posture.recommendations.length > 0 ? (
              <Timeline
                items={posture.recommendations.map((rec, index) => ({
                  color: index === 0 ? 'red' : index < 3 ? 'orange' : 'blue',
                  children: <Text>{rec}</Text>,
                }))}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                <CheckCircleOutlined style={{ fontSize: 32, marginBottom: 8 }} />
                <div>{t('dashboard.securityPostureGood')}</div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Active Sessions */}
      <Card title={t('sessions.activeSessions')} style={{ marginTop: 16 }}>
        <Table
          columns={sessionColumns}
          dataSource={sessionsResponse?.sessions || []}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Resolve Event Modal */}
      <Modal
        title={t('dashboard.resolveEvent')}
        open={resolveModalOpen}
        onOk={handleSubmitResolve}
        onCancel={() => {
          setResolveModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={resolveMutation.isPending}
      >
        {selectedEvent && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Tag color={severityColors[selectedEvent.severity]}>
                {selectedEvent.severity.toUpperCase()}
              </Tag>
              <Text strong style={{ marginLeft: 8 }}>
                {selectedEvent.event_type.replace(/_/g, ' ')}
              </Text>
            </div>
            <Paragraph type="secondary">
              User: {selectedEvent.user_id} | Time:{' '}
              {dayjs(selectedEvent.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Paragraph>
          </>
        )}
        <Form form={form} layout="vertical">
          <Form.Item
            name="resolution_notes"
            label={t('dashboard.resolutionNotes')}
            rules={[{ required: true, message: t('common:pleaseInput', { field: t('dashboard.resolutionNotes') }) }]}
          >
            <TextArea
              rows={4}
              placeholder={t('dashboard.resolutionPlaceholder')}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SecurityDashboard;
