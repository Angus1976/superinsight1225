// Task edit page - reuses TaskCreateModal in edit mode
import { Navigate, useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, Skeleton, Alert, message } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useTask, useUpdateTask } from '@/hooks/useTask';
import { TaskEditForm } from './TaskEditForm';

const TaskEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation('tasks');
  const taskId = id && id !== 'create' ? id : '';
  const hasValidId = Boolean(taskId);

  const { data: task, isLoading, error } = useTask(taskId, { enabled: hasValidId });
  const updateTask = useUpdateTask();

  // Redirect if ID is invalid (e.g., "create")
  if (!hasValidId) {
    return <Navigate to="/tasks" replace />;
  }

  const handleSave = async (values: any) => {
    if (!taskId) return;
    
    try {
      await updateTask.mutateAsync({ id: taskId, payload: values });
      message.success(t('taskUpdated'));
      navigate(`/tasks/${taskId}`);
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

  if (error || !task) {
    return (
      <Alert
        type="error"
        message={t('failedToLoadTask')}
        description={error?.message || t('failedToLoadTaskDescription')}
        showIcon
        action={
          <Button type="primary" onClick={() => navigate('/tasks')}>
            {t('backToTasks')}
          </Button>
        }
      />
    );
  }

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/tasks/${taskId}`)}>
            {t('backToDetail')}
          </Button>
        </Space>
        <h2 style={{ marginTop: 16, marginBottom: 0 }}>{t('editTask')}: {task.name}</h2>
      </Card>

      <Card>
        <TaskEditForm
          initialValues={task}
          onSubmit={handleSave}
          onCancel={() => navigate(`/tasks/${taskId}`)}
          loading={updateTask.isPending}
        />
      </Card>
    </div>
  );
};

export default TaskEditPage;
