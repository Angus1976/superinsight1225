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
  
  // Redirect if ID is invalid (e.g., "create")
  if (id === 'create' || !id) {
    navigate('/tasks', { replace: true });
    return null;
  }
  
  const { data: task, isLoading, error } = useTask(id);
  const updateTask = useUpdateTask();

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
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/tasks/${id}`)}>
            {t('backToDetail')}
          </Button>
        </Space>
        <h2 style={{ marginTop: 16, marginBottom: 0 }}>{t('editTask')}: {task.name}</h2>
      </Card>

      <Card>
        <TaskEditForm
          initialValues={task}
          onSubmit={handleSave}
          onCancel={() => navigate(`/tasks/${id}`)}
          loading={updateTask.isPending}
        />
      </Card>
    </div>
  );
};

export default TaskEditPage;
