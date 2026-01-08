// Task creation modal component
import { Modal, Form, Input, Select, DatePicker, message, Steps, Card, Upload, Radio, Switch, Divider, Space, Button, Row, Col } from 'antd';
import { useState } from 'react';
import { InboxOutlined, UserOutlined, SettingOutlined, DatabaseOutlined, FileTextOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useCreateTask } from '@/hooks/useTask';
import type { CreateTaskPayload, TaskPriority, AnnotationType } from '@/types';

const { TextArea } = Input;
const { Step } = Steps;
const { Dragger } = Upload;

interface TaskCreateModalProps {
  open: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

interface DataSource {
  id: string;
  name: string;
  type: 'file' | 'api' | 'database';
  description?: string;
}

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar?: string;
}

const priorityOptions: { label: string; value: TaskPriority; color: string }[] = [
  { label: 'Low', value: 'low', color: 'green' },
  { label: 'Medium', value: 'medium', color: 'blue' },
  { label: 'High', value: 'high', color: 'orange' },
  { label: 'Urgent', value: 'urgent', color: 'red' },
];

const annotationTypeOptions: { 
  label: string; 
  value: AnnotationType; 
  description: string;
  config?: Record<string, any>;
}[] = [
  { 
    label: 'Text Classification', 
    value: 'text_classification',
    description: 'Classify text into predefined categories',
    config: { categories: [], multiLabel: false }
  },
  { 
    label: 'Named Entity Recognition (NER)', 
    value: 'ner',
    description: 'Identify and classify named entities in text',
    config: { entities: [], nested: false }
  },
  { 
    label: 'Sentiment Analysis', 
    value: 'sentiment',
    description: 'Analyze emotional tone of text',
    config: { scale: 'binary', includeNeutral: true }
  },
  { 
    label: 'Question & Answer', 
    value: 'qa',
    description: 'Create question-answer pairs from text',
    config: { questionTypes: [], answerFormat: 'text' }
  },
  { 
    label: 'Custom', 
    value: 'custom',
    description: 'Define custom annotation schema',
    config: { schema: null }
  },
];

// Mock data for development
const mockDataSources: DataSource[] = [
  {
    id: 'ds1',
    name: 'Customer Reviews Dataset',
    type: 'file',
    description: 'CSV file containing customer reviews and ratings'
  },
  {
    id: 'ds2',
    name: 'Product Descriptions API',
    type: 'api',
    description: 'REST API endpoint for product descriptions'
  },
  {
    id: 'ds3',
    name: 'Support Tickets Database',
    type: 'database',
    description: 'PostgreSQL database with support ticket data'
  },
];

const mockUsers: User[] = [
  {
    id: 'user1',
    name: 'John Doe',
    email: 'john.doe@company.com',
    role: 'Business Expert',
  },
  {
    id: 'user2',
    name: 'Jane Smith',
    email: 'jane.smith@company.com',
    role: 'Technical Expert',
  },
  {
    id: 'user3',
    name: 'Bob Wilson',
    email: 'bob.wilson@company.com',
    role: 'Annotator',
  },
];

export const TaskCreateModal: React.FC<TaskCreateModalProps> = ({
  open,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const [form] = Form.useForm();
  const createTask = useCreateTask();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedAnnotationType, setSelectedAnnotationType] = useState<AnnotationType>('text_classification');
  const [annotationConfig, setAnnotationConfig] = useState<Record<string, any>>({});

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const payload: CreateTaskPayload = {
        name: values.name,
        description: values.description,
        priority: values.priority,
        annotation_type: values.annotation_type,
        assignee_id: values.assignee_id,
        due_date: values.due_date?.toISOString(),
        tags: values.tags,
        data_source: {
          type: values.data_source_type,
          config: {
            source_id: values.data_source_id,
            file_path: values.file_path,
            api_endpoint: values.api_endpoint,
            database_query: values.database_query,
            ...annotationConfig,
          },
        },
      };

      await createTask.mutateAsync(payload);
      form.resetFields();
      setCurrentStep(0);
      setAnnotationConfig({});
      onSuccess();
    } catch (error) {
      if (error instanceof Error && error.message !== 'Validation failed') {
        message.error(t('tasks.createTaskError'));
      }
    }
  };

  const handleNext = async () => {
    try {
      const currentFields = getCurrentStepFields();
      await form.validateFields(currentFields);
      setCurrentStep(currentStep + 1);
    } catch (error) {
      // Validation failed, stay on current step
    }
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const getCurrentStepFields = () => {
    switch (currentStep) {
      case 0:
        return ['name', 'description', 'priority', 'due_date', 'tags'];
      case 1:
        return ['data_source_type', 'data_source_id'];
      case 2:
        return ['annotation_type'];
      case 3:
        return ['assignee_id'];
      default:
        return [];
    }
  };

  const handleAnnotationTypeChange = (value: AnnotationType) => {
    setSelectedAnnotationType(value);
    const typeConfig = annotationTypeOptions.find(opt => opt.value === value);
    setAnnotationConfig(typeConfig?.config || {});
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Card title={t('tasks.basicInfo')} bordered={false}>
            <Form.Item
              name="name"
              label={t('tasks.taskName')}
              rules={[
                { required: true, message: t('tasks.taskNameRequired') },
                { max: 100, message: t('tasks.taskNameMaxLength') },
              ]}
            >
              <Input placeholder={t('tasks.taskNamePlaceholder')} />
            </Form.Item>

            <Form.Item
              name="description"
              label={t('tasks.description')}
              rules={[{ max: 500, message: t('tasks.descriptionMaxLength') }]}
            >
              <TextArea rows={3} placeholder={t('tasks.descriptionPlaceholder')} />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="priority"
                  label={t('tasks.priority')}
                  rules={[{ required: true, message: t('tasks.priorityRequired') }]}
                >
                  <Select placeholder={t('tasks.priorityPlaceholder')}>
                    {priorityOptions.map(option => (
                      <Select.Option key={option.value} value={option.value}>
                        <Space>
                          <div 
                            style={{ 
                              width: 8, 
                              height: 8, 
                              borderRadius: '50%', 
                              backgroundColor: option.color 
                            }} 
                          />
                          {option.label}
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="due_date" label={t('tasks.dueDate')}>
                  <DatePicker style={{ width: '100%' }} placeholder={t('tasks.dueDatePlaceholder')} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="tags" label={t('tasks.tags')}>
              <Select
                mode="tags"
                placeholder={t('tasks.tagsPlaceholder')}
                tokenSeparators={[',']}
              />
            </Form.Item>
          </Card>
        );

      case 1:
        return (
          <Card title={t('tasks.dataSource')} bordered={false}>
            <Form.Item
              name="data_source_type"
              label={t('tasks.dataSourceType')}
              rules={[{ required: true, message: t('tasks.dataSourceTypeRequired') }]}
            >
              <Radio.Group>
                <Space direction="vertical">
                  <Radio value="file">
                    <Space>
                      <FileTextOutlined />
                      {t('tasks.fileUpload')}
                    </Space>
                  </Radio>
                  <Radio value="api">
                    <Space>
                      <DatabaseOutlined />
                      {t('tasks.apiEndpoint')}
                    </Space>
                  </Radio>
                  <Radio value="database">
                    <Space>
                      <DatabaseOutlined />
                      {t('tasks.database')}
                    </Space>
                  </Radio>
                </Space>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              name="data_source_id"
              label={t('tasks.selectDataSource')}
              rules={[{ required: true, message: t('tasks.dataSourceRequired') }]}
            >
              <Select placeholder={t('tasks.dataSourcePlaceholder')}>
                {mockDataSources.map(source => (
                  <Select.Option key={source.id} value={source.id}>
                    <Space direction="vertical" size={0}>
                      <span>{source.name}</span>
                      <span style={{ fontSize: 12, color: '#999' }}>
                        {source.description}
                      </span>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Divider />

            <Form.Item name="file_upload" label={t('tasks.uploadFile')}>
              <Dragger
                name="file"
                multiple={false}
                accept=".csv,.json,.txt,.xlsx"
                beforeUpload={() => false}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">{t('tasks.uploadText')}</p>
                <p className="ant-upload-hint">{t('tasks.uploadHint')}</p>
              </Dragger>
            </Form.Item>
          </Card>
        );

      case 2:
        return (
          <Card title={t('tasks.annotationConfig')} bordered={false}>
            <Form.Item
              name="annotation_type"
              label={t('tasks.annotationType')}
              rules={[{ required: true, message: t('tasks.annotationTypeRequired') }]}
            >
              <Radio.Group 
                onChange={(e) => handleAnnotationTypeChange(e.target.value)}
                style={{ width: '100%' }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  {annotationTypeOptions.map(option => (
                    <Radio key={option.value} value={option.value} style={{ width: '100%' }}>
                      <Space direction="vertical" size={0}>
                        <span style={{ fontWeight: 500 }}>{option.label}</span>
                        <span style={{ fontSize: 12, color: '#666' }}>
                          {option.description}
                        </span>
                      </Space>
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            </Form.Item>

            {selectedAnnotationType === 'text_classification' && (
              <Card size="small" title={t('tasks.classificationConfig')}>
                <Form.Item name="categories" label={t('tasks.categories')}>
                  <Select
                    mode="tags"
                    placeholder={t('tasks.categoriesPlaceholder')}
                    tokenSeparators={[',']}
                  />
                </Form.Item>
                <Form.Item name="multi_label" valuePropName="checked">
                  <Switch /> {t('tasks.multiLabel')}
                </Form.Item>
              </Card>
            )}

            {selectedAnnotationType === 'ner' && (
              <Card size="small" title={t('tasks.nerConfig')}>
                <Form.Item name="entities" label={t('tasks.entityTypes')}>
                  <Select
                    mode="tags"
                    placeholder={t('tasks.entityTypesPlaceholder')}
                    tokenSeparators={[',']}
                  />
                </Form.Item>
                <Form.Item name="nested_entities" valuePropName="checked">
                  <Switch /> {t('tasks.nestedEntities')}
                </Form.Item>
              </Card>
            )}

            {selectedAnnotationType === 'sentiment' && (
              <Card size="small" title={t('tasks.sentimentConfig')}>
                <Form.Item name="sentiment_scale" label={t('tasks.sentimentScale')}>
                  <Radio.Group>
                    <Radio value="binary">{t('tasks.binaryScale')}</Radio>
                    <Radio value="ternary">{t('tasks.ternaryScale')}</Radio>
                    <Radio value="five_point">{t('tasks.fivePointScale')}</Radio>
                  </Radio.Group>
                </Form.Item>
              </Card>
            )}
          </Card>
        );

      case 3:
        return (
          <Card title={t('tasks.assignmentConfig')} bordered={false}>
            <Form.Item
              name="assignee_id"
              label={t('tasks.assignTo')}
              rules={[{ required: true, message: t('tasks.assigneeRequired') }]}
            >
              <Select placeholder={t('tasks.assigneePlaceholder')}>
                {mockUsers.map(user => (
                  <Select.Option key={user.id} value={user.id}>
                    <Space>
                      <UserOutlined />
                      <Space direction="vertical" size={0}>
                        <span>{user.name}</span>
                        <span style={{ fontSize: 12, color: '#999' }}>
                          {user.role} • {user.email}
                        </span>
                      </Space>
                    </Space>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Divider />

            <Form.Item name="auto_assignment" valuePropName="checked">
              <Switch /> {t('tasks.autoAssignment')}
            </Form.Item>

            <Form.Item name="notification_enabled" valuePropName="checked">
              <Switch /> {t('tasks.notifyAssignee')}
            </Form.Item>

            <Form.Item name="deadline_reminder" valuePropName="checked">
              <Switch /> {t('tasks.deadlineReminder')}
            </Form.Item>
          </Card>
        );

      default:
        return null;
    }
  };

  const steps = [
    {
      title: t('tasks.basicInfo'),
      icon: <SettingOutlined />,
    },
    {
      title: t('tasks.dataSource'),
      icon: <DatabaseOutlined />,
    },
    {
      title: t('tasks.annotationConfig'),
      icon: <FileTextOutlined />,
    },
    {
      title: t('tasks.assignment'),
      icon: <UserOutlined />,
    },
  ];

  return (
    <Modal
      title={t('tasks.createNewTask')}
      open={open}
      onCancel={onCancel}
      width={800}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={onCancel}>
          {t('common.cancel')}
        </Button>,
        currentStep > 0 && (
          <Button key="prev" onClick={handlePrev}>
            {t('tasks.previous')}
          </Button>
        ),
        currentStep < steps.length - 1 ? (
          <Button key="next" type="primary" onClick={handleNext}>
            {t('tasks.next')}
          </Button>
        ) : (
          <Button
            key="submit"
            type="primary"
            loading={createTask.isPending}
            onClick={handleSubmit}
          >
            {t('tasks.createTask')}
          </Button>
        ),
      ]}
    >
      <Steps current={currentStep} style={{ marginBottom: 24 }}>
        {steps.map((step, index) => (
          <Step key={index} title={step.title} icon={step.icon} />
        ))}
      </Steps>

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          priority: 'medium',
          annotation_type: 'text_classification',
          data_source_type: 'file',
          auto_assignment: false,
          notification_enabled: true,
          deadline_reminder: true,
        }}
      >
        {renderStepContent()}
      </Form>
    </Modal>
  );
};
