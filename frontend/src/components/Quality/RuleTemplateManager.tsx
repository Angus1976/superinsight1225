import React, { useState } from 'react';
import {
  Card,
  List,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Tooltip,
  message,
  Typography,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  PlayCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

export interface RuleTemplate {
  id: string;
  name: string;
  type: 'format' | 'content' | 'consistency' | 'custom';
  description: string;
  severity: 'warning' | 'error';
  config: Record<string, unknown>;
  isBuiltIn: boolean;
  usageCount: number;
}

interface RuleTemplateManagerProps {
  templates: RuleTemplate[];
  onCreateFromTemplate: (template: RuleTemplate) => void;
  onCreateTemplate: (template: Omit<RuleTemplate, 'id' | 'usageCount'>) => void;
  onUpdateTemplate: (id: string, template: Partial<RuleTemplate>) => void;
  onDeleteTemplate: (id: string) => void;
}

const RuleTemplateManager: React.FC<RuleTemplateManagerProps> = ({
  templates,
  onCreateFromTemplate,
  onCreateTemplate,
  onUpdateTemplate,
  onDeleteTemplate,
}) => {
  const { t } = useTranslation();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<RuleTemplate | null>(null);
  const [form] = Form.useForm();

  const handleCreateTemplate = async (values: Record<string, unknown>) => {
    try {
      const templateData = {
        name: values.name as string,
        type: values.type as RuleTemplate['type'],
        description: values.description as string,
        severity: values.severity as RuleTemplate['severity'],
        config: values.config as Record<string, unknown> || {},
        isBuiltIn: false,
      };

      if (editingTemplate) {
        await onUpdateTemplate(editingTemplate.id, templateData);
        message.success(t('quality.messages.ruleUpdated'));
      } else {
        await onCreateTemplate(templateData);
        message.success(t('quality.messages.ruleCreated'));
      }

      setModalOpen(false);
      setEditingTemplate(null);
      form.resetFields();
    } catch (error) {
      message.error(t('quality.messages.validationFailed'));
    }
  };

  const handleEditTemplate = (template: RuleTemplate) => {
    setEditingTemplate(template);
    form.setFieldsValue({
      name: template.name,
      type: template.type,
      description: template.description,
      severity: template.severity,
      config: JSON.stringify(template.config, null, 2),
    });
    setModalOpen(true);
  };

  const handleDeleteTemplate = (template: RuleTemplate) => {
    Modal.confirm({
      title: t('quality.messages.confirmDelete'),
      content: `${t('quality.rules.template')}: ${template.name}`,
      onOk: () => {
        onDeleteTemplate(template.id);
        message.success(t('quality.messages.ruleDeleted'));
      },
    });
  };

  const handleCopyTemplate = (template: RuleTemplate) => {
    const newTemplate = {
      ...template,
      name: `${template.name} (Copy)`,
      isBuiltIn: false,
    };
    onCreateTemplate(newTemplate);
    message.success(t('quality.messages.ruleCreated'));
  };

  const typeColors = {
    format: 'blue',
    content: 'green',
    consistency: 'orange',
    custom: 'purple',
  };

  const severityColors = {
    warning: 'warning',
    error: 'error',
  } as const;

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>{t('quality.rules.template')}</h3>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalOpen(true)}
        >
          {t('quality.rules.create')} {t('quality.rules.template')}
        </Button>
      </div>

      <List
        grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 3, xxl: 4 }}
        dataSource={templates}
        renderItem={(template) => (
          <List.Item>
            <Card
              size="small"
              title={
                <Space>
                  <Text strong>{template.name}</Text>
                  {template.isBuiltIn && <Tag color="blue">Built-in</Tag>}
                </Space>
              }
              extra={
                <Space>
                  <Tooltip title={t('quality.rules.run')}>
                    <Button
                      type="text"
                      size="small"
                      icon={<PlayCircleOutlined />}
                      onClick={() => onCreateFromTemplate(template)}
                    />
                  </Tooltip>
                  <Tooltip title={t('common.copy')}>
                    <Button
                      type="text"
                      size="small"
                      icon={<CopyOutlined />}
                      onClick={() => handleCopyTemplate(template)}
                    />
                  </Tooltip>
                  {!template.isBuiltIn && (
                    <>
                      <Tooltip title={t('quality.rules.edit')}>
                        <Button
                          type="text"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => handleEditTemplate(template)}
                        />
                      </Tooltip>
                      <Tooltip title={t('quality.rules.delete')}>
                        <Button
                          type="text"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleDeleteTemplate(template)}
                        />
                      </Tooltip>
                    </>
                  )}
                </Space>
              }
              actions={[
                <Space key="info" size="small">
                  <Tag color={typeColors[template.type]}>
                    {t(`quality.rules.types.${template.type}`)}
                  </Tag>
                  <Tag color={severityColors[template.severity]}>
                    {t(`quality.rules.severities.${template.severity}`)}
                  </Tag>
                </Space>,
                <Text key="usage" type="secondary">
                  {t('common.used')}: {template.usageCount}
                </Text>,
              ]}
            >
              <Paragraph
                ellipsis={{ rows: 2, expandable: true }}
                style={{ marginBottom: 0 }}
              >
                {template.description}
              </Paragraph>
            </Card>
          </List.Item>
        )}
      />

      <Modal
        title={editingTemplate ? t('quality.rules.edit') : t('quality.rules.create')}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          setEditingTemplate(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateTemplate}
        >
          <Form.Item
            name="name"
            label={t('quality.rules.name')}
            rules={[{ required: true, message: t('common.required') }]}
          >
            <Input placeholder={t('quality.rules.name')} />
          </Form.Item>

          <Form.Item
            name="type"
            label={t('quality.rules.type')}
            rules={[{ required: true, message: t('common.required') }]}
          >
            <Select placeholder={t('quality.rules.type')}>
              <Select.Option value="format">{t('quality.rules.types.format')}</Select.Option>
              <Select.Option value="content">{t('quality.rules.types.content')}</Select.Option>
              <Select.Option value="consistency">{t('quality.rules.types.consistency')}</Select.Option>
              <Select.Option value="custom">{t('quality.rules.types.custom')}</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="severity"
            label={t('quality.rules.severity')}
            rules={[{ required: true, message: t('common.required') }]}
            initialValue="warning"
          >
            <Select>
              <Select.Option value="warning">{t('quality.rules.severities.warning')}</Select.Option>
              <Select.Option value="error">{t('quality.rules.severities.error')}</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="description"
            label={t('quality.rules.description')}
          >
            <TextArea rows={3} placeholder={t('quality.rules.description')} />
          </Form.Item>

          <Divider />

          <Form.Item
            name="config"
            label={
              <Space>
                <SettingOutlined />
                {t('quality.rules.config')}
              </Space>
            }
            help={t('common.jsonFormat')}
          >
            <TextArea
              rows={6}
              placeholder='{"threshold": 0.8, "pattern": ".*"}'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RuleTemplateManager;