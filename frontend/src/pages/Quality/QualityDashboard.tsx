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
      message.success('数据已刷新');
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
      title: '确认删除',
      content: '确定要删除这条规则吗？',
      onOk: () => {
        setRules(rules.filter(r => r.id !== ruleId));
        message.success('规则已删除');
      },
    });
  };

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    setRules(rules.map(r => r.id === ruleId ? { ...r, enabled } : r));
    message.success(enabled ? '规则已启用' : '规则已禁用');
  };

  const handleSaveRule = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule) {
        setRules(rules.map(r => r.id === editingRule.id ? { ...r, ...values } : r));
        message.success('规则已更新');
      } else {
        const newRule: QualityRule = {
          id: String(Date.now()),
          ...values,
          version: 1,
        };
        setRules([...rules, newRule]);
        message.success('规则已创建');
      }
      setRuleModalVisible(false);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleAcknowledgeAlert = (alertId: string) => {
    setAlerts(alerts.map(a => a.id === alertId ? { ...a, status: 'acknowledged' } : a));
    message.success('预警已确认');
  };

  const handleResolveAlert = (alertId: string) => {
    setAlerts(alerts.map(a => a.id === alertId ? { ...a, status: 'resolved' } : a));
    message.success('预警已解决');
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
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { 
      title: '类型', 
      dataIndex: 'ruleType', 
      key: 'ruleType',
      render: (type: string) => (
        <Tag color={type === 'builtin' ? 'blue' : 'purple'}>
          {type === 'builtin' ? '内置' : '自定义'}
        </Tag>
      ),
    },
    { 
      title: '严重程度', 
      dataIndex: 'severity', 
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      ),
    },
    { title: '优先级', dataIndex: 'priority', key: 'priority' },
    { 
      title: '状态', 
      dataIndex: 'enabled', 
      key: 'enabled',
      render: (enabled: boolean, record: QualityRule) => (
        <Switch checked={enabled} onChange={(checked) => handleToggleRule(record.id, checked)} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: QualityRule) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEditRule(record)}>编辑</Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDeleteRule(record.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  const alertColumns: ColumnsType<QualityAlert> = [
    { 
      title: '严重程度', 
      dataIndex: 'severity', 
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      ),
    },
    { 
      title: '触发维度', 
      dataIndex: 'triggeredDimensions', 
      key: 'triggeredDimensions',
      render: (dims: string[]) => dims.join(', '),
    },
    { 
      title: '分数', 
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
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => (
        <Badge status={getStatusColor(status) as any} text={status} />
      ),
    },
    { 
      title: '创建时间', 
      dataIndex: 'createdAt', 
      key: 'createdAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: QualityAlert) => (
        <Space>
          {record.status === 'open' && (
            <Button type="link" onClick={() => handleAcknowledgeAlert(record.id)}>确认</Button>
          )}
          {record.status !== 'resolved' && (
            <Button type="link" onClick={() => handleResolveAlert(record.id)}>解决</Button>
          )}
        </Space>
      ),
    },
  ];

  const annotatorColumns: ColumnsType<AnnotatorRanking> = [
    { title: '排名', dataIndex: 'rank', key: 'rank', render: (rank: number) => <TrophyOutlined style={{ color: rank <= 3 ? '#faad14' : '#999' }} /> },
    { title: '标注员', dataIndex: 'annotatorName', key: 'annotatorName' },
    { title: '标注数', dataIndex: 'totalAnnotations', key: 'totalAnnotations' },
    { 
      title: '平均分', 
      dataIndex: 'averageScore', 
      key: 'averageScore',
      render: (score: number) => <Progress percent={score * 100} size="small" format={(p) => `${p?.toFixed(0)}%`} />,
    },
    { 
      title: '准确率', 
      dataIndex: 'accuracy', 
      key: 'accuracy',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
    { 
      title: '通过率', 
      dataIndex: 'passRate', 
      key: 'passRate',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>质量仪表板</h2>
        <Space>
          <RangePicker />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>刷新</Button>
          <Button type="primary" icon={<ExportOutlined />}>导出报告</Button>
        </Space>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={<span><LineChartOutlined />概览</span>} key="overview">
          {/* 关键指标 */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均质量分"
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
                  title="通过率"
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
                  title="待处理问题"
                  value={overview.pendingIssues}
                  valueStyle={{ color: overview.pendingIssues > 20 ? '#cf1322' : '#3f8600' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="活跃预警"
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
              <Card title="质量趋势" extra={<Select defaultValue="week" style={{ width: 100 }}><Option value="week">本周</Option><Option value="month">本月</Option></Select>}>
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fafafa' }}>
                  <span style={{ color: '#999' }}>趋势图表 (需要集成图表库)</span>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card title="标注员排名" extra={<Button type="link">查看全部</Button>}>
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

        <TabPane tab={<span><SettingOutlined />规则配置</span>} key="rules">
          <Card
            title="质量规则"
            extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleCreateRule}>添加规则</Button>}
          >
            <Table
              dataSource={rules}
              columns={ruleColumns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={<span><BellOutlined />预警列表</span>} key="alerts">
          <Card title="质量预警">
            <Table
              dataSource={alerts}
              columns={alertColumns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={<span><FileTextOutlined />报告</span>} key="reports">
          <Card title="质量报告">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert message="选择报告类型和时间范围，生成质量分析报告" type="info" showIcon />
              <Row gutter={16}>
                <Col span={8}>
                  <Card hoverable onClick={() => message.info('生成项目报告')}>
                    <Statistic title="项目质量报告" value="生成" prefix={<FileTextOutlined />} />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card hoverable onClick={() => message.info('生成排名报告')}>
                    <Statistic title="标注员排名报告" value="生成" prefix={<TrophyOutlined />} />
                  </Card>
                </Col>
                <Col span={8}>
                  <Card hoverable onClick={() => message.info('生成趋势报告')}>
                    <Statistic title="质量趋势报告" value="生成" prefix={<LineChartOutlined />} />
                  </Card>
                </Col>
              </Row>
            </Space>
          </Card>
        </TabPane>
      </Tabs>

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? '编辑规则' : '添加规则'}
        open={ruleModalVisible}
        onOk={handleSaveRule}
        onCancel={() => setRuleModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
            <Input placeholder="请输入规则名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="请输入规则描述" rows={3} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="ruleType" label="规则类型" rules={[{ required: true }]}>
                <Select placeholder="选择规则类型">
                  <Option value="builtin">内置规则</Option>
                  <Option value="custom">自定义规则</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="severity" label="严重程度" rules={[{ required: true }]}>
                <Select placeholder="选择严重程度">
                  <Option value="critical">严重</Option>
                  <Option value="high">高</Option>
                  <Option value="medium">中</Option>
                  <Option value="low">低</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="priority" label="优先级">
            <InputNumber min={0} max={100} style={{ width: '100%' }} placeholder="0-100" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QualityDashboard;
