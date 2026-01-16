/**
 * Improvement Task List Component - 改进任务列表组件
 * 实现改进任务的列表展示和管理
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Badge,
  Select,
  Input,
  message,
  Tooltip,
  Row,
  Col,
  Statistic,
  Progress,
  Avatar,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  UserOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { workflowApi, type ImprovementTask, type TaskListParams } from '@/services/workflowApi';

const { Option } = Select;
const { Search } = Input;

interface ImprovementTaskListProps {
  projectId?: string;
  assigneeId?: string;
}

const ImprovementTaskList: React.FC<ImprovementTaskListProps> = ({ projectId, assigneeId }) => {
  const navigate = useNavigate();
  const { t } = useTranslation(['quality', 'common']);
  const [tasks, setTasks] = useState<ImprovementTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<TaskListParams>({
    project_id: projectId,
    assignee_id: assigneeId,
    page: 1,
    page_size: 10,
  });

  useEffect(() => {
    loadTasks();
  }, [filters]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const response = await workflowApi.listTasks(filters);
      setTasks(response.items);
      setTotal(response.total);
    } catch {
      message.error(t('improvementTask.loadError'));
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = (taskId: string) => {
    navigate(`/quality/workflow/tasks/${taskId}`);
  };

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: t('improvementTask.status.pending') },
      in_progress: { color: 'processing', icon: <SyncOutlined spin />, text: t('improvementTask.status.inProgress') },
      submitted: { color: 'warning', icon: <ExclamationCircleOutlined />, text: t('improvementTask.status.submitted') },
      approved: { color: 'success', icon: <CheckCircleOutlined />, text: t('improvementTask.status.approved') },
      rejected: { color: 'error', icon: <ExclamationCircleOutlined />, text: t('improvementTask.status.rejected') },
    };
    return configs[status] || { color: 'default', icon: null, text: status };
  };

  const getPriorityConfig = (priority: number) => {
    if (priority >= 3) return { color: 'red', text: t('improvementTask.priority.highShort') };
    if (priority >= 2) return { color: 'orange', text: t('improvementTask.priority.mediumShort') };
    return { color: 'blue', text: t('improvementTask.priority.lowShort') };
  };

  const columns: ColumnsType<ImprovementTask> = [
    {
      title: t('improvementTask.columns.taskId'),
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => (
        <Tooltip title={id}>
          <span style={{ fontFamily: 'monospace' }}>{id.slice(0, 8)}...</span>
        </Tooltip>
      ),
    },
    {
      title: t('improvementTask.columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: number) => {
        const config = getPriorityConfig(priority);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
      sorter: (a, b) => b.priority - a.priority,
    },
    {
      title: t('improvementTask.columns.issueCount'),
      dataIndex: 'issues',
      key: 'issues',
      width: 80,
      render: (issues: unknown[]) => (
        <Badge count={issues.length} style={{ backgroundColor: issues.length > 3 ? '#f5222d' : '#faad14' }} />
      ),
    },
    {
      title: t('improvementTask.columns.assignee'),
      dataIndex: 'assignee_name',
      key: 'assignee_name',
      width: 120,
      render: (name: string) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          {name || t('improvementTask.unassigned')}
        </Space>
      ),
    },
    {
      title: t('improvementTask.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = getStatusConfig(status);
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.text}
          </Tag>
        );
      },
      filters: [
        { text: t('improvementTask.status.pending'), value: 'pending' },
        { text: t('improvementTask.status.inProgress'), value: 'in_progress' },
        { text: t('improvementTask.status.submitted'), value: 'submitted' },
        { text: t('improvementTask.status.approved'), value: 'approved' },
        { text: t('improvementTask.status.rejected'), value: 'rejected' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: t('improvementTask.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: t('improvementTask.columns.submittedAt'),
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 170,
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: t('improvementTask.columns.actions'),
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleViewDetail(record.id)}>
            {t('improvementTask.viewDetail')}
          </Button>
        </Space>
      ),
    },
  ];

  // 统计数据
  const stats = {
    total: total,
    pending: tasks.filter((t) => t.status === 'pending').length,
    inProgress: tasks.filter((t) => t.status === 'in_progress').length,
    submitted: tasks.filter((t) => t.status === 'submitted').length,
    completed: tasks.filter((t) => t.status === 'approved').length,
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('improvementTask.stats.total')} value={stats.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('improvementTask.stats.pending')} value={stats.pending} valueStyle={{ color: stats.pending > 0 ? '#faad14' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('improvementTask.stats.submitted')} value={stats.submitted} valueStyle={{ color: stats.submitted > 0 ? '#1890ff' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('improvementTask.stats.completionRate')} value={stats.total > 0 ? ((stats.completed / stats.total) * 100).toFixed(1) : 0} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Card
        title={t('improvementTask.title')}
        extra={
          <Space>
            <Search placeholder={t('improvementTask.searchPlaceholder')} style={{ width: 200 }} onSearch={(v) => setFilters({ ...filters, page: 1 })} />
            <Select
              value={filters.status}
              onChange={(v) => setFilters({ ...filters, status: v, page: 1 })}
              style={{ width: 120 }}
              allowClear
              placeholder={t('improvementTask.filters.status')}
            >
              <Option value="pending">{t('improvementTask.status.pending')}</Option>
              <Option value="in_progress">{t('improvementTask.status.inProgress')}</Option>
              <Option value="submitted">{t('improvementTask.status.submitted')}</Option>
              <Option value="approved">{t('improvementTask.status.approved')}</Option>
              <Option value="rejected">{t('improvementTask.status.rejected')}</Option>
            </Select>
            <Select
              value={filters.priority}
              onChange={(v) => setFilters({ ...filters, priority: v, page: 1 })}
              style={{ width: 120 }}
              allowClear
              placeholder={t('improvementTask.filters.priority')}
            >
              <Option value={3}>{t('improvementTask.priority.high')}</Option>
              <Option value={2}>{t('improvementTask.priority.medium')}</Option>
              <Option value={1}>{t('improvementTask.priority.low')}</Option>
            </Select>
          </Space>
        }
      >
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: filters.page,
            pageSize: filters.page_size,
            total: total,
            onChange: (page, pageSize) => setFilters({ ...filters, page, page_size: pageSize }),
            showSizeChanger: true,
            showTotal: (total) => t('improvementTask.total', { total }),
          }}
        />
      </Card>
    </div>
  );
};

export default ImprovementTaskList;
