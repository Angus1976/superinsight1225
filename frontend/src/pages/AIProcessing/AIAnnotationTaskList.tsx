/**
 * AI Annotation Task List
 * 
 * AI 智能标注任务清单组件
 * 显示多个标注任务及其各自的进度
 */

import React, { useState, useEffect } from 'react';
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
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

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
  const [tasks, setTasks] = useState<AnnotationTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AnnotationTask | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

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
      pending: { color: 'default', text: '待开始' },
      learning: { color: 'processing', text: 'AI 学习中' },
      annotating: { color: 'processing', text: '批量标注中' },
      validating: { color: 'processing', text: '效果验证中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      paused: { color: 'warning', text: '已暂停' },
    };
    return configs[status];
  };

  const getStepText = (step: AnnotationTask['progress']['current_step']) => {
    const steps = {
      'data-source': '数据来源',
      'samples': '人工样本',
      'learning': 'AI 学习',
      'annotation': '批量标注',
      'validation': '效果验证',
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
      message.success('任务已启动');
      await loadTasks();
    } catch (error) {
      message.error('启动任务失败');
    } finally {
      setLoading(false);
    }
  };

  const handlePauseTask = async (taskId: string) => {
    try {
      setLoading(true);
      // 调用 API 暂停任务
      message.success('任务已暂停');
      await loadTasks();
    } catch (error) {
      message.error('暂停任务失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个标注任务吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          setLoading(true);
          // 调用 API 删除任务
          message.success('任务已删除');
          await loadTasks();
        } catch (error) {
          message.error('删除任务失败');
        } finally {
          setLoading(false);
        }
      },
    });
  };

  const getActionMenu = (task: AnnotationTask) => (
    <Menu>
      <Menu.Item
        key="view"
        icon={<EyeOutlined />}
        onClick={() => handleViewDetail(task)}
      >
        查看详情
      </Menu.Item>
      {(task.status === 'pending' || task.status === 'paused') && (
        <Menu.Item
          key="start"
          icon={<PlayCircleOutlined />}
          onClick={() => handleStartTask(task.id)}
        >
          启动任务
        </Menu.Item>
      )}
      {(task.status === 'learning' || task.status === 'annotating') && (
        <Menu.Item
          key="pause"
          icon={<PauseCircleOutlined />}
          onClick={() => handlePauseTask(task.id)}
        >
          暂停任务
        </Menu.Item>
      )}
      <Menu.Divider />
      <Menu.Item
        key="delete"
        icon={<DeleteOutlined />}
        danger
        onClick={() => handleDeleteTask(task.id)}
      >
        删除任务
      </Menu.Item>
    </Menu>
  );

  const columns: ColumnsType<AnnotationTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string, record: AnnotationTask) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.annotation_type === 'entity' ? '实体标注' : '分类标注'}
          </Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: AnnotationTask['status']) => {
        const config = getStatusConfig(status);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '当前步骤',
      dataIndex: ['progress', 'current_step'],
      key: 'current_step',
      width: 120,
      render: (step: AnnotationTask['progress']['current_step']) => (
        <Text>{getStepText(step)}</Text>
      ),
    },
    {
      title: '标注进度',
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
                <Tooltip title="平均置信度">
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    置信度: {(average_confidence * 100).toFixed(0)}%
                  </Text>
                </Tooltip>
              )}
            </Space>
          </Space>
        );
      },
    },
    {
      title: '样本数',
      dataIndex: ['progress', 'sample_count'],
      key: 'sample_count',
      width: 100,
      render: (count: number) => <Text>{count}</Text>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (time: string) => (
        <Text type="secondary">
          {new Date(time).toLocaleString('zh-CN')}
        </Text>
      ),
    },
    {
      title: '操作',
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
            详情
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
            <Title level={5} style={{ margin: 0 }}>AI 智能标注任务清单</Title>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadTasks}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => message.info('创建新任务功能开发中')}
              >
                创建任务
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
              showTotal: (total) => `共 ${total} 个任务`,
            }}
            scroll={{ x: 1200 }}
          />
        </Space>
      </Card>

      {/* 任务详情弹窗 */}
      <Modal
        title="任务详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {selectedTask && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>任务名称：</Text>
              <Text>{selectedTask.name}</Text>
            </div>
            <div>
              <Text strong>标注类型：</Text>
              <Text>{selectedTask.annotation_type === 'entity' ? '实体标注' : '分类标注'}</Text>
            </div>
            <div>
              <Text strong>状态：</Text>
              <Tag color={getStatusConfig(selectedTask.status).color}>
                {getStatusConfig(selectedTask.status).text}
              </Tag>
            </div>
            <div>
              <Text strong>当前步骤：</Text>
              <Text>{getStepText(selectedTask.progress.current_step)}</Text>
            </div>
            <div>
              <Text strong>样本数量：</Text>
              <Text>{selectedTask.progress.sample_count}</Text>
            </div>
            <div>
              <Text strong>标注进度：</Text>
              <Text>
                {selectedTask.progress.annotated_count} / {selectedTask.progress.total_count}
                {' '}({Math.round((selectedTask.progress.annotated_count / selectedTask.progress.total_count) * 100)}%)
              </Text>
            </div>
            {selectedTask.progress.average_confidence > 0 && (
              <div>
                <Text strong>平均置信度：</Text>
                <Text>{(selectedTask.progress.average_confidence * 100).toFixed(1)}%</Text>
              </div>
            )}
            {selectedTask.learning_job_id && (
              <div>
                <Text strong>学习任务 ID：</Text>
                <Text type="secondary">{selectedTask.learning_job_id}</Text>
              </div>
            )}
            {selectedTask.batch_job_id && (
              <div>
                <Text strong>批量标注 ID：</Text>
                <Text type="secondary">{selectedTask.batch_job_id}</Text>
              </div>
            )}
            <div>
              <Text strong>创建时间：</Text>
              <Text>{new Date(selectedTask.created_at).toLocaleString('zh-CN')}</Text>
            </div>
            <div>
              <Text strong>更新时间：</Text>
              <Text>{new Date(selectedTask.updated_at).toLocaleString('zh-CN')}</Text>
            </div>
          </Space>
        )}
      </Modal>
    </Space>
  );
};

export default AIAnnotationTaskList;
