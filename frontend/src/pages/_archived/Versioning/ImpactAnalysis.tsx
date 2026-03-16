/**
 * Impact Analysis Component
 * 
 * Analyzes and visualizes the impact of data changes:
 * - Risk assessment
 * - Affected entities list
 * - Recommendations
 * - Impact visualization
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Space,
  Button,
  Select,
  Spin,
  Empty,
  message,
  Tag,
  Alert,
  List,
  Progress,
  Statistic,
  Row,
  Col,
  Typography,
  Collapse,
  Tooltip,
} from 'antd';
import {
  ThunderboltOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  BulbOutlined,
  ApartmentOutlined,
  NumberOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { lineageApi, ImpactReport, EntityImpact } from '../../services/lineageApi';

const { Text, Title, Paragraph } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

interface ImpactAnalysisProps {
  entityType: string;
  entityId: string;
  tenantId?: string;
  onAnalysisComplete?: (report: ImpactReport) => void;
}

const ImpactAnalysis: React.FC<ImpactAnalysisProps> = ({
  entityType,
  entityId,
  tenantId,
  onAnalysisComplete,
}) => {
  const { t } = useTranslation(['impact', 'common']);
  const [report, setReport] = useState<ImpactReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [changeType, setChangeType] = useState<string>('update');
  const [maxDepth, setMaxDepth] = useState(5);

  const analyzeImpact = async () => {
    setLoading(true);
    try {
      const result = await lineageApi.analyzeImpact(
        entityType,
        entityId,
        changeType,
        maxDepth,
        tenantId
      );
      setReport(result.impact_report);
      onAnalysisComplete?.(result.impact_report);
    } catch (error) {
      message.error(t('analyzeError', 'Failed to analyze impact'));
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'critical':
        return '#ff4d4f';
      case 'high':
        return '#fa8c16';
      case 'medium':
        return '#faad14';
      case 'low':
        return '#52c41a';
      default:
        return '#d9d9d9';
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'critical':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'high':
        return <ExclamationCircleOutlined style={{ color: '#fa8c16' }} />;
      case 'medium':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'low':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      default:
        return null;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'orange';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getRiskProgress = (level: string) => {
    switch (level) {
      case 'critical':
        return 100;
      case 'high':
        return 75;
      case 'medium':
        return 50;
      case 'low':
        return 25;
      default:
        return 0;
    }
  };

  const countBySeverity = (entities: EntityImpact[]) => {
    return entities.reduce(
      (acc, e) => {
        acc[e.severity] = (acc[e.severity] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );
  };

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text type="secondary">{t('analyzing', 'Analyzing impact...')}</Text>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          <span>{t('analysis', 'Impact Analysis')}</span>
        </Space>
      }
      extra={
        <Space>
          <Select
            value={changeType}
            onChange={setChangeType}
            style={{ width: 120 }}
          >
            <Option value="update">{t('update', 'Update')}</Option>
            <Option value="delete">{t('delete', 'Delete')}</Option>
            <Option value="create">{t('create', 'Create')}</Option>
          </Select>
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={analyzeImpact}
            loading={loading}
          >
            {t('analyze', 'Analyze')}
          </Button>
        </Space>
      }
    >
      {!report ? (
        <Empty
          description={t('clickToAnalyze', 'Click Analyze to assess impact')}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Risk Level Summary */}
          <Alert
            type={
              report.risk_level === 'critical' || report.risk_level === 'high'
                ? 'error'
                : report.risk_level === 'medium'
                ? 'warning'
                : 'success'
            }
            icon={getRiskIcon(report.risk_level)}
            message={
              <Space>
                <Text strong>
                  {t('riskLevel', 'Risk Level')}:
                </Text>
                <Tag color={getRiskColor(report.risk_level)}>
                  {report.risk_level.toUpperCase()}
                </Tag>
              </Space>
            }
            description={
              <Progress
                percent={getRiskProgress(report.risk_level)}
                strokeColor={getRiskColor(report.risk_level)}
                showInfo={false}
                size="small"
              />
            }
          />

          {/* Statistics */}
          <Row gutter={16}>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title={t('affectedEntities', 'Affected Entities')}
                  value={report.affected_count}
                  prefix={<ApartmentOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title={t('estimatedRecords', 'Est. Records')}
                  value={report.estimated_records}
                  prefix={<NumberOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title={t('criticalPaths', 'Critical Paths')}
                  value={report.critical_paths.length}
                  valueStyle={{ color: report.critical_paths.length > 0 ? '#ff4d4f' : '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title={t('riskFactors', 'Risk Factors')}
                  value={report.risk_factors.length}
                  valueStyle={{ color: report.risk_factors.length > 0 ? '#faad14' : '#52c41a' }}
                />
              </Card>
            </Col>
          </Row>

          {/* Severity Breakdown */}
          {report.affected_entities.length > 0 && (
            <Card size="small" title={t('severityBreakdown', 'Severity Breakdown')}>
              <Space wrap>
                {Object.entries(countBySeverity(report.affected_entities)).map(
                  ([severity, count]) => (
                    <Tag key={severity} color={getSeverityColor(severity)}>
                      {severity}: {count}
                    </Tag>
                  )
                )}
              </Space>
            </Card>
          )}

          {/* Risk Factors */}
          {report.risk_factors.length > 0 && (
            <Card
              size="small"
              title={
                <Space>
                  <WarningOutlined style={{ color: '#faad14' }} />
                  {t('riskFactors', 'Risk Factors')}
                </Space>
              }
            >
              <List
                size="small"
                dataSource={report.risk_factors}
                renderItem={(factor) => (
                  <List.Item>
                    <Text type="warning">{factor}</Text>
                  </List.Item>
                )}
              />
            </Card>
          )}

          {/* Recommendations */}
          {report.recommendations.length > 0 && (
            <Card
              size="small"
              title={
                <Space>
                  <BulbOutlined style={{ color: '#1890ff' }} />
                  {t('recommendations', 'Recommendations')}
                </Space>
              }
            >
              <List
                size="small"
                dataSource={report.recommendations}
                renderItem={(rec, index) => (
                  <List.Item>
                    <Space>
                      <Tag color="blue">{index + 1}</Tag>
                      <Text>{rec}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          )}

          {/* Affected Entities */}
          <Collapse>
            <Panel
              header={
                <Space>
                  <ApartmentOutlined />
                  {t('affectedEntitiesList', 'Affected Entities')}
                  <Tag>{report.affected_count}</Tag>
                </Space>
              }
              key="entities"
            >
              <List
                size="small"
                dataSource={report.affected_entities}
                renderItem={(entity) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color={getSeverityColor(entity.severity)}>
                            {entity.severity}
                          </Tag>
                          <Text strong>
                            {entity.entity_name || `${entity.entity_type}:${entity.entity_id}`}
                          </Text>
                        </Space>
                      }
                      description={
                        <Space>
                          <Text type="secondary">
                            {t('type', 'Type')}: {entity.entity_type}
                          </Text>
                          <Text type="secondary">
                            {t('distance', 'Distance')}: {entity.distance}
                          </Text>
                          <Text type="secondary">
                            {t('impactType', 'Impact')}: {entity.impact_type}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
                pagination={{ pageSize: 10 }}
              />
            </Panel>

            {/* Critical Paths */}
            {report.critical_paths.length > 0 && (
              <Panel
                header={
                  <Space>
                    <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                    {t('criticalPaths', 'Critical Paths')}
                    <Tag color="error">{report.critical_paths.length}</Tag>
                  </Space>
                }
                key="paths"
              >
                <List
                  size="small"
                  dataSource={report.critical_paths}
                  renderItem={(pathInfo, index) => (
                    <List.Item>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <Tag color="error">{pathInfo.severity}</Tag>
                          <Text strong>{pathInfo.target}</Text>
                        </Space>
                        <div style={{ paddingLeft: 16 }}>
                          {pathInfo.path.path?.map((node, i) => (
                            <React.Fragment key={i}>
                              <Tag>{`${node.entity_type}:${node.entity_id.slice(0, 8)}`}</Tag>
                              {i < (pathInfo.path.path?.length || 0) - 1 && (
                                <span style={{ margin: '0 4px' }}>→</span>
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </Space>
                    </List.Item>
                  )}
                />
              </Panel>
            )}
          </Collapse>
        </Space>
      )}
    </Card>
  );
};

export default ImpactAnalysis;
