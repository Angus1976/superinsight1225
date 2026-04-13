// Task edit modal component
// Features:
// - Edit task basic info (name, description, status, priority)
// - Edit annotation configuration
// - Edit assignment info (assignee, due date)
// - Edit history tracking with rollback support
import { 
  Modal, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  App, 
  Tabs,
  Space,
  Button,
  Spin,
  Timeline,
  Tag,
  Tooltip,
  Popconfirm,
  Empty
} from 'antd';
import { useState, useEffect, useCallback } from 'react';
import { 
  UserOutlined, 
  HistoryOutlined,
  RollbackOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import { useTask, useUpdateTask } from '@/hooks/useTask';
import type { Task, TaskStatus, TaskPriority, AnnotationType, UpdateTaskPayload } from '@/types';

const { TextArea } = Input;

interface TaskEditModalProps {
  open: boolean;
  taskId: string | null;
  onCancel: () => void;
  onSuccess: () => void;
}

interface EditHistoryEntry {
  id: string;
  field: string;
  oldValue: string | null;
  newValue: string | null;
  editedBy: string;
  editedAt: string;
}

/** 与表单字段一致（due_date 为 Dayjs，与 Task 的 ISO 字符串区分） */
type TaskEditFormValues = {
  name: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  annotation_type: AnnotationType;
  assignee_id?: string;
  due_date: dayjs.Dayjs | null;
  tags: string[];
};

// Mock users for assignment - TODO: Replace with real API
const mockUsers = [
  { id: 'b0000001-0000-4000-8000-000000000001', name: 'John Doe', email: 'john.doe@company.com', role: 'Business Expert' },
  { id: 'b0000002-0000-4000-8000-000000000002', name: 'Jane Smith', email: 'jane.smith@company.com', role: 'Technical Expert' },
  { id: 'b0000003-0000-4000-8000-000000000003', name: 'Bob Wilson', email: 'bob.wilson@company.com', role: 'Annotator' },
];

const statusOptions: { label: string; value: TaskStatus; color: string }[] = [
  { label: 'statusPending', value: 'pending', color: 'default' },
  { label: 'statusInProgress', value: 'in_progress', color: 'processing' },
  { label: 'statusCompleted', value: 'completed', color: 'success' },
  { label: 'statusCancelled', value: 'cancelled', color: 'error' },
];

const priorityOptions: { label: string; value: TaskPriority; color: string }[] = [
  { label: 'priorityLow', value: 'low', color: 'green' },
  { label: 'priorityMedium', value: 'medium', color: 'blue' },
  { label: 'priorityHigh', value: 'high', color: 'orange' },
  { label: 'priorityUrgent', value: 'urgent', color: 'red' },
];

const annotationTypeOptions: { label: string; value: AnnotationType }[] = [
  { label: 'typeTextClassification', value: 'text_classification' },
  { label: 'typeNER', value: 'ner' },
  { label: 'typeSentiment', value: 'sentiment' },
  { label: 'typeQA', value: 'qa' },
  { label: 'typeCustom', value: 'custom' },
];

// Local storage key for edit history
const EDIT_HISTORY_KEY = 'task_edit_history';

// Load edit history from localStorage
const loadEditHistory = (taskId: string): EditHistoryEntry[] => {
  try {
    const stored = localStorage.getItem(`${EDIT_HISTORY_KEY}_${taskId}`);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

// Save edit history to localStorage
const saveEditHistory = (taskId: string, history: EditHistoryEntry[]): void => {
  // Keep only last 50 entries
  const trimmedHistory = history.slice(-50);
  localStorage.setItem(`${EDIT_HISTORY_KEY}_${taskId}`, JSON.stringify(trimmedHistory));
};

// Add entry to edit history
const addEditHistoryEntry = (
  taskId: string, 
  field: string, 
  oldValue: string | null, 
  newValue: string | null,
  editedBy: string = 'Current User'
): void => {
  const history = loadEditHistory(taskId);
  const entry: EditHistoryEntry = {
    id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    field,
    oldValue,
    newValue,
    editedBy,
    editedAt: new Date().toISOString(),
  };
  history.push(entry);
  saveEditHistory(taskId, history);
};

export const TaskEditModal: React.FC<TaskEditModalProps> = ({
  open,
  taskId,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('basic');
  const [editHistory, setEditHistory] = useState<EditHistoryEntry[]>([]);
  const [originalValues, setOriginalValues] = useState<Partial<TaskEditFormValues>>({});

  // Fetch task data
  const { data: task, isLoading, error } = useTask(taskId || '', { enabled: !!taskId && open });
  const updateTask = useUpdateTask();

  // Load edit history when task changes
  useEffect(() => {
    if (taskId && open) {
      setEditHistory(loadEditHistory(taskId));
    }
  }, [taskId, open]);

  // Populate form when task data is loaded
  useEffect(() => {
    if (task && open) {
      const formValues: TaskEditFormValues = {
        name: task.name,
        description: task.description || '',
        status: task.status,
        priority: task.priority,
        annotation_type: task.annotation_type,
        assignee_id: task.assignee_id,
        due_date: task.due_date ? dayjs(task.due_date) : null,
        tags: task.tags || [],
      };
      form.setFieldsValue(formValues);
      setOriginalValues(formValues);
    }
  }, [task, open, form]);

  // Reset form when modal closes
  useEffect(() => {
    if (!open) {
      form.resetFields();
      setActiveTab('basic');
      setOriginalValues({});
    }
  }, [open, form]);

  // Handle form submission
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (!taskId) {
        message.error(t('edit.loadFailed'));
        return;
      }

      // Build update payload and track changes
      const payload: UpdateTaskPayload = {};
      const changes: { field: string; oldValue: string | null; newValue: string | null }[] = [];

      // Check each field for changes
      if (values.name !== originalValues.name) {
        payload.name = values.name;
        changes.push({ field: 'name', oldValue: originalValues.name as string, newValue: values.name });
      }
      if (values.description !== originalValues.description) {
        payload.description = values.description;
        changes.push({ field: 'description', oldValue: originalValues.description as string || null, newValue: values.description || null });
      }
      if (values.status !== originalValues.status) {
        payload.status = values.status;
        changes.push({ field: 'status', oldValue: originalValues.status as string, newValue: values.status });
      }
      if (values.priority !== originalValues.priority) {
        payload.priority = values.priority;
        changes.push({ field: 'priority', oldValue: originalValues.priority as string, newValue: values.priority });
      }
      if (values.assignee_id !== originalValues.assignee_id) {
        payload.assignee_id = values.assignee_id;
        changes.push({ field: 'assignee_id', oldValue: originalValues.assignee_id as string || null, newValue: values.assignee_id || null });
      }
      
      // Handle due_date comparison
      const newDueDate = values.due_date ? values.due_date.toISOString() : undefined;
      const originalDueDate = originalValues.due_date
        ? originalValues.due_date.toISOString()
        : undefined;
      if (newDueDate !== originalDueDate) {
        payload.due_date = newDueDate;
        changes.push({ field: 'due_date', oldValue: originalDueDate || null, newValue: newDueDate || null });
      }

      // Handle tags comparison
      const newTags = values.tags || [];
      const originalTags = (originalValues.tags as string[]) || [];
      if (JSON.stringify(newTags.sort()) !== JSON.stringify(originalTags.sort())) {
        payload.tags = newTags;
        changes.push({ field: 'tags', oldValue: originalTags.join(', ') || null, newValue: newTags.join(', ') || null });
      }

      // If no changes, just close
      if (Object.keys(payload).length === 0) {
        onCancel();
        return;
      }

      // Update task
      await updateTask.mutateAsync({ id: taskId, payload });

      // Record changes in edit history
      for (const change of changes) {
        addEditHistoryEntry(taskId, change.field, change.oldValue, change.newValue);
      }

      message.success(t('edit.saveSuccess'));
      onSuccess();
    } catch (error) {
      if (error instanceof Error && error.message !== 'Validation failed') {
        message.error(t('edit.saveFailed'));
      }
    }
  };

  // Handle rollback
  const handleRollback = useCallback(async (entry: EditHistoryEntry) => {
    if (!taskId) return;

    try {
      const payload: UpdateTaskPayload = {};
      
      // Set the field back to old value
      switch (entry.field) {
        case 'name':
          payload.name = entry.oldValue || undefined;
          break;
        case 'description':
          payload.description = entry.oldValue || undefined;
          break;
        case 'status':
          payload.status = entry.oldValue as TaskStatus;
          break;
        case 'priority':
          payload.priority = entry.oldValue as TaskPriority;
          break;
        case 'assignee_id':
          payload.assignee_id = entry.oldValue || undefined;
          break;
        case 'due_date':
          payload.due_date = entry.oldValue || undefined;
          break;
        case 'tags':
          payload.tags = entry.oldValue ? entry.oldValue.split(', ') : [];
          break;
      }

      await updateTask.mutateAsync({ id: taskId, payload });

      // Add rollback entry to history
      addEditHistoryEntry(taskId, entry.field, entry.newValue, entry.oldValue, 'Rollback');
      setEditHistory(loadEditHistory(taskId));

      message.success(t('editHistory.rollbackSuccess'));
    } catch {
      message.error(t('editHistory.rollbackFailed'));
    }
  }, [taskId, updateTask, message, t]);

  // Format field name for display
  const formatFieldName = (field: string): string => {
    const fieldMap: Record<string, string> = {
      name: t('taskName'),
      description: t('description'),
      status: t('columns.status'),
      priority: t('columns.priority'),
      annotation_type: t('annotationType'),
      assignee_id: t('assignee'),
      due_date: t('dueDate'),
      tags: t('tagsLabel'),
    };
    return fieldMap[field] || field;
  };

  // Format value for display
  const formatValue = (field: string, value: string | null): string => {
    if (!value) return '-';
    
    switch (field) {
      case 'status': {
        const statusOpt = statusOptions.find(s => s.value === value);
        return statusOpt ? t(statusOpt.label) : value;
      }
      case 'priority': {
        const priorityOpt = priorityOptions.find(p => p.value === value);
        return priorityOpt ? t(priorityOpt.label) : value;
      }
      case 'annotation_type': {
        const typeOpt = annotationTypeOptions.find(a => a.value === value);
        return typeOpt ? t(typeOpt.label) : value;
      }
      case 'due_date':
        return dayjs(value).format('YYYY-MM-DD');
      case 'assignee_id': {
        const user = mockUsers.find(u => u.id === value);
        return user ? user.name : value;
      }
      default:
        return value;
    }
  };

  const tabItems = [
    {
      key: 'basic',
      label: t('edit.basicInfo'),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Form.Item
            name="name"
            label={t('edit.taskName')}
            rules={[
              { required: true, message: t('edit.taskNameRequired') },
              { max: 100, message: t('taskNameMaxLength') },
            ]}
          >
            <Input placeholder={t('edit.taskNamePlaceholder')} maxLength={100} showCount />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('edit.description')}
            rules={[{ max: 500, message: t('descriptionMaxLength') }]}
          >
            <TextArea 
              rows={3} 
              placeholder={t('edit.descriptionPlaceholder')} 
              maxLength={500} 
              showCount 
            />
          </Form.Item>

          <Form.Item name="status" label={t('edit.status')}>
            <Select placeholder={t('edit.statusPlaceholder')}>
              {statusOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  <Tag color={option.color}>{t(option.label)}</Tag>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="priority" label={t('edit.priority')}>
            <Select placeholder={t('edit.priorityPlaceholder')}>
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

          <Form.Item name="tags" label={t('edit.tags')}>
            <Select 
              mode="tags" 
              placeholder={t('edit.tagsPlaceholder')} 
              tokenSeparators={[',']} 
            />
          </Form.Item>
        </Space>
      ),
    },
    {
      key: 'annotation',
      label: t('edit.annotationConfig'),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Form.Item name="annotation_type" label={t('edit.annotationType')}>
            <Select placeholder={t('edit.annotationTypePlaceholder')} disabled>
              {annotationTypeOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {t(option.label)}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <div style={{ color: '#999', fontSize: 12 }}>
            <InfoCircleOutlined style={{ marginRight: 4 }} />
            {t('annotationType')} cannot be changed after task creation.
          </div>
        </Space>
      ),
    },
    {
      key: 'assignment',
      label: t('edit.assignmentInfo'),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Form.Item name="assignee_id" label={t('edit.assignee')}>
            <Select 
              placeholder={t('edit.assigneePlaceholder')} 
              allowClear
            >
              {mockUsers.map(user => (
                <Select.Option key={user.id} value={user.id}>
                  <Space>
                    <UserOutlined />
                    <Space direction="vertical" size={0}>
                      <span>{user.name}</span>
                      <span style={{ fontSize: 12, color: '#999' }}>{user.role}</span>
                    </Space>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="due_date" label={t('edit.dueDate')}>
            <DatePicker 
              style={{ width: '100%' }} 
              placeholder={t('edit.dueDatePlaceholder')} 
            />
          </Form.Item>
        </Space>
      ),
    },
    {
      key: 'history',
      label: (
        <Space>
          <HistoryOutlined />
          {t('editHistory.title')}
        </Space>
      ),
      children: (
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {editHistory.length === 0 ? (
            <Empty description={t('editHistory.noHistory')} />
          ) : (
            <Timeline
              items={editHistory.slice().reverse().map(entry => ({
                key: entry.id,
                children: (
                  <div>
                    <div style={{ marginBottom: 4 }}>
                      <strong>{formatFieldName(entry.field)}</strong>
                      <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                        {dayjs(entry.editedAt).format('YYYY-MM-DD HH:mm')}
                      </span>
                    </div>
                    <div style={{ fontSize: 13 }}>
                      <Tag color="red">{formatValue(entry.field, entry.oldValue)}</Tag>
                      <span style={{ margin: '0 8px' }}>→</span>
                      <Tag color="green">{formatValue(entry.field, entry.newValue)}</Tag>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      <span style={{ color: '#999', fontSize: 12 }}>
                        {t('editHistory.editedBy')}: {entry.editedBy}
                      </span>
                      <Popconfirm
                        title={t('editHistory.rollbackConfirm')}
                        onConfirm={() => handleRollback(entry)}
                        okText={t('confirm')}
                        cancelText={t('cancel')}
                      >
                        <Tooltip title={t('editHistory.rollback')}>
                          <Button 
                            type="link" 
                            size="small" 
                            icon={<RollbackOutlined />}
                            style={{ marginLeft: 8 }}
                          >
                            {t('editHistory.rollback')}
                          </Button>
                        </Tooltip>
                      </Popconfirm>
                    </div>
                  </div>
                ),
              }))}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <Modal
      title={t('edit.title')}
      open={open}
      onCancel={onCancel}
      width={700}
      destroyOnHidden
      footer={[
        <Button key="cancel" onClick={onCancel}>
          {t('edit.cancel')}
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={updateTask.isPending}
          onClick={handleSubmit}
        >
          {updateTask.isPending ? t('edit.saving') : t('edit.save')}
        </Button>,
      ]}
    >
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#ff4d4f' }}>
          {t('edit.loadFailed')}
        </div>
      ) : (
        <Form form={form} layout="vertical">
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            items={tabItems}
          />
        </Form>
      )}
    </Modal>
  );
};

export default TaskEditModal;
