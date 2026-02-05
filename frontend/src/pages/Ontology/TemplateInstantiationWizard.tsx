/**
 * Template Instantiation Wizard Component (模板实例化向导)
 * 
 * Step-by-step wizard for instantiating ontology templates.
 * Allows preview of entity types and relations, and customization during instantiation.
 * 
 * Requirements: Task 21.2 - Template Management
 * Validates: Requirements 2.2, 2.3
 */

import React, { useState, useMemo } from 'react';
import {
  Modal,
  Steps,
  Card,
  Form,
  Input,
  Select,
  Table,
  Tag,
  Typography,
  Space,
  Button,
  Checkbox,
  Alert,
  Divider,
  Row,
  Col,
  Spin,
  Result,
  message,
} from 'antd';
import {
  FileTextOutlined,
  NodeIndexOutlined,
  BranchesOutlined,
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import {
  ontologyTemplateApi,
  OntologyTemplate,
  EntityTypeDefinition,
  RelationTypeDefinition,
  TemplateInstantiateRequest,
} from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface TemplateInstantiationWizardProps {
  template: OntologyTemplate | null;
  visible: boolean;
  onClose: () => void;
  onSuccess?: (instanceId: string) => void;
}

interface CustomizationState {
  excludedEntityTypes: string[];
  excludedRelationTypes: string[];
  projectName: string;
  projectDescription: string;
}

const TemplateInstantiationWizard: React.FC<TemplateInstantiationWizardProps> = ({
  template,
  visible,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [customization, setCustomization] = useState<CustomizationState>({
    excludedEntityTypes: [],
    excludedRelationTypes: [],
    projectName: '',
    projectDescription: '',
  });

  // Instantiate mutation
  const instantiateMutation = useMutation({
    mutationFn: (data: { templateId: string; request: TemplateInstantiateRequest }) =>
      ontologyTemplateApi.instantiateTemplate(data.templateId, data.request),
    onSuccess: (result) => {
      message.success(t('ontology:template.instantiateSuccess'));
      onSuccess?.(result.instance_id);
      handleClose();
    },
    onError: () => {
      message.error(t('ontology:template.instantiateFailed'));
    },
  });

  // Reset state when modal closes
  const handleClose = () => {
    setCurrentStep(0);
    setCustomization({
      excludedEntityTypes: [],
      excludedRelationTypes: [],
      projectName: '',
      projectDescription: '',
    });
    form.resetFields();
    onClose();
  };

  // Calculate included items
  const includedEntityTypes = useMemo(() => {
    if (!template) return [];
    return template.entity_types.filter(
      (et) => !customization.excludedEntityTypes.includes(et.id)
    );
  }, [template, customization.excludedEntityTypes]);

  const includedRelationTypes = useMemo(() => {
    if (!template) return [];
    return template.relation_types.filter(
      (rt) => !customization.excludedRelationTypes.includes(rt.id)
    );
  }, [template, customization.excludedRelationTypes]);

  // Handle entity type toggle
  const handleEntityTypeToggle = (entityId: string, checked: boolean) => {
    setCustomization((prev) => ({
      ...prev,
      excludedEntityTypes: checked
        ? prev.excludedEntityTypes.filter((id) => id !== entityId)
        : [...prev.excludedEntityTypes, entityId],
    }));
  };

  // Handle relation type toggle
  const handleRelationTypeToggle = (relationId: string, checked: boolean) => {
    setCustomization((prev) => ({
      ...prev,
      excludedRelationTypes: checked
        ? prev.excludedRelationTypes.filter((id) => id !== relationId)
        : [...prev.excludedRelationTypes, relationId],
    }));
  };

  // Handle form submission
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (!template) return;

      const request: TemplateInstantiateRequest = {
        project_id: values.projectId,
        customizations: {
          excluded_entity_types: customization.excludedEntityTypes,
          excluded_relation_types: customization.excludedRelationTypes,
          project_name: values.projectName,
          project_description: values.projectDescription,
        },
      };

      instantiateMutation.mutate({
        templateId: template.id,
        request,
      });
    } catch {
      // Form validation failed
    }
  };

  // Entity types table columns
  const entityColumns = [
    {
      title: t('ontology:template.include'),
      dataIndex: 'include',
      width: 80,
      render: (_: unknown, record: EntityTypeDefinition) => (
        <Checkbox
          checked={!customization.excludedEntityTypes.includes(record.id)}
          disabled={record.is_core}
          onChange={(e) => handleEntityTypeToggle(record.id, e.target.checked)}
        />
      ),
    },
    {
      title: t('ontology:template.entityName'),
      dataIndex: 'name',
      render: (name: string, record: EntityTypeDefinition) => (
        <Space>
          <Text strong>{name}</Text>
          {record.name_en && (
            <Text type="secondary">({record.name_en})</Text>
          )}
          {record.is_core && (
            <Tag color="blue">{t('ontology:template.core')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('ontology:template.attributes'),
      dataIndex: 'attributes',
      render: (attributes: EntityTypeDefinition['attributes']) => (
        <Text type="secondary">
          {attributes?.length || 0} {t('ontology:template.attributeCount')}
        </Text>
      ),
    },
    {
      title: t('ontology:template.description'),
      dataIndex: 'description',
      ellipsis: true,
      render: (desc: string) => (
        <Text type="secondary" ellipsis={{ tooltip: desc }}>
          {desc || '-'}
        </Text>
      ),
    },
  ];

  // Relation types table columns
  const relationColumns = [
    {
      title: t('ontology:template.include'),
      dataIndex: 'include',
      width: 80,
      render: (_: unknown, record: RelationTypeDefinition) => (
        <Checkbox
          checked={!customization.excludedRelationTypes.includes(record.id)}
          disabled={record.is_core}
          onChange={(e) => handleRelationTypeToggle(record.id, e.target.checked)}
        />
      ),
    },
    {
      title: t('ontology:template.relationName'),
      dataIndex: 'name',
      render: (name: string, record: RelationTypeDefinition) => (
        <Space>
          <Text strong>{name}</Text>
          {record.name_en && (
            <Text type="secondary">({record.name_en})</Text>
          )}
          {record.is_core && (
            <Tag color="blue">{t('ontology:template.core')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('ontology:template.sourceTarget'),
      render: (_: unknown, record: RelationTypeDefinition) => (
        <Text type="secondary">
          {record.source_type} → {record.target_type}
        </Text>
      ),
    },
    {
      title: t('ontology:template.description'),
      dataIndex: 'description',
      ellipsis: true,
      render: (desc: string) => (
        <Text type="secondary" ellipsis={{ tooltip: desc }}>
          {desc || '-'}
        </Text>
      ),
    },
  ];

  // Step content renderers
  const renderTemplateOverview = () => (
    <div>
      <Alert
        message={t('ontology:template.instantiateInfo')}
        description={t('ontology:template.instantiateInfoDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      
      {template && (
        <Card>
          <Row gutter={[24, 16]}>
            <Col span={24}>
              <Space align="start">
                <FileTextOutlined style={{ fontSize: 48, color: '#1890ff' }} />
                <div>
                  <Title level={4} style={{ margin: 0 }}>
                    {template.name}
                  </Title>
                  <Text type="secondary">v{template.version}</Text>
                  <Tag color="gold" style={{ marginLeft: 8 }}>
                    {template.industry}
                  </Tag>
                </div>
              </Space>
            </Col>
            <Col span={24}>
              <Paragraph>{template.description}</Paragraph>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Space>
                  <NodeIndexOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                  <div>
                    <Text type="secondary">{t('ontology:template.entityTypes')}</Text>
                    <Title level={4} style={{ margin: 0 }}>
                      {template.entity_types?.length || 0}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Space>
                  <BranchesOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  <div>
                    <Text type="secondary">{t('ontology:template.relationTypes')}</Text>
                    <Title level={4} style={{ margin: 0 }}>
                      {template.relation_types?.length || 0}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Space>
                  <SafetyCertificateOutlined style={{ fontSize: 24, color: '#faad14' }} />
                  <div>
                    <Text type="secondary">{t('ontology:template.validationRules')}</Text>
                    <Title level={4} style={{ margin: 0 }}>
                      {template.validation_rules?.length || 0}
                    </Title>
                  </div>
                </Space>
              </Card>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );

  const renderCustomization = () => (
    <div>
      <Alert
        message={t('ontology:template.customizeInfo')}
        description={t('ontology:template.customizeInfoDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      
      <Divider orientation="left">
        <Space>
          <NodeIndexOutlined />
          {t('ontology:template.entityTypes')}
        </Space>
      </Divider>
      
      <Table
        dataSource={template?.entity_types || []}
        columns={entityColumns}
        rowKey="id"
        pagination={false}
        size="small"
        scroll={{ y: 200 }}
      />
      
      <Divider orientation="left">
        <Space>
          <BranchesOutlined />
          {t('ontology:template.relationTypes')}
        </Space>
      </Divider>
      
      <Table
        dataSource={template?.relation_types || []}
        columns={relationColumns}
        rowKey="id"
        pagination={false}
        size="small"
        scroll={{ y: 200 }}
      />
    </div>
  );

  const renderProjectConfig = () => (
    <div>
      <Alert
        message={t('ontology:template.projectConfigInfo')}
        description={t('ontology:template.projectConfigInfoDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />
      
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          projectId: `project-${Date.now()}`,
          projectName: `${template?.name || ''} Instance`,
          projectDescription: '',
        }}
      >
        <Form.Item
          name="projectId"
          label={t('ontology:template.projectId')}
          rules={[
            { required: true, message: t('ontology:template.projectIdRequired') },
            { pattern: /^[a-zA-Z0-9-_]+$/, message: t('ontology:template.projectIdInvalid') },
          ]}
        >
          <Input placeholder={t('ontology:template.projectIdPlaceholder')} />
        </Form.Item>
        
        <Form.Item
          name="projectName"
          label={t('ontology:template.projectName')}
          rules={[{ required: true, message: t('ontology:template.projectNameRequired') }]}
        >
          <Input placeholder={t('ontology:template.projectNamePlaceholder')} />
        </Form.Item>
        
        <Form.Item
          name="projectDescription"
          label={t('ontology:template.projectDescription')}
        >
          <TextArea
            rows={4}
            placeholder={t('ontology:template.projectDescriptionPlaceholder')}
          />
        </Form.Item>
      </Form>
    </div>
  );

  const renderConfirmation = () => (
    <div>
      <Alert
        message={t('ontology:template.confirmInfo')}
        description={t('ontology:template.confirmInfoDesc')}
        type="warning"
        showIcon
        style={{ marginBottom: 24 }}
      />
      
      <Card title={t('ontology:template.summary')}>
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Text type="secondary">{t('ontology:template.templateName')}</Text>
            <div>
              <Text strong>{template?.name}</Text>
            </div>
          </Col>
          <Col span={12}>
            <Text type="secondary">{t('ontology:template.version')}</Text>
            <div>
              <Text strong>v{template?.version}</Text>
            </div>
          </Col>
          <Col span={12}>
            <Text type="secondary">{t('ontology:template.includedEntities')}</Text>
            <div>
              <Text strong>{includedEntityTypes.length}</Text>
              <Text type="secondary"> / {template?.entity_types?.length || 0}</Text>
            </div>
          </Col>
          <Col span={12}>
            <Text type="secondary">{t('ontology:template.includedRelations')}</Text>
            <div>
              <Text strong>{includedRelationTypes.length}</Text>
              <Text type="secondary"> / {template?.relation_types?.length || 0}</Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );

  const steps = [
    {
      title: t('ontology:template.stepOverview'),
      icon: <FileTextOutlined />,
      content: renderTemplateOverview(),
    },
    {
      title: t('ontology:template.stepCustomize'),
      icon: <SettingOutlined />,
      content: renderCustomization(),
    },
    {
      title: t('ontology:template.stepConfigure'),
      icon: <NodeIndexOutlined />,
      content: renderProjectConfig(),
    },
    {
      title: t('ontology:template.stepConfirm'),
      icon: <CheckCircleOutlined />,
      content: renderConfirmation(),
    },
  ];

  const handleNext = async () => {
    if (currentStep === 2) {
      // Validate form before proceeding to confirmation
      try {
        await form.validateFields();
        setCurrentStep(currentStep + 1);
      } catch {
        // Form validation failed
      }
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  return (
    <Modal
      title={
        <Space>
          <RocketOutlined />
          {t('ontology:template.instantiateTitle')}
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={900}
      footer={
        <Space>
          <Button onClick={handleClose}>
            {t('common:cancel')}
          </Button>
          {currentStep > 0 && (
            <Button onClick={handlePrev}>
              {t('common:previous')}
            </Button>
          )}
          {currentStep < steps.length - 1 ? (
            <Button type="primary" onClick={handleNext}>
              {t('common:next')}
            </Button>
          ) : (
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={instantiateMutation.isPending}
              icon={<RocketOutlined />}
            >
              {t('ontology:template.instantiate')}
            </Button>
          )}
        </Space>
      }
    >
      <Spin spinning={instantiateMutation.isPending}>
        <Steps
          current={currentStep}
          items={steps.map((step) => ({
            title: step.title,
            icon: step.icon,
          }))}
          style={{ marginBottom: 24 }}
        />
        
        <div style={{ minHeight: 400 }}>
          {steps[currentStep].content}
        </div>
      </Spin>
    </Modal>
  );
};

export default TemplateInstantiationWizard;
