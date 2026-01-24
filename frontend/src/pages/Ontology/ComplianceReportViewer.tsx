/**
 * ComplianceReportViewer Component (合规报告查看器)
 * 
 * Component for viewing compliance reports with:
 * - Display compliance report
 * - Show ontology element to regulation mapping
 * - Include citation references
 * - Export to PDF/JSON
 * 
 * Requirements: 8.5
 */

import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Tag,
  Button,
  Space,
  Progress,
  Table,
  List,
  Empty,
  Divider,
  Statistic,
  Alert,
  Tooltip,
  Dropdown,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  FileTextOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileOutlined,
  SafetyCertificateOutlined,
  LinkOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;

interface EntityMapping {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  classification: string;
  regulations: string[];
  compliance_status: 'compliant' | 'non_compliant' | 'needs_review';
}

interface Citation {
  regulation: string;
  article: string;
  content: string;
  relevance: string;
}

interface Recommendation {
  priority: 'high' | 'medium' | 'low';
  category: string;
  description: string;
  affected_entities: string[];
}

interface ComplianceReport {
  id: string;
  ontology_id: string;
  generated_at: string;
  compliance_score: number;
  entity_mappings: EntityMapping[];
  citations: Citation[];
  recommendations: Recommendation[];
  summary: {
    total_entities: number;
    compliant_count: number;
    non_compliant_count: number;
    needs_review_count: number;
  };
}

interface ComplianceReportViewerProps {
  report?: ComplianceReport;
  loading?: boolean;
  onGenerate?: () => void;
  onExport?: (format: 'pdf' | 'json') => void;
}

// Mock report for demonstration
const MOCK_REPORT: ComplianceReport = {
  id: 'report-001',
  ontology_id: 'ontology-001',
  generated_at: new Date().toISOString(),
  compliance_score: 78,
  entity_mappings: [
    {
      entity_id: 'e1',
      entity_name: '客户信息',
      entity_type: 'PersonalInfo',
      classification: '敏感个人信息',
      regulations: ['个人信息保护法 第28条', '数据安全法 第21条'],
      compliance_status: 'compliant',
    },
    {
      entity_id: 'e2',
      entity_name: '交易记录',
      entity_type: 'Transaction',
      classification: '重要数据',
      regulations: ['数据安全法 第21条'],
      compliance_status: 'needs_review',
    },
    {
      entity_id: 'e3',
      entity_name: '用户行为日志',
      entity_type: 'BehaviorLog',
      classification: '一般数据',
      regulations: ['网络安全法 第21条'],
      compliance_status: 'non_compliant',
    },
  ],
  citations: [
    {
      regulation: '个人信息保护法',
      article: '第28条',
      content: '敏感个人信息是一旦泄露或者非法使用，容易导致自然人的人格尊严受到侵害或者人身、财产安全受到危害的个人信息',
      relevance: '适用于客户信息实体的分类',
    },
    {
      regulation: '数据安全法',
      article: '第21条',
      content: '国家建立数据分类分级保护制度，根据数据在经济社会发展中的重要程度，以及一旦遭到篡改、破坏、泄露或者非法获取、非法利用，对国家安全、公共利益或者个人、组织合法权益造成的危害程度，对数据实行分类分级保护',
      relevance: '适用于所有数据实体的分类分级',
    },
  ],
  recommendations: [
    {
      priority: 'high',
      category: '数据分类',
      description: '建议对"用户行为日志"实体进行重新分类，当前分类可能不符合网络安全法要求',
      affected_entities: ['用户行为日志'],
    },
    {
      priority: 'medium',
      category: '访问控制',
      description: '建议为"交易记录"实体添加更严格的访问控制规则',
      affected_entities: ['交易记录'],
    },
    {
      priority: 'low',
      category: '文档完善',
      description: '建议完善数据处理目的说明文档',
      affected_entities: ['客户信息', '交易记录'],
    },
  ],
  summary: {
    total_entities: 3,
    compliant_count: 1,
    non_compliant_count: 1,
    needs_review_count: 1,
  },
};

const ComplianceReportViewer: React.FC<ComplianceReportViewerProps> = ({
  report = MOCK_REPORT,
  loading = false,
  onGenerate,
  onExport,
}) => {
  const { t } = useTranslation('ontology');

  const getScoreStatus = (score: number) => {
    if (score >= 90) return { color: '#52c41a', text: t('compliance.report.scoreExcellent') };
    if (score >= 70) return { color: '#1890ff', text: t('compliance.report.scoreGood') };
    if (score >= 50) return { color: '#faad14', text: t('compliance.report.scoreFair') };
    return { color: '#ff4d4f', text: t('compliance.report.scorePoor') };
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'compliant':
        return <Tag color="success" icon={<CheckCircleOutlined />}>{t('validation.isValid')}</Tag>;
      case 'non_compliant':
        return <Tag color="error" icon={<CloseCircleOutlined />}>{t('validation.isInvalid')}</Tag>;
      case 'needs_review':
        return <Tag color="warning" icon={<WarningOutlined />}>{t('expert.pending')}</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const getPriorityTag = (priority: string) => {
    const colors: Record<string, string> = {
      high: 'red',
      medium: 'orange',
      low: 'blue',
    };
    return <Tag color={colors[priority]}>{priority.toUpperCase()}</Tag>;
  };

  const exportMenuItems: MenuProps['items'] = [
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: t('compliance.report.exportPdf'),
      onClick: () => onExport?.('pdf'),
    },
    {
      key: 'json',
      icon: <FileOutlined />,
      label: t('compliance.report.exportJson'),
      onClick: () => onExport?.('json'),
    },
  ];

  const entityColumns: ColumnsType<EntityMapping> = [
    {
      title: t('template.entityName'),
      dataIndex: 'entity_name',
      key: 'entity_name',
    },
    {
      title: t('validation.targetEntityType'),
      dataIndex: 'entity_type',
      key: 'entity_type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('compliance.classification.title'),
      dataIndex: 'classification',
      key: 'classification',
      render: (cls: string) => {
        const colors: Record<string, string> = {
          '核心数据': 'red',
          '重要数据': 'orange',
          '一般数据': 'green',
          '敏感个人信息': 'red',
          '一般个人信息': 'blue',
        };
        return <Tag color={colors[cls] || 'default'}>{cls}</Tag>;
      },
    },
    {
      title: t('compliance.report.citations'),
      dataIndex: 'regulations',
      key: 'regulations',
      render: (regs: string[]) => (
        <Space wrap>
          {regs.map((reg, idx) => (
            <Tooltip key={idx} title={reg}>
              <Tag icon={<LinkOutlined />}>{reg.split(' ')[0]}</Tag>
            </Tooltip>
          ))}
        </Space>
      ),
    },
    {
      title: t('comparison.status'),
      dataIndex: 'compliance_status',
      key: 'compliance_status',
      render: (status: string) => getStatusTag(status),
    },
  ];

  if (!report) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('compliance.report.noReport')}
        >
          <Button type="primary" onClick={onGenerate} loading={loading}>
            {t('compliance.report.generate')}
          </Button>
        </Empty>
      </Card>
    );
  }

  const scoreStatus = getScoreStatus(report.compliance_score);

  return (
    <div>
      {/* Header with Score */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24} align="middle">
          <Col span={8}>
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="dashboard"
                percent={report.compliance_score}
                strokeColor={scoreStatus.color}
                format={(percent) => (
                  <div>
                    <div style={{ fontSize: 24, fontWeight: 'bold' }}>{percent}</div>
                    <div style={{ fontSize: 12, color: scoreStatus.color }}>
                      {scoreStatus.text}
                    </div>
                  </div>
                )}
              />
              <Text type="secondary">{t('compliance.report.complianceScore')}</Text>
            </div>
          </Col>
          <Col span={16}>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title={t('validation.isValid')}
                  value={report.summary.compliant_count}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                  suffix={`/ ${report.summary.total_entities}`}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title={t('expert.pending')}
                  value={report.summary.needs_review_count}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<WarningOutlined />}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title={t('validation.isInvalid')}
                  value={report.summary.non_compliant_count}
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Col>
            </Row>
            <Divider style={{ margin: '16px 0' }} />
            <Space>
              <Text type="secondary">
                {t('comparison.createdAt')}: {new Date(report.generated_at).toLocaleString()}
              </Text>
              <Dropdown menu={{ items: exportMenuItems }}>
                <Button icon={<DownloadOutlined />}>
                  {t('template.export')}
                </Button>
              </Dropdown>
              <Button onClick={onGenerate} loading={loading}>
                {t('common.refresh')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Entity Mappings */}
      <Card
        title={
          <Space>
            <FileTextOutlined />
            {t('compliance.report.entityMapping')}
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={entityColumns}
          dataSource={report.entity_mappings}
          rowKey="entity_id"
          pagination={false}
          size="small"
        />
      </Card>

      {/* Citations */}
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            {t('compliance.report.citations')}
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <List
          dataSource={report.citations}
          renderItem={(citation) => (
            <List.Item>
              <List.Item.Meta
                avatar={<LinkOutlined style={{ fontSize: 20, color: '#1890ff' }} />}
                title={
                  <Space>
                    <Text strong>{citation.regulation}</Text>
                    <Tag>{citation.article}</Tag>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={4}>
                    <Paragraph
                      style={{ marginBottom: 0 }}
                      ellipsis={{ rows: 2, expandable: true }}
                    >
                      {citation.content}
                    </Paragraph>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {citation.relevance}
                    </Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      {/* Recommendations */}
      <Card
        title={
          <Space>
            <BulbOutlined />
            {t('compliance.report.recommendations')}
          </Space>
        }
      >
        <List
          dataSource={report.recommendations}
          renderItem={(rec) => (
            <List.Item>
              <List.Item.Meta
                avatar={getPriorityTag(rec.priority)}
                title={
                  <Space>
                    <Tag color="blue">{rec.category}</Tag>
                    <Text>{rec.description}</Text>
                  </Space>
                }
                description={
                  <Space wrap>
                    <Text type="secondary">{t('approval.affectedEntities')}:</Text>
                    {rec.affected_entities.map((entity) => (
                      <Tag key={entity}>{entity}</Tag>
                    ))}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default ComplianceReportViewer;
