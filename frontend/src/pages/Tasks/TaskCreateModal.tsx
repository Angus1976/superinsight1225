// Task creation modal component with enhanced features
// - Improved form layout with better organization
// - Comprehensive field validation
// - Batch task creation support
// - Task template functionality
// - Automatic Label Studio project creation
// - Data import from CSV, JSON, Excel
import { 
  Modal, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  App, 
  Steps, 
  Card, 
  Upload, 
  Radio, 
  Switch, 
  Divider, 
  Space, 
  Button, 
  Row, 
  Col,
  InputNumber,
  Tooltip,
  Alert,
  List,
  Typography,
  Popconfirm,
  Empty,
  Checkbox,
  Table,
  Tag
} from 'antd';
import { useState, useEffect, useCallback } from 'react';
import { 
  InboxOutlined, 
  UserOutlined, 
  SettingOutlined, 
  DatabaseOutlined, 
  FileTextOutlined,
  PlusOutlined,
  DeleteOutlined,
  SaveOutlined,
  FolderOpenOutlined,
  CopyOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  UploadOutlined,
  DownloadOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useCreateTask } from '@/hooks/useTask';
import labelStudioService from '@/services/labelStudioService';
import type { AnnotationTemplateConfig } from '@/services/labelStudioService';
import type { CreateTaskPayload, TaskPriority, AnnotationType } from '@/types';
import { 
  importTasksFromFile, 
  downloadCSVTemplate,
  type ImportResult,
  type ImportedTaskData 
} from '@/utils/import';

const { TextArea } = Input;
const { Step } = Steps;
const { Dragger } = Upload;
const { Text } = Typography;

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

// Task template interface for saving/loading templates
interface TaskTemplate {
  id: string;
  name: string;
  description?: string;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  data_source_type?: 'file' | 'api' | 'database';
  categories?: string[];
  entities?: string[];
  sentiment_scale?: string;
  auto_assignment?: boolean;
  notification_enabled?: boolean;
  deadline_reminder?: boolean;
  created_at: string;
}

// Batch task item interface
interface BatchTaskItem {
  key: string;
  name: string;
  description?: string;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  due_date?: string;
  tags?: string[];
  isValid: boolean;
  errors: string[];
}

// Local storage key for templates
const TEMPLATES_STORAGE_KEY = 'task_create_templates';

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
  config?: Record<string, unknown>;
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
const mockDataSources: DataSource[] = [
  { id: 'a0000001-0000-4000-8000-000000000001', name: 'Test Customer Reviews Dataset', type: 'file', description: 'CSV file containing customer reviews' },
  { id: 'a0000002-0000-4000-8000-000000000002', name: 'Test Product Descriptions API', type: 'api', description: 'REST API endpoint for product descriptions' },
  { id: 'a0000003-0000-4000-8000-000000000003', name: 'Test Support Tickets Database', type: 'database', description: 'PostgreSQL database with support tickets' },
];

const mockUsers: User[] = [
  { id: 'b0000001-0000-4000-8000-000000000001', name: 'John Doe', email: 'john.doe@company.com', role: 'Business Expert' },
  { id: 'b0000002-0000-4000-8000-000000000002', name: 'Jane Smith', email: 'jane.smith@company.com', role: 'Technical Expert' },
  { id: 'b0000003-0000-4000-8000-000000000003', name: 'Bob Wilson', email: 'bob.wilson@company.com', role: 'Annotator' },
];

// Template management utilities
const loadTemplates = (): TaskTemplate[] => {
  try {
    const stored = localStorage.getItem(TEMPLATES_STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const saveTemplates = (templates: TaskTemplate[]): void => {
  localStorage.setItem(TEMPLATES_STORAGE_KEY, JSON.stringify(templates));
};

const generateTemplateId = (): string => {
  return `template_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

const generateBatchItemKey = (): string => {
  return `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const TaskCreateModal: React.FC<TaskCreateModalProps> = ({
  open,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const { message, modal } = App.useApp();
  const [form] = Form.useForm();
  const createTask = useCreateTask();
  
  // State management
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedAnnotationType, setSelectedAnnotationType] = useState<AnnotationType>('text_classification');
  const [createMode, setCreateMode] = useState<'single' | 'batch'>('single');
  const [batchTasks, setBatchTasks] = useState<BatchTaskItem[]>([]);
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [saveTemplateModalOpen, setSaveTemplateModalOpen] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Label Studio project creation state
  const [autoCreateProject, setAutoCreateProject] = useState(true);
  const [isCreatingProject, setIsCreatingProject] = useState(false);

  // Import state
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult<ImportedTaskData> | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  // Load templates on mount
  useEffect(() => {
    setTemplates(loadTemplates());
  }, []);

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      form.resetFields();
      setCurrentStep(0);
      setCreateMode('single');
      setBatchTasks([]);
      setSelectedAnnotationType('text_classification');
      setImportResult(null);
      setImportModalOpen(false);
    }
  }, [open, form]);

  // Validation helper for batch tasks
  const validateBatchTask = useCallback((task: Partial<BatchTaskItem>): { isValid: boolean; errors: string[] } => {
    const errors: string[] = [];
    if (!task.name || task.name.trim().length === 0) {
      errors.push(t('taskNameRequired'));
    }
    if (task.name && task.name.length > 100) {
      errors.push(t('taskNameMaxLength'));
    }
    return { isValid: errors.length === 0, errors };
  }, [t]);

  // Add new batch task
  const handleAddBatchTask = useCallback(() => {
    const formValues = form.getFieldsValue();
    const newTask: BatchTaskItem = {
      key: generateBatchItemKey(),
      name: '',
      description: '',
      priority: formValues.priority || 'medium',
      annotation_type: formValues.annotation_type || 'text_classification',
      tags: [],
      isValid: false,
      errors: [t('taskNameRequired')],
    };
    setBatchTasks(prev => [...prev, newTask]);
  }, [form, t]);

  // Update batch task
  const handleUpdateBatchTask = useCallback((key: string, field: keyof BatchTaskItem, value: unknown) => {
    setBatchTasks(prev => prev.map(task => {
      if (task.key !== key) return task;
      const updated = { ...task, [field]: value };
      const validation = validateBatchTask(updated);
      return { ...updated, ...validation };
    }));
  }, [validateBatchTask]);

  // Remove batch task
  const handleRemoveBatchTask = useCallback((key: string) => {
    setBatchTasks(prev => prev.filter(task => task.key !== key));
  }, []);

  // Duplicate batch task
  const handleDuplicateBatchTask = useCallback((task: BatchTaskItem) => {
    const newTask: BatchTaskItem = {
      ...task,
      key: generateBatchItemKey(),
      name: `${task.name} (${t('copy') || 'Copy'})`,
    };
    const validation = validateBatchTask(newTask);
    setBatchTasks(prev => [...prev, { ...newTask, ...validation }]);
  }, [validateBatchTask, t]);

  // Template management
  const handleSaveTemplate = useCallback(() => {
    if (!templateName.trim()) {
      message.warning(t('templateNameRequired') || 'Please enter template name');
      return;
    }
    const formValues = form.getFieldsValue(true);
    const newTemplate: TaskTemplate = {
      id: generateTemplateId(),
      name: templateName.trim(),
      description: formValues.description,
      priority: formValues.priority || 'medium',
      annotation_type: formValues.annotation_type || 'text_classification',
      data_source_type: formValues.data_source_type,
      categories: formValues.categories,
      entities: formValues.entities,
      sentiment_scale: formValues.sentiment_scale,
      auto_assignment: formValues.auto_assignment,
      notification_enabled: formValues.notification_enabled,
      deadline_reminder: formValues.deadline_reminder,
      created_at: new Date().toISOString(),
    };
    const updatedTemplates = [...templates, newTemplate];
    setTemplates(updatedTemplates);
    saveTemplates(updatedTemplates);
    setSaveTemplateModalOpen(false);
    setTemplateName('');
    message.success(t('templateSaved') || 'Template saved successfully');
  }, [templateName, form, templates, message, t]);

  const handleLoadTemplate = useCallback((template: TaskTemplate) => {
    form.setFieldsValue({
      priority: template.priority,
      annotation_type: template.annotation_type,
      data_source_type: template.data_source_type,
      categories: template.categories,
      entities: template.entities,
      sentiment_scale: template.sentiment_scale,
      auto_assignment: template.auto_assignment,
      notification_enabled: template.notification_enabled,
      deadline_reminder: template.deadline_reminder,
    });
    setSelectedAnnotationType(template.annotation_type);
    setTemplateModalOpen(false);
    message.success(t('templateLoaded') || 'Template loaded');
  }, [form, message, t]);

  const handleDeleteTemplate = useCallback((templateId: string) => {
    const updatedTemplates = templates.filter(t => t.id !== templateId);
    setTemplates(updatedTemplates);
    saveTemplates(updatedTemplates);
    message.success(t('templateDeleted') || 'Template deleted');
  }, [templates, message, t]);

  // Import handlers
  const handleFileImport = useCallback(async (file: File) => {
    setIsImporting(true);
    try {
      const result = await importTasksFromFile(file, { t });
      setImportResult(result);
      
      if (result.success && result.data.length > 0) {
        // Convert imported data to batch tasks
        const importedBatchTasks: BatchTaskItem[] = result.data.map((task, index) => ({
          key: generateBatchItemKey(),
          name: task.name,
          description: task.description,
          priority: task.priority,
          annotation_type: task.annotation_type,
          due_date: task.due_date,
          tags: task.tags,
          isValid: true,
          errors: [],
        }));
        setBatchTasks(prev => [...prev, ...importedBatchTasks]);
        setCreateMode('batch');
        setImportModalOpen(false);
        message.success(t('import.importSuccess', { count: result.data.length }) || `Successfully imported ${result.data.length} tasks`);
      } else if (result.errors.length > 0) {
        message.error(t('import.importFailed') || 'Import failed');
      }
    } catch (error) {
      message.error(t('import.importFailed') || 'Import failed');
    } finally {
      setIsImporting(false);
    }
    return false; // Prevent default upload behavior
  }, [t, message]);

  const handleDownloadTemplate = useCallback(() => {
    downloadCSVTemplate(t);
    message.success(t('import.downloadTemplate') || 'Template downloaded');
  }, [t, message]);

  // Submit handlers
  const handleSubmitSingle = async () => {
    try {
      const allFieldNames = [
        'name', 'description', 'priority', 'due_date', 'tags',
        'data_source_type', 'data_source_id',
        'annotation_type', 'categories', 'multi_label', 'entities', 'nested_entities', 'sentiment_scale',
        'assignee_id', 'auto_assignment', 'notification_enabled', 'deadline_reminder'
      ];
      const values = await form.validateFields(allFieldNames);
      
      if (!values.name) {
        message.error(t('taskNameRequired'));
        setCurrentStep(0);
        return;
      }

      let dataSource = undefined;
      if (values.data_source_id) {
        dataSource = {
          type: values.data_source_type || 'file',
          config: { source_id: values.data_source_id },
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

      // Create the task first
      const createdTask = await createTask.mutateAsync(payload);
      
      // Auto-create Label Studio project if enabled
      if (autoCreateProject && createdTask?.id) {
        setIsCreatingProject(true);
        try {
          // Build template configuration based on annotation type
          const templateConfig: AnnotationTemplateConfig = {};
          
          if (values.annotation_type === 'text_classification' && values.categories?.length > 0) {
            templateConfig.categories = values.categories;
            templateConfig.multiLabel = values.multi_label || false;
          } else if (values.annotation_type === 'ner' && values.entities?.length > 0) {
            templateConfig.entityTypes = values.entities;
          } else if (values.annotation_type === 'sentiment' && values.sentiment_scale) {
            templateConfig.sentimentScale = values.sentiment_scale;
          }
          
          // Create Label Studio project with template
          const projectId = await labelStudioService.createAndLinkProject(
            createdTask.id,
            values.name,
            values.annotation_type || 'text_classification',
            Object.keys(templateConfig).length > 0 ? templateConfig : undefined
          );
          
          if (projectId) {
            message.success(t('labelStudioProjectCreated') || 'Label Studio project created successfully');
          }
        } catch (projectError) {
          console.warn('Failed to create Label Studio project:', projectError);
          message.warning(t('labelStudioProjectFailed') || 'Task created, but Label Studio project creation failed');
        } finally {
          setIsCreatingProject(false);
        }
      }
      
      message.success(t('createTaskSuccess') || 'Task created successfully');
      form.resetFields();
      setCurrentStep(0);
      onSuccess();
    } catch (error) {
      if (error instanceof Error && error.message !== 'Validation failed') {
        message.error(t('createTaskError') || 'Failed to create task');
      }
    }
  };

  const handleSubmitBatch = async () => {
    const validTasks = batchTasks.filter(task => task.isValid);
    if (validTasks.length === 0) {
      message.warning(t('noValidBatchTasks') || 'No valid tasks to create');
      return;
    }

    setIsSubmitting(true);
    let successCount = 0;
    let failCount = 0;

    for (const task of validTasks) {
      try {
        const payload: CreateTaskPayload = {
          name: task.name,
          description: task.description,
          priority: task.priority,
          annotation_type: task.annotation_type,
          due_date: task.due_date,
          tags: task.tags,
        };
        await createTask.mutateAsync(payload);
        successCount++;
      } catch {
        failCount++;
      }
    }

    setIsSubmitting(false);

    if (failCount === 0) {
      message.success(t('batchCreateSuccess', { count: successCount }) || `Successfully created ${successCount} tasks`);
      form.resetFields();
      setCurrentStep(0);
      setBatchTasks([]);
      onSuccess();
    } else {
      message.warning(t('batchCreatePartial', { success: successCount, fail: failCount }) || 
        `Created ${successCount} tasks, ${failCount} failed`);
    }
  };

  const handleSubmit = async () => {
    if (createMode === 'batch') {
      await handleSubmitBatch();
    } else {
      await handleSubmitSingle();
    }
  };

  // Step navigation
  const handleNext = async () => {
    try {
      const currentFields = getCurrentStepFields();
      await form.validateFields(currentFields);
      setCurrentStep(currentStep + 1);
    } catch {
      // Validation failed, stay on current step
    }
  };

  const handlePrev = () => setCurrentStep(currentStep - 1);

  const getCurrentStepFields = () => {
    switch (currentStep) {
      case 0: return ['name', 'description', 'priority', 'due_date', 'tags'];
      case 1: return ['data_source_type', 'data_source_id'];
      case 2: return ['annotation_type'];
      case 3: return ['assignee_id'];
      default: return [];
    }
  };

  const handleAnnotationTypeChange = (value: AnnotationType) => {
    setSelectedAnnotationType(value);
  };

  const steps = [
    { title: t('basicInfo'), icon: <SettingOutlined /> },
    { title: t('dataSource'), icon: <DatabaseOutlined /> },
    { title: t('annotationConfig'), icon: <FileTextOutlined /> },
    { title: t('assignment'), icon: <UserOutlined /> },
  ];

  // Render batch task list
  const renderBatchTaskList = () => (
    <Card 
      title={
        <Space>
          <span>{t('batchTasks') || 'Batch Tasks'}</span>
          <Text type="secondary">({batchTasks.length})</Text>
        </Space>
      }
      extra={
        <Space>
          <Upload
            accept=".csv,.json,.xlsx,.xls"
            showUploadList={false}
            beforeUpload={handleFileImport}
          >
            <Button icon={<UploadOutlined />} loading={isImporting}>
              {t('import.title') || 'Import'}
            </Button>
          </Upload>
          <Tooltip title={t('import.downloadTemplate') || 'Download Template'}>
            <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate} />
          </Tooltip>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddBatchTask}>
            {t('addTask') || 'Add Task'}
          </Button>
        </Space>
      }
      variant="borderless"
    >
      {batchTasks.length === 0 ? (
        <Empty description={t('noBatchTasks') || 'No tasks added yet'}>
          <Space direction="vertical">
            <Upload
              accept=".csv,.json,.xlsx,.xls"
              showUploadList={false}
              beforeUpload={handleFileImport}
            >
              <Button type="primary" icon={<UploadOutlined />} loading={isImporting}>
                {t('import.title') || 'Import from File'}
              </Button>
            </Upload>
            <Button onClick={handleAddBatchTask}>
              {t('addFirstTask') || 'Add Manually'}
            </Button>
            <Button type="link" size="small" onClick={handleDownloadTemplate}>
              {t('import.downloadTemplate') || 'Download Template'}
            </Button>
          </Space>
        </Empty>
      ) : (
        <List
          dataSource={batchTasks}
          renderItem={(task, index) => (
            <List.Item
              key={task.key}
              style={{ 
                background: task.isValid ? '#f6ffed' : '#fff2f0',
                marginBottom: 8,
                padding: '12px 16px',
                borderRadius: 8,
                border: `1px solid ${task.isValid ? '#b7eb8f' : '#ffccc7'}`
              }}
            >
              <Row gutter={16} style={{ width: '100%' }} align="middle">
                <Col span={1}>
                  <Text type="secondary">#{index + 1}</Text>
                </Col>
                <Col span={8}>
                  <Input
                    placeholder={t('taskNamePlaceholder')}
                    value={task.name}
                    onChange={e => handleUpdateBatchTask(task.key, 'name', e.target.value)}
                    status={task.errors.length > 0 ? 'error' : undefined}
                  />
                </Col>
                <Col span={5}>
                  <Select
                    style={{ width: '100%' }}
                    value={task.priority}
                    onChange={v => handleUpdateBatchTask(task.key, 'priority', v)}
                  >
                    {priorityOptions.map(opt => (
                      <Select.Option key={opt.value} value={opt.value}>
                        <Space>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: opt.color }} />
                          {t(opt.label)}
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Col>
                <Col span={6}>
                  <Select
                    style={{ width: '100%' }}
                    value={task.annotation_type}
                    onChange={v => handleUpdateBatchTask(task.key, 'annotation_type', v)}
                  >
                    {annotationTypeOptions.map(opt => (
                      <Select.Option key={opt.value} value={opt.value}>{t(opt.label)}</Select.Option>
                    ))}
                  </Select>
                </Col>
                <Col span={4}>
                  <Space>
                    <Tooltip title={t('duplicate') || 'Duplicate'}>
                      <Button icon={<CopyOutlined />} size="small" onClick={() => handleDuplicateBatchTask(task)} />
                    </Tooltip>
                    <Tooltip title={t('deleteAction')}>
                      <Button icon={<DeleteOutlined />} size="small" danger onClick={() => handleRemoveBatchTask(task.key)} />
                    </Tooltip>
                    {task.isValid && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
                  </Space>
                </Col>
              </Row>
            </List.Item>
          )}
        />
      )}
      {batchTasks.length > 0 && (
        <Alert
          type={batchTasks.every(t => t.isValid) ? 'success' : 'warning'}
          message={t('batchValidation', { 
            valid: batchTasks.filter(t => t.isValid).length, 
            total: batchTasks.length 
          }) || `${batchTasks.filter(t => t.isValid).length} of ${batchTasks.length} tasks are valid`}
          showIcon
          style={{ marginTop: 16 }}
        />
      )}
    </Card>
  );

  // Render step content
  const renderStepContent = () => (
    <>
      {/* Step 0: Basic Info */}
      <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
        <Card title={t('basicInfo')} variant="borderless">
          <Form.Item
            name="name"
            label={t('taskName')}
            rules={[
              { required: true, message: t('taskNameRequired') },
              { max: 100, message: t('taskNameMaxLength') },
              { whitespace: true, message: t('taskNameRequired') },
            ]}
            tooltip={t('taskNameTooltip') || 'Enter a descriptive name for the task'}
          >
            <Input placeholder={t('taskNamePlaceholder')} maxLength={100} showCount />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('description')}
            rules={[{ max: 500, message: t('descriptionMaxLength') }]}
          >
            <TextArea rows={3} placeholder={t('descriptionPlaceholder')} maxLength={500} showCount />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label={t('columns.priority')}
                rules={[{ required: true, message: t('create.priorityRequired') }]}
              >
                <Select placeholder={t('priorityPlaceholder')}>
                  {priorityOptions.map(option => (
                    <Select.Option key={option.value} value={option.value}>
                      <Space>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: option.color }} />
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
            <Select mode="tags" placeholder={t('tagsPlaceholder')} tokenSeparators={[',']} />
          </Form.Item>
        </Card>
      </div>

      {/* Step 1: Data Source */}
      <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
        <Card title={t('dataSource')} variant="borderless">
          <Form.Item name="data_source_type" label={t('dataSourceType')}>
            <Radio.Group>
              <Space direction="vertical">
                <Radio value="file"><Space><FileTextOutlined />{t('fileUpload')}</Space></Radio>
                <Radio value="api"><Space><DatabaseOutlined />{t('apiEndpoint')}</Space></Radio>
                <Radio value="database"><Space><DatabaseOutlined />{t('database')}</Space></Radio>
              </Space>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="data_source_id" label={t('selectDataSource')}>
            <Select placeholder={t('dataSourcePlaceholder')}>
              {mockDataSources.map(source => (
                <Select.Option key={source.id} value={source.id}>
                  <Space direction="vertical" size={0}>
                    <span>{source.name}</span>
                    <span style={{ fontSize: 12, color: '#999' }}>{source.description}</span>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Divider />

          <Form.Item name="file_upload" label={t('uploadFile')}>
            <Dragger name="file" multiple={false} accept=".csv,.json,.txt,.xlsx" beforeUpload={() => false}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">{t('uploadText')}</p>
              <p className="ant-upload-hint">{t('uploadHint')}</p>
            </Dragger>
          </Form.Item>
        </Card>
      </div>

      {/* Step 2: Annotation Config */}
      <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
        <Card title={t('annotationConfig')} variant="borderless">
          <Form.Item
            name="annotation_type"
            label={t('annotationType')}
            rules={[{ required: true, message: t('annotationTypeRequired') }]}
          >
            <Radio.Group onChange={(e) => handleAnnotationTypeChange(e.target.value)} style={{ width: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {annotationTypeOptions.map(option => (
                  <Radio key={option.value} value={option.value} style={{ width: '100%' }}>
                    <Space direction="vertical" size={0}>
                      <span style={{ fontWeight: 500 }}>{t(option.label)}</span>
                      <span style={{ fontSize: 12, color: '#666' }}>{t(option.description)}</span>
                    </Space>
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
          </Form.Item>

          {selectedAnnotationType === 'text_classification' && (
            <Card size="small" title={t('classificationConfig')}>
              <Form.Item name="categories" label={t('categories')}>
                <Select mode="tags" placeholder={t('categoriesPlaceholder')} tokenSeparators={[',']} />
              </Form.Item>
              <Form.Item name="multi_label" label={t('multiLabel')} valuePropName="checked">
                <Switch />
              </Form.Item>
            </Card>
          )}

          {selectedAnnotationType === 'ner' && (
            <Card size="small" title={t('nerConfig')}>
              <Form.Item name="entities" label={t('entityTypes')}>
                <Select mode="tags" placeholder={t('entityTypesPlaceholder')} tokenSeparators={[',']} />
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
        <Card title={t('assignmentConfig')} variant="borderless">
          <Form.Item name="assignee_id" label={t('assignTo')}>
            <Select placeholder={t('assigneePlaceholder')}>
              {mockUsers.map(user => (
                <Select.Option key={user.id} value={user.id}>
                  <Space>
                    <UserOutlined />
                    <Space direction="vertical" size={0}>
                      <span>{user.name}</span>
                      <span style={{ fontSize: 12, color: '#999' }}>{user.role} • {user.email}</span>
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
          
          <Divider />
          
          {/* Label Studio Project Auto-Creation */}
          <Card 
            size="small" 
            title={
              <Space>
                <CloudServerOutlined />
                <span>{t('labelStudioIntegration') || 'Label Studio Integration'}</span>
              </Space>
            }
          >
            <Form.Item 
              label={t('autoCreateProject') || 'Auto-create Label Studio Project'}
              tooltip={t('autoCreateProjectTooltip') || 'Automatically create a Label Studio project when the task is created'}
            >
              <Checkbox 
                checked={autoCreateProject} 
                onChange={e => setAutoCreateProject(e.target.checked)}
              >
                {t('autoCreateProjectDescription') || 'Create annotation project automatically'}
              </Checkbox>
            </Form.Item>
            {autoCreateProject && (
              <Alert
                type="info"
                showIcon
                message={t('autoCreateProjectInfo') || 'A Label Studio project will be created with the configured annotation template'}
                style={{ marginTop: 8 }}
              />
            )}
          </Card>
        </Card>
      </div>
    </>
  );

  return (
    <>
      <Modal
        title={
          <Space>
            <span>{t('createNewTask')}</span>
            <Radio.Group 
              value={createMode} 
              onChange={e => setCreateMode(e.target.value)}
              size="small"
              buttonStyle="solid"
            >
              <Radio.Button value="single">{t('singleTask') || 'Single'}</Radio.Button>
              <Radio.Button value="batch">{t('batchCreate') || 'Batch'}</Radio.Button>
            </Radio.Group>
          </Space>
        }
        open={open}
        onCancel={onCancel}
        width={900}
        destroyOnHidden
        footer={[
          <Space key="template-actions" style={{ float: 'left' }}>
            <Tooltip title={t('loadTemplate') || 'Load Template'}>
              <Button icon={<FolderOpenOutlined />} onClick={() => setTemplateModalOpen(true)}>
                {t('templates') || 'Templates'}
              </Button>
            </Tooltip>
            <Tooltip title={t('saveAsTemplate') || 'Save as Template'}>
              <Button icon={<SaveOutlined />} onClick={() => setSaveTemplateModalOpen(true)} />
            </Tooltip>
          </Space>,
          <Button key="cancel" onClick={onCancel}>{t('cancel')}</Button>,
          createMode === 'single' && currentStep > 0 && (
            <Button key="prev" onClick={handlePrev}>{t('previous')}</Button>
          ),
          createMode === 'single' && currentStep < steps.length - 1 ? (
            <Button key="next" type="primary" onClick={handleNext}>{t('next')}</Button>
          ) : (
            <Button
              key="submit"
              type="primary"
              loading={createTask.isPending || isSubmitting}
              onClick={handleSubmit}
            >
              {createMode === 'batch' 
                ? (t('createTasks', { count: batchTasks.filter(t => t.isValid).length }) || `Create ${batchTasks.filter(t => t.isValid).length} Tasks`)
                : t('createTask')
              }
            </Button>
          ),
        ]}
      >
        {createMode === 'single' ? (
          <>
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
          </>
        ) : (
          <Form form={form} layout="vertical" initialValues={{ priority: 'medium', annotation_type: 'text_classification' }}>
            {renderBatchTaskList()}
          </Form>
        )}
      </Modal>

      {/* Template Selection Modal */}
      <Modal
        title={t('selectTemplate') || 'Select Template'}
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        footer={null}
        width={600}
      >
        {templates.length === 0 ? (
          <Empty description={t('noTemplates') || 'No templates saved yet'} />
        ) : (
          <List
            dataSource={templates}
            renderItem={template => (
              <List.Item
                actions={[
                  <Button key="load" type="link" onClick={() => handleLoadTemplate(template)}>
                    {t('load') || 'Load'}
                  </Button>,
                  <Popconfirm
                    key="delete"
                    title={t('confirmDeleteTemplate') || 'Delete this template?'}
                    onConfirm={() => handleDeleteTemplate(template.id)}
                    okText={t('confirm') || 'Yes'}
                    cancelText={t('cancel')}
                  >
                    <Button type="link" danger>{t('deleteAction')}</Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  title={template.name}
                  description={
                    <Space>
                      <Text type="secondary">{t(priorityOptions.find(p => p.value === template.priority)?.label || '')}</Text>
                      <Text type="secondary">•</Text>
                      <Text type="secondary">{t(annotationTypeOptions.find(a => a.value === template.annotation_type)?.label || '')}</Text>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Modal>

      {/* Save Template Modal */}
      <Modal
        title={t('saveAsTemplate') || 'Save as Template'}
        open={saveTemplateModalOpen}
        onCancel={() => { setSaveTemplateModalOpen(false); setTemplateName(''); }}
        onOk={handleSaveTemplate}
        okText={t('save') || 'Save'}
        cancelText={t('cancel')}
      >
        <Form layout="vertical">
          <Form.Item label={t('templateName') || 'Template Name'} required>
            <Input
              value={templateName}
              onChange={e => setTemplateName(e.target.value)}
              placeholder={t('templateNamePlaceholder') || 'Enter template name'}
              maxLength={50}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};
