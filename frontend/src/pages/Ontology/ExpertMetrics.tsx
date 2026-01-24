/**
 * Expert Metrics Component (专家贡献指标)
 * 
 * Displays contribution metrics for an expert including:
 * - Total contributions
 * - Acceptance rate
 * - Quality score
 * - Recognition score
 * 
 * Requirements: 6.5 - Expert Contribution Metrics
 */

import React from 'react';
import {
  Card,
  Statistic,
  Row,
  Col,
  Progress,
  Typography,
  Spin,
  Alert,
  Space,
  Divider,
  Tag,
} from 'antd';
import {
  TrophyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StarOutlined,
  RiseOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { ontologyExpertApi, ExpertMetrics as ExpertMetricsType } from '@/services/ontologyExpertApi';

const { Title, Text } = Typography;

interface ExpertMetricsProps {
  expertId: string;
}

// Get quality level based on score
const getQualityLevel = (score: number): { level: string; color: string } => {
  if (score >= 4.5) return { level: 'Excellent', color: 'green' };
  if (score >= 4.0) return { level: 'Good', color: 'blue' };
  if (score >= 3.0) return { level: 'Average', color: 'orange' };
  return { level: 'Needs Improvement', color: 'red' };
};

// Get acceptance rate level
const getAcceptanceLevel = (rate: number): { level: string; color: string } => {
  if (rate >= 0.9) return { level: 'Outstanding', color: 'green' };
  if (rate >= 0.75) return { level: 'Good', color: 'blue' };
  if (rate >= 0.5) return { level: 'Average', color: 'orange' };
  return { level: 'Low', color: 'red' };
};

const ExpertMetrics: React.FC<ExpertMetricsProps> = ({ expertId }) => {
  const { t } = useTranslation(['ontology', 'common']);

  // Fetch metrics
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['expert-metrics', expertId],
    queryFn: () => ontologyExpertApi.getExpertMetrics(expertId),
    enabled: !!expertId,
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message={t('ontology:expert.metricsLoadError')}
        description={(error as Error).message}
      />
    );
  }

  if (!metrics) {
    return (
      <Alert
        type="info"
        message={t('ontology:expert.noMetrics')}
      />
    );
  }

  const qualityInfo = getQualityLevel(metrics.quality_score);
  const acceptanceInfo = getAcceptanceLevel(metrics.acceptance_rate);

  return (
    <div>
      {/* Summary Stats */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8}>
          <Card size="small">
            <Statistic
              title={t('ontology:expert.totalContributions')}
              value={metrics.total_contributions}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card size="small">
            <Statistic
              title={t('ontology:expert.acceptedContributions')}
              value={metrics.accepted_contributions}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card size="small">
            <Statistic
              title={t('ontology:expert.rejectedContributions')}
              value={metrics.rejected_contributions}
              prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* Quality Score */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <StarOutlined style={{ color: '#faad14' }} />
              <Text strong>{t('ontology:expert.qualityScore')}</Text>
            </Space>
            <Tag color={qualityInfo.color}>{qualityInfo.level}</Tag>
          </div>
          <Progress
            percent={Math.round((metrics.quality_score / 5) * 100)}
            strokeColor={qualityInfo.color}
            format={() => `${metrics.quality_score.toFixed(2)} / 5.0`}
          />
        </Space>
      </Card>

      {/* Acceptance Rate */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <RiseOutlined style={{ color: '#1890ff' }} />
              <Text strong>{t('ontology:expert.acceptanceRate')}</Text>
            </Space>
            <Tag color={acceptanceInfo.color}>{acceptanceInfo.level}</Tag>
          </div>
          <Progress
            percent={Math.round(metrics.acceptance_rate * 100)}
            strokeColor={acceptanceInfo.color}
            format={(percent) => `${percent}%`}
          />
        </Space>
      </Card>

      {/* Recognition Score */}
      <Card size="small">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <TrophyOutlined style={{ color: '#722ed1' }} />
              <Text strong>{t('ontology:expert.recognitionScore')}</Text>
            </Space>
            <Text strong style={{ fontSize: 18, color: '#722ed1' }}>
              {metrics.recognition_score.toFixed(2)}
            </Text>
          </div>
          <Text type="secondary">
            {t('ontology:expert.recognitionScoreDescription')}
          </Text>
        </Space>
      </Card>

      <Divider />

      {/* Contribution Breakdown */}
      <Title level={5}>{t('ontology:expert.contributionBreakdown')}</Title>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1 }}>
              <Progress
                percent={
                  metrics.total_contributions > 0
                    ? Math.round((metrics.accepted_contributions / metrics.total_contributions) * 100)
                    : 0
                }
                success={{
                  percent:
                    metrics.total_contributions > 0
                      ? Math.round((metrics.accepted_contributions / metrics.total_contributions) * 100)
                      : 0,
                }}
                strokeColor="#52c41a"
                trailColor="#ff4d4f"
                showInfo={false}
              />
            </div>
            <Space>
              <Tag color="green">{t('ontology:expert.accepted')}: {metrics.accepted_contributions}</Tag>
              <Tag color="red">{t('ontology:expert.rejected')}: {metrics.rejected_contributions}</Tag>
              <Tag color="default">
                {t('ontology:expert.pending')}: {metrics.total_contributions - metrics.accepted_contributions - metrics.rejected_contributions}
              </Tag>
            </Space>
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default ExpertMetrics;
