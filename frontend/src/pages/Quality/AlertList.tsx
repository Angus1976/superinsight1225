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
import type { ColumnsType } from 'antd/es/table';
import { qualityApi, type QualityAlert, type AlertConfig } from '@/services/qualityApi';

const { Option } = Select;

interface AlertListProps {
  projectId: string;
}

const AlertList: React.FC<AlertListProps> = ({ projectId }) => {
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
      message.error('加载预警列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      await qualityApi.acknowledgeAlert(alertId);
      message.success('预警已确认');
      loadAlerts();
    } catch {
      message.error('操作失败');
    }
  };

  const handleResolve = async (alertId: string) => {
    try {
      await qualityApi.resolveAlert(alertId);
      message.success('预警已解决');
      loadAlerts();
    } catch {
      message.error('操作失败');
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
      message.success('阈值配置已保存');
      setConfigModalVisible(false);
    } catch {
      message.error('保存失败');
    }
  };

  const handleSetSilence = async () => {
    try {
      const values = await silenceForm.validateFields();
      await qualityApi.setSilencePeriod({
        project_id: projectId,
        duration_minutes: values.duration,
      });
      message.success(`静默期已设置: ${values.duration} 分钟`);
      setSilenceModalVisible(false);
    } catch {
      message.error('设置失败');
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
      open: { status: 'error', text: '待处理' },
      acknowledged: { status: 'warning', text: '已确认' },
      resolved: { status: 'success', text: '已解决' },
    };
    const config = statusMap[status] || { status: 'default' as const, text: status };
    return <Badge status={config.status} text={config.text} />;
  };

  const columns: ColumnsType<QualityAlert> = [
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => <Tag color={getSeverityColor(severity)}>{severity.toUpperCase()}</Tag>,
      filters: [
        { text: '严重', value: 'critical' },
        { text: '高', value: 'high' },
        { text: '中', value: 'medium' },
        { text: '低', value: 'low' },
      ],
      onFilter: (value, record) => record.severity === value,
    },
    {
      title: '触发维度',
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
      title: '分数',
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
      title: '升级级别',
      dataIndex: 'escalation_level',
      key: 'escalation_level',
      width: 100,
      render: (level: number) => (level > 0 ? <Tag color="red">Level {level}</Tag> : '-'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title="查看详情">
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)} />
          </Tooltip>
          {record.status === 'open' && (
            <Button type="link" size="small" onClick={() => handleAcknowledge(record.id)}>
              确认
            </Button>
          )}
          {record.status !== 'resolved' && (
            <Button type="link" size="small" onClick={() => handleResolve(record.id)}>
              解决
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
          message={`有 ${criticalCount} 个严重预警需要立即处理`}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" danger onClick={() => setStatusFilter('open')}>
              查看
            </Button>
          }
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="待处理预警" value={openCount} prefix={<ExclamationCircleOutlined />} valueStyle={{ color: openCount > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="严重预警" value={criticalCount} prefix={<BellOutlined />} valueStyle={{ color: criticalCount > 0 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已确认" value={alerts.filter((a) => a.status === 'acknowledged').length} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已解决" value={alerts.filter((a) => a.status === 'resolved').length} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
      </Row>

      <Card
        title="质量预警"
        extra={
          <Space>
            <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 120 }} allowClear placeholder="状态筛选">
              <Option value="open">待处理</Option>
              <Option value="acknowledged">已确认</Option>
              <Option value="resolved">已解决</Option>
            </Select>
            <Button icon={<ClockCircleOutlined />} onClick={() => setSilenceModalVisible(true)}>
              设置静默期
            </Button>
            <Button icon={<SettingOutlined />} onClick={() => setConfigModalVisible(true)}>
              配置阈值
            </Button>
          </Space>
        }
      >
        <Table dataSource={alerts} columns={columns} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
      </Card>

      {/* 阈值配置弹窗 */}
      <Modal title="配置预警阈值" open={configModalVisible} onOk={handleConfigureThresholds} onCancel={() => setConfigModalVisible(false)}>
        <Form form={form} layout="vertical" initialValues={{ accuracy_threshold: 0.7, completeness_threshold: 0.8, timeliness_threshold: 0.6, channels: ['in_app'] }}>
          <Form.Item name="accuracy_threshold" label="准确性阈值" help="低于此值将触发预警">
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="completeness_threshold" label="完整性阈值">
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="timeliness_threshold" label="时效性阈值">
            <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="channels" label="通知渠道">
            <Select mode="multiple" placeholder="选择通知渠道">
              <Option value="in_app">站内通知</Option>
              <Option value="email">邮件</Option>
              <Option value="webhook">Webhook</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 静默期设置弹窗 */}
      <Modal title="设置静默期" open={silenceModalVisible} onOk={handleSetSilence} onCancel={() => setSilenceModalVisible(false)}>
        <Form form={silenceForm} layout="vertical">
          <Form.Item name="duration" label="静默时长（分钟）" rules={[{ required: true }]}>
            <Select placeholder="选择静默时长">
              <Option value={30}>30 分钟</Option>
              <Option value={60}>1 小时</Option>
              <Option value={120}>2 小时</Option>
              <Option value={240}>4 小时</Option>
              <Option value={480}>8 小时</Option>
              <Option value={1440}>24 小时</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 预警详情抽屉 */}
      <Drawer title="预警详情" open={detailDrawerVisible} onClose={() => setDetailDrawerVisible(false)} width={500}>
        {selectedAlert && (
          <>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="预警ID">{selectedAlert.id}</Descriptions.Item>
              <Descriptions.Item label="严重程度">
                <Tag color={getSeverityColor(selectedAlert.severity)}>{selectedAlert.severity}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">{getStatusBadge(selectedAlert.status)}</Descriptions.Item>
              <Descriptions.Item label="触发维度">{selectedAlert.triggered_dimensions.join(', ')}</Descriptions.Item>
              <Descriptions.Item label="升级级别">{selectedAlert.escalation_level}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{new Date(selectedAlert.created_at).toLocaleString()}</Descriptions.Item>
              {selectedAlert.resolved_at && <Descriptions.Item label="解决时间">{new Date(selectedAlert.resolved_at).toLocaleString()}</Descriptions.Item>}
            </Descriptions>
            <Card title="分数详情" size="small" style={{ marginTop: 16 }}>
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
