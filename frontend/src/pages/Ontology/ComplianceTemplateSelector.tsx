/**
 * ComplianceTemplateSelector Component (合规模板选择器)
 * 
 * Component for selecting and applying compliance templates with:
 * - List compliance templates (数据安全法, 个人信息保护法, etc.)
 * - Show template description and requirements
 * - Apply template to ontology
 * 
 * Requirements: 8.1
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
  Alert,
  Collapse,
  List,
  Checkbox,
  message,
  Modal,
  Divider,
  Badge,
} from 'antd';
import {
  SafetyCertificateOutlined,
  UserOutlined,
  GlobalOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  FileProtectOutlined,
  LockOutlined,
  AuditOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface ComplianceTemplate {
  id: string;
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  requirements: ComplianceRequirement[];
  classifications: DataClassification[];
}

interface ComplianceRequirement {
  key: string;
  name: string;
  description: string;
  article?: string;
}

interface DataClassification {
  level: string;
  name: string;
  description: string;
  color: string;
}

interface ComplianceTemplateSelectorProps {
  ontologyId: string;
  onApply?: (templateId: string) => void;
}

const COMPLIANCE_TEMPLATES: ComplianceTemplate[] = [
  {
    id: 'dsl',
    key: 'dsl',
    name: 'compliance.templates.dsl',
    description: 'compliance.templates.dslDesc',
    icon: <SafetyCertificateOutlined style={{ fontSize: 32 }} />,
    color: '#1890ff',
    requirements: [
      {
        key: 'classification',
        name: 'compliance.classification.title',
        description: '对数据实行分类分级保护',
        article: '第21条',
      },
      {
        key: 'security',
        name: '数据安全保护',
        description: '建立健全全流程数据安全管理制度',
        article: '第27条',
      },
      {
        key: 'risk_assessment',
        name: '风险评估',
        description: '定期开展数据安全风险评估',
        article: '第30条',
      },
    ],
    classifications: [
      {
        level: 'core',
        name: 'compliance.classification.core',
        description: 'compliance.classification.coreDesc',
        color: 'red',
      },
      {
        level: 'important',
        name: 'compliance.classification.important',
        description: 'compliance.classification.importantDesc',
        color: 'orange',
      },
      {
        level: 'general',
        name: 'compliance.classification.general',
        description: 'compliance.classification.generalDesc',
        color: 'green',
      },
    ],
  },
  {
    id: 'pipl',
    key: 'pipl',
    name: 'compliance.templates.pipl',
    description: 'compliance.templates.piplDesc',
    icon: <UserOutlined style={{ fontSize: 32 }} />,
    color: '#52c41a',
    requirements: [
      {
        key: 'consent',
        name: 'compliance.pipl.consent',
        description: 'compliance.pipl.consentDesc',
        article: '第13条',
      },
      {
        key: 'purpose_limitation',
        name: 'compliance.pipl.purposeLimitation',
        description: 'compliance.pipl.purposeLimitationDesc',
        article: '第6条',
      },
      {
        key: 'data_minimization',
        name: 'compliance.pipl.dataMinimization',
        description: 'compliance.pipl.dataMinimizationDesc',
        article: '第6条',
      },
      {
        key: 'cross_border',
        name: 'compliance.pipl.crossBorder',
        description: 'compliance.pipl.crossBorderDesc',
        article: '第38条',
      },
    ],
    classifications: [
      {
        level: 'sensitive',
        name: '敏感个人信息',
        description: '一旦泄露或者非法使用，容易导致自然人的人格尊严受到侵害或者人身、财产安全受到危害的个人信息',
        color: 'red',
      },
      {
        level: 'basic',
        name: '一般个人信息',
        description: '除敏感个人信息以外的其他个人信息',
        color: 'blue',
      },
    ],
  },
  {
    id: 'csl',
    key: 'csl',
    name: 'compliance.templates.csl',
    description: 'compliance.templates.cslDesc',
    icon: <GlobalOutlined style={{ fontSize: 32 }} />,
    color: '#722ed1',
    requirements: [
      {
        key: 'security_protection',
        name: '网络安全等级保护',
        description: '按照网络安全等级保护制度的要求，履行安全保护义务',
        article: '第21条',
      },
      {
        key: 'incident_response',
        name: '安全事件应急',
        description: '制定网络安全事件应急预案',
        article: '第25条',
      },
      {
        key: 'data_localization',
        name: '数据本地化',
        description: '关键信息基础设施运营者在境内收集和产生的个人信息和重要数据应当在境内存储',
        article: '第37条',
      },
    ],
    classifications: [
      {
        level: 'critical',
        name: '关键信息基础设施',
        description: '公共通信和信息服务、能源、交通、水利、金融、公共服务、电子政务等重要行业和领域',
        color: 'red',
      },
      {
        level: 'normal',
        name: '一般网络',
        description: '除关键信息基础设施以外的其他网络',
        color: 'blue',
      },
    ],
  },
];

const ComplianceTemplateSelector: React.FC<ComplianceTemplateSelectorProps> = ({
  ontologyId,
  onApply,
}) => {
  const { t } = useTranslation('ontology');
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [applying, setApplying] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedDetail, setSelectedDetail] = useState<ComplianceTemplate | null>(null);

  const handleToggleTemplate = (templateId: string) => {
    setSelectedTemplates((prev) =>
      prev.includes(templateId)
        ? prev.filter((id) => id !== templateId)
        : [...prev, templateId]
    );
  };

  const handleApply = async () => {
    if (selectedTemplates.length === 0) {
      message.warning(t('compliance.selectTemplate'));
      return;
    }

    setApplying(true);
    try {
      // Apply each selected template
      for (const templateId of selectedTemplates) {
        onApply?.(templateId);
      }
      message.success(t('compliance.applySuccess'));
      setSelectedTemplates([]);
    } catch (error) {
      console.error('Failed to apply templates:', error);
      message.error(t('compliance.applyFailed'));
    } finally {
      setApplying(false);
    }
  };

  const showDetail = (template: ComplianceTemplate) => {
    setSelectedDetail(template);
    setDetailModalVisible(true);
  };

  const renderTemplateCard = (template: ComplianceTemplate) => {
    const isSelected = selectedTemplates.includes(template.id);

    return (
      <Col span={8} key={template.id}>
        <Badge.Ribbon
          text={isSelected ? <CheckCircleOutlined /> : null}
          color={isSelected ? 'green' : 'transparent'}
        >
          <Card
            hoverable
            style={{
              borderColor: isSelected ? template.color : undefined,
              borderWidth: isSelected ? 2 : 1,
            }}
            actions={[
              <Checkbox
                checked={isSelected}
                onChange={() => handleToggleTemplate(template.id)}
              >
                {t('common.select')}
              </Checkbox>,
              <Button type="link" onClick={() => showDetail(template)}>
                {t('common.details')}
              </Button>,
            ]}
          >
            <Card.Meta
              avatar={
                <div style={{ color: template.color }}>
                  {template.icon}
                </div>
              }
              title={t(template.name)}
              description={
                <Paragraph
                  ellipsis={{ rows: 2 }}
                  type="secondary"
                  style={{ marginBottom: 0 }}
                >
                  {t(template.description)}
                </Paragraph>
              }
            />
            <Divider style={{ margin: '12px 0' }} />
            <Space wrap>
              <Tag icon={<FileProtectOutlined />}>
                {template.requirements.length} {t('common.requirements')}
              </Tag>
              <Tag icon={<AuditOutlined />}>
                {template.classifications.length} {t('compliance.classification.title')}
              </Tag>
            </Space>
          </Card>
        </Badge.Ribbon>
      </Col>
    );
  };

  return (
    <div>
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>
          <LockOutlined /> {t('compliance.title')}
        </Title>
        <Paragraph type="secondary">
          {t('compliance.selectTemplateDesc')}
        </Paragraph>
      </Card>

      {/* Template Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {COMPLIANCE_TEMPLATES.map(renderTemplateCard)}
      </Row>

      {/* Apply Button */}
      {selectedTemplates.length > 0 && (
        <Card>
          <Space>
            <Text>
              {t('common.selected')}: {selectedTemplates.length} {t('common.items')}
            </Text>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={handleApply}
              loading={applying}
            >
              {t('compliance.applyTemplate')}
            </Button>
          </Space>
        </Card>
      )}

      {/* Detail Modal */}
      <Modal
        title={selectedDetail ? t(selectedDetail.name) : ''}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            {t('common.close')}
          </Button>,
          <Button
            key="apply"
            type="primary"
            onClick={() => {
              if (selectedDetail) {
                handleToggleTemplate(selectedDetail.id);
                setDetailModalVisible(false);
              }
            }}
          >
            {selectedTemplates.includes(selectedDetail?.id || '')
              ? t('common.deselect')
              : t('common.select')}
          </Button>,
        ]}
        width={700}
      >
        {selectedDetail && (
          <>
            <Alert
              type="info"
              showIcon
              icon={selectedDetail.icon}
              message={t(selectedDetail.name)}
              description={t(selectedDetail.description)}
              style={{ marginBottom: 16 }}
            />

            <Collapse defaultActiveKey={['requirements', 'classifications']}>
              <Panel
                header={
                  <Space>
                    <FileProtectOutlined />
                    {t('common.requirements')}
                  </Space>
                }
                key="requirements"
              >
                <List
                  size="small"
                  dataSource={selectedDetail.requirements}
                  renderItem={(req) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                        title={
                          <Space>
                            {t(req.name)}
                            {req.article && <Tag>{req.article}</Tag>}
                          </Space>
                        }
                        description={t(req.description)}
                      />
                    </List.Item>
                  )}
                />
              </Panel>

              <Panel
                header={
                  <Space>
                    <AuditOutlined />
                    {t('compliance.classification.title')}
                  </Space>
                }
                key="classifications"
              >
                <List
                  size="small"
                  dataSource={selectedDetail.classifications}
                  renderItem={(cls) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={
                          <Tag color={cls.color}>{cls.level.toUpperCase()}</Tag>
                        }
                        title={t(cls.name)}
                        description={t(cls.description)}
                      />
                    </List.Item>
                  )}
                />
              </Panel>
            </Collapse>
          </>
        )}
      </Modal>
    </div>
  );
};

export default ComplianceTemplateSelector;
