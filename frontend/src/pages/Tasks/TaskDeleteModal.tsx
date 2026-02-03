/**
 * TaskDeleteModal - Enhanced delete functionality for tasks
 * 
 * Features:
 * - Confirmation dialog with task details and impact
 * - Option to delete associated Label Studio project
 * - Progress indicator for batch deletes
 * - Error handling and partial success reporting
 * - Soft delete support
 */
import React, { useState, useCallback, useMemo } from 'react';
import {
  Modal,
  Checkbox,
  Progress,
  Alert,
  Space,
  Typography,
  List,
  Tag,
  Divider,
  Button,
  Result,
} from 'antd';
import {
  ExclamationCircleOutlined,
  DeleteOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  FileOutlined,
  CloudOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@/services';
import { API_ENDPOINTS } from '@/constants';
import type { Task } from '@/types';

const { Text, Title } = Typography;

export interface DeleteOptions {
  deleteLabelStudioProject: boolean;
  softDelete: boolean;
}

export interface DeleteProgress {
  current: number;
  total: number;
  status: 'idle' | 'deleting' | 'completed' | 'error';
  message: string;
  failedTasks: Array<{ id: string; name: string; error: string }>;
  successCount: number;
}

export interface TaskDeleteModalProps {
  open: boolean;
  tasks: Task[];
  onCancel: () => void;
  onSuccess: (deletedIds: string[]) => void;
}

export const TaskDeleteModal: React.FC<TaskDeleteModalProps> = ({
  open,
  tasks,
  onCancel,
  onSuccess,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  
  const [options, setOptions] = useState<DeleteOptions>({
    deleteLabelStudioProject: false,
    softDelete: false,
  });
  
  const [progress, setProgress] = useState<DeleteProgress>({
    current: 0,
    total: 0,
    status: 'idle',
    message: '',
    failedTasks: [],
    successCount: 0,
  });

  const isBatchDelete = tasks.length > 1;
  const hasLabelStudioProjects = useMemo(
    () => tasks.some(task => task.label_studio_project_id),
    [tasks]
  );

  // Calculate delete impact
  const deleteImpact = useMemo(() => {
    const totalItems = tasks.reduce((sum, task) => sum + (task.total_items || 0), 0);
    const completedItems = tasks.reduce((sum, task) => sum + (task.completed_items || 0), 0);
    const projectCount = tasks.filter(task => task.label_studio_project_id).length;
    
    return {
      taskCount: tasks.length,
      totalItems,
      completedItems,
      projectCount,
    };
  }, [tasks]);

  // Delete a single Label Studio project
  const deleteLabelStudioProject = useCallback(async (projectId: string): Promise<void> => {
    try {
      await apiClient.delete(API_ENDPOINTS.LABEL_STUDIO.PROJECT_BY_ID(projectId));
    } catch (error) {
      console.error(`Failed to delete Label Studio project ${projectId}:`, error);
      throw error;
    }
  }, []);

  // Delete a single task
  const deleteTask = useCallback(async (
    task: Task,
    deleteProject: boolean
  ): Promise<void> => {
    // Delete Label Studio project first if requested
    if (deleteProject && task.label_studio_project_id) {
      await deleteLabelStudioProject(task.label_studio_project_id);
    }
    
    // Delete the task
    await apiClient.delete(API_ENDPOINTS.TASKS.BY_ID(task.id));
  }, [deleteLabelStudioProject]);

  // Handle delete confirmation
  const handleDelete = useCallback(async () => {
    const total = tasks.length;
    const deletedIds: string[] = [];
    const failedTasks: Array<{ id: string; name: string; error: string }> = [];
    
    setProgress({
      current: 0,
      total,
      status: 'deleting',
      message: t('tasks.delete.progress.deleting'),
      failedTasks: [],
      successCount: 0,
    });

    for (let i = 0; i < tasks.length; i++) {
      const task = tasks[i];
      
      setProgress(prev => ({
        ...prev,
        current: i + 1,
        message: isBatchDelete
          ? t('tasks.delete.progress.deletingTask', { current: i + 1, total })
          : t('tasks.delete.progress.deleting'),
      }));

      try {
        await deleteTask(task, options.deleteLabelStudioProject);
        deletedIds.push(task.id);
      } catch (error) {
        const errorMessage = error instanceof Error 
          ? error.message 
          : (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail 
            || t('tasks.delete.result.failed');
        
        failedTasks.push({
          id: task.id,
          name: task.name,
          error: errorMessage,
        });
        console.error(`Failed to delete task ${task.id}:`, error);
      }
    }

    // Update final progress
    const hasFailures = failedTasks.length > 0;
    const allFailed = failedTasks.length === tasks.length;
    
    setProgress({
      current: total,
      total,
      status: allFailed ? 'error' : 'completed',
      message: hasFailures
        ? t('tasks.delete.result.partialSuccess', { 
            success: deletedIds.length, 
            failed: failedTasks.length 
          })
        : t('tasks.delete.result.success', { count: deletedIds.length }),
      failedTasks,
      successCount: deletedIds.length,
    });

    // Call onSuccess after a short delay to show the result
    if (deletedIds.length > 0) {
      setTimeout(() => {
        onSuccess(deletedIds);
      }, 1500);
    }
  }, [tasks, options, deleteTask, isBatchDelete, t, onSuccess]);

  // Reset state when modal closes
  const handleCancel = useCallback(() => {
    if (progress.status !== 'deleting') {
      setProgress({
        current: 0,
        total: 0,
        status: 'idle',
        message: '',
        failedTasks: [],
        successCount: 0,
      });
      setOptions({
        deleteLabelStudioProject: false,
        softDelete: false,
      });
      onCancel();
    }
  }, [progress.status, onCancel]);

  // Render confirmation content
  const renderConfirmContent = () => (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Warning Alert */}
      <Alert
        type="warning"
        icon={<WarningOutlined />}
        message={t('tasks.delete.warning')}
        showIcon
      />

      {/* Task Info */}
      {!isBatchDelete && tasks[0] && (
        <div>
          <Text strong>{t('taskName')}: </Text>
          <Text>{tasks[0].name}</Text>
          {tasks[0].label_studio_project_id && (
            <Tag color="blue" style={{ marginLeft: 8 }}>
              <CloudOutlined /> Label Studio
            </Tag>
          )}
        </div>
      )}

      {/* Batch Delete Info */}
      {isBatchDelete && (
        <div>
          <Text strong>{t('tasks.delete.batchConfirmMessage', { count: tasks.length })}</Text>
        </div>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* Delete Impact */}
      <div>
        <Title level={5} style={{ marginBottom: 8 }}>
          <ExclamationCircleOutlined style={{ color: '#faad14', marginRight: 8 }} />
          {t('tasks.delete.impact.title')}
        </Title>
        <List
          size="small"
          dataSource={[
            {
              icon: <DatabaseOutlined />,
              text: t('tasks.delete.impact.taskInfo'),
              detail: `${deleteImpact.taskCount} ${t('tasks.export.tasks')}`,
            },
            {
              icon: <FileOutlined />,
              text: t('tasks.delete.impact.annotationData'),
              detail: `${deleteImpact.completedItems} / ${deleteImpact.totalItems}`,
            },
            ...(deleteImpact.projectCount > 0 ? [{
              icon: <CloudOutlined />,
              text: t('tasks.delete.impact.labelStudioProject'),
              detail: `${deleteImpact.projectCount} ${t('tasks.export.tasks')}`,
            }] : []),
          ]}
          renderItem={(item) => (
            <List.Item style={{ padding: '4px 0' }}>
              <Space>
                {item.icon}
                <Text>{item.text}</Text>
                <Text type="secondary">({item.detail})</Text>
              </Space>
            </List.Item>
          )}
        />
      </div>

      <Divider style={{ margin: '12px 0' }} />

      {/* Delete Options */}
      <Space direction="vertical" size="small">
        {hasLabelStudioProjects && (
          <Checkbox
            checked={options.deleteLabelStudioProject}
            onChange={(e) => setOptions(prev => ({
              ...prev,
              deleteLabelStudioProject: e.target.checked,
            }))}
          >
            <Space>
              <Text>{t('tasks.delete.options.deleteLabelStudioProject')}</Text>
            </Space>
          </Checkbox>
        )}
        {hasLabelStudioProjects && options.deleteLabelStudioProject && (
          <Alert
            type="error"
            message={t('tasks.delete.options.deleteLabelStudioProjectTip')}
            style={{ marginLeft: 24 }}
            showIcon
          />
        )}
      </Space>
    </Space>
  );

  // Render progress content
  const renderProgressContent = () => (
    <div style={{ textAlign: 'center', padding: '20px 0' }}>
      <Progress
        type="circle"
        percent={Math.round((progress.current / progress.total) * 100)}
        status={
          progress.status === 'error' ? 'exception' :
          progress.status === 'completed' ? 'success' : 'active'
        }
        format={() => `${progress.current}/${progress.total}`}
      />
      <p style={{ marginTop: 16, color: '#666' }}>
        {progress.message}
      </p>
    </div>
  );

  // Render result content
  const renderResultContent = () => (
    <Result
      status={progress.failedTasks.length === 0 ? 'success' : 'warning'}
      icon={progress.failedTasks.length === 0 
        ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
        : <WarningOutlined style={{ color: '#faad14' }} />
      }
      title={progress.status === 'completed' 
        ? t('tasks.delete.progress.completed')
        : t('tasks.delete.progress.failed')
      }
      subTitle={progress.message}
      extra={
        progress.failedTasks.length > 0 && (
          <div style={{ textAlign: 'left', maxHeight: 200, overflow: 'auto' }}>
            <Text strong>{t('tasks.delete.result.failedTasks')}</Text>
            <List
              size="small"
              dataSource={progress.failedTasks}
              renderItem={(item) => (
                <List.Item>
                  <Space>
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    <Text>{item.name}</Text>
                    <Text type="secondary">- {item.error}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </div>
        )
      }
    />
  );

  // Determine what to render based on progress status
  const renderContent = () => {
    switch (progress.status) {
      case 'deleting':
        return renderProgressContent();
      case 'completed':
      case 'error':
        return renderResultContent();
      default:
        return renderConfirmContent();
    }
  };

  // Determine footer buttons
  const renderFooter = () => {
    if (progress.status === 'deleting') {
      return null; // No buttons while deleting
    }
    
    if (progress.status === 'completed' || progress.status === 'error') {
      return (
        <Button type="primary" onClick={handleCancel}>
          {t('close')}
        </Button>
      );
    }
    
    return (
      <Space>
        <Button onClick={handleCancel}>
          {t('tasks.delete.buttons.cancel')}
        </Button>
        <Button 
          type="primary" 
          danger 
          icon={<DeleteOutlined />}
          onClick={handleDelete}
        >
          {t('tasks.delete.buttons.confirm')}
        </Button>
      </Space>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <DeleteOutlined style={{ color: '#ff4d4f' }} />
          {isBatchDelete 
            ? t('tasks.delete.batchTitle')
            : t('tasks.delete.title')
          }
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      footer={renderFooter()}
      closable={progress.status !== 'deleting'}
      maskClosable={progress.status !== 'deleting'}
      width={500}
    >
      {renderContent()}
    </Modal>
  );
};

export default TaskDeleteModal;
