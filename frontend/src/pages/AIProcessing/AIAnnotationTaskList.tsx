/**
 * AI Annotation Task List
 * 
 * AI 智能标注任务清单组件
 * 显示多个标注任务及其各自的进度
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Table,
  Space,
  Typography,
  Button,
  Tag,
  Progress,
  Tooltip,
  Modal,
  message,
  Dropdown,
  Menu,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  MoreOutlined,
  PlusOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import TransferToLifecycleModal, { TransferDataItem } from '@/components/DataLifecycle/TransferToLifecycleModal';

const { Title, Text } = Typography;

interface AnnotationTask {
  id: string;
  name: string;
  project_id: string;
  data_source_id: string;
  annotation_type: string;
  status: 'pending' | 'learning' | 'annotating' | 'validating' | 'completed' | 'failed' | 'paused';
  progress: {
    current_step: 'data-source' | 'samples' | 'learning' | 'annotation' | 'validation';
    sample_count: number;
    annotated_count: number;
    total_count: number;
    average_confidence: number;
  };
  learning_job_id?: string;
  batch_job_id?: string;
  created_at: string;
  updated_at: string;
}

const AIAnnotationTaskList: React.FC = () => {
  const { t } = useTranslation('aiAnnotation');
  const [tasks, setTasks] = useState<AnnotationTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AnnotationTask | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [transferModalVisible, setTransferModalVisible] = useState(false);
  const [taskToTransfer, setTaskToTransfer] = useState<AnnotationTask | null>(null);

  useEffect(() => {
    loadTasks();
    // 每 5 秒刷新一次任务列表
    const interval = setInterval(loadTasks, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadTasks = async () => {
    try {
      // 模拟 API 调用
      // const response = await fetch('/api/v1/annotation/workflow/tasks');
      // const data = await response.json();
      
      // 使用模拟数据
      const mockTasks: AnnotationTask[] = [
        {
          id: 'task_1',
          name: '客户反馈实体标注',
          project_id: 'proj_1',
          data_source_id: 'ds_1',
          annotation_type: 'entity',
          status: 'annotating',
          progress: {
            current_step: 'annotation',
            sample_count: 15,
            annotated_count: 450,
            total_count: 1000,
            average_confidence: 0.82,
          },
          learning_job_id: 'learn_1',
          batch_job_id: 'batch_1',
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-02T15:30:00Z',
        },
        {
          id: 'task_2',
          name: '产品评论情感分析',
          project_id: 'proj_1',
          data_source_id: 'ds_2',
          annotation_type: 'classification',
          status: 'learning',
          progress: {
            current_step: 'learning',
            sample_count: 20,
            annotated_count: 0,
            total_count: 1500,
            average_confidence: 0.0,
          },
          learning_job_id: 'learn_2',
          created_at: '2026-03-02T09:00:00Z',
          updated_at: '2026-03-02T15:45:00Z',
        },
        {
          id: 'task_3',
          name: '合同关键信息提取',
          project_id: 'proj_2',
          data_source_id: 'ds_3',
          annotation_type: 'entity',
          status: 'completed',
          progress: {
            current_step: 'validation',
            sample_count: 25,
            annotated_count: 800,
            total_count: 800,
            average_confidence: 0.88,
          },
          learning_job_id: 'learn_3',
          batch_job_id: 'batch_3',
          created_at: '2026-02-28T14:00:00Z',
          updated_at: '2026-03-01T18:20:00Z',
        },
        {
          id: 'task_4',
          name: '新闻分类标注',
          project_id: 'proj_1',
          data_source_id: 'ds_4',
          annotation_type: 'classification',
          status: 'pending',
          progress: {
            current_step: 'data-source',
            sample_count: 0,
            annotated_count: 0,
            total_count: 2000,
            average_confidence: 0.0,
          },
          created_at: '2026-03-02T16:00:00Z',
          updated_at: '2026-03-02T16:00:00Z',
        },
      ];
      
      setTasks(mockTasks);
    } catch (error) {
      console.error('加载任务列表失败', error);
    }
  };

  const getStatusConfig = (status: AnnotationTask['status']) => {
    const configs = {
      pending: { color: 'default', text: t('task_list.status.pending') },
      learning: { color: 'processing', text: t('task_list.status.learning') },
      annotating: { color: 'processing', text: t('task_list.status.annotating') },
      validating: { color: 'processing', text: t('task_list.status.validating') },
      completed: { color: 'success', text: t('task_list.status.completed') },
      failed: { color: 'error', text: t('task_list.status.failed') },
      paused: { color: 'warning', text: t('task_list.status.paused') },
    };
    return configs[status];
  };

  const getStepText = (step: AnnotationTask['progress']['current_step']) => {
    const steps = {
      'data-source': t('workflow.steps.data_source'),
      'samples': t('workflow.steps.samples'),
      'learning': t('workflow.steps.learning'),
      'annotation': t('workflow.steps.annotation'),
      'validation': t('workflow.steps.validation'),
    };
    return steps[step];
  };

  const handleViewDetail = (task: AnnotationTask) => {
    setSelectedTask(task);
    setDetailModalVisible(true);
  };

  const handleStartTask = async (taskId: string) => {
    try {
      setLoading(true);
      // 调用 API 启动任务
      message.success(t('task_list.task_started'));
      await loadTasks();
    } catch (error) {
      message.error(t('task_list.task_start_failed'));
    } finally {
      setLoading(false);
    }
  };

  const handlePauseTask = async (taskId: string) => {
    try {
      setLoading(true);
      // 调用 API 暂停任务
      message.success(t('task_list.task_paused'));
      await loadTasks();
    } catch (error) {
      message.error(t('task_list.task_pause_failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    Modal.confirm({
      title: t('task_list.confirm_delete_title'),
      content: t('task_list.confirm_delete_content'),
      okText: t('task_list.delete_ok'),
      okType: 'danger',
      cancelText: t('task_list.delete_cancel'),
      onOk: async () => {
        try {
          setLoading(true);
          // 调用 API 删除任务
          message.success(t('task_list.task_deleted'));
          await loadTasks();
        } catch (error) {
          message.error(t('task_list.task_delete_failed'));
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const handleTransferToLifecycle = (task: AnnotationTask) => {
    setTaskToTransfer(task);
    setTransferModalVisible(true);
  };

  const handleTransferSuccess = () => {
    message.success(t('transfer.messages.success'));
    setTransferModalVisible(false);
    setTaskToTransfer(null);
  };

  const handleTransferClose = () => {
    setTransferModalVisible(false);
    setTaskToTransfer(null);
  };

  // Convert task to transfer data format
  const getTransferData = (task: AnnotationTask): TransferDataItem[] => {
    return [{
      id: task.id,
      name: task.name,
      content: {
        annotationType: task.annotation_type,
        progress: task.progress,
        learningJobId: task.learning_job_id,
        batchJobId: task.batch_job_id,
      },
      metadata: {
        projectId: task.project_id,
        dataSourceId: task.data_source_id,
        status: task.status,
        annotatedCount: task.progress.annotated_count,
        totalCount: task.progress.total_count,
        averageConfidence: task.progress.average_confidence,
        createdAt: task.created_at,
        updatedAt: task.updated_at,
      },
    }];
  };

  const getActionMenu = (task: AnnotationTask) => (
    <Menu>
      <Menu.Item
        key="view"
        icon={<EyeOutlined />}
        onClick={() => handleViewDetail(task)}
      >
        {t('task_list.view_detail')}
      </Menu.Item>
      {(task.status === 'pending' || task.status === 'paused') && (
        <Menu.Item
          key="start"
          icon={<PlayCircleOutlined />}
          onClick={() => handleStartTask(task.id)}
        >
          {t('task_list.start_task')}
        </Menu.Item>
      )}
      {(task.status === 'learning' || task.status === 'annotating') && (
        <Menu.Item
          key="pause"
          icon={<PauseCircleOutlined />}
          onClick={() => handlePauseTask(task.id)}
        >
          {t('task_list.pause_task')}
        </Menu.Item>
      )}
      <Menu.Divider />
      <Menu.Item
        key="delete"
        icon={<DeleteOutlined />}
        danger
        onClick={() => handleDeleteTask(task.id)}
      >
        {t('task_list.delete_task')}
      </Menu.Item>
    </Menu>
  );

  const columns: ColumnsType<AnnotationTask> = [
    {
      title: t('task_list.columns.task_name'),
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string, record: AnnotationTask) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.annotation_type === 'entity' ? t('task_list.annotation_types.entity') : t('task_list.annotation_types.classification')}
          </Text>
        </Space>
      ),
    },
    {
      title: t('task_list.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: AnnotationTask['status']) => {
        const config = getStatusConfig(status);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: t('task_list.columns.current_step'),
      dataIndex: ['progress', 'current_step'],
      key: 'current_step',
      width: 120,
      render: (step: AnnotationTask['progress']['current_step']) => (
        <Text>{getStepText(step)}</Text>
      ),
    },
    {
      title: t('task_list.columns.annotation_progress'),
      key: 'progress',
      width: 250,
      render: (_, record: AnnotationTask) => {
        const { annotated_count, total_count, average_confidence } = record.progress;
        const percent = total_count > 0 ? (annotated_count / total_count) * 100 : 0;
        
        return (
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Progress
              percent={Math.round(percent)}
              size="small"
              status={record.status === 'completed' ? 'success' : 'active'}
              showInfo={false}
            />
            <Space size={16}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {annotated_count} / {total_count}
              </Text>
              {average_confidence > 0 && (
                <Tooltip title={t('task_list.avg_confidence')}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {t('task_list.confidence')}: {(average_confidence * 100).toFixed(0)}%
                  </Text>
                </Tooltip>
              )}
            </Space>
          </Space>
        );
      },
    },
    {
      title: t('task_list.columns.sample_count'),
      dataIndex: ['progress', 'sample_count'],
      key: 'sample_count',
      width: 100,
      render: (count: number) => <Text>{count}</Text>,
    },
    {
      title: t('task_list.columns.updated_at'),
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (time: string) => (
        <Text type="secondary">
          {new Date(time).toLocaleString()}
        </Text>
      ),
    },
    {
      title: t('task_list.columns.actions'),
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record: AnnotationTask) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            {t('task_list.detail')}
          </Button>
          <Dropdown overlay={getActionMenu(record)} trigger={['click']}>
            <Button type="text" size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={5} style={{ margin: 0 }}>{t('task_list.title')}</Title>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadTasks}
                loading={loading}
              >
                {t('task_list.refresh')}
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => message.info(t('task_list.create_task_wip'))}
              >
                {t('task_list.create_task')}
              </Button>
            </Space>
          </div>

          <Table
            columns={columns}
            dataSource={tasks}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => t('task_list.total_tasks', { total }),
            }}
            scroll={{ x: 1200 }}
          />
        </Space>
      </Card>

      {/* 任务详情弹窗 */}
      <Modal
        title={t('task_list.modal.title')}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          selectedTask?.status === 'completed' ? (
            <Button 
              key="transfer" 
              type="primary"
              icon={<ExportOutlined />}
              onClick={() => {
                if (selectedTask) {
                  handleTransferToLifecycle(selectedTask);
                  setDetailModalVisible(false);
                }
              }}
            >
              {t('transfer.button')}
            </Button>
          ) : null,
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            {t('task_list.modal.close')}
          </Button>,
        ].filter(Boolean)}
        width={700}
      >
        {selectedTask && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>{t('task_list.modal.task_name')}</Text>
              <Text>{selectedTask.name}</Text>
            </div>
            <div>
              <Text strong>{t('task_list.modal.annotation_type')}</Text>
              <Text>{selectedTask.annotation_type === 'entity' ? t('task_list.annotation_types.entity') : t('task_list.annotation_types.classification')}</Text>
            </div>
            <div>
              <Text strong>{t('task_list.modal.status')}</Text>
              <Tag color={getStatusConfig(selectedTask.status).color}>
                {getStatusConfig(selectedTask.status).text}
              </Tag>
            </div>
            <div>
              <Text strong>{t('task_list.modal.current_step')}</Text>
              <Text>{getStepText(selectedTask.progress.current_step)}</Text>
            </div>
            <div>
              <Text strong>{t('task_list.modal.sample_count')}</Text>
              <Text>{selectedTask.progress.sample_count}</Text>
            </div>
            <div>
              <Text strong>{t('task_list.modal.annotation_progress')}</Text>
              <Text>
                {selectedTask.progress.annotated_count} / {selectedTask.progress.total_count}
                {' '}({Math.round((selectedTask.progress.annotated_count / selectedTask.progress.total_count) * 100)}%)
              </Text>
            </div>
            {selectedTask.progress.average_confidence > 0 && (
              <div>
                <Text strong>{t('task_list.modal.avg_confidence')}</Text>
                <Text>{(selectedTask.progress.average_confidence * 100).toFixed(1)}%</Text>
              </div>
            )}
            {selectedTask.learning_job_id && (
              <div>
                <Text strong>{t('task_list.modal.learning_job_id')}</Text>
                <Text type="secondary">{selectedTask.learning_job_id}</Text>
              </div>
            )}
            {selectedTask.batch_job_id && (
              <div>
                <Text strong>{t('task_list.modal.batch_job_id')}</Text>
                <Text type="secondary">{selectedTask.batch_job_id}</Text>
              </div>
            )}
            <div>
              <Text strong>{t('task_list.modal.created_at')}</Text>
              <Text>{new Date(selectedTask.created_at).toLocaleString()}</Text>
            </div>
            <div>
              <Text strong>{t('task_list.modal.updated_at')}</Text>
              <Text>{new Date(selectedTask.updated_at).toLocaleString()}</Text>
            </div>
          </Space>
        )}
      </Modal>

      {/* Transfer to Lifecycle Modal */}
      {taskToTransfer && (
        <TransferToLifecycleModal
          visible={transferModalVisible}
          onClose={handleTransferClose}
          onSuccess={handleTransferSuccess}
          sourceType="ai_annotation"
          selectedData={getTransferData(taskToTransfer)}
        />
      )}
    </Space>
  );
};

export default AIAnnotationTaskList;
