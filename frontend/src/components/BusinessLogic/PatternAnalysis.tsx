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
          type: '情感关联分析',
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
          type: '关键词关联分析',
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
          type: '时间趋势分析',
          metrics: {
            trend_direction: 'upward',
            trend_strength: 0.68,
            volatility: 0.23,
          },
          time_periods: [
            { period: '工作日', activity: 0.75 },
            { period: '周末', activity: 0.45 },
          ],
          peak_hours: ['10:00-12:00', '14:00-16:00'],
          confidence: pattern.strength,
        };
      case 'user_behavior':
        return {
          type: '用户行为分析',
          metrics: {
            active_users: 15,
            avg_annotations_per_user: 25.6,
            consistency_score: 0.82,
          },
          user_segments: [
            { segment: '高频用户', count: 5, contribution: 0.60 },
            { segment: '中频用户', count: 7, contribution: 0.30 },
            { segment: '低频用户', count: 3, contribution: 0.10 },
          ],
          confidence: pattern.strength,
        };
      default:
        return {
          type: '通用分析',
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
          '继续保持正面情感标注的高质量',
          '增加负面情感样本以平衡数据集',
          '关注中性情感的标注一致性',
          '建立情感标注质量检查机制',
        ];
      case 'keyword_association':
        return [
          '建立关键词标准化词典',
          '优化关键词提取算法',
          '增加同义词和近义词处理',
          '定期更新关键词库',
        ];
      case 'temporal_trend':
        return [
          '合理安排标注任务时间',
          '在高峰时段增加标注人员',
          '建立时间趋势预警机制',
          '优化工作流程提高效率',
        ];
      case 'user_behavior':
        return [
          '激励高频用户持续参与',
          '提升中低频用户的参与度',
          '建立用户培训和指导机制',
          '优化用户体验和界面设计',
        ];
      default:
        return ['持续监控模式变化', '定期分析和优化'];
    }
  };

  // 获取模式类型配置
  const getPatternTypeConfig = (type: string) => {
    const configs: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
      sentiment_correlation: {
        color: 'blue',
        text: '情感关联',
        icon: <BarChartOutlined />,
      },
      keyword_association: {
        color: 'green',
        text: '关键词关联',
        icon: <TagOutlined />,
      },
      temporal_trend: {
        color: 'orange',
        text: '时间趋势',
        icon: <TrendingUpOutlined />,
      },
      user_behavior: {
        color: 'purple',
        text: '用户行为',
        icon: <UserOutlined />,
      },
    };
    return configs[type] || { color: 'default', text: type, icon: <InfoCircleOutlined /> };
  };

  // 表格列定义
  const columns = [
    {
      title: '模式类型',
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
      title: '描述',
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
      title: '强度',
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
      title: '检测时间',
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
      title: '最后出现',
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
              text={diffHours < 1 ? '刚刚' : `${diffHours}小时前`}
            />
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: Pattern) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => viewPatternDetail(record)}
        >
          查看详情
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
              title="模式总数"
              value={stats.total}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均强度"
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
              title="强模式数"
              value={stats.strongPatterns}
              prefix={<TrendingUpOutlined />}
              suffix={`/ ${stats.total}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="类型数量"
              value={Object.keys(stats.typeStats).length}
              prefix={<TagOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 模式提醒 */}
      {stats.strongPatterns > 0 && (
        <Alert
          message={`发现 ${stats.strongPatterns} 个强模式`}
          description="这些模式具有较高的强度，建议重点关注和分析"
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 模式列表 */}
      <Card title="业务模式列表" extra={
        <Space>
          <Text type="secondary">共 {patterns.length} 个模式</Text>
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
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 模式详情模态框 */}
      <Modal
        title={
          selectedPattern && (
            <Space>
              {getPatternTypeConfig(selectedPattern.pattern_type).icon}
              <span>模式详情 - {getPatternTypeConfig(selectedPattern.pattern_type).text}</span>
            </Space>
          )
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {patternDetail && (
          <div>
            {/* 基本信息 */}
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="模式ID">
                {patternDetail.pattern.id}
              </Descriptions.Item>
              <Descriptions.Item label="模式类型">
                <Tag color={getPatternTypeConfig(patternDetail.pattern.pattern_type).color}>
                  {getPatternTypeConfig(patternDetail.pattern.pattern_type).text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="强度" span={2}>
                <Progress
                  percent={Math.round(patternDetail.pattern.strength * 100)}
                  status={patternDetail.pattern.strength >= 0.7 ? 'success' : 'normal'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {patternDetail.pattern.description}
              </Descriptions.Item>
              <Descriptions.Item label="检测时间">
                {new Date(patternDetail.pattern.detected_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="最后出现">
                {new Date(patternDetail.pattern.last_seen).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            {/* 分析结果 */}
            <Card title="分析结果" style={{ marginTop: 16 }}>
              {patternDetail.analysis.type === '情感关联分析' && (
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="正面情感比例"
                      value={patternDetail.analysis.metrics.positive_ratio}
                      precision={1}
                      suffix="%"
                      formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="负面情感比例"
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
                  <Title level={5}>关键词</Title>
                  <Space wrap>
                    {patternDetail.analysis.keywords.map((keyword: string, index: number) => (
                      <Tag key={index} color="blue">{keyword}</Tag>
                    ))}
                  </Space>
                </div>
              )}
            </Card>

            {/* 建议 */}
            <Card title="优化建议" style={{ marginTop: 16 }}>
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