/**
 * Expert Recommendation Component (专家推荐)
 * 
 * Displays recommended experts for a specific ontology area.
 * Shows expertise match score, contribution quality, and availability.
 * 
 * Requirements: 9.1, 9.2 - Expert Recommendation System
 */

import React, { useState } from 'react';
import {
  Card,
  List,
  Avatar,
  Tag,
  Space,
  Input,
  Button,
  Typography,
  Progress,
  Tooltip,
  Empty,
  Spin,
  Badge,
  Rate,
  Select,
} from 'antd';
import {
  UserOutlined,
  SearchOutlined,
  StarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  ontologyExpertApi,
  ExpertRecommendation as ExpertRecommendationType,
  ExpertiseArea,
  AvailabilityLevel,
} from '@/services/ontologyExpertApi';

const { Text, Title } = Typography;

// Expertise area options
const EXPERTISE_AREAS: { value: ExpertiseArea; label: string }[] = [
  { value: '金融', label: '金融 (Finance)' },
  { value: '医疗', label: '医疗 (Healthcare)' },
  { value: '制造', label: '制造 (Manufacturing)' },
  { value: '政务', label: '政务 (Government)' },
  { value: '法律', label: '法律 (Legal)' },
  { value: '教育', label: '教育 (Education)' },
];

// Availability badge colors
const AVAILABILITY_COLORS: Record<AvailabilityLevel, string> = {
  high: 'green',
  medium: 'orange',
  low: 'red',
  unavailable: 'default',
};

// Availability icons
const AVAILABILITY_ICONS: Record<AvailabilityLevel, React.ReactNode> = {
  high: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  medium: <ClockCircleOutlined style={{ color: '#faad14' }} />,
  low: <ClockCircleOutlined style={{ color: '#ff4d4f' }} />,
  unavailable: <ClockCircleOutlined style={{ color: '#d9d9d9' }} />,
};

// Expertise area colors
const EXPERTISE_COLORS: Record<ExpertiseArea, string> = {
  '金融': 'blue',
  '医疗': 'green',
  '制造': 'orange',
  '政务': 'purple',
  '法律': 'red',
  '教育': 'cyan',
};

interface ExpertRecommendationProps {
  defaultOntologyArea?: string;
  onSelectExpert?: (expert: ExpertRecommendationType) => void;
}

const ExpertRecommendation: React.FC<ExpertRecommendationProps> = ({
  defaultOntologyArea,
  onSelectExpert,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const [ontologyArea, setOntologyArea] = useState<string>(defaultOntologyArea || '');
  const [searchArea, setSearchArea] = useState<string>(defaultOntologyArea || '');
  const [limit, setLimit] = useState(5);

  // Fetch recommendations
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['expert-recommendations', searchArea, limit],
    queryFn: () => ontologyExpertApi.recommendExperts(searchArea, limit),
    enabled: !!searchArea,
  });

  // Handle search
  const handleSearch = () => {
    if (ontologyArea.trim()) {
      setSearchArea(ontologyArea.trim());
    }
  };

  // Handle expert selection
  const handleSelectExpert = (expert: ExpertRecommendationType) => {
    onSelectExpert?.(expert);
  };

  // Get match score color
  const getMatchScoreColor = (score: number): string => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#1890ff';
    if (score >= 0.4) return '#faad14';
    return '#ff4d4f';
  };

  return (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>{t('ontology:expert.recommendationTitle')}</span>
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={() => refetch()}
          loading={isFetching}
          disabled={!searchArea}
        >
          {t('common:refresh')}
        </Button>
      }
    >
      {/* Search Area */}
      <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
        <Select
          placeholder={t('ontology:expert.selectOntologyArea')}
          value={ontologyArea || undefined}
          onChange={setOntologyArea}
          options={EXPERTISE_AREAS}
          style={{ width: '60%' }}
          allowClear
        />
        <Input
          placeholder={t('ontology:expert.customOntologyArea')}
          value={ontologyArea}
          onChange={(e) => setOntologyArea(e.target.value)}
          style={{ width: '40%' }}
        />
      </Space.Compact>

      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleSearch}
          loading={isLoading}
          disabled={!ontologyArea.trim()}
        >
          {t('ontology:expert.findExperts')}
        </Button>
        <Select
          value={limit}
          onChange={setLimit}
          options={[
            { value: 3, label: t('ontology:expert.top3') },
            { value: 5, label: t('ontology:expert.top5') },
            { value: 10, label: t('ontology:expert.top10') },
          ]}
          style={{ width: 120 }}
        />
      </Space>

      {/* Results */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : data?.experts && data.experts.length > 0 ? (
        <>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            {t('ontology:expert.foundExperts', {
              count: data.total_count,
              area: data.ontology_area,
            })}
          </Text>

          <List
            itemLayout="horizontal"
            dataSource={data.experts}
            renderItem={(expert, index) => (
              <List.Item
                actions={[
                  <Button
                    key="select"
                    type="link"
                    onClick={() => handleSelectExpert(expert)}
                  >
                    {t('ontology:expert.selectExpert')}
                  </Button>,
                ]}
                style={{
                  cursor: onSelectExpert ? 'pointer' : 'default',
                  padding: '12px 16px',
                  borderRadius: 8,
                  marginBottom: 8,
                  background: index === 0 ? '#f6ffed' : undefined,
                  border: index === 0 ? '1px solid #b7eb8f' : '1px solid #f0f0f0',
                }}
                onClick={() => handleSelectExpert(expert)}
              >
                <List.Item.Meta
                  avatar={
                    <Badge
                      count={index + 1}
                      style={{
                        backgroundColor: index === 0 ? '#52c41a' : index < 3 ? '#1890ff' : '#d9d9d9',
                      }}
                    >
                      <Avatar icon={<UserOutlined />} size={48} />
                    </Badge>
                  }
                  title={
                    <Space>
                      <Text strong>{expert.name}</Text>
                      {index === 0 && (
                        <Tag color="gold" icon={<StarOutlined />}>
                          {t('ontology:expert.topRecommended')}
                        </Tag>
                      )}
                      {AVAILABILITY_ICONS[expert.availability]}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      {/* Expertise Areas */}
                      <Space wrap>
                        {expert.expertise_areas.map((area) => (
                          <Tag key={area} color={EXPERTISE_COLORS[area]}>
                            {area}
                          </Tag>
                        ))}
                      </Space>

                      {/* Match Score */}
                      <Space>
                        <Text type="secondary">{t('ontology:expert.matchScore')}:</Text>
                        <Progress
                          percent={Math.round(expert.match_score * 100)}
                          size="small"
                          strokeColor={getMatchScoreColor(expert.match_score)}
                          style={{ width: 100 }}
                        />
                      </Space>

                      {/* Contribution Score */}
                      <Space>
                        <Text type="secondary">{t('ontology:expert.contributionScore')}:</Text>
                        <Rate
                          disabled
                          allowHalf
                          value={expert.contribution_score}
                          style={{ fontSize: 12 }}
                        />
                        <Text>({expert.contribution_score.toFixed(1)})</Text>
                      </Space>

                      {/* Availability */}
                      <Space>
                        <Text type="secondary">{t('ontology:expert.availability')}:</Text>
                        <Tag color={AVAILABILITY_COLORS[expert.availability]}>
                          {expert.availability}
                        </Tag>
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </>
      ) : searchArea ? (
        <Empty
          description={
            <Space direction="vertical">
              <Text>{t('ontology:expert.noExpertsFound')}</Text>
              <Text type="secondary">
                {t('ontology:expert.noExpertsFoundDescription', { area: searchArea })}
              </Text>
            </Space>
          }
        />
      ) : (
        <Empty
          description={t('ontology:expert.enterOntologyArea')}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}
    </Card>
  );
};

export default ExpertRecommendation;
