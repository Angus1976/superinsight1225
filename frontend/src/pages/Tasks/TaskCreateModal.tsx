// Task creation modal component
import { Modal, Form, Input, Select, DatePicker, App, Steps, Card, Upload, Radio, Switch, Divider, Space, Button, Row, Col } from 'antd';
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
  { label: 'priorityLow', value: 'low', color: 'green' },
  { label: 'priorityMedium', value: 'medium', color: 'blue' },
  { label: 'priorityHigh', value: 'high', color: 'orange' },
  { label: 'priorityUrgent', value: 'urgent', color: 'red' },
];

const annotationTypeOptions: { 
  label: string; 
  value: AnnotationType; 
  description: string;
  config?: Record<string, any>;
}[] = [
  { 
    label: 'textClassification', 
    value: 'text_classification',
    description: 'classifyTextCategories',
    config: { categories: [], multiLabel: false }
  },
  { 
    label: 'namedEntityRecognition', 
    value: 'ner',
    description: 'identifyEntities',
    config: { entities: [], nested: false }
  },
  { 
    label: 'sentimentAnalysis', 
    value: 'sentiment',
    description: 'analyzeEmotionalTone',
    config: { scale: 'binary', includeNeutral: true }
  },
  { 
    label: 'questionAnswer', 
    value: 'qa',
    description: 'createQAPairs',
    config: { questionTypes: [], answerFormat: 'text' }
  },
  { 
    label: 'custom', 
    value: 'custom',
    description: 'defineCustomSchema',
    config: { schema: null }
  },
];

// Mock data for development - TODO: Replace with real API calls
// These should be fetched from backend APIs:
// - Data sources: GET /api/data-sources
// - Users: GET /api/users (filtered by role/permissions)
const mockDataSources: DataSource[] = [
  {
    id: 'a0000001-0000-4000-8000-000000000001',
    name: 'Test Customer Reviews Dataset',
    type: 'file',
    description: 'CSV file containing customer reviews and ratings for testing'
  },
  {
    id: 'a0000002-0000-4000-8000-000000000002',
    name: 'Test Product Descriptions API',
    type: 'api',
    description: 'REST API endpoint for product descriptions (mock)'
  },
  {
    id: 'a0000003-0000-4000-8000-000000000003',
    name: 'Test Support Tickets Database',
    type: 'database',
    description: 'PostgreSQL database with support ticket data (test)'
  },
  {
    id: 'a0000004-0000-4000-8000-000000000004',
    name: 'Test E-commerce Orders API',
    type: 'api',
    description: 'GraphQL API for e-commerce order data (test)'
  },
  {
    id: 'a0000005-0000-4000-8000-000000000005',
    name: 'Test Social Media Comments',
    type: 'file',
    description: 'JSON file with social media comments for sentiment analysis'
  },
  {
    id: 'a0000006-0000-4000-8000-000000000006',
    name: 'Test Medical Records Database',
    type: 'database',
    description: 'MySQL database with anonymized medical records (test)'
  },
  {
    id: 'a0000007-0000-4000-8000-000000000007',
    name: 'Test News Articles Feed',
    type: 'api',
    description: 'RSS/XML feed with news articles for classification'
  },
  {
    id: 'a0000008-0000-4000-8000-000000000008',
    name: 'Test Financial Transactions',
    type: 'file',
    description: 'S3 bucket with financial transaction data (CSV)'
  },
];

const mockUsers: User[] = [
  {
    id: 'b0000001-0000-4000-8000-000000000001',
    name: 'John Doe',
    email: 'john.doe@company.com',
    role: 'Business Expert',
  },
  {
    id: 'b0000002-0000-4000-8000-000000000002',
    name: 'Jane Smith',
    email: 'jane.smith@company.com',
    role: 'Technical Expert',
  },
  {
    id: 'b0000003-0000-4000-8000-000000000003',
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
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createTask = useCreateTask();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedAnnotationType, setSelectedAnnotationType] = useState<AnnotationType>('text_classification');
  const [annotationConfig, setAnnotationConfig] = useState<Record<string, any>>({});

  const handleSubmit = async () => {
    try {
      console.log('[TaskCreateModal] ========== SUBMIT START ==========');
      console.log('[TaskCreateModal] Current step:', currentStep);
      
      // Get ALL form values WITHOUT validation
      const rawValues = form.getFieldsValue(true);
      console.log('[TaskCreateModal] RAW form values:', JSON.stringify(rawValues, null, 2));
      
      // CRITICAL FIX: Validate ALL fields, not just visible ones
      // By default, validateFields() only validates visible fields
      // We need to explicitly pass field names to validate hidden fields too
      const allFieldNames = [
        'name', 'description', 'priority', 'due_date', 'tags',
        'data_source_type', 'data_source_id', 'file_path', 'api_endpoint', 'database_query',
        'annotation_type', 'categories', 'multi_label', 'entities', 'nested_entities', 'sentiment_scale',
        'assignee_id', 'auto_assignment', 'notification_enabled', 'deadline_reminder'
      ];
      
      const values = await form.validateFields(allFieldNames);
      console.log('[TaskCreateModal] Validated values:', JSON.stringify(values, null, 2));
      
      // Validate required fields
      if (!values.name) {
        console.error('[TaskCreateModal] Name is required');
        message.error(t('taskNameRequired'));
        setCurrentStep(0);
        return;
      }
      
      // Build data_source - only include if user selected a data source
      let dataSource = undefined;
      if (values.data_source_id) {
        dataSource = {
          type: values.data_source_type || 'file',
          config: {
            source_id: values.data_source_id,
          },
        };
      }
      
      const payload: CreateTaskPayload = {
        name: values.name,
        description: values.description,
        priority: values.priority || 'medium',
        annotation_type: values.annotation_type || 'text_classification',
        assignee_id: values.assignee_id,
        due_date: values.due_date?.toISOString(),
        tags: values.tags,
        data_source: dataSource,
      };
      
      console.log('[TaskCreateModal] Final payload:', JSON.stringify(payload, null, 2));

      await createTask.mutateAsync(payload);
      
      console.log('[TaskCreateModal] ✅ Task created successfully!');
      message.success(t('createTaskSuccess'));
      form.resetFields();
      setCurrentStep(0);
      setAnnotationConfig({});
      onSuccess();
    } catch (error) {
      console.error('[TaskCreateModal] ❌ Error:', error);
      if (error instanceof Error && error.message !== 'Validation failed') {
        message.error(t('createTaskError'));
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
    return (
      <>
        {/* Step 0: Basic Info */}
        <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
          <Card title={t('basicInfo')} bordered={false}>
            <Form.Item
              name="name"
              label={t('taskName')}
              rules={[
                { required: true, message: t('taskNameRequired') },
                { max: 100, message: t('taskNameMaxLength') },
              ]}
            >
              <Input placeholder={t('taskNamePlaceholder')} />
            </Form.Item>

            <Form.Item
              name="description"
              label={t('description')}
              rules={[{ max: 500, message: t('descriptionMaxLength') }]}
            >
              <TextArea rows={3} placeholder={t('descriptionPlaceholder')} />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="priority"
                  label={t('priority')}
                  rules={[{ required: true, message: t('priorityRequired') }]}
                >
                  <Select placeholder={t('priorityPlaceholder')}>
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
                          {t(option.label)}
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="due_date" label={t('dueDate')}>
                  <DatePicker style={{ width: '100%' }} placeholder={t('dueDatePlaceholder')} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="tags" label={t('tagsLabel')}>
              <Select
                mode="tags"
                placeholder={t('tagsPlaceholder')}
                tokenSeparators={[',']}
              />
            </Form.Item>
          </Card>
        </div>

        {/* Step 1: Data Source */}
        <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
          <Card title={t('dataSource')} bordered={false}>
            <Form.Item
              name="data_source_type"
              label={t('dataSourceType')}
            >
              <Radio.Group>
                <Space direction="vertical">
                  <Radio value="file">
                    <Space>
                      <FileTextOutlined />
                      {t('fileUpload')}
                    </Space>
                  </Radio>
                  <Radio value="api">
                    <Space>
                      <DatabaseOutlined />
                      {t('apiEndpoint')}
                    </Space>
                  </Radio>
                  <Radio value="database">
                    <Space>
                      <DatabaseOutlined />
                      {t('database')}
                    </Space>
                  </Radio>
                </Space>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              name="data_source_id"
              label={t('selectDataSource')}
            >
              <Select placeholder={t('dataSourcePlaceholder')}>
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

            <Form.Item name="file_upload" label={t('uploadFile')}>
              <Dragger
                name="file"
                multiple={false}
                accept=".csv,.json,.txt,.xlsx"
                beforeUpload={() => false}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">{t('uploadText')}</p>
                <p className="ant-upload-hint">{t('uploadHint')}</p>
              </Dragger>
            </Form.Item>
          </Card>
        </div>

        {/* Step 2: Annotation Config */}
        <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
          <Card title={t('annotationConfig')} bordered={false}>
            <Form.Item
              name="annotation_type"
              label={t('annotationType')}
              rules={[{ required: true, message: t('annotationTypeRequired') }]}
            >
              <Radio.Group 
                onChange={(e) => handleAnnotationTypeChange(e.target.value)}
                style={{ width: '100%' }}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  {annotationTypeOptions.map(option => (
                    <Radio key={option.value} value={option.value} style={{ width: '100%' }}>
                      <Space direction="vertical" size={0}>
                        <span style={{ fontWeight: 500 }}>{t(option.label)}</span>
                        <span style={{ fontSize: 12, color: '#666' }}>
                          {t(option.description)}
                        </span>
                      </Space>
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            </Form.Item>

            {selectedAnnotationType === 'text_classification' && (
              <Card size="small" title={t('classificationConfig')}>
                <Form.Item name="categories" label={t('categories')}>
                  <Select
                    mode="tags"
                    placeholder={t('categoriesPlaceholder')}
                    tokenSeparators={[',']}
                  />
                </Form.Item>
                <Form.Item name="multi_label" label={t('multiLabel')} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Card>
            )}

            {selectedAnnotationType === 'ner' && (
              <Card size="small" title={t('nerConfig')}>
                <Form.Item name="entities" label={t('entityTypes')}>
                  <Select
                    mode="tags"
                    placeholder={t('entityTypesPlaceholder')}
                    tokenSeparators={[',']}
                  />
                </Form.Item>
                <Form.Item name="nested_entities" label={t('nestedEntities')} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Card>
            )}

            {selectedAnnotationType === 'sentiment' && (
              <Card size="small" title={t('sentimentConfig')}>
                <Form.Item name="sentiment_scale" label={t('sentimentScale')}>
                  <Radio.Group>
                    <Radio value="binary">{t('binaryScale')}</Radio>
                    <Radio value="ternary">{t('ternaryScale')}</Radio>
                    <Radio value="five_point">{t('fivePointScale')}</Radio>
                  </Radio.Group>
                </Form.Item>
              </Card>
            )}
          </Card>
        </div>

        {/* Step 3: Assignment Config */}
        <div style={{ display: currentStep === 3 ? 'block' : 'none' }}>
          <Card title={t('assignmentConfig')} bordered={false}>
            <Form.Item
              name="assignee_id"
              label={t('assignTo')}
            >
              <Select placeholder={t('assigneePlaceholder')}>
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

            <Form.Item name="auto_assignment" label={t('autoAssignment')} valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item name="notification_enabled" label={t('notifyAssignee')} valuePropName="checked">
              <Switch />
            </Form.Item>

            <Form.Item name="deadline_reminder" label={t('deadlineReminder')} valuePropName="checked">
              <Switch />
            </Form.Item>
          </Card>
        </div>
      </>
    );
  };

  const steps = [
    {
      title: t('basicInfo'),
      icon: <SettingOutlined />,
    },
    {
      title: t('dataSource'),
      icon: <DatabaseOutlined />,
    },
    {
      title: t('annotationConfig'),
      icon: <FileTextOutlined />,
    },
    {
      title: t('assignment'),
      icon: <UserOutlined />,
    },
  ];

  return (
    <Modal
      title={t('createNewTask')}
      open={open}
      onCancel={onCancel}
      width={800}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={onCancel}>
          {t('cancel')}
        </Button>,
        currentStep > 0 && (
          <Button key="prev" onClick={handlePrev}>
            {t('previous')}
          </Button>
        ),
        currentStep < steps.length - 1 ? (
          <Button key="next" type="primary" onClick={handleNext}>
            {t('next')}
          </Button>
        ) : (
          <Button
            key="submit"
            type="primary"
            loading={createTask.isPending}
            onClick={handleSubmit}
          >
            {t('createTask')}
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
