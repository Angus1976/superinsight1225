/**
 * Alert List Component - 预警列表组件
 * 实现质量预警的查看和处理功能
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Badge,
  Modal,
  Form,
  InputNumber,
  Select,
  message,
  Tooltip,
  Row,
  Col,
  Statistic,
  Alert,
  Drawer,
  Timeline,
  Descriptions,
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  ClockCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { qualityApi, type QualityAlert, type AlertConfig } from '@/services/qualityApi';

const { Option } = Select;

interface AlertListProps {
  projectId: string;
}

const AlertList: React.FC<AlertListProps> = ({ projectId }) => {
  const { t } = useTranslation(['quality', 'common']);
  const [alerts, setAlerts] = useState<QualityAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [silenceModalVisible, setSilenceModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<QualityAlert | null>(null);
  const [form] = Form.useForm();
  const [silenceForm] = Form.useForm();

  useEffect(() => {
    loadAlerts();
  }, [projectId, statusFilter]);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await qualityApi.listAlerts(projectId, statusFilter);
      setAlerts(data);
    } catch {
      message.error(t('alerts.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      await qualityApi.acknowledgeAlert(alertId);
      message.success(t('alerts.messages.acknowledged'));
      loadAlerts();
    } catch {
      message.error(t('alerts.messages.operationFailed'));
    }
  };

  const handleResolve = async (alertId: string) => {
    try {
      await qualityApi.resolveAlert(alertId);
      message.success(t('alerts.messages.resolved'));
      loadAlerts();
    } catch {
      message.error(t('alerts.messages.operationFailed'));
    }
  };

  const handleConfigureThresholds = async () => {
    try {
      const values = await form.validateFields();
      await qualityApi.configureAlerts({
        project_id: projectId,
        thresholds: {
          accuracy: values.accuracy_threshold,
          completeness: values.completeness_threshold,
          timeliness: values.timeliness_threshold,
        },
        notification_channels: values.channels,
      });
      message.success(t('alerts.messages.thresholdSaved'));
      setConfigModalVisible(false);
    } catch {
      message.error(t('alerts.messages.saveFailed'));
    }
  };

  const handleSetSilence = async () => {
    try {
      const values = await silenceForm.validateFields();
      await qualityApi.setSilencePeriod({
        project_id: projectId,
        duration_minutes: values.duration,
      });
      message.success(t('alerts.messages.silenceSet', { duration: values.duration }));
      setSilenceModalVisible(false);
    } catch {
      message.error(t('alerts.messages.setFailed'));
    }
  };

  const handleViewDetail = (alert: QualityAlert) => {
    setSelectedAlert(alert);
    setDetailDrawerVisible(true);
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'red',
      high: 'orange',
      medium: 'gold',
      low: 'blue',
    };
    return colors[severity] || 'default';
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { status: 'error' | 'warning' | 'success'; text: string }> = {
      open: { status: 'error', text: t('alerts.status.open') },
      acknowledged: { status: 'warning', text: t('alerts.status.acknowledged') },
      resolved: { status: 'success', text: t('alerts.status.resolved') },
    };
    const config = statusMap[status] || { status: 'default' as const, text: status };
    return <Badge status={config.status} text={config.text} />;
  };

  const columns: ColumnsType<QualityAlert> = [
    {
      title: t('alerts.columns.severity'),
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => <Tag color={getSeverityColor(severity)}>{t(`alerts.severity.${severity}`)}</Tag>,
      filters: [
        { text: t('alerts.severity.critical'), value: 'critical' },
        { text: t('alerts.severity.high'), value: 'high' },
        { text: t('alerts.severity.medium'), value: 'medium' },
        { text: t('alerts.severity.low'), value: 'low' },
      ],
      onFilter: (value, record) => record.severity === value,
    },
    {
      title: t('alerts.columns.triggeredDimensions'),
      dataIndex: 'triggered_dimensions',
      key: 'triggered_dimensions',
      render: (dims: string[]) => (
        <Space wrap>
          {dims.map((dim) => (
            <Tag key={dim}>{dim}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('alerts.columns.scores'),
      dataIndex: 'scores',
      key: 'scores',
      render: (scores: Record<string, number>) => (
        <Space wrap>
          {Object.entries(scores).map(([k, v]) => (
            <Tooltip key={k} title={k}>
              <Tag color={v < 0.6 ? 'red' : v < 0.8 ? 'gold' : 'green'}>{(v * 100).toFixed(0)}%</Tag>
            </Tooltip>
          ))}
        </Space>
      ),
    },
    {
      title: t('alerts.columns.escalationLevel'),
      dataIndex: 'escalation_level',
      key: 'escalation_level',
      width: 100,
      render: (level: number) => (level > 0 ? <Tag color="red">Level {level}</Tag> : '-'),
    },
    {
      title: t('alerts.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: t('alerts.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: t('alerts.columns.actions'),
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('alerts.actions.viewDetail')}>
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)} />
          </Tooltip>
          {record.status === 'open' && (
            <Button type="link" size="small" onClick={() => handleAcknowledge(record.id)}>
              {t('alerts.actions.acknowledge')}
            </Button>
          )}
          {record.status !== 'resolved' && (
            <Button type="link" size="small" onClick={() => handleResolve(record.id)}>
              {t('alerts.actions.resolve')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const openCount = alerts.filter((a) => a.status === 'open').length;
  const criticalCount = alerts.filter((a) => a.severity === 'critical' && a.status !== 'resolved').length;

  return (
    <div>
      {criticalCount > 0 && (
        <Alert
          message={t('alerts.criticalAlert', { count: criticalCount })}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" danger onClick={() => setStatusFilter('open')}>
              {t('alerts.view')}
            </Button>
          }
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('alerts.stats.pending')} value={openCount} prefix={<ExclamationCircleOutlined />} valueStyle={{ color: openCount > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('alerts.stats.critical')} value={criticalCount} prefix={<BellOutlined />} valueStyle={{ color: criticalCount > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('alerts.stats.acknowledged')} value={alerts.filter((a) => a.status === 'acknowledged').length} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('alerts.stats.resolved')} value={alerts.filter((a) => a.status === 'resolved').length} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
      </Row>

      <Card
        title={t('alerts.title')}
        extra={
          <Space>
            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }} allowClear placeholder={t('alerts.filter.status')}>
              <Option value="open">{t('alerts.status.open')}</Option>
              <Option value="acknowledged">{t('alerts.status.acknowledged')}</Option>
              <Option value="resolved">{t('alerts.status.resolved')}</Option>
            </Select>
            <Button icon={<ClockCircleOutlined />} onClick={() => setSilenceModalVisible(true)}>
              {t('alerts.silencePeriod')}
            </Button>
            <Button icon={<SettingOutlined />} onClick={() => setConfigModalVisible(true)}>
              {t('alerts.configThreshold')}
            </Button>
          </Space>
        }
      >
        <Table dataSource={alerts} columns={columns} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
      </Card>

      {/* 阈值配置弹窗 */}
      <Modal title={t('alerts.thresholdModal.title')} open={configModalVisible} onOk={handleConfigureThresholds} onCancel={() => setConfigModalVisible(false)}>
        <Form form={form} layout="vertical" initialValues={{ accuracy_threshold: 0.7, completeness_threshold: 0.8, timeliness_threshold: 0.6, channels: ['in_app'] }}>
          <Form.Item name="accuracy_threshold" label={t('alerts.thresholdModal.accuracyThreshold')} help={t('alerts.thresholdModal.thresholdHelp')}>
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="completeness_threshold" label={t('alerts.thresholdModal.completenessThreshold')}>
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="timeliness_threshold" label={t('alerts.thresholdModal.timelinessThreshold')}>
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="channels" label={t('alerts.thresholdModal.notificationChannels')}>
            <Select mode="multiple" placeholder={t('alerts.thresholdModal.selectChannels')}>
              <Option value="in_app">{t('alerts.thresholdModal.inApp')}</Option>
              <Option value="email">{t('alerts.thresholdModal.email')}</Option>
              <Option value="webhook">{t('alerts.thresholdModal.webhook')}</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 静默期设置弹窗 */}
      <Modal title={t('alerts.silenceModal.title')} open={silenceModalVisible} onOk={handleSetSilence} onCancel={() => setSilenceModalVisible(false)}>
        <Form form={silenceForm} layout="vertical">
          <Form.Item name="duration" label={t('alerts.silenceModal.duration')} rules={[{ required: true }]}>
            <Select placeholder={t('alerts.silenceModal.selectDuration')}>
              <Option value={30}>{t('alerts.silenceModal.30min')}</Option>
              <Option value={60}>{t('alerts.silenceModal.1hour')}</Option>
              <Option value={120}>{t('alerts.silenceModal.2hours')}</Option>
              <Option value={240}>{t('alerts.silenceModal.4hours')}</Option>
              <Option value={480}>{t('alerts.silenceModal.8hours')}</Option>
              <Option value={1440}>{t('alerts.silenceModal.24hours')}</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 预警详情抽屉 */}
      <Drawer title={t('alerts.detailDrawer.title')} open={detailDrawerVisible} onClose={() => setDetailDrawerVisible(false)} width={500}>
        {selectedAlert && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label={t('alerts.detailDrawer.alertId')}>{selectedAlert.id}</Descriptions.Item>
              <Descriptions.Item label={t('alerts.detailDrawer.severity')}>
                <Tag color={getSeverityColor(selectedAlert.severity)}>{t(`alerts.severity.${selectedAlert.severity}`)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('alerts.detailDrawer.status')}>{getStatusBadge(selectedAlert.status)}</Descriptions.Item>
              <Descriptions.Item label={t('alerts.detailDrawer.triggeredDimensions')}>{selectedAlert.triggered_dimensions.join(', ')}</Descriptions.Item>
              <Descriptions.Item label={t('alerts.detailDrawer.escalationLevel')}>{selectedAlert.escalation_level}</Descriptions.Item>
              <Descriptions.Item label={t('alerts.detailDrawer.createdAt')}>{new Date(selectedAlert.created_at).toLocaleString()}</Descriptions.Item>
              {selectedAlert.resolved_at && <Descriptions.Item label={t('alerts.detailDrawer.resolvedAt')}>{new Date(selectedAlert.resolved_at).toLocaleString()}</Descriptions.Item>}
            </Descriptions>
            <Card title={t('alerts.detailDrawer.scoreDetail')} size="small" style={{ marginTop: 16 }}>
              {Object.entries(selectedAlert.scores).map(([dim, score]) => (
                <div key={dim} style={{ marginBottom: 8 }}>
                  <span>{dim}: </span>
                  <Tag color={score < 0.6 ? 'red' : score < 0.8 ? 'gold' : 'green'}>{(score * 100).toFixed(1)}%</Tag>
                </div>
              ))}
            </Card>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default AlertList;
