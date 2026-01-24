/**
 * Template Customization Editor Component (模板定制编辑器)
 * 
 * Visual editor for customizing ontology templates.
 * Allows adding/removing entity types and relations while validating against template constraints.
 * Shows lineage to parent template.
 * 
 * Requirements: Task 21.3 - Template Management
 * Validates: Requirements 12.1, 12.2, 12.3
 */

import React, { useState, useCallback } from 'react';
import {
  Modal,
  Card,
  Form,
  Input,
  Select,
  Table,
  Tag,
  Typography,
  Space,
  Button,
  Tabs,
  Alert,
  Divider,
  Row,
  Col,
  Popconfirm,
  message,
  Tooltip,
  Tree,
  Empty,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  NodeIndexOutlined,
  BranchesOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  HistoryOutlined,
  LockOutlined,
  UnlockOutlined,
  ForkOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import {
  ontologyTemplateApi,
  OntologyTemplate,
  EntityTypeDefinition,
  RelationTypeDefinition,
  AttributeDefinition,
  TemplateCustomizeRequest,
} from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface TemplateCustomizationEditorProps {
  template: OntologyTemplate | null;
  visible: boolean;
  onClose: () => void;
  onSuccess?: (customizedTemplate: OntologyTemplate) => void;
}

interface EntityFormValues {
  id: string;
  name: string;
  name_en?: string;
  description?: string;
  attributes: AttributeDefinition[];
}

interface RelationFormValues {
  id: string;
  name: string;
  name_en?: string;
  description?: string;
  source_type: string;
  target_type: string;
}

const TemplateCustomizationEditor: React.FC<TemplateCustomizationEditorProps> = ({
  template,
  visible,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const [activeTab, setActiveTab] = useState('entities');
  const [entityForm] = Form.useForm<EntityFormValues>();
  const [relationForm] = Form.useForm<RelationFormValues>();
  
  // Track customizations
  const [addedEntityTypes, setAddedEntityTypes] = useState<EntityTypeDefinition[]>([]);
  const [removedEntityTypes, setRemovedEntityTypes] = useState<string[]>([]);
  const [addedRelationTypes, setAddedRelationTypes] = useState<RelationTypeDefinition[]>([]);
  const [removedRelationTypes, setRemovedRelationTypes] = useState<string[]>([]);
  
  // Modal states
  const [entityModalVisible, setEntityModalVisible] = useState(false);
  const [relationModalVisible, setRelationModalVisible] = useState(false);
  const [editingEntity, setEditingEntity] = useState<EntityTypeDefinition | null>(null);
  const [editingRelation, setEditingRelation] = useState<RelationTypeDefinition | null>(null);

  // Customize mutation
  const customizeMutation = useMutation({
    mutationFn: (data: { templateId: string; request: TemplateCustomizeRequest }) =>
      ontologyTemplateApi.customizeTemplate(data.templateId, data.request),
    onSuccess: (result) => {
      message.success(t('ontology:template.customizeSuccess'));
      onSuccess?.(result);
      handleClose();
    },
    onError: () => {
      message.error(t('ontology:template.customizeFailed'));
    },
  });

  // Reset state when modal closes
  const handleClose = () => {
    setAddedEntityTypes([]);
    setRemovedEntityTypes([]);
    setAddedRelationTypes([]);
    setRemovedRelationTypes([]);
    setActiveTab('entities');
    entityForm.resetFields();
    relationForm.resetFields();
    onClose();
  };

  // Get all entity types (original + added - removed)
  const getAllEntityTypes = useCallback((): EntityTypeDefinition[] => {
    if (!template) return addedEntityTypes;
    
    const originalEntities = template.entity_types.filter(
      (et) => !removedEntityTypes.includes(et.id)
    );
    return [...originalEntities, ...addedEntityTypes];
  }, [template, addedEntityTypes, removedEntityTypes]);

  // Get all relation types (original + added - removed)
  const getAllRelationTypes = useCallback((): RelationTypeDefinition[] => {
    if (!template) return addedRelationTypes;
    
    const originalRelations = template.relation_types.filter(
      (rt) => !removedRelationTypes.includes(rt.id)
    );
    return [...originalRelations, ...addedRelationTypes];
  }, [template, addedRelationTypes, removedRelationTypes]);

  // Handle add entity
  const handleAddEntity = () => {
    setEditingEntity(null);
    entityForm.resetFields();
    entityForm.setFieldsValue({
      id: `entity-${Date.now()}`,
      attributes: [],
    });
    setEntityModalVisible(true);
  };

  // Handle edit entity (only for added entities)
  const handleEditEntity = (entity: EntityTypeDefinition) => {
    setEditingEntity(entity);
    entityForm.setFieldsValue(entity);
    setEntityModalVisible(true);
  };

  // Handle remove entity
  const handleRemoveEntity = (entityId: string) => {
    // Check if it's an added entity
    const addedIndex = addedEntityTypes.findIndex((et) => et.id === entityId);
    if (addedIndex >= 0) {
      setAddedEntityTypes((prev) => prev.filter((et) => et.id !== entityId));
    } else {
      // It's an original entity, mark as removed
      setRemovedEntityTypes((prev) => [...prev, entityId]);
    }
    message.success(t('ontology:template.entityRemoved'));
  };

  // Handle entity form submit
  const handleEntitySubmit = async () => {
    try {
      const values = await entityForm.validateFields();
      const newEntity: EntityTypeDefinition = {
        ...values,
        is_core: false,
      };

      if (editingEntity) {
        // Update existing added entity
        setAddedEntityTypes((prev) =>
          prev.map((et) => (et.id === editingEntity.id ? newEntity : et))
        );
      } else {
        // Add new entity
        setAddedEntityTypes((prev) => [...prev, newEntity]);
      }

      setEntityModalVisible(false);
      entityForm.resetFields();
      message.success(
        editingEntity
          ? t('ontology:template.entityUpdated')
          : t('ontology:template.entityAdded')
      );
    } catch {
      // Form validation failed
    }
  };

  // Handle add relation
  const handleAddRelation = () => {
    setEditingRelation(null);
    relationForm.resetFields();
    relationForm.setFieldsValue({
      id: `relation-${Date.now()}`,
    });
    setRelationModalVisible(true);
  };

  // Handle edit relation (only for added relations)
  const handleEditRelation = (relation: RelationTypeDefinition) => {
    setEditingRelation(relation);
    relationForm.setFieldsValue(relation);
    setRelationModalVisible(true);
  };

  // Handle remove relation
  const handleRemoveRelation = (relationId: string) => {
    const addedIndex = addedRelationTypes.findIndex((rt) => rt.id === relationId);
    if (addedIndex >= 0) {
      setAddedRelationTypes((prev) => prev.filter((rt) => rt.id !== relationId));
    } else {
      setRemovedRelationTypes((prev) => [...prev, relationId]);
    }
    message.success(t('ontology:template.relationRemoved'));
  };

  // Handle relation form submit
  const handleRelationSubmit = async () => {
    try {
      const values = await relationForm.validateFields();
      const newRelation: RelationTypeDefinition = {
        ...values,
        is_core: false,
      };

      if (editingRelation) {
        setAddedRelationTypes((prev) =>
          prev.map((rt) => (rt.id === editingRelation.id ? newRelation : rt))
        );
      } else {
        setAddedRelationTypes((prev) => [...prev, newRelation]);
      }

      setRelationModalVisible(false);
      relationForm.resetFields();
      message.success(
        editingRelation
          ? t('ontology:template.relationUpdated')
          : t('ontology:template.relationAdded')
      );
    } catch {
      // Form validation failed
    }
  };

  // Handle save customization
  const handleSave = () => {
    if (!template) return;

    const request: TemplateCustomizeRequest = {
      add_entity_types: addedEntityTypes,
      remove_entity_types: removedEntityTypes,
      add_relation_types: addedRelationTypes,
      remove_relation_types: removedRelationTypes,
    };

    customizeMutation.mutate({
      templateId: template.id,
      request,
    });
  };

  // Check if entity is removable (not core)
  const isEntityRemovable = (entity: EntityTypeDefinition): boolean => {
    return !entity.is_core;
  };

  // Check if entity is editable (only added entities)
  const isEntityEditable = (entity: EntityTypeDefinition): boolean => {
    return addedEntityTypes.some((et) => et.id === entity.id);
  };

  // Build lineage tree data
  const buildLineageTree = (): DataNode[] => {
    if (!template) return [];

    const nodes: DataNode[] = [];
    
    // Add parent templates
    if (template.lineage && template.lineage.length > 0) {
      template.lineage.forEach((parentId, index) => {
        nodes.push({
          key: parentId,
          title: (
            <Space>
              <ForkOutlined />
              <Text type="secondary">
                {t('ontology:template.parentTemplate')} {index + 1}
              </Text>
              <Text code>{parentId}</Text>
            </Space>
          ),
        });
      });
    }

    // Add current template
    nodes.push({
      key: template.id,
      title: (
        <Space>
          <NodeIndexOutlined style={{ color: '#1890ff' }} />
          <Text strong>{template.name}</Text>
          <Tag color="blue">{t('ontology:template.current')}</Tag>
        </Space>
      ),
    });

    return nodes;
  };

  // Entity types table columns
  const entityColumns = [
    {
      title: t('ontology:template.entityName'),
      dataIndex: 'name',
      render: (name: string, record: EntityTypeDefinition) => (
        <Space>
          <Text strong>{name}</Text>
          {record.name_en && <Text type="secondary">({record.name_en})</Text>}
          {record.is_core && (
            <Tooltip title={t('ontology:template.coreCannotRemove')}>
              <Tag color="blue" icon={<LockOutlined />}>
                {t('ontology:template.core')}
              </Tag>
            </Tooltip>
          )}
          {addedEntityTypes.some((et) => et.id === record.id) && (
            <Tag color="green">{t('ontology:template.new')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('ontology:template.attributes'),
      dataIndex: 'attributes',
      render: (attributes: AttributeDefinition[]) => (
        <Text type="secondary">
          {attributes?.length || 0} {t('ontology:template.attributeCount')}
        </Text>
      ),
    },
    {
      title: t('ontology:template.description'),
      dataIndex: 'description',
      ellipsis: true,
    },
    {
      title: t('common:actions'),
      width: 120,
      render: (_: unknown, record: EntityTypeDefinition) => (
        <Space>
          {isEntityEditable(record) && (
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditEntity(record)}
            />
          )}
          {isEntityRemovable(record) && (
            <Popconfirm
              title={t('ontology:template.confirmRemoveEntity')}
              onConfirm={() => handleRemoveEntity(record.id)}
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // Relation types table columns
  const relationColumns = [
    {
      title: t('ontology:template.relationName'),
      dataIndex: 'name',
      render: (name: string, record: RelationTypeDefinition) => (
        <Space>
          <Text strong>{name}</Text>
          {record.name_en && <Text type="secondary">({record.name_en})</Text>}
          {record.is_core && (
            <Tooltip title={t('ontology:template.coreCannotRemove')}>
              <Tag color="blue" icon={<LockOutlined />}>
                {t('ontology:template.core')}
              </Tag>
            </Tooltip>
          )}
          {addedRelationTypes.some((rt) => rt.id === record.id) && (
            <Tag color="green">{t('ontology:template.new')}</Tag>
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
    },
    {
      title: t('common:actions'),
      width: 120,
      render: (_: unknown, record: RelationTypeDefinition) => (
        <Space>
          {addedRelationTypes.some((rt) => rt.id === record.id) && (
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditRelation(record)}
            />
          )}
          {!record.is_core && (
            <Popconfirm
              title={t('ontology:template.confirmRemoveRelation')}
              onConfirm={() => handleRemoveRelation(record.id)}
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // Entity type options for relation form
  const entityTypeOptions = getAllEntityTypes().map((et) => ({
    value: et.id,
    label: et.name,
  }));

  const hasChanges =
    addedEntityTypes.length > 0 ||
    removedEntityTypes.length > 0 ||
    addedRelationTypes.length > 0 ||
    removedRelationTypes.length > 0;

  return (
    <>
      <Modal
        title={
          <Space>
            <EditOutlined />
            {t('ontology:template.customizeTitle')}
          </Space>
        }
        open={visible}
        onCancel={handleClose}
        width={1000}
        footer={
          <Space>
            <Button onClick={handleClose}>{t('common:cancel')}</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={customizeMutation.isPending}
              disabled={!hasChanges}
            >
              {t('ontology:template.saveCustomization')}
            </Button>
          </Space>
        }
      >
        {/* Template Info */}
        {template && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Space>
                  <NodeIndexOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  <div>
                    <Text strong>{template.name}</Text>
                    <br />
                    <Text type="secondary">v{template.version}</Text>
                  </div>
                  <Tag color="gold">{template.industry}</Tag>
                </Space>
              </Col>
              <Col>
                <Space split={<Divider type="vertical" />}>
                  <Text type="secondary">
                    {t('ontology:template.added')}: {addedEntityTypes.length + addedRelationTypes.length}
                  </Text>
                  <Text type="secondary">
                    {t('ontology:template.removed')}: {removedEntityTypes.length + removedRelationTypes.length}
                  </Text>
                </Space>
              </Col>
            </Row>
          </Card>
        )}

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'entities',
              label: (
                <Space>
                  <NodeIndexOutlined />
                  {t('ontology:template.entityTypes')}
                  <Tag>{getAllEntityTypes().length}</Tag>
                </Space>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={handleAddEntity}
                    >
                      {t('ontology:template.addEntityType')}
                    </Button>
                  </div>
                  <Table
                    dataSource={getAllEntityTypes()}
                    columns={entityColumns}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    scroll={{ y: 300 }}
                  />
                </div>
              ),
            },
            {
              key: 'relations',
              label: (
                <Space>
                  <BranchesOutlined />
                  {t('ontology:template.relationTypes')}
                  <Tag>{getAllRelationTypes().length}</Tag>
                </Space>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={handleAddRelation}
                    >
                      {t('ontology:template.addRelationType')}
                    </Button>
                  </div>
                  <Table
                    dataSource={getAllRelationTypes()}
                    columns={relationColumns}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    scroll={{ y: 300 }}
                  />
                </div>
              ),
            },
            {
              key: 'lineage',
              label: (
                <Space>
                  <HistoryOutlined />
                  {t('ontology:template.lineage')}
                </Space>
              ),
              children: (
                <div>
                  <Alert
                    message={t('ontology:template.lineageInfo')}
                    description={t('ontology:template.lineageInfoDesc')}
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  {template?.lineage && template.lineage.length > 0 ? (
                    <Tree
                      showLine
                      defaultExpandAll
                      treeData={buildLineageTree()}
                    />
                  ) : (
                    <Empty
                      description={t('ontology:template.noLineage')}
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                  )}
                </div>
              ),
            },
          ]}
        />
      </Modal>

      {/* Add/Edit Entity Modal */}
      <Modal
        title={
          editingEntity
            ? t('ontology:template.editEntityType')
            : t('ontology:template.addEntityType')
        }
        open={entityModalVisible}
        onCancel={() => setEntityModalVisible(false)}
        onOk={handleEntitySubmit}
        width={600}
      >
        <Form form={entityForm} layout="vertical">
          <Form.Item
            name="id"
            label={t('ontology:template.entityId')}
            rules={[{ required: true }]}
          >
            <Input disabled={!!editingEntity} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={t('ontology:template.entityNameZh')}
                rules={[{ required: true, message: t('ontology:template.entityNameRequired') }]}
              >
                <Input placeholder={t('ontology:template.entityNamePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name_en"
                label={t('ontology:template.entityNameEn')}
              >
                <Input placeholder={t('ontology:template.entityNameEnPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="description"
            label={t('ontology:template.description')}
          >
            <TextArea rows={3} placeholder={t('ontology:template.descriptionPlaceholder')} />
          </Form.Item>
          <Form.Item
            name="attributes"
            label={t('ontology:template.attributes')}
          >
            <Form.List name="attributes">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Row key={key} gutter={8} style={{ marginBottom: 8 }}>
                      <Col span={8}>
                        <Form.Item
                          {...restField}
                          name={[name, 'name']}
                          rules={[{ required: true }]}
                          noStyle
                        >
                          <Input placeholder={t('ontology:template.attributeName')} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item
                          {...restField}
                          name={[name, 'type']}
                          rules={[{ required: true }]}
                          noStyle
                        >
                          <Select
                            placeholder={t('ontology:template.attributeType')}
                            options={[
                              { value: 'string', label: 'String' },
                              { value: 'number', label: 'Number' },
                              { value: 'boolean', label: 'Boolean' },
                              { value: 'date', label: 'Date' },
                              { value: 'array', label: 'Array' },
                            ]}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={6}>
                        <Form.Item
                          {...restField}
                          name={[name, 'required']}
                          valuePropName="checked"
                          noStyle
                        >
                          <Select
                            placeholder={t('ontology:template.required')}
                            options={[
                              { value: true, label: t('common:yes') },
                              { value: false, label: t('common:no') },
                            ]}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={2}>
                        <Button
                          type="text"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(name)}
                        />
                      </Col>
                    </Row>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => add()}
                    block
                    icon={<PlusOutlined />}
                  >
                    {t('ontology:template.addAttribute')}
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Modal>

      {/* Add/Edit Relation Modal */}
      <Modal
        title={
          editingRelation
            ? t('ontology:template.editRelationType')
            : t('ontology:template.addRelationType')
        }
        open={relationModalVisible}
        onCancel={() => setRelationModalVisible(false)}
        onOk={handleRelationSubmit}
        width={600}
      >
        <Form form={relationForm} layout="vertical">
          <Form.Item
            name="id"
            label={t('ontology:template.relationId')}
            rules={[{ required: true }]}
          >
            <Input disabled={!!editingRelation} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={t('ontology:template.relationNameZh')}
                rules={[{ required: true, message: t('ontology:template.relationNameRequired') }]}
              >
                <Input placeholder={t('ontology:template.relationNamePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name_en"
                label={t('ontology:template.relationNameEn')}
              >
                <Input placeholder={t('ontology:template.relationNameEnPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="source_type"
                label={t('ontology:template.sourceType')}
                rules={[{ required: true, message: t('ontology:template.sourceTypeRequired') }]}
              >
                <Select
                  placeholder={t('ontology:template.selectSourceType')}
                  options={entityTypeOptions}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="target_type"
                label={t('ontology:template.targetType')}
                rules={[{ required: true, message: t('ontology:template.targetTypeRequired') }]}
              >
                <Select
                  placeholder={t('ontology:template.selectTargetType')}
                  options={entityTypeOptions}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="description"
            label={t('ontology:template.description')}
          >
            <TextArea rows={3} placeholder={t('ontology:template.descriptionPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default TemplateCustomizationEditor;
