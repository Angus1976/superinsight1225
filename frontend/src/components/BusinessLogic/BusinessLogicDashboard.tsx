// 业务逻辑仪表板组件
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Table,
  Tag,
  Progress,
  Space,
  Tabs,
  Alert,
  Spin,
  message,
  Modal,
  Form,
  Select,
  InputNumber,
  Typography,
  Tooltip,
  Badge,
} from 'antd';
import {
  BarChartOutlined,
  NodeIndexOutlined,
  BulbOutlined,
  SettingOutlined,
  DownloadOutlined,
  PlayCircleOutlined,
  EyeOutlined,
  NotificationOutlined,
} from '@ant-design/icons';
import { usePermissions } from '@/hooks/usePermissions';
import { RuleVisualization } from './RuleVisualization';
import { PatternAnalysis } from './PatternAnalysis';
import { InsightCards } from './InsightCards';
import { BusinessRuleManager } from './BusinessRuleManager';
import { InsightNotification } from './InsightNotification';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface BusinessLogicDashboardProps {
  projectId: string;
  onRuleExtracted?: (rules: BusinessRule[]) => void;
  onPatternDetected?: (patterns: Pattern[]) => void;
  loading?: boolean;
}

interface BusinessRule {
  id: string;
  name: string;
  description: string;
  pattern: string;
  rule_type: string;
  confidence: number;
  frequency: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Pattern {
  id: string;
  pattern_type: string;
  description: string;
  strength: number;
  evidence: any[];
  detected_at: string;
  last_seen: string;
}

interface BusinessInsight {
  id: string;
  insight_type: string;
  title: string;
  description: string;
  impact_score: number;
  recommendations: string[];
  data_points: any[];
  created_at: string;
  acknowledged_at?: string;
}

interface BusinessLogicStats {
  total_rules: number;
  active_rules: number;
  total_patterns: number;
  total_insights: number;
  last_analysis?: string;
  avg_rule_confidence: number;
  top_pattern_types: Array<{ type: string; count: number }>;
}

export const BusinessLogicDashboard: React.FC<BusinessLogicDashboardProps> = ({
  projectId,
  onRuleExtracted,
  onPatternDetected,
  loading = false,
}) => {
  const { annotation: annotationPerms } = usePermissions();
  const [stats, setStats] = useState<BusinessLogicStats | null>(null);
  const [rules, setRules] = useState<BusinessRule[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [insights, setInsights] = useState<BusinessInsight[]>([]);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [analysisModalVisible, setAnalysisModalVisible] = useState(false);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 加载仪表板数据
  const loadDashboardData = async () => {
    setDashboardLoading(true);
    try {
      // 并行加载所有数据
      const [statsRes, rulesRes, patternsRes, insightsRes] = await Promise.all([
        fetch(`/api/business-logic/stats/${projectId}`),
        fetch(`/api/business-logic/rules/${projectId}`),
        fetch(`/api/business-logic/patterns/${projectId}`),
        fetch(`/api/business-logic/insights/${projectId}?unacknowledged_only=true`),
      ]);

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (rulesRes.ok) {
        const rulesData = await rulesRes.json();
        setRules(rulesData);
      }

      if (patternsRes.ok) {
        const patternsData = await patternsRes.json();
        setPatterns(patternsData);
      }

      if (insightsRes.ok) {
        const insightsData = await insightsRes.json();
        setInsights(insightsData);
      }
    } catch (error) {
      console.error('加载仪表板数据失败:', error);
      message.error('加载仪表板数据失败');
    } finally {
      setDashboardLoading(false);
    }
  };

  // 执行模式分析
  const runPatternAnalysis = async (values: any) => {
    setAnalysisLoading(true);
    try {
      const response = await fetch('/api/business-logic/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          confidence_threshold: values.confidence_threshold || 0.8,
          min_frequency: values.min_frequency || 3,
          time_range_days: values.time_range_days,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        message.success(`模式分析完成，识别出 ${result.patterns.length} 个模式`);
        setPatterns(result.patterns);
        onPatternDetected?.(result.patterns);
        setAnalysisModalVisible(false);
        form.resetFields();
      } else {
        throw new Error('模式分析失败');
      }
    } catch (error) {
      console.error('模式分析失败:', error);
      message.error('模式分析失败');
    } finally {
      setAnalysisLoading(false);
    }
  };

  // 提取业务规则
  const extractBusinessRules = async () => {
    setAnalysisLoading(true);
    try {
      const response = await fetch('/api/business-logic/rules/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          threshold: 0.8,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        message.success(`规则提取完成，提取出 ${result.rules.length} 个规则`);
        setRules(result.rules);
        onRuleExtracted?.(result.rules);
      } else {
        throw new Error('规则提取失败');
      }
    } catch (error) {
      console.error('规则提取失败:', error);
      message.error('规则提取失败');
    } finally {
      setAnalysisLoading(false);
    }
  };

  // 导出业务逻辑
  const exportBusinessLogic = async (values: any) => {
    try {
      const response = await fetch('/api/business-logic/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          export_format: values.export_format || 'json',
          include_rules: values.include_rules !== false,
          include_patterns: values.include_patterns !== false,
          include_insights: values.include_insights !== false,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        message.success('导出任务已创建，请稍后下载');
        // 可以在这里处理下载链接
        window.open(result.download_url, '_blank');
        setExportModalVisible(false);
      } else {
        throw new Error('导出失败');
      }
    } catch (error) {
      console.error('导出失败:', error);
      message.error('导出失败');
    }
  };

  // 确认洞察
  const acknowledgeInsight = async (insightId: string) => {
    try {
      const response = await fetch(`/api/business-logic/insights/${insightId}/acknowledge`, {
        method: 'POST',
      });

      if (response.ok) {
        message.success('洞察已确认');
        // 更新洞察列表
        setInsights(insights.filter(insight => insight.id !== insightId));
      } else {
        throw new Error('确认洞察失败');
      }
    } catch (error) {
      console.error('确认洞察失败:', error);
      message.error('确认洞察失败');
    }
  };

  useEffect(() => {
    if (projectId) {
      loadDashboardData();
    }
  }, [projectId]);

  // 规则表格列定义
  const ruleColumns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: BusinessRule) => (
        <Space>
          <Text strong>{text}</Text>
          {!record.is_active && <Tag color="red">已停用</Tag>}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          sentiment_rule: { color: 'blue', text: '情感规则' },
          keyword_rule: { color: 'green', text: '关键词规则' },
          temporal_rule: { color: 'orange', text: '时间规则' },
          behavioral_rule: { color: 'purple', text: '行为规则' },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status={confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '频率',
      dataIndex: 'frequency',
      key: 'frequency',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  ];

  // 模式表格列定义
  const patternColumns = [
    {
      title: '模式类型',
      dataIndex: 'pattern_type',
      key: 'pattern_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          sentiment_correlation: { color: 'blue', text: '情感关联' },
          keyword_association: { color: 'green', text: '关键词关联' },
          temporal_trend: { color: 'orange', text: '时间趋势' },
          user_behavior: { color: 'purple', text: '用户行为' },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '强度',
      dataIndex: 'strength',
      key: 'strength',
      render: (strength: number) => (
        <Progress
          percent={Math.round(strength * 100)}
          size="small"
          status={strength >= 0.7 ? 'success' : strength >= 0.4 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '检测时间',
      dataIndex: 'detected_at',
      key: 'detected_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  ];

  if (loading || dashboardLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text>加载业务逻辑仪表板...</Text>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题和操作按钮 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>
            <BulbOutlined /> 业务逻辑仪表板
          </Title>
          <Text type="secondary">项目: {projectId}</Text>
        </Col>
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => setAnalysisModalVisible(true)}
              loading={analysisLoading}
              disabled={!annotationPerms.create}
            >
              运行分析
            </Button>
            <Button
              icon={<NodeIndexOutlined />}
              onClick={extractBusinessRules}
              loading={analysisLoading}
              disabled={!annotationPerms.create}
            >
              提取规则
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => setExportModalVisible(true)}
              disabled={!annotationPerms.view}
            >
              导出数据
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={loadDashboardData}
            >
              刷新
            </Button>
            <InsightNotification
              projectId={projectId}
              onInsightReceived={(insight) => {
                setInsights(prev => [insight, ...prev]);
                onPatternDetected?.([]);
              }}
              onInsightAcknowledge={acknowledgeInsight}
            />
          </Space>
        </Col>
      </Row>

      {/* 未确认洞察提醒 */}
      {insights.length > 0 && (
        <Alert
          message={`您有 ${insights.length} 个未确认的业务洞察`}
          description="点击查看详情并确认这些洞察"
          type="info"
          showIcon
          icon={<NotificationOutlined />}
          action={
            <Button size="small" onClick={() => setActiveTab('insights')}>
              查看洞察
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="业务规则总数"
                value={stats.total_rules}
                prefix={<NodeIndexOutlined />}
                suffix={
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    ({stats.active_rules} 个激活)
                  </Text>
                }
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="识别模式数"
                value={stats.total_patterns}
                prefix={<BarChartOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="业务洞察数"
                value={stats.total_insights}
                prefix={<BulbOutlined />}
                suffix={
                  insights.length > 0 && (
                    <Badge count={insights.length} style={{ marginLeft: 8 }} />
                  )
                }
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="平均置信度"
                value={stats.avg_rule_confidence}
                precision={2}
                suffix="%"
                formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主要内容标签页 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="概览" key="overview">
          <Row gutter={16}>
            <Col span={12}>
              <Card title="业务规则" extra={<Button type="link">查看全部</Button>}>
                <Table
                  dataSource={rules.slice(0, 5)}
                  columns={ruleColumns}
                  pagination={false}
                  size="small"
                  rowKey="id"
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="业务模式" extra={<Button type="link">查看全部</Button>}>
                <Table
                  dataSource={patterns.slice(0, 5)}
                  columns={patternColumns}
                  pagination={false}
                  size="small"
                  rowKey="id"
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="规则管理" key="rules">
          <BusinessRuleManager
            projectId={projectId}
            rules={rules}
            onRulesChange={setRules}
          />
        </TabPane>

        <TabPane tab="模式分析" key="patterns">
          <PatternAnalysis
            projectId={projectId}
            patterns={patterns}
            onPatternsChange={setPatterns}
          />
        </TabPane>

        <TabPane tab="可视化" key="visualization">
          <RuleVisualization
            projectId={projectId}
            rules={rules}
            patterns={patterns}
          />
        </TabPane>

        <TabPane
          tab={
            <Badge count={insights.length} size="small">
              业务洞察
            </Badge>
          }
          key="insights"
        >
          <InsightCards
            projectId={projectId}
            insights={insights}
            onInsightAcknowledge={acknowledgeInsight}
          />
        </TabPane>
      </Tabs>

      {/* 分析配置模态框 */}
      <Modal
        title="运行业务逻辑分析"
        open={analysisModalVisible}
        onCancel={() => setAnalysisModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={analysisLoading}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={runPatternAnalysis}
          initialValues={{
            confidence_threshold: 0.8,
            min_frequency: 3,
          }}
        >
          <Form.Item
            name="confidence_threshold"
            label="置信度阈值"
            tooltip="只有置信度高于此值的模式才会被识别"
          >
            <InputNumber
              min={0.1}
              max={1.0}
              step={0.1}
              style={{ width: '100%' }}
              formatter={(value) => `${((value as number) * 100).toFixed(0)}%`}
              parser={(value) => (parseFloat(value?.replace('%', '') || '0') / 100)}
            />
          </Form.Item>

          <Form.Item
            name="min_frequency"
            label="最小频率"
            tooltip="模式至少出现多少次才被认为是有效的"
          >
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="time_range_days"
            label="时间范围（天）"
            tooltip="分析最近多少天的数据，留空表示分析全部数据"
          >
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 导出配置模态框 */}
      <Modal
        title="导出业务逻辑数据"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        onOk={() => {
          const values = form.getFieldsValue();
          exportBusinessLogic(values);
        }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            export_format: 'json',
            include_rules: true,
            include_patterns: true,
            include_insights: true,
          }}
        >
          <Form.Item name="export_format" label="导出格式">
            <Select>
              <Select.Option value="json">JSON</Select.Option>
              <Select.Option value="csv">CSV</Select.Option>
              <Select.Option value="xml">XML</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="include_rules" valuePropName="checked">
            <span>包含业务规则</span>
          </Form.Item>

          <Form.Item name="include_patterns" valuePropName="checked">
            <span>包含业务模式</span>
          </Form.Item>

          <Form.Item name="include_insights" valuePropName="checked">
            <span>包含业务洞察</span>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};