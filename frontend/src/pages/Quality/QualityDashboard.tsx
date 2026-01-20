/**
 * Quality Dashboard - 质量仪表板
 * 显示质量概览、趋势图表、规则配置和预警列表
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Select,
  DatePicker,
  Progress,
  Alert,
  Tabs,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  message,
  Tooltip,
  Badge,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  TrophyOutlined,
  LineChartOutlined,
  SettingOutlined,
  BellOutlined,
  FileTextOutlined,
  ReloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { RangePicker } = DatePicker;
const { TabPane } = Tabs;
const { Option } = Select;

// Types
interface QualityOverview {
  averageScore: number;
  passRate: number;
  totalAnnotations: number;
  pendingIssues: number;
  activeAlerts: number;
  trend: TrendPoint[];
  topAnnotators: AnnotatorRanking[];
  issueDistribution: Record<string, number>;
}

interface TrendPoint {
  date: string;
  score: number;
  dimension?: string;
  count: number;
}

interface AnnotatorRanking {
  rank: number;
  annotatorId: string;
  annotatorName: string;
  totalAnnotations: number;
  averageScore: number;
  accuracy: number;
  passRate: number;
}

interface QualityRule {
  id: string;
  name: string;
  description?: string;
  ruleType: string;
  severity: string;
  priority: number;
  enabled: boolean;
  version: number;
}

interface QualityAlert {
  id: string;
  projectId: string;
  annotationId?: string;
  triggeredDimensions: string[];
  scores: Record<string, number>;
  severity: string;
  status: string;
  createdAt: string;
}

// Mock data
const mockOverview: QualityOverview = {
  averageScore: 0.85,
  passRate: 92.5,
  totalAnnotations: 1250,
  pendingIssues: 23,
  activeAlerts: 5,
  trend: [
    { date: '2026-01-08', score: 0.82, count: 150 },
    { date: '2026-01-09', score: 0.84, count: 180 },
    { date: '2026-01-10', score: 0.83, count: 165 },
    { date: '2026-01-11', score: 0.86, count: 190 },
    { date: '2026-01-12', score: 0.85, count: 175 },
    { date: '2026-01-13', score: 0.87, count: 200 },
    { date: '2026-01-14', score: 0.85, count: 190 },
  ],
  topAnnotators: [
    { rank: 1, annotatorId: '1', annotatorName: '张三', totalAnnotations: 320, averageScore: 0.95, accuracy: 0.96, passRate: 0.98 },
    { rank: 2, annotatorId: '2', annotatorName: '李四', totalAnnotations: 280, averageScore: 0.92, accuracy: 0.93, passRate: 0.95 },
    { rank: 3, annotatorId: '3', annotatorName: '王五', totalAnnotations: 250, averageScore: 0.89, accuracy: 0.90, passRate: 0.92 },
  ],
  issueDistribution: {
    'required_fields': 12,
    'format_validation': 8,
    'value_range': 3,
  },
};

const mockRules: QualityRule[] = [
  { id: '1', name: '必填字段检查', description: '检查所有必填字段是否已填写', ruleType: 'builtin', severity: 'high', priority: 100, enabled: true, version: 1 },
  { id: '2', name: '格式验证', description: '验证字段格式是否正确', ruleType: 'builtin', severity: 'medium', priority: 80, enabled: true, version: 1 },
  { id: '3', name: '值范围检查', description: '检查数值是否在有效范围内', ruleType: 'builtin', severity: 'medium', priority: 70, enabled: true, version: 1 },
  { id: '4', name: '自定义脚本', description: '执行自定义验证脚本', ruleType: 'custom', severity: 'low', priority: 50, enabled: false, version: 2 },
];

const mockAlerts: QualityAlert[] = [
  { id: '1', projectId: 'p1', annotationId: 'a1', triggeredDimensions: ['accuracy'], scores: { accuracy: 0.65 }, severity: 'high', status: 'open', createdAt: '2026-01-14T10:30:00Z' },
  { id: '2', projectId: 'p1', annotationId: 'a2', triggeredDimensions: ['completeness'], scores: { completeness: 0.70 }, severity: 'medium', status: 'acknowledged', createdAt: '2026-01-14T09:15:00Z' },
  { id: '3', projectId: 'p1', triggeredDimensions: ['timeliness'], scores: { timeliness: 0.55 }, severity: 'low', status: 'open', createdAt: '2026-01-13T16:45:00Z' },
];

// Components
const QualityDashboard: React.FC<{ projectId?: string }> = ({ projectId = 'default' }) => {
  const { t } = useTranslation(['quality', 'common']);
  const [overview, setOverview] = useState<QualityOverview>(mockOverview);
  const [rules, setRules] = useState<QualityRule[]>(mockRules);
  const [alerts, setAlerts] = useState<QualityAlert[]>(mockAlerts);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<QualityRule | null>(null);
  const [form] = Form.useForm();

  const handleRefresh = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      message.success(t('dashboard.dataRefreshed'));
    }, 1000);
  };

  const handleCreateRule = () => {
    setEditingRule(null);
    form.resetFields();
    setRuleModalVisible(true);
  };

  const handleEditRule = (rule: QualityRule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setRuleModalVisible(true);
  };

  const handleDeleteRule = (ruleId: string) => {
    Modal.confirm({
      title: t('common:confirmDelete'),
      content: t('messages.confirmDelete'),
      onOk: () => {
        setRules(rules.filter(r => r.id !== ruleId));
        message.success(t('messages.ruleDeleted'));
      },
    });
  };

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    setRules(rules.map(r => r.id === ruleId ? { ...r, enabled } : r));
    message.success(enabled ? t('messages.ruleEnabled') : t('messages.ruleDisabled'));
  };

  const handleSaveRule = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule) {
        setRules(rules.map(r => r.id === editingRule.id ? { ...r, ...values } : r));
        message.success(t('messages.ruleUpdated'));
      } else {
        const newRule: QualityRule = {
          id: String(Date.now()),
          ...values,
          version: 1,
        };
        setRules([...rules, newRule]);
        message.success(t('messages.ruleCreated'));
      }
      setRuleModalVisible(false);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleAcknowledgeAlert = (alertId: string) => {
    setAlerts(alerts.map(a => a.id === alertId ? { ...a, status: 'acknowledged' } : a));
    message.success(t('alerts.messages.acknowledged'));
  };

  const handleResolveAlert = (alertId: string) => {
    setAlerts(alerts.map(a => a.id === alertId ? { ...a, status: 'resolved' } : a));
    message.success(t('alerts.messages.resolved'));
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'gold';
      case 'low': return 'blue';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open': return 'error';
      case 'acknowledged': return 'warning';
      case 'resolved': return 'success';
      default: return 'default';
    }
  };

  const ruleColumns: ColumnsType<QualityRule> = [
    { title: t('rules.name'), dataIndex: 'name', key: 'name' },
    { title: t('rules.description'), dataIndex: 'description', key: 'description', ellipsis: true },
    { 
      title: t('rules.type'), 
      dataIndex: 'ruleType', 
      key: 'ruleType',
      render: (type: string) => (
        <Tag color={type === 'builtin' ? 'blue' : 'purple'}>
          {type === 'builtin' ? t('rules.types.builtin') : t('rules.types.custom')}
        </Tag>
      ),
    },
    { 
      title: t('rules.severity'), 
      dataIndex: 'severity', 
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{t(`rules.severities.${severity}`)}</Tag>
      ),
    },
    { title: t('rules.priority'), dataIndex: 'priority', key: 'priority' },
    { 
      title: t('common:status'), 
      dataIndex: 'enabled', 
      key: 'enabled',
      render: (enabled: boolean, record: QualityRule) => (
        <Switch checked={enabled} onChange={(checked) => handleToggleRule(record.id, checked)} />
      ),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      render: (_, record: QualityRule) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEditRule(record)}>{t('common:edit')}</Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDeleteRule(record.id)}>{t('common:delete')}</Button>
        </Space>
      ),
    },
  ];

  const alertColumns: ColumnsType<QualityAlert> = [
    { 
      title: t('alerts.columns.severity'), 
      dataIndex: 'severity', 
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{t(`alerts.severity.${severity}`)}</Tag>
      ),
    },
    { 
      title: t('alerts.columns.triggeredDimensions'), 
      dataIndex: 'triggeredDimensions', 
      key: 'triggeredDimensions',
      render: (dims: string[]) => dims.join(', '),
    },
    { 
      title: t('alerts.columns.scores'), 
      dataIndex: 'scores', 
      key: 'scores',
      render: (scores: Record<string, number>) => (
        <Space>
          {Object.entries(scores).map(([k, v]) => (
            <Tag key={k}>{k}: {(v * 100).toFixed(0)}%</Tag>
          ))}
        </Space>
      ),
    },
    { 
      title: t('alerts.columns.status'), 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => (
        <Badge status={getStatusColor(status) as any} text={t(`alerts.status.${status}`)} />
      ),
    },
    { 
      title: t('alerts.columns.createdAt'), 
      dataIndex: 'createdAt', 
      key: 'createdAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: t('alerts.columns.actions'),
      key: 'actions',
      render: (_, record: QualityAlert) => (
        <Space>
          {record.status === 'open' && (
            <Button type="link" onClick={() => handleAcknowledgeAlert(record.id)}>{t('alerts.actions.acknowledge')}</Button>
          )}
          {record.status !== 'resolved' && (
            <Button type="link" onClick={() => handleResolveAlert(record.id)}>{t('alerts.actions.resolve')}</Button>
          )}
        </Space>
      ),
    },
  ];

  const annotatorColumns: ColumnsType<AnnotatorRanking> = [
    { title: t('reports.annotatorRanking.columns.rank'), dataIndex: 'rank', key: 'rank', render: (rank: number) => <TrophyOutlined style={{ color: rank <= 3 ? '#faad14' : '#999' }} /> },
    { title: t('reports.annotatorRanking.columns.annotator'), dataIndex: 'annotatorName', key: 'annotatorName' },
    { title: t('reports.annotatorRanking.columns.annotations'), dataIndex: 'totalAnnotations', key: 'totalAnnotations' },
    { 
      title: t('reports.annotatorRanking.columns.avgScore'), 
      dataIndex: 'averageScore', 
      key: 'averageScore',
      render: (score: number) => <Progress percent={score * 100} size="small" format={(p) => `${p?.toFixed(0)}%`} />,
    },
    { 
      title: t('reports.annotatorRanking.columns.accuracy'), 
      dataIndex: 'accuracy', 
      key: 'accuracy',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
    { 
      title: t('reports.annotatorRanking.columns.passRate'), 
      dataIndex: 'passRate', 
      key: 'passRate',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>{t('dashboard.title')}</h2>
        <Space>
          <RangePicker />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>{t('dashboard.refresh')}</Button>
          <Button type="primary" icon={<ExportOutlined />}>{t('dashboard.exportReport')}</Button>
        </Space>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={<span><LineChartOutlined />{t('dashboard.overview')}</span>} key="overview">
          {/* 关键指标 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('dashboard.averageScore')}
                  value={overview.averageScore * 100}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: overview.averageScore >= 0.8 ? '#3f8600' : '#cf1322' }}
                  prefix={overview.averageScore >= 0.8 ? <CheckCircleOutlined /> : <WarningOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('dashboard.passRate')}
                  value={overview.passRate}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: overview.passRate >= 90 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('dashboard.pendingIssues')}
                  value={overview.pendingIssues}
                  valueStyle={{ color: overview.pendingIssues > 20 ? '#cf1322' : '#3f8600' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title={t('dashboard.activeAlerts')}
                  value={overview.activeAlerts}
                  valueStyle={{ color: overview.activeAlerts > 0 ? '#faad14' : '#3f8600' }}
                  prefix={<BellOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* 趋势和排名 */}
          <Row gutter={16}>
            <Col span={16}>
              <Card title={t('dashboard.qualityTrend')} extra={<Select defaultValue="week" style={{ width: 100 }}><Option value="week">{t('dashboard.thisWeek')}</Option><Option value="month">{t('dashboard.thisMonth')}</Option></Select>}>
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                  <span style={{ color: '#999' }}>{t('reports.projectReport.trendChart')}</span>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card title={t('dashboard.annotatorRanking')} extra={<Button type="link">{t('dashboard.viewAll')}</Button>}>
                <Table
                  dataSource={overview.topAnnotators}
                  columns={annotatorColumns}
                  pagination={false}
                  size="small"
                  rowKey="annotatorId"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab={<span><SettingOutlined />{t('dashboard.ruleConfig')}</span>} key="rules">
          <Card
            title={t('rules.title')}
            extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleCreateRule}>{t('rules.addRule')}</Button>}
          >
            <Table
              dataSource={rules}
              columns={ruleColumns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={<span><BellOutlined />{t('dashboard.alertList')}</span>} key="alerts">
          <Card title={t('alerts.title')}>
            <Table
              dataSource={alerts}
              columns={alertColumns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={<span><FileTextOutlined />{t('dashboard.reports')}</span>} key="reports">
          <Card title={t('reports.title')}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert message={t('dashboard.selectReportType')} type="info" showIcon />
              <Row gutter={16}>
                <Col span={8}>
                  <Card hoverable onClick={() => message.info(t('messages.reportGenerated'))}>
                    <Statistic title={t('dashboard.projectReport')} value={t('dashboard.generate')} prefix={<FileTextOutlined />} />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card hoverable onClick={() => message.info(t('messages.rankingGenerated'))}>
                    <Statistic title={t('dashboard.annotatorRankingReport')} value={t('dashboard.generate')} prefix={<TrophyOutlined />} />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card hoverable onClick={() => message.info(t('messages.reportGenerated'))}>
                    <Statistic title={t('dashboard.trendReport')} value={t('dashboard.generate')} prefix={<LineChartOutlined />} />
                  </Card>
                </Col>
              </Row>
            </Space>
          </Card>
        </TabPane>
      </Tabs>

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? t('rules.editRule') : t('rules.addRule')}
        open={ruleModalVisible}
        onOk={handleSaveRule}
        onCancel={() => setRuleModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('rules.name')} rules={[{ required: true, message: t('rules.inputRuleName') }]}>
            <Input placeholder={t('rules.inputRuleName')} />
          </Form.Item>
          <Form.Item name="description" label={t('rules.description')}>
            <Input.TextArea placeholder={t('rules.inputRuleDesc')} rows={3} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="ruleType" label={t('rules.type')} rules={[{ required: true }]}>
                <Select placeholder={t('rules.selectRuleType')}>
                  <Option value="builtin">{t('rules.types.builtin')}</Option>
                  <Option value="custom">{t('rules.types.custom')}</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="severity" label={t('rules.severity')} rules={[{ required: true }]}>
                <Select placeholder={t('rules.selectPriority')}>
                  <Option value="critical">{t('rules.severities.critical')}</Option>
                  <Option value="high">{t('rules.severities.high')}</Option>
                  <Option value="medium">{t('rules.severities.medium')}</Option>
                  <Option value="low">{t('rules.severities.low')}</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="priority" label={t('rules.priority')}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} placeholder="0-100" />
          </Form.Item>
          <Form.Item name="enabled" label={t('rules.enabledStatus')} valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QualityDashboard;
