/**
 * Template Browser Component (模板浏览器)
 * 
 * Displays a grid of available ontology templates with filtering by industry.
 * Shows template metadata including version, author, and usage count.
 * 
 * Requirements: Task 21.1 - Template Management
 * Validates: Requirements 2.1, 2.4
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Input,
  Select,
  Tag,
  Typography,
  Space,
  Button,
  Empty,
  Spin,
  Badge,
  Tooltip,
  Statistic,
} from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  BranchesOutlined,
  NodeIndexOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  CalendarOutlined,
  RiseOutlined,
  EyeOutlined,
  PlusOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { ontologyTemplateApi, OntologyTemplate } from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

// Industry options for filtering
const INDUSTRY_OPTIONS = [
  { value: '金融', labelKey: 'template.industries.finance' },
  { value: '医疗', labelKey: 'template.industries.healthcare' },
  { value: '制造', labelKey: 'template.industries.manufacturing' },
  { value: '政务', labelKey: 'template.industries.government' },
  { value: '法律', labelKey: 'template.industries.legal' },
  { value: '教育', labelKey: 'template.industries.education' },
];

// Industry color mapping
const INDUSTRY_COLORS: Record<string, string> = {
  '金融': 'gold',
  '医疗': 'green',
  '制造': 'blue',
  '政务': 'red',
  '法律': 'purple',
  '教育': 'cyan',
};

interface TemplateBrowserProps {
  onSelectTemplate?: (template: OntologyTemplate) => void;
  onInstantiate?: (template: OntologyTemplate) => void;
  onCustomize?: (template: OntologyTemplate) => void;
  onExport?: (template: OntologyTemplate) => void;
}

const TemplateBrowser: React.FC<TemplateBrowserProps> = ({
  onSelectTemplate,
  onInstantiate,
  onCustomize,
  onExport,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const [searchText, setSearchText] = useState('');
  const [selectedIndustry, setSelectedIndustry] = useState<string | undefined>();

  // Fetch templates
  const {
    data: templateResponse,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['ontology-templates', selectedIndustry],
    queryFn: () => ontologyTemplateApi.listTemplates({ industry: selectedIndustry }),
  });

  // Filter templates by search text
  const filteredTemplates = useMemo(() => {
    if (!templateResponse?.templates) return [];
    
    if (!searchText.trim()) return templateResponse.templates;
    
    const lowerSearch = searchText.toLowerCase();
    return templateResponse.templates.filter(
      (template) =>
        template.name.toLowerCase().includes(lowerSearch) ||
        template.description?.toLowerCase().includes(lowerSearch) ||
        template.industry.toLowerCase().includes(lowerSearch)
    );
  }, [templateResponse?.templates, searchText]);

  // Handle template card click
  const handleTemplateClick = (template: OntologyTemplate) => {
    onSelectTemplate?.(template);
  };

  // Render template card
  const renderTemplateCard = (template: OntologyTemplate) => {
    const industryColor = INDUSTRY_COLORS[template.industry] || 'default';
    
    return (
      <Col xs={24} sm={12} lg={8} xl={6} key={template.id}>
        <Badge.Ribbon
          text={template.industry}
          color={industryColor}
        >
          <Card
            hoverable
            onClick={() => handleTemplateClick(template)}
            className="template-card"
            actions={[
              <Tooltip title={t('ontology:template.viewDetails')} key="view">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemplateClick(template);
                  }}
                />
              </Tooltip>,
              <Tooltip title={t('ontology:template.instantiate')} key="instantiate">
                <Button
                  type="text"
                  icon={<PlusOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onInstantiate?.(template);
                  }}
                />
              </Tooltip>,
              <Tooltip title={t('ontology:template.export')} key="export">
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onExport?.(template);
                  }}
                />
              </Tooltip>,
            ]}
          >
            <Card.Meta
              avatar={
                <FileTextOutlined style={{ fontSize: 32, color: '#1890ff' }} />
              }
              title={
                <Space direction="vertical" size={0}>
                  <Text strong ellipsis={{ tooltip: template.name }}>
                    {template.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    v{template.version}
                  </Text>
                </Space>
              }
              description={
                <Paragraph
                  ellipsis={{ rows: 2, tooltip: template.description }}
                  style={{ marginBottom: 12 }}
                >
                  {template.description || t('ontology:template.noDescription')}
                </Paragraph>
              }
            />
            
            <Row gutter={[8, 8]} style={{ marginTop: 12 }}>
              <Col span={8}>
                <Statistic
                  title={
                    <Tooltip title={t('ontology:template.entityTypes')}>
                      <Space size={4}>
                        <NodeIndexOutlined />
                        <span style={{ fontSize: 11 }}>
                          {t('ontology:template.entities')}
                        </span>
                      </Space>
                    </Tooltip>
                  }
                  value={template.entity_types?.length || 0}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title={
                    <Tooltip title={t('ontology:template.relationTypes')}>
                      <Space size={4}>
                        <BranchesOutlined />
                        <span style={{ fontSize: 11 }}>
                          {t('ontology:template.relations')}
                        </span>
                      </Space>
                    </Tooltip>
                  }
                  value={template.relation_types?.length || 0}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title={
                    <Tooltip title={t('ontology:template.validationRules')}>
                      <Space size={4}>
                        <SafetyCertificateOutlined />
                        <span style={{ fontSize: 11 }}>
                          {t('ontology:template.rules')}
                        </span>
                      </Space>
                    </Tooltip>
                  }
                  value={template.validation_rules?.length || 0}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
            </Row>
            
            <div style={{ marginTop: 12, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
              <Space size={16}>
                <Tooltip title={t('ontology:template.usageCount')}>
                  <Space size={4}>
                    <RiseOutlined style={{ color: '#52c41a' }} />
                    <Text type="secondary">{template.usage_count || 0}</Text>
                  </Space>
                </Tooltip>
                {template.created_by && (
                  <Tooltip title={t('ontology:template.createdBy')}>
                    <Space size={4}>
                      <UserOutlined />
                      <Text type="secondary" ellipsis style={{ maxWidth: 80 }}>
                        {template.created_by}
                      </Text>
                    </Space>
                  </Tooltip>
                )}
              </Space>
            </div>
          </Card>
        </Badge.Ribbon>
      </Col>
    );
  };

  if (error) {
    return (
      <Card>
        <Empty
          description={t('ontology:template.loadError')}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  return (
    <div className="template-browser">
      <Card>
        <Title level={4}>
          <Space>
            <FileTextOutlined />
            {t('ontology:template.listTitle')}
          </Space>
        </Title>
        
        {/* Filters */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder={t('ontology:template.searchPlaceholder')}
              allowClear
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Select
              placeholder={t('ontology:template.filterByIndustry')}
              allowClear
              style={{ width: '100%' }}
              value={selectedIndustry}
              onChange={setSelectedIndustry}
              options={INDUSTRY_OPTIONS.map((opt) => ({
                value: opt.value,
                label: t(opt.labelKey, { defaultValue: opt.value }),
              }))}
            />
          </Col>
          <Col xs={24} sm={24} md={8} style={{ textAlign: 'right' }}>
            <Text type="secondary">
              {t('ontology:template.totalTemplates', {
                count: filteredTemplates.length,
              })}
            </Text>
          </Col>
        </Row>
        
        {/* Template Grid */}
        <Spin spinning={isLoading}>
          {filteredTemplates.length > 0 ? (
            <Row gutter={[16, 16]}>
              {filteredTemplates.map(renderTemplateCard)}
            </Row>
          ) : (
            <Empty
              description={
                searchText || selectedIndustry
                  ? t('ontology:template.noMatchingTemplates')
                  : t('ontology:template.noTemplates')
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default TemplateBrowser;
