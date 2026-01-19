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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['businessLogic', 'common']);
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
      message.error(t('dashboard.loadError'));
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
        message.success(t('analysis.success', { count: result.patterns.length }));
        setPatterns(result.patterns);
        onPatternDetected?.(result.patterns);
        setAnalysisModalVisible(false);
        form.resetFields();
      } else {
        throw new Error(t('analysis.error'));
      }
    } catch (error) {
      console.error('模式分析失败:', error);
      message.error(t('analysis.error'));
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
        message.success(t('analysis.extractSuccess', { count: result.rules.length }));
        setRules(result.rules);
        onRuleExtracted?.(result.rules);
      } else {
        throw new Error(t('analysis.extractError'));
      }
    } catch (error) {
      console.error('规则提取失败:', error);
      message.error(t('analysis.extractError'));
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
        message.success(t('export.success'));
        // 可以在这里处理下载链接
        window.open(result.download_url, '_blank');
        setExportModalVisible(false);
      } else {
        throw new Error(t('export.error'));
      }
    } catch (error) {
      console.error('导出失败:', error);
      message.error(t('export.error'));
    }
  };

  // 确认洞察
  const acknowledgeInsight = async (insightId: string) => {
    try {
      const response = await fetch(`/api/business-logic/insights/${insightId}/acknowledge`, {
        method: 'POST',
      });

      if (response.ok) {
        message.success(t('insights.acknowledged'));
        // 更新洞察列表
        setInsights(insights.filter(insight => insight.id !== insightId));
      } else {
        throw new Error(t('insights.acknowledgeError'));
      }
    } catch (error) {
      console.error('确认洞察失败:', error);
      message.error(t('insights.acknowledgeError'));
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
      title: t('rules.columns.ruleName'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: BusinessRule) => (
        <Space>
          <Text strong>{text}</Text>
          {!record.is_active && <Tag color="red">{t('rules.status.disabled')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('rules.columns.type'),
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          sentiment_rule: { color: 'blue', text: t('rules.types.sentimentRule') },
          keyword_rule: { color: 'green', text: t('rules.types.keywordRule') },
          temporal_rule: { color: 'orange', text: t('rules.types.temporalRule') },
          behavioral_rule: { color: 'purple', text: t('rules.types.behavioralRule') },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: t('rules.columns.confidence'),
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
      title: t('rules.columns.frequency'),
      dataIndex: 'frequency',
      key: 'frequency',
    },
    {
      title: t('rules.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  ];

  // 模式表格列定义
  const patternColumns = [
    {
      title: t('patterns.columns.patternType'),
      dataIndex: 'pattern_type',
      key: 'pattern_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          sentiment_correlation: { color: 'blue', text: t('patterns.types.sentimentCorrelation') },
          keyword_association: { color: 'green', text: t('patterns.types.keywordAssociation') },
          temporal_trend: { color: 'orange', text: t('patterns.types.temporalTrend') },
          user_behavior: { color: 'purple', text: t('patterns.types.userBehavior') },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: t('patterns.columns.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('patterns.columns.strength'),
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
      title: t('patterns.columns.detectedAt'),
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
          <Text>{t('dashboard.loading')}</Text>
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
            <BulbOutlined /> {t('dashboard.title')}
          </Title>
          <Text type="secondary">{t('dashboard.project')}: {projectId}</Text>
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
              {t('dashboard.runAnalysis')}
            </Button>
            <Button
              icon={<NodeIndexOutlined />}
              onClick={extractBusinessRules}
              loading={analysisLoading}
              disabled={!annotationPerms.create}
            >
              {t('dashboard.extractRules')}
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={() => setExportModalVisible(true)}
              disabled={!annotationPerms.view}
            >
              {t('dashboard.exportData')}
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={loadDashboardData}
            >
              {t('common:refresh')}
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
          message={t('dashboard.unacknowledgedInsights', { count: insights.length })}
          description={t('dashboard.clickToViewInsights')}
          type="info"
          showIcon
          icon={<NotificationOutlined />}
          action={
            <Button size="small" onClick={() => setActiveTab('insights')}>
              {t('dashboard.viewInsights')}
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
                title={t('stats.totalRules')}
                value={stats.total_rules}
                prefix={<NodeIndexOutlined />}
                suffix={
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    ({stats.active_rules} {t('stats.activeRules')})
                  </Text>
                }
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('stats.patternsIdentified')}
                value={stats.total_patterns}
                prefix={<BarChartOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('stats.businessInsights')}
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
                title={t('stats.avgConfidence')}
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
        <TabPane tab={t('tabs.overview')} key="overview">
          <Row gutter={16}>
            <Col span={12}>
              <Card title={t('rules.title')} extra={<Button type="link">{t('rules.viewAll')}</Button>}>
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
              <Card title={t('patterns.title')} extra={<Button type="link">{t('patterns.viewAll')}</Button>}>
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

        <TabPane tab={t('tabs.ruleManagement')} key="rules">
          <BusinessRuleManager
            projectId={projectId}
            rules={rules}
            onRulesChange={setRules}
          />
        </TabPane>

        <TabPane tab={t('tabs.patternAnalysis')} key="patterns">
          <PatternAnalysis
            projectId={projectId}
            patterns={patterns}
            onPatternsChange={setPatterns}
          />
        </TabPane>

        <TabPane tab={t('tabs.visualization')} key="visualization">
          <RuleVisualization
            projectId={projectId}
            rules={rules}
            patterns={patterns}
          />
        </TabPane>

        <TabPane
          tab={
            <Badge count={insights.length} size="small">
              {t('tabs.businessInsights')}
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
        title={t('analysis.title')}
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
            label={t('analysis.confidenceThreshold')}
            tooltip={t('analysis.confidenceThresholdTooltip')}
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
            label={t('analysis.minFrequency')}
            tooltip={t('analysis.minFrequencyTooltip')}
          >
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="time_range_days"
            label={t('analysis.timeRangeDays')}
            tooltip={t('analysis.timeRangeDaysTooltip')}
          >
            <InputNumber min={1} max={365} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 导出配置模态框 */}
      <Modal
        title={t('export.title')}
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
          <Form.Item name="export_format" label={t('export.format')}>
            <Select>
              <Select.Option value="json">JSON</Select.Option>
              <Select.Option value="csv">CSV</Select.Option>
              <Select.Option value="xml">XML</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="include_rules" valuePropName="checked">
            <span>{t('export.includeRules')}</span>
          </Form.Item>

          <Form.Item name="include_patterns" valuePropName="checked">
            <span>{t('export.includePatterns')}</span>
          </Form.Item>

          <Form.Item name="include_insights" valuePropName="checked">
            <span>{t('export.includeInsights')}</span>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};