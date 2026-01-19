// 模式分析组件
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Button,
  Space,
  Modal,
  Descriptions,
  Typography,
  Row,
  Col,
  Statistic,
  Timeline,
  Alert,
  Tooltip,
  Badge,
} from 'antd';
import {
  EyeOutlined,
  BarChartOutlined,
  TrendingUpOutlined,
  UserOutlined,
  TagOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Text, Paragraph } = Typography;

interface PatternAnalysisProps {
  projectId: string;
  patterns: Pattern[];
  onPatternsChange: (patterns: Pattern[]) => void;
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

interface PatternDetail {
  pattern: Pattern;
  analysis: any;
  recommendations: string[];
}

export const PatternAnalysis: React.FC<PatternAnalysisProps> = ({
  projectId,
  patterns,
  onPatternsChange,
}) => {
  const { t } = useTranslation(['businessLogic', 'common']);
  const [selectedPattern, setSelectedPattern] = useState<Pattern | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [patternDetail, setPatternDetail] = useState<PatternDetail | null>(null);
  const [loading, setLoading] = useState(false);

  // 查看模式详情
  const viewPatternDetail = async (pattern: Pattern) => {
    setSelectedPattern(pattern);
    setDetailModalVisible(true);
    setLoading(true);

    try {
      // 模拟获取详细分析数据
      const detail: PatternDetail = {
        pattern,
        analysis: generatePatternAnalysis(pattern),
        recommendations: generateRecommendations(pattern),
      };
      setPatternDetail(detail);
    } catch (error) {
      console.error('获取模式详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 生成模式分析数据
  const generatePatternAnalysis = (pattern: Pattern) => {
    switch (pattern.pattern_type) {
      case 'sentiment_correlation':
        return {
          type: t('patterns.analysis.sentimentAnalysis'),
          metrics: {
            positive_ratio: 0.65,
            negative_ratio: 0.20,
            neutral_ratio: 0.15,
          },
          keywords: ['excellent', 'great', 'amazing', 'wonderful', 'fantastic'],
          trend: 'increasing',
          confidence: pattern.strength,
        };
      case 'keyword_association':
        return {
          type: t('patterns.analysis.keywordAnalysis'),
          metrics: {
            unique_keywords: 45,
            avg_frequency: 12.5,
            coverage: 0.78,
          },
          top_keywords: ['quality', 'service', 'product', 'experience', 'support'],
          associations: [
            { keyword1: 'quality', keyword2: 'excellent', strength: 0.85 },
            { keyword1: 'service', keyword2: 'support', strength: 0.72 },
          ],
          confidence: pattern.strength,
        };
      case 'temporal_trend':
        return {
          type: t('patterns.analysis.temporalAnalysis'),
          metrics: {
            trend_direction: 'upward',
            trend_strength: 0.68,
            volatility: 0.23,
          },
          time_periods: [
            { period: t('common:time.weekday', { defaultValue: '工作日' }), activity: 0.75 },
            { period: t('common:time.weekend', { defaultValue: '周末' }), activity: 0.45 },
          ],
          peak_hours: ['10:00-12:00', '14:00-16:00'],
          confidence: pattern.strength,
        };
      case 'user_behavior':
        return {
          type: t('patterns.analysis.behaviorAnalysis'),
          metrics: {
            active_users: 15,
            avg_annotations_per_user: 25.6,
            consistency_score: 0.82,
          },
          user_segments: [
            { segment: t('common:common.highFrequencyUser', { defaultValue: '高频用户' }), count: 5, contribution: 0.60 },
            { segment: t('common:common.mediumFrequencyUser', { defaultValue: '中频用户' }), count: 7, contribution: 0.30 },
            { segment: t('common:common.lowFrequencyUser', { defaultValue: '低频用户' }), count: 3, contribution: 0.10 },
          ],
          confidence: pattern.strength,
        };
      default:
        return {
          type: t('patterns.analysis.generalAnalysis'),
          metrics: {},
          confidence: pattern.strength,
        };
    }
  };

  // 生成建议
  const generateRecommendations = (pattern: Pattern) => {
    switch (pattern.pattern_type) {
      case 'sentiment_correlation':
        return [
          t('patterns.recommendations.sentiment.maintainQuality'),
          t('patterns.recommendations.sentiment.balanceDataset'),
          t('patterns.recommendations.sentiment.neutralConsistency'),
          t('patterns.recommendations.sentiment.qualityCheck'),
        ];
      case 'keyword_association':
        return [
          t('patterns.recommendations.keyword.standardize'),
          t('patterns.recommendations.keyword.optimizeExtraction'),
          t('patterns.recommendations.keyword.synonyms'),
          t('patterns.recommendations.keyword.updateRegularly'),
        ];
      case 'temporal_trend':
        return [
          t('patterns.recommendations.temporal.scheduleWisely'),
          t('patterns.recommendations.temporal.increasePeakStaff'),
          t('patterns.recommendations.temporal.trendAlert'),
          t('patterns.recommendations.temporal.optimizeWorkflow'),
        ];
      case 'user_behavior':
        return [
          t('patterns.recommendations.behavior.incentivize'),
          t('patterns.recommendations.behavior.improveEngagement'),
          t('patterns.recommendations.behavior.training'),
          t('patterns.recommendations.behavior.optimizeUX'),
        ];
      default:
        return [
          t('patterns.recommendations.general.monitor'),
          t('patterns.recommendations.general.analyze'),
        ];
    }
  };

  // 获取模式类型配置
  const getPatternTypeConfig = (type: string) => {
    const configs: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
      sentiment_correlation: {
        color: 'blue',
        text: t('patterns.types.sentimentCorrelation'),
        icon: <BarChartOutlined />,
      },
      keyword_association: {
        color: 'green',
        text: t('patterns.types.keywordAssociation'),
        icon: <TagOutlined />,
      },
      temporal_trend: {
        color: 'orange',
        text: t('patterns.types.temporalTrend'),
        icon: <TrendingUpOutlined />,
      },
      user_behavior: {
        color: 'purple',
        text: t('patterns.types.userBehavior'),
        icon: <UserOutlined />,
      },
    };
    return configs[type] || { color: 'default', text: type, icon: <InfoCircleOutlined /> };
  };

  // 表格列定义
  const columns = [
    {
      title: t('patterns.columns.patternType'),
      dataIndex: 'pattern_type',
      key: 'pattern_type',
      render: (type: string) => {
        const config = getPatternTypeConfig(type);
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
    },
    {
      title: t('patterns.columns.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: t('patterns.columns.strength'),
      dataIndex: 'strength',
      key: 'strength',
      render: (strength: number) => (
        <Space>
          <Progress
            percent={Math.round(strength * 100)}
            size="small"
            status={strength >= 0.7 ? 'success' : strength >= 0.4 ? 'normal' : 'exception'}
            style={{ width: 100 }}
          />
          <Text>{(strength * 100).toFixed(1)}%</Text>
        </Space>
      ),
      sorter: (a: Pattern, b: Pattern) => a.strength - b.strength,
    },
    {
      title: t('patterns.columns.detectedAt'),
      dataIndex: 'detected_at',
      key: 'detected_at',
      render: (date: string) => (
        <Space>
          <ClockCircleOutlined />
          <Text>{new Date(date).toLocaleString()}</Text>
        </Space>
      ),
      sorter: (a: Pattern, b: Pattern) => 
        new Date(a.detected_at).getTime() - new Date(b.detected_at).getTime(),
    },
    {
      title: t('patterns.columns.lastSeen'),
      dataIndex: 'last_seen',
      key: 'last_seen',
      render: (date: string) => {
        const lastSeen = new Date(date);
        const now = new Date();
        const diffHours = Math.floor((now.getTime() - lastSeen.getTime()) / (1000 * 60 * 60));
        
        return (
          <Space>
            <Badge
              status={diffHours < 24 ? 'success' : diffHours < 72 ? 'warning' : 'default'}
              text={diffHours < 1 ? t('patterns.lastSeen.justNow') : t('patterns.lastSeen.hoursAgo', { hours: diffHours })}
            />
          </Space>
        );
      },
    },
    {
      title: t('patterns.columns.actions'),
      key: 'actions',
      render: (_: unknown, record: Pattern) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => viewPatternDetail(record)}
        >
          {t('patterns.detail.title')}
        </Button>
      ),
    },
  ];

  // 统计信息
  const getPatternStats = () => {
    const typeStats = patterns.reduce((acc, pattern) => {
      acc[pattern.pattern_type] = (acc[pattern.pattern_type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const avgStrength = patterns.length > 0 
      ? patterns.reduce((sum, p) => sum + p.strength, 0) / patterns.length 
      : 0;

    const strongPatterns = patterns.filter(p => p.strength >= 0.7).length;

    return {
      total: patterns.length,
      avgStrength,
      strongPatterns,
      typeStats,
    };
  };

  const stats = getPatternStats();

  return (
    <div>
      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('patterns.stats.totalPatterns')}
              value={stats.total}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('patterns.stats.avgStrength')}
              value={stats.avgStrength}
              precision={2}
              suffix="%"
              formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('patterns.stats.strongPatterns')}
              value={stats.strongPatterns}
              prefix={<TrendingUpOutlined />}
              suffix={`/ ${stats.total}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('patterns.stats.typeCount')}
              value={Object.keys(stats.typeStats).length}
              prefix={<TagOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 模式提醒 */}
      {stats.strongPatterns > 0 && (
        <Alert
          message={t('patterns.strongPatternsFound', { count: stats.strongPatterns })}
          description={t('patterns.strongPatternsHint')}
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 模式列表 */}
      <Card title={t('patterns.listTitle')} extra={
        <Space>
          <Text type="secondary">{t('patterns.total', { count: patterns.length })}</Text>
        </Space>
      }>
        <Table
          dataSource={patterns}
          columns={columns}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => t('rules.pagination.total', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      {/* 模式详情模态框 */}
      <Modal
        title={
          selectedPattern && (
            <Space>
              {getPatternTypeConfig(selectedPattern.pattern_type).icon}
              <span>{t('patterns.detail.title')} - {getPatternTypeConfig(selectedPattern.pattern_type).text}</span>
            </Space>
          )
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            {t('common:actions.cancel')}
          </Button>,
        ]}
      >
        {patternDetail && (
          <div>
            {/* 基本信息 */}
            <Descriptions title={t('patterns.detail.basicInfo')} bordered column={2}>
              <Descriptions.Item label={t('patterns.detail.patternId')}>
                {patternDetail.pattern.id}
              </Descriptions.Item>
              <Descriptions.Item label={t('patterns.detail.patternType')}>
                <Tag color={getPatternTypeConfig(patternDetail.pattern.pattern_type).color}>
                  {getPatternTypeConfig(patternDetail.pattern.pattern_type).text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('patterns.detail.strength')} span={2}>
                <Progress
                  percent={Math.round(patternDetail.pattern.strength * 100)}
                  status={patternDetail.pattern.strength >= 0.7 ? 'success' : 'normal'}
                />
              </Descriptions.Item>
              <Descriptions.Item label={t('patterns.detail.description')} span={2}>
                {patternDetail.pattern.description}
              </Descriptions.Item>
              <Descriptions.Item label={t('patterns.detail.detectedAt')}>
                {new Date(patternDetail.pattern.detected_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('patterns.detail.lastSeen')}>
                {new Date(patternDetail.pattern.last_seen).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            {/* 分析结果 */}
            <Card title={t('patterns.detail.analysisResult')} style={{ marginTop: 16 }}>
              {patternDetail.analysis.type === t('patterns.analysis.sentimentAnalysis') && (
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title={t('patterns.analysis.positiveRatio')}
                      value={patternDetail.analysis.metrics.positive_ratio}
                      precision={1}
                      suffix="%"
                      formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t('patterns.analysis.negativeRatio')}
                      value={patternDetail.analysis.metrics.negative_ratio}
                      precision={1}
                      suffix="%"
                      formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
                    />
                  </Col>
                </Row>
              )}

              {patternDetail.analysis.keywords && (
                <div style={{ marginTop: 16 }}>
                  <Title level={5}>{t('patterns.analysis.keywords')}</Title>
                  <Space wrap>
                    {patternDetail.analysis.keywords.map((keyword: string, index: number) => (
                      <Tag key={index} color="blue">{keyword}</Tag>
                    ))}
                  </Space>
                </div>
              )}
            </Card>

            {/* 建议 */}
            <Card title={t('patterns.detail.recommendations')} style={{ marginTop: 16 }}>
              <Timeline>
                {patternDetail.recommendations.map((recommendation, index) => (
                  <Timeline.Item key={index}>
                    <Text>{recommendation}</Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  );
};