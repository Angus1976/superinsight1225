// Batch edit modal component for tasks
// Features:
// - Batch modify status
// - Batch modify priority
// - Batch assign personnel
// - Batch set due date
import { 
  Modal, 
  Form, 
  Select, 
  DatePicker, 
  App, 
  Space,
  Button,
  Alert,
  Progress,
  Tag
} from 'antd';
import { useState, useCallback } from 'react';
import { 
  UserOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useUpdateTask } from '@/hooks/useTask';
import type { Task, TaskStatus, TaskPriority, UpdateTaskPayload } from '@/types';

interface BatchEditModalProps {
  open: boolean;
  tasks: Task[];
  onCancel: () => void;
  onSuccess: () => void;
}

type BatchEditField = 'status' | 'priority' | 'assignee_id' | 'due_date';

// Mock users for assignment - TODO: Replace with real API
const mockUsers = [
  { id: 'b0000001-0000-4000-8000-000000000001', name: 'John Doe', role: 'Business Expert' },
  { id: 'b0000002-0000-4000-8000-000000000002', name: 'Jane Smith', role: 'Technical Expert' },
  { id: 'b0000003-0000-4000-8000-000000000003', name: 'Bob Wilson', role: 'Annotator' },
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

const fieldOptions: { label: string; value: BatchEditField }[] = [
  { label: 'tasks.batchEdit.status', value: 'status' },
  { label: 'tasks.batchEdit.priority', value: 'priority' },
  { label: 'tasks.batchEdit.assignee', value: 'assignee_id' },
  { label: 'tasks.batchEdit.dueDate', value: 'due_date' },
];

interface BatchProgress {
  current: number;
  total: number;
  success: number;
  failed: number;
  status: 'idle' | 'processing' | 'completed' | 'error';
}

export const BatchEditModal: React.FC<BatchEditModalProps> = ({
  open,
  tasks,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [selectedField, setSelectedField] = useState<BatchEditField | null>(null);
  const [progress, setProgress] = useState<BatchProgress>({
    current: 0,
    total: 0,
    success: 0,
    failed: 0,
    status: 'idle',
  });

  const updateTask = useUpdateTask();

  // Reset form when modal closes
  const handleCancel = useCallback(() => {
    form.resetFields();
    setSelectedField(null);
    setProgress({ current: 0, total: 0, success: 0, failed: 0, status: 'idle' });
    onCancel();
  }, [form, onCancel]);

  // Handle batch update
  const handleSubmit = async () => {
    if (!selectedField) {
      message.warning(t('tasks.batchEdit.noFieldSelected'));
      return;
    }

    try {
      const values = await form.validateFields();
      const newValue = values[selectedField];

      if (newValue === undefined || newValue === null || newValue === '') {
        message.warning(t('tasks.batchEdit.noValueProvided'));
        return;
      }

      // Start batch processing
      setProgress({
        current: 0,
        total: tasks.length,
        success: 0,
        failed: 0,
        status: 'processing',
      });

      let successCount = 0;
      let failCount = 0;

      // Process tasks one by one
      for (let i = 0; i < tasks.length; i++) {
        const task = tasks[i];
        
        try {
          const payload: UpdateTaskPayload = {};
          
          switch (selectedField) {
            case 'status':
              payload.status = newValue;
              break;
            case 'priority':
              payload.priority = newValue;
              break;
            case 'assignee_id':
              payload.assignee_id = newValue;
              break;
            case 'due_date':
              payload.due_date = newValue.toISOString();
              break;
          }

          await updateTask.mutateAsync({ id: task.id, payload });
          successCount++;
        } catch {
          failCount++;
        }

        setProgress(prev => ({
          ...prev,
          current: i + 1,
          success: successCount,
          failed: failCount,
        }));
      }

      // Update final status
      setProgress(prev => ({
        ...prev,
        status: failCount > 0 ? 'error' : 'completed',
      }));

      // Show result message
      if (failCount === 0) {
        message.success(t('tasks.batchEdit.applySuccess', { count: successCount }));
        setTimeout(() => {
          handleCancel();
          onSuccess();
        }, 1000);
      } else if (successCount > 0) {
        message.warning(t('tasks.batchEdit.applyPartial', { success: successCount, failed: failCount }));
        setTimeout(() => {
          handleCancel();
          onSuccess();
        }, 2000);
      } else {
        message.error(t('tasks.batchEdit.applyFailed'));
      }
    } catch {
      message.error(t('tasks.batchEdit.applyFailed'));
    }
  };

  // Render value input based on selected field
  const renderValueInput = () => {
    switch (selectedField) {
      case 'status':
        return (
          <Form.Item
            name="status"
            label={t('tasks.batchEdit.newValue')}
            rules={[{ required: true, message: t('tasks.batchEdit.noValueProvided') }]}
          >
            <Select placeholder={t('tasks.edit.statusPlaceholder')}>
              {statusOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  <Tag color={option.color}>{t(option.label)}</Tag>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        );

      case 'priority':
        return (
          <Form.Item
            name="priority"
            label={t('tasks.batchEdit.newValue')}
            rules={[{ required: true, message: t('tasks.batchEdit.noValueProvided') }]}
          >
            <Select placeholder={t('tasks.edit.priorityPlaceholder')}>
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
        );

      case 'assignee_id':
        return (
          <Form.Item
            name="assignee_id"
            label={t('tasks.batchEdit.newValue')}
            rules={[{ required: true, message: t('tasks.batchEdit.noValueProvided') }]}
          >
            <Select placeholder={t('tasks.edit.assigneePlaceholder')}>
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
        );

      case 'due_date':
        return (
          <Form.Item
            name="due_date"
            label={t('tasks.batchEdit.newValue')}
            rules={[{ required: true, message: t('tasks.batchEdit.noValueProvided') }]}
          >
            <DatePicker 
              style={{ width: '100%' }} 
              placeholder={t('tasks.edit.dueDatePlaceholder')} 
            />
          </Form.Item>
        );

      default:
        return null;
    }
  };

  const isProcessing = progress.status === 'processing';

  return (
    <Modal
      title={t('tasks.batchEdit.title')}
      open={open}
      onCancel={handleCancel}
      width={500}
      destroyOnHidden
      closable={!isProcessing}
      maskClosable={!isProcessing}
      footer={
        isProcessing ? null : [
          <Button key="cancel" onClick={handleCancel}>
            {t('tasks.batchEdit.cancel')}
          </Button>,
          <Button
            key="submit"
            type="primary"
            onClick={handleSubmit}
            disabled={!selectedField}
          >
            {t('tasks.batchEdit.apply')}
          </Button>,
        ]
      }
    >
      {/* Selected tasks info */}
      <Alert
        type="info"
        message={t('tasks.batchEdit.selectedCount', { count: tasks.length })}
        style={{ marginBottom: 16 }}
        showIcon
      />

      {/* Progress display */}
      {progress.status !== 'idle' && (
        <div style={{ marginBottom: 16, textAlign: 'center' }}>
          <Progress
            type="circle"
            percent={Math.round((progress.current / progress.total) * 100)}
            status={
              progress.status === 'error' ? 'exception' :
              progress.status === 'completed' ? 'success' : 'active'
            }
            format={() => `${progress.current}/${progress.total}`}
            size={80}
          />
          <div style={{ marginTop: 8 }}>
            {progress.status === 'processing' && (
              <span>{t('tasks.batchEdit.applying')}</span>
            )}
            {progress.status === 'completed' && (
              <Tag color="success" icon={<CheckCircleOutlined />}>
                {t('tasks.batchEdit.applySuccess', { count: progress.success })}
              </Tag>
            )}
            {progress.status === 'error' && progress.success > 0 && (
              <Tag color="warning" icon={<ExclamationCircleOutlined />}>
                {t('tasks.batchEdit.applyPartial', { success: progress.success, failed: progress.failed })}
              </Tag>
            )}
          </div>
        </div>
      )}

      {/* Form */}
      {progress.status === 'idle' && (
        <Form form={form} layout="vertical">
          <Form.Item
            label={t('tasks.batchEdit.selectField')}
            required
          >
            <Select
              placeholder={t('tasks.batchEdit.selectField')}
              value={selectedField}
              onChange={(value) => {
                setSelectedField(value);
                form.resetFields([value]);
              }}
            >
              {fieldOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {t(option.label)}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {selectedField && renderValueInput()}
        </Form>
      )}
    </Modal>
  );
};

export default BatchEditModal;
