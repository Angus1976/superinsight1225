/**
 * AI Annotation Panel Component
 * 
 * Displays AI pre-annotation results, confidence scores, and allows
 * users to accept, modify, or reject AI suggestions.
 * 
 * Requirements: 7.1, 7.2 - 标注界面
 */

import { useState, useCallback } from 'react';
import {
  Card,
  Space,
  Tag,
  Button,
  Progress,
  Tooltip,
  List,
  Badge,
  Collapse,
  Typography,
  Divider,
  Alert,
  Spin,
  Empty,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  RobotOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  HistoryOutlined,
  BulbOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text, Title } = Typography;
const { Panel } = Collapse;

// Types
interface AIAnnotationResult {
  id: string;
  label: string;
  confidence: number;
  source: 'llm' | 'ml_backend' | 'pattern_match';
  explanation?: string;
  alternatives?: Array<{
    label: string;
    confidence: number;
  }>;
}

interface AnnotationHistory {
  id: string;
  action: 'created' | 'modified' | 'accepted' | 'rejected';
  timestamp: string;
  user: string;
  details?: string;
}

interface AIAnnotationPanelProps {
  taskId: string;
  aiResults: AIAnnotationResult[];
  history: AnnotationHistory[];
  loading?: boolean;
  onAccept: (result: AIAnnotationResult) => void;
  onReject: (result: AIAnnotationResult) => void;
  onModify: (result: AIAnnotationResult, newLabel: string) => void;
  onRefresh: () => void;
}

// Confidence level helper - returns keys for translation
const getConfidenceLevel = (confidence: number): { color: string; textKey: string } => {
  if (confidence >= 0.9) return { color: 'success', textKey: 'high' };
  if (confidence >= 0.7) return { color: 'warning', textKey: 'medium' };
  return { color: 'error', textKey: 'low' };
};

// Source label helper - returns keys for translation
const getSourceLabel = (source: AIAnnotationResult['source']): { icon: React.ReactNode; textKey: string } => {
  switch (source) {
    case 'llm':
      return { icon: <RobotOutlined />, textKey: 'llmModel' };
    case 'ml_backend':
      return { icon: <ThunderboltOutlined />, textKey: 'mlBackend' };
    case 'pattern_match':
      return { icon: <BulbOutlined />, textKey: 'patternMatch' };
    default:
      return { icon: <RobotOutlined />, textKey: 'ai' };
  }
};

const AIAnnotationPanel: React.FC<AIAnnotationPanelProps> = ({
  taskId,
  aiResults,
  history,
  loading = false,
  onAccept,
  onReject,
  onModify,
  onRefresh,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const [expandedResult, setExpandedResult] = useState<string | null>(null);

  // Calculate stats
  const stats = {
    total: aiResults.length,
    highConfidence: aiResults.filter(r => r.confidence >= 0.9).length,
    mediumConfidence: aiResults.filter(r => r.confidence >= 0.7 && r.confidence < 0.9).length,
    lowConfidence: aiResults.filter(r => r.confidence < 0.7).length,
    avgConfidence: aiResults.length > 0 
      ? aiResults.reduce((sum, r) => sum + r.confidence, 0) / aiResults.length 
      : 0,
  };

  const handleAccept = useCallback((result: AIAnnotationResult) => {
    onAccept(result);
  }, [onAccept]);

  const handleReject = useCallback((result: AIAnnotationResult) => {
    onReject(result);
  }, [onReject]);

  const handleSelectAlternative = useCallback((result: AIAnnotationResult, altLabel: string) => {
    onModify(result, altLabel);
  }, [onModify]);

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>{t('ai.fetchingResults')}</p>
        </div>
      </Card>
    );
  }

  return (
    <div>
      {/* Header with Stats */}
      <Card 
        title={
          <Space>
            <RobotOutlined />
            <span>{t('ai.preAnnotationResults')}</span>
            <Badge count={aiResults.length} style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={
          <Button 
            icon={<SyncOutlined />} 
            onClick={onRefresh}
            size="small"
          >
            {t('ai.refresh')}
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        {/* Stats Row */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic
              title={t('ai.totalPredictions')}
              value={stats.total}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai.highConfidence')}
              value={stats.highConfidence}
              valueStyle={{ fontSize: 20, color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai.needsReview')}
              value={stats.lowConfidence}
              valueStyle={{ fontSize: 20, color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai.avgConfidence')}
              value={Math.round(stats.avgConfidence * 100)}
              suffix="%"
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
        </Row>

        {/* Confidence Distribution */}
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">{t('ai.confidenceDistribution')}</Text>
          <Progress
            percent={100}
            success={{ percent: (stats.highConfidence / Math.max(stats.total, 1)) * 100 }}
            strokeColor={{
              '0%': '#52c41a',
              '50%': '#faad14',
              '100%': '#ff4d4f',
            }}
            showInfo={false}
          />
          <Space style={{ marginTop: 4 }}>
            <Tag color="success">{t('ai.high')}: {stats.highConfidence}</Tag>
            <Tag color="warning">{t('ai.medium')}: {stats.mediumConfidence}</Tag>
            <Tag color="error">{t('ai.low')}: {stats.lowConfidence}</Tag>
          </Space>
        </div>
      </Card>

      {/* AI Results List */}
      {aiResults.length === 0 ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('ai.noResults')}
          >
            <Button type="primary" onClick={onRefresh}>
              {t('ai.getPreAnnotation')}
            </Button>
          </Empty>
        </Card>
      ) : (
        <List
          dataSource={aiResults}
          renderItem={(result) => {
            const confidenceLevel = getConfidenceLevel(result.confidence);
            const sourceInfo = getSourceLabel(result.source);
            const isExpanded = expandedResult === result.id;

            return (
              <Card
                size="small"
                style={{ marginBottom: 8 }}
                hoverable
                onClick={() => setExpandedResult(isExpanded ? null : result.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                      {result.label}
                    </Tag>
                    <Tooltip title={`${t('ai.confidence')}: ${Math.round(result.confidence * 100)}%`}>
                      <Progress
                        type="circle"
                        percent={Math.round(result.confidence * 100)}
                        size={40}
                        strokeColor={
                          result.confidence >= 0.9 ? '#52c41a' :
                          result.confidence >= 0.7 ? '#faad14' : '#ff4d4f'
                        }
                      />
                    </Tooltip>
                    <Tag color={confidenceLevel.color}>{t(`ai.${confidenceLevel.textKey}`)}</Tag>
                    <Tooltip title={t(`ai.${sourceInfo.textKey}`)}>
                      <Tag icon={sourceInfo.icon}>{t(`ai.${sourceInfo.textKey}`)}</Tag>
                    </Tooltip>
                  </Space>

                  <Space>
                    <Tooltip title={t('ai.acceptAnnotation')}>
                      <Button
                        type="primary"
                        size="small"
                        icon={<CheckCircleOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAccept(result);
                        }}
                      >
                        {t('ai.accept')}
                      </Button>
                    </Tooltip>
                    <Tooltip title={t('ai.rejectAnnotation')}>
                      <Button
                        danger
                        size="small"
                        icon={<CloseCircleOutlined />}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReject(result);
                        }}
                      >
                        {t('ai.reject')}
                      </Button>
                    </Tooltip>
                  </Space>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
                    {/* Explanation */}
                    {result.explanation && (
                      <Alert
                        message={t('ai.aiExplanation')}
                        description={result.explanation}
                        type="info"
                        showIcon
                        icon={<InfoCircleOutlined />}
                        style={{ marginBottom: 12 }}
                      />
                    )}

                    {/* Alternatives */}
                    {result.alternatives && result.alternatives.length > 0 && (
                      <div>
                        <Text type="secondary">{t('ai.alternativeLabels')}:</Text>
                        <div style={{ marginTop: 8 }}>
                          {result.alternatives.map((alt, idx) => (
                            <Tag
                              key={idx}
                              style={{ cursor: 'pointer', marginBottom: 4 }}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectAlternative(result, alt.label);
                              }}
                            >
                              {alt.label} ({Math.round(alt.confidence * 100)}%)
                            </Tag>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          }}
        />
      )}

      {/* History Panel */}
      <Collapse style={{ marginTop: 16 }}>
        <Panel
          header={
            <Space>
              <HistoryOutlined />
              <span>{t('ai.modifyHistory')}</span>
              <Badge count={history.length} style={{ backgroundColor: '#999' }} />
            </Space>
          }
          key="history"
        >
          {history.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t('ai.noHistory')}
            />
          ) : (
            <List
              size="small"
              dataSource={history}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    {item.action === 'accepted' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                    {item.action === 'rejected' && <CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                    {item.action === 'modified' && <EditOutlined style={{ color: '#1890ff' }} />}
                    {item.action === 'created' && <RobotOutlined style={{ color: '#722ed1' }} />}
                    <Text>{item.user}</Text>
                    <Text type="secondary">{item.details || item.action}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(item.timestamp).toLocaleString()}
                    </Text>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </Panel>
      </Collapse>
    </div>
  );
};

export default AIAnnotationPanel;
