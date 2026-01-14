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
import { workflowApi, type ImprovementTask, type TaskListParams } from '@/services/workflowApi';

const { Option } = Select;
const { Search } = Input;

interface ImprovementTaskListProps {
  projectId?: string;
  assigneeId?: string;
}

const ImprovementTaskList: React.FC<ImprovementTaskListProps> = ({ projectId, assigneeId }) => {
  const navigate = useNavigate();
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
      message.error('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = (taskId: string) => {
    navigate(`/quality/workflow/tasks/${taskId}`);
  };

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待处理' },
      in_progress: { color: 'processing', icon: <SyncOutlined spin />, text: '进行中' },
      submitted: { color: 'warning', icon: <ExclamationCircleOutlined />, text: '待审核' },
      approved: { color: 'success', icon: <CheckCircleOutlined />, text: '已通过' },
      rejected: { color: 'error', icon: <ExclamationCircleOutlined />, text: '已拒绝' },
    };
    return configs[status] || { color: 'default', icon: null, text: status };
  };

  const getPriorityConfig = (priority: number) => {
    if (priority >= 3) return { color: 'red', text: '高' };
    if (priority >= 2) return { color: 'orange', text: '中' };
    return { color: 'blue', text: '低' };
  };

  const columns: ColumnsType<ImprovementTask> = [
    {
      title: '任务ID',
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
      title: '优先级',
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
      title: '问题数',
      dataIndex: 'issues',
      key: 'issues',
      width: 80,
      render: (issues: unknown[]) => (
        <Badge count={issues.length} style={{ backgroundColor: issues.length > 3 ? '#f5222d' : '#faad14' }} />
      ),
    },
    {
      title: '负责人',
      dataIndex: 'assignee_name',
      key: 'assignee_name',
      width: 120,
      render: (name: string) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          {name || '未分配'}
        </Space>
      ),
    },
    {
      title: '状态',
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
        { text: '待处理', value: 'pending' },
        { text: '进行中', value: 'in_progress' },
        { text: '待审核', value: 'submitted' },
        { text: '已通过', value: 'approved' },
        { text: '已拒绝', value: 'rejected' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (time: string) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '提交时间',
      dataIndex: 'submitted_at',
      key: 'submitted_at',
      width: 170,
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleViewDetail(record.id)}>
            查看详情
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
            <Statistic title="总任务数" value={stats.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="待处理" value={stats.pending} valueStyle={{ color: stats.pending > 0 ? '#faad14' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="待审核" value={stats.submitted} valueStyle={{ color: stats.submitted > 0 ? '#1890ff' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="完成率" value={stats.total > 0 ? ((stats.completed / stats.total) * 100).toFixed(1) : 0} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Card
        title="改进任务列表"
        extra={
          <Space>
            <Search placeholder="搜索任务" style={{ width: 200 }} onSearch={(v) => setFilters({ ...filters, page: 1 })} />
            <Select
              value={filters.status}
              onChange={(v) => setFilters({ ...filters, status: v, page: 1 })}
              style={{ width: 120 }}
              allowClear
              placeholder="状态筛选"
            >
              <Option value="pending">待处理</Option>
              <Option value="in_progress">进行中</Option>
              <Option value="submitted">待审核</Option>
              <Option value="approved">已通过</Option>
              <Option value="rejected">已拒绝</Option>
            </Select>
            <Select
              value={filters.priority}
              onChange={(v) => setFilters({ ...filters, priority: v, page: 1 })}
              style={{ width: 120 }}
              allowClear
              placeholder="优先级"
            >
              <Option value={3}>高优先级</Option>
              <Option value={2}>中优先级</Option>
              <Option value={1}>低优先级</Option>
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
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  );
};

export default ImprovementTaskList;
