// 业务洞察卡片组件
import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Tag,
  Typography,
  Space,
  Progress,
  List,
  Avatar,
  Badge,
  Tooltip,
  Modal,
  Alert,
  Statistic,
  Timeline,
} from 'antd';
import {
  BulbOutlined,
  TrendingUpOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  StarOutlined,
  ClockCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Text, Paragraph } = Typography;

interface InsightCardsProps {
  projectId: string;
  insights: BusinessInsight[];
  onInsightAcknowledge: (insightId: string) => void;
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

export const InsightCards: React.FC<InsightCardsProps> = ({
  projectId,
  insights,
  onInsightAcknowledge,
}) => {
  const { t } = useTranslation(['businessLogic', 'common']);
  const [selectedInsight, setSelectedInsight] = useState<BusinessInsight | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  // 获取洞察类型配置
  const getInsightTypeConfig = (type: string) => {
    const configs: Record<string, { 
      color: string; 
      text: string; 
      icon: React.ReactNode;
      bgColor: string;
    }> = {
      quality_insight: {
        color: 'success',
        text: t('insights.types.qualityInsight'),
        icon: <StarOutlined />,
        bgColor: '#f6ffed',
      },
      efficiency_insight: {
        color: 'processing',
        text: t('insights.types.efficiencyInsight'),
        icon: <TrendingUpOutlined />,
        bgColor: '#e6f7ff',
      },
      pattern_insight: {
        color: 'warning',
        text: t('insights.types.patternInsight'),
        icon: <BulbOutlined />,
        bgColor: '#fffbe6',
      },
      trend_insight: {
        color: 'error',
        text: t('insights.types.trendInsight'),
        icon: <WarningOutlined />,
        bgColor: '#fff2f0',
      },
    };
    return configs[type] || { 
      color: 'default', 
      text: type, 
      icon: <InfoCircleOutlined />,
      bgColor: '#fafafa',
    };
  };

  // 获取影响等级
  const getImpactLevel = (score: number) => {
    if (score >= 0.8) return { level: t('insights.impactLevel.high'), color: 'red' };
    if (score >= 0.6) return { level: t('insights.impactLevel.medium'), color: 'orange' };
    if (score >= 0.4) return { level: t('insights.impactLevel.low'), color: 'blue' };
    return { level: t('insights.impactLevel.veryLow'), color: 'gray' };
  };

  // 查看洞察详情
  const viewInsightDetail = (insight: BusinessInsight) => {
    setSelectedInsight(insight);
    setDetailModalVisible(true);
  };

  // 确认洞察
  const handleAcknowledge = (insight: BusinessInsight) => {
    Modal.confirm({
      title: t('insights.confirmAcknowledge'),
      content: t('insights.confirmAcknowledgeMessage', { title: insight.title }),
      onOk: () => {
        onInsightAcknowledge(insight.id);
      },
    });
  };

  // 渲染洞察卡片
  const renderInsightCard = (insight: BusinessInsight) => {
    const typeConfig = getInsightTypeConfig(insight.insight_type);
    const impactLevel = getImpactLevel(insight.impact_score);
    const isNew = new Date().getTime() - new Date(insight.created_at).getTime() < 24 * 60 * 60 * 1000;

    return (
      <Badge.Ribbon 
        text={isNew ? t('insights.new') : undefined} 
        color="red" 
        style={{ display: isNew ? 'block' : 'none' }}
      >
        <Card
          hoverable
          style={{ 
            height: '100%',
            backgroundColor: typeConfig.bgColor,
            border: `1px solid ${typeConfig.color === 'success' ? '#52c41a' : 
                                   typeConfig.color === 'processing' ? '#1890ff' :
                                   typeConfig.color === 'warning' ? '#faad14' : '#ff4d4f'}20`
          }}
          actions={[
            <Tooltip title={t('insights.detail')}>
              <Button 
                type="text" 
                icon={<EyeOutlined />}
                onClick={() => viewInsightDetail(insight)}
              >
                {t('insights.detail')}
              </Button>
            </Tooltip>,
            <Tooltip title={t('insights.acknowledge')}>
              <Button 
                type="text" 
                icon={<CheckCircleOutlined />}
                onClick={() => handleAcknowledge(insight)}
              >
                {t('insights.acknowledge')}
              </Button>
            </Tooltip>,
          ]}
        >
          <Card.Meta
            avatar={
              <Avatar 
                icon={typeConfig.icon} 
                style={{ 
                  backgroundColor: typeConfig.color === 'success' ? '#52c41a' : 
                                   typeConfig.color === 'processing' ? '#1890ff' :
                                   typeConfig.color === 'warning' ? '#faad14' : '#ff4d4f'
                }}
              />
            }
            title={
              <Space>
                <Text strong>{insight.title}</Text>
                <Tag color={typeConfig.color}>{typeConfig.text}</Tag>
              </Space>
            }
            description={
              <div>
                <Paragraph ellipsis={{ rows: 2, tooltip: insight.description }}>
                  {insight.description}
                </Paragraph>
                <Space style={{ marginTop: 8 }}>
                  <Text type="secondary">影响等级:</Text>
                  <Tag color={impactLevel.color}>{impactLevel.level}</Tag>
                  <Progress 
                    percent={Math.round(insight.impact_score * 100)} 
                    size="small" 
                    style={{ width: 60 }}
                    showInfo={false}
                  />
                </Space>
                <div style={{ marginTop: 8 }}>
                  <Space>
                    <ClockCircleOutlined />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(insight.created_at).toLocaleString()}
                    </Text>
                  </Space>
                </div>
              </div>
            }
          />
        </Card>
      </Badge.Ribbon>
    );
  };

  // 按类型分组洞察
  const groupedInsights = insights.reduce((groups, insight) => {
    const type = insight.insight_type;
    if (!groups[type]) {
      groups[type] = [];
    }
    groups[type].push(insight);
    return groups;
  }, {} as Record<string, BusinessInsight[]>);

  return (
    <div>
      {/* 洞察概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('insights.unacknowledged')}
              value={insights.length}
              prefix={<BulbOutlined />}
              valueStyle={{ color: insights.length > 0 ? '#cf1322' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('insights.highImpact')}
              value={insights.filter(i => i.impact_score >= 0.8).length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#fa541c' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('insights.avgImpactScore')}
              value={insights.length > 0 ? insights.reduce((sum, i) => sum + i.impact_score, 0) / insights.length : 0}
              precision={2}
              prefix={<TrendingUpOutlined />}
              formatter={(value) => `${((value as number) * 100).toFixed(1)}%`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('insights.insightTypes')}
              value={Object.keys(groupedInsights).length}
              prefix={<InfoCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 洞察提醒 */}
      {insights.filter(i => i.impact_score >= 0.8).length > 0 && (
        <Alert
          message={t('insights.highImpactFound')}
          description={t('insights.highImpactHint', { count: insights.filter(i => i.impact_score >= 0.8).length })}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 洞察卡片 */}
      {insights.length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <BulbOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
            <Title level={4} type="secondary">{t('insights.noUnacknowledged')}</Title>
            <Text type="secondary">{t('insights.autoGenerate')}</Text>
          </div>
        </Card>
      ) : (
        Object.entries(groupedInsights).map(([type, typeInsights]) => {
          const typeConfig = getInsightTypeConfig(type);
          return (
            <div key={type} style={{ marginBottom: 24 }}>
              <Title level={4}>
                {typeConfig.icon} {typeConfig.text} ({typeInsights.length})
              </Title>
              <Row gutter={[16, 16]}>
                {typeInsights.map((insight) => (
                  <Col key={insight.id} xs={24} sm={12} lg={8} xl={6}>
                    {renderInsightCard(insight)}
                  </Col>
                ))}
              </Row>
            </div>
          );
        })
      )}

      {/* 洞察详情模态框 */}
      <Modal
        title={
          selectedInsight && (
            <Space>
              {getInsightTypeConfig(selectedInsight.insight_type).icon}
              <span>{selectedInsight.title}</span>
              <Tag color={getInsightTypeConfig(selectedInsight.insight_type).color}>
                {getInsightTypeConfig(selectedInsight.insight_type).text}
              </Tag>
            </Space>
          )
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            {t('insights.close')}
          </Button>,
          selectedInsight && (
            <Button 
              key="acknowledge" 
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                handleAcknowledge(selectedInsight);
                setDetailModalVisible(false);
              }}
            >
              {t('insights.acknowledgeInsight')}
            </Button>
          ),
        ]}
      >
        {selectedInsight && (
          <div>
            {/* 洞察基本信息 */}
            <Card title={t('insights.insightInfo')} style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Text strong>{t('insights.insightType')}: </Text>
                  <Tag color={getInsightTypeConfig(selectedInsight.insight_type).color}>
                    {getInsightTypeConfig(selectedInsight.insight_type).text}
                  </Tag>
                </Col>
                <Col span={12}>
                  <Text strong>{t('insights.impactScore')}: </Text>
                  <Progress 
                    percent={Math.round(selectedInsight.impact_score * 100)}
                    size="small"
                    style={{ width: 100, display: 'inline-block' }}
                  />
                  <Text style={{ marginLeft: 8 }}>
                    {getImpactLevel(selectedInsight.impact_score).level}
                  </Text>
                </Col>
              </Row>
              <div style={{ marginTop: 16 }}>
                <Text strong>{t('insights.description')}: </Text>
                <Paragraph>{selectedInsight.description}</Paragraph>
              </div>
              <div>
                <Text strong>{t('insights.generatedAt')}: </Text>
                <Text>{new Date(selectedInsight.created_at).toLocaleString()}</Text>
              </div>
            </Card>

            {/* 数据点 */}
            {selectedInsight.data_points && selectedInsight.data_points.length > 0 && (
              <Card title={t('insights.keyData')} style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  {selectedInsight.data_points.map((point, index) => (
                    <Col key={index} span={8}>
                      <Statistic
                        title={point.metric}
                        value={point.value}
                        suffix={point.change && (
                          <Text type={point.change.startsWith('+') ? 'success' : 'danger'}>
                            {point.change}
                          </Text>
                        )}
                      />
                    </Col>
                  ))}
                </Row>
              </Card>
            )}

            {/* 建议 */}
            {selectedInsight.recommendations && selectedInsight.recommendations.length > 0 && (
              <Card title={t('insights.recommendations')}>
                <Timeline>
                  {selectedInsight.recommendations.map((recommendation, index) => (
                    <Timeline.Item key={index}>
                      <Text>{recommendation}</Text>
                    </Timeline.Item>
                  ))}
                </Timeline>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};