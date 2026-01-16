// Task edit page - reuses TaskCreateModal in edit mode
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, Skeleton, Alert, message } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTask, useUpdateTask } from '@/hooks/useTask';
import { TaskEditForm } from './TaskEditForm';

const TaskEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation('tasks');
  const { data: task, isLoading, error } = useTask(id || '');
  const updateTask = useUpdateTask();

  // Mock data for development
  const mockTask = {
    id: id || '1',
    name: 'Customer Review Classification',
    description: 'Classify customer reviews by sentiment',
    status: 'in_progress' as const,
    priority: 'high' as const,
    annotation_type: 'sentiment' as const,
    assignee_id: 'user1',
    assignee_name: 'John Doe',
    created_by: 'admin',
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-20T14:30:00Z',
    due_date: '2025-02-01T00:00:00Z',
    progress: 65,
    total_items: 1000,
    completed_items: 650,
    tenant_id: 'tenant1',
    tags: ['urgent', 'customer'],
  };

  const currentTask = task || mockTask;

  const handleSave = async (values: any) => {
    if (!id) return;
    
    try {
      await updateTask.mutateAsync({ id, payload: values });
      message.success(t('taskUpdated'));
      navigate(`/tasks/${id}`);
    } catch (error) {
      message.error(t('taskUpdateFailed'));
    }
  };

  if (isLoading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 10 }} />
      </Card>
    );
  }

  if (error && !mockTask) {
    return (
      <Alert
        type="error"
        message={t('failedToLoadTask')}
        description={t('failedToLoadTaskDescription')}
        showIcon
      />
    );
  }

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/tasks/${id}`)}>
            {t('backToDetail')}
          </Button>
        </Space>
        <h2 style={{ marginTop: 16, marginBottom: 0 }}>{t('editTask')}: {currentTask.name}</h2>
      </Card>

      <Card>
        <TaskEditForm
          initialValues={currentTask}
          onSubmit={handleSave}
          onCancel={() => navigate(`/tasks/${id}`)}
          loading={updateTask.isPending}
        />
      </Card>
    </div>
  );
};

export default TaskEditPage;
