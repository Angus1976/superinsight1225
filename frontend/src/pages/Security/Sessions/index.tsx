/**
 * Session Manager Page
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Modal,
  Form,
  InputNumber,
  Typography,
  message,
  Popconfirm,
  Input,
  Tooltip,
  Descriptions,
} from 'antd';
import {
  UserOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  SettingOutlined,
  ReloadOutlined,
  SearchOutlined,
  GlobalOutlined,
  DesktopOutlined,
  LogoutOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { sessionApi, Session, SessionConfig, SessionStatistics } from '@/services/securityApi';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const SessionManager: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [searchText, setSearchText] = useState('');
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch sessions
  const { data: sessionsResponse, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionApi.listSessions({ limit: 100 }),
  });

  // Fetch statistics
  const { data: stats } = useQuery({
    queryKey: ['sessionStats'],
    queryFn: () => sessionApi.getStatistics(),
  });

  // Fetch config
  const { data: config } = useQuery({
    queryKey: ['sessionConfig'],
    queryFn: () => sessionApi.getConfig(),
  });

  // Destroy session mutation
  const destroyMutation = useMutation({
    mutationFn: (sessionId: string) => sessionApi.destroySession(sessionId),
    onSuccess: () => {
      message.success(t('sessions.sessionTerminated'));
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['sessionStats'] });
    },
    onError: () => {
      message.error(t('sessions.terminateFailed'));
    },
  });

  // Force logout mutation
  const forceLogoutMutation = useMutation({
    mutationFn: (userId: string) => sessionApi.forceLogout(userId, 'admin'),
    onSuccess: (result) => {
      message.success(t('sessions.logoutSuccess', { count: result.sessions_destroyed }));
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['sessionStats'] });
    },
    onError: () => {
      message.error(t('sessions.logoutFailed'));
    },
  });

  // Update config mutation
  const updateConfigMutation = useMutation({
    mutationFn: (data: Partial<SessionConfig>) => sessionApi.updateConfig(data, 'admin'),
    onSuccess: () => {
      message.success(t('sessions.config.updateSuccess'));
      queryClient.invalidateQueries({ queryKey: ['sessionConfig'] });
      setConfigModalOpen(false);
    },
    onError: () => {
      message.error(t('sessions.config.updateFailed'));
    },
  });

  // Cleanup mutation
  const cleanupMutation = useMutation({
    mutationFn: () => sessionApi.cleanup('admin'),
    onSuccess: (result) => {
      message.success(t('sessions.cleanupSuccess', { count: result.cleaned_count }));
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['sessionStats'] });
    },
    onError: () => {
      message.error(t('sessions.cleanupFailed'));
    },
  });

  const handleOpenConfig = () => {
    if (config) {
      form.setFieldsValue({
        default_timeout: config.default_timeout,
        max_concurrent_sessions: config.max_concurrent_sessions,
      });
    }
    setConfigModalOpen(true);
  };

  const handleSaveConfig = async () => {
    try {
      const values = await form.validateFields();
      updateConfigMutation.mutate(values);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleViewDetail = (session: Session) => {
    setSelectedSession(session);
    setDetailModalOpen(true);
  };

  // Filter sessions by search text
  const filteredSessions = (sessionsResponse?.sessions || []).filter(
    (session) =>
      session.user_id.toLowerCase().includes(searchText.toLowerCase()) ||
      session.ip_address.includes(searchText)
  );

  // Group sessions by user for statistics
  const sessionsByUser = new Map<string, number>();
  (sessionsResponse?.sessions || []).forEach((session) => {
    const count = sessionsByUser.get(session.user_id) || 0;
    sessionsByUser.set(session.user_id, count + 1);
  });

  const columns: ColumnsType<Session> = [
    {
      title: t('sessions.columns.user'),
      dataIndex: 'user_id',
      key: 'user_id',
      render: (userId) => (
        <Space>
          <UserOutlined />
          <Text strong>{userId}</Text>
        </Space>
      ),
    },
    {
      title: t('sessions.columns.ipAddress'),
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (ip) => (
        <Space>
          <GlobalOutlined />
          <Text>{ip}</Text>
        </Space>
      ),
    },
    {
      title: t('sessions.columns.userAgent'),
      dataIndex: 'user_agent',
      key: 'user_agent',
      ellipsis: true,
      width: 200,
      render: (ua) => (
        <Tooltip title={ua}>
          <Space>
            <DesktopOutlined />
            <Text ellipsis style={{ maxWidth: 150 }}>
              {ua || '-'}
            </Text>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: t('sessions.columns.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).format('MM-DD HH:mm'),
    },
    {
      title: t('sessions.columns.lastActivity'),
      dataIndex: 'last_activity',
      key: 'last_activity',
      width: 120,
      render: (date) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(date).fromNow()}
        </Tooltip>
      ),
    },
    {
      title: t('sessions.columns.expires'),
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 120,
      render: (date) =>
        date ? (
          <Tag color={dayjs(date).isBefore(dayjs().add(10, 'minute')) ? 'warning' : 'default'}>
            {dayjs(date).fromNow()}
          </Tag>
        ) : (
          '-'
        ),
    },
    {
      title: t('common:actions'),
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => handleViewDetail(record)}
          >
            {t('common:view')}
          </Button>
          <Popconfirm
            title={t('sessions.terminateSession')}
            onConfirm={() => destroyMutation.mutate(record.id)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <ClockCircleOutlined /> {t('sessions.title')}
      </Title>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('sessions.activeSessions')}
              value={stats?.total_active_sessions || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('sessions.usersWithSessions')}
              value={stats?.total_users_with_sessions || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('sessions.defaultTimeout')}
              value={config?.default_timeout ? Math.floor(config.default_timeout / 60) : 0}
              suffix={t('sessions.minutes')}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('sessions.maxConcurrent')}
              value={config?.max_concurrent_sessions || 0}
              suffix={t('sessions.perUser')}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        title={t('sessions.activeSessions')}
        extra={
          <Space>
            <Input
              placeholder={t('sessions.searchPlaceholder')}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Button
              icon={<ClearOutlined />}
              onClick={() => cleanupMutation.mutate()}
              loading={cleanupMutation.isPending}
            >
              {t('sessions.cleanupExpired')}
            </Button>
            <Button icon={<SettingOutlined />} onClick={handleOpenConfig}>
              {t('sessions.configure')}
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['sessions'] })}
            >
              {t('common:refresh')}
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredSessions}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => t('common.totalSessions', { total }),
          }}
        />
      </Card>

      {/* Configuration Modal */}
      <Modal
        title={t('sessions.config.title')}
        open={configModalOpen}
        onOk={handleSaveConfig}
        onCancel={() => setConfigModalOpen(false)}
        confirmLoading={updateConfigMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="default_timeout"
            label={t('sessions.config.defaultTimeout')}
            rules={[{ required: true }]}
          >
            <InputNumber
              min={60}
              max={86400}
              style={{ width: '100%' }}
              addonAfter={
                <Text type="secondary">
                  = {form.getFieldValue('default_timeout') ? Math.floor(form.getFieldValue('default_timeout') / 60) : 0} {t('sessions.minutes')}
                </Text>
              }
            />
          </Form.Item>

          <Form.Item
            name="max_concurrent_sessions"
            label={t('sessions.config.maxConcurrent')}
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Session Detail Modal */}
      <Modal
        title={t('sessions.sessionDetails')}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Popconfirm
            key="logout"
            title={t('sessions.forceLogoutConfirm')}
            description={t('sessions.forceLogoutDesc')}
            onConfirm={() => {
              if (selectedSession) {
                forceLogoutMutation.mutate(selectedSession.user_id);
                setDetailModalOpen(false);
              }
            }}
          >
            <Button danger icon={<LogoutOutlined />}>
              {t('sessions.forceLogout')}
            </Button>
          </Popconfirm>,
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {t('common:close')}
          </Button>,
        ]}
        width={600}
      >
        {selectedSession && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Session ID">
              <Text code>{selectedSession.id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={t('sessions.columns.user')}>{selectedSession.user_id}</Descriptions.Item>
            <Descriptions.Item label={t('sessions.columns.ipAddress')}>{selectedSession.ip_address}</Descriptions.Item>
            <Descriptions.Item label={t('sessions.columns.userAgent')}>
              {selectedSession.user_agent || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('sessions.columns.created')}>
              {dayjs(selectedSession.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label={t('sessions.columns.lastActivity')}>
              {dayjs(selectedSession.last_activity).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label={t('sessions.columns.expires')}>
              {selectedSession.expires_at
                ? dayjs(selectedSession.expires_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            {selectedSession.metadata && Object.keys(selectedSession.metadata).length > 0 && (
              <Descriptions.Item label={t('sessions.metadata')}>
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedSession.metadata, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default SessionManager;
