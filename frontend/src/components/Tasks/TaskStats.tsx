// Task statistics and reporting component
import { useState, useCallback } from 'react';
import { Card, Row, Col, Statistic, Progress, Select, DatePicker, Space, Button, Table, message } from 'antd';
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  UserOutlined,
  TrophyOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;

interface TaskStatsData {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  pendingTasks: number;
  overdueTasks: number;
  avgCompletionTime: number;
  avgQualityScore: number;
  totalAnnotations: number;
}

interface UserPerformance {
  userId: string;
  userName: string;
  tasksCompleted: number;
  avgQualityScore: number;
  avgCompletionTime: number;
  efficiency: number;
}

interface TaskTrend {
  date: string;
  completed: number;
  created: number;
  inProgress: number;
}

interface TaskStatsProps {
  tenantId?: string;
  workspaceId?: string;
  showExport?: boolean;
}

export const TaskStats: React.FC<TaskStatsProps> = ({
  showExport = true,
}) => {
  const { t } = useTranslation(['tasks', 'dashboard']);
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(30, 'days'),
    dayjs(),
  ]);
  const [selectedUser, setSelectedUser] = useState<string>('all');

  // Mock data
  const statsData: TaskStatsData = {
    totalTasks: 156,
    completedTasks: 98,
    inProgressTasks: 42,
    pendingTasks: 12,
    overdueTasks: 4,
    avgCompletionTime: 4.5,
    avgQualityScore: 0.87,
    totalAnnotations: 15680,
  };

  const userPerformance: UserPerformance[] = [
    { userId: '1', userName: '张三', tasksCompleted: 28, avgQualityScore: 0.92, avgCompletionTime: 3.8, efficiency: 0.95 },
    { userId: '2', userName: '李四', tasksCompleted: 24, avgQualityScore: 0.88, avgCompletionTime: 4.2, efficiency: 0.88 },
    { userId: '3', userName: '王五', tasksCompleted: 22, avgQualityScore: 0.85, avgCompletionTime: 4.8, efficiency: 0.82 },
    { userId: '4', userName: '赵六', tasksCompleted: 18, avgQualityScore: 0.90, avgCompletionTime: 4.0, efficiency: 0.90 },
    { userId: '5', userName: '钱七', tasksCompleted: 6, avgQualityScore: 0.78, avgCompletionTime: 5.5, efficiency: 0.72 },
  ];

  const taskTrends: TaskTrend[] = Array.from({ length: 30 }, (_, i) => ({
    date: dayjs().subtract(29 - i, 'days').format('MM-DD'),
    completed: Math.floor(Math.random() * 8) + 2,
    created: Math.floor(Math.random() * 6) + 1,
    inProgress: Math.floor(Math.random() * 5) + 3,
  }));

  const statusDistribution = [
    { name: t('tasks.statusCompleted'), value: statsData.completedTasks, color: '#52c41a' },
    { name: t('tasks.statusInProgress'), value: statsData.inProgressTasks, color: '#1890ff' },
    { name: t('tasks.statusPending'), value: statsData.pendingTasks, color: '#faad14' },
    { name: t('tasks.overdue'), value: statsData.overdueTasks, color: '#ff4d4f' },
  ];

  // Export functions
  const exportToCSV = useCallback(() => {
    const headers = ['User', 'Tasks Completed', 'Avg Quality Score', 'Avg Completion Time (days)', 'Efficiency'];
    const rows = userPerformance.map(u => [
      u.userName,
      u.tasksCompleted,
      (u.avgQualityScore * 100).toFixed(1) + '%',
      u.avgCompletionTime.toFixed(1),
      (u.efficiency * 100).toFixed(1) + '%',
    ]);
    
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `task_stats_${dayjs().format('YYYY-MM-DD')}.csv`;
    link.click();
    message.success(t('dashboard:export.csvSuccess'));
  }, [userPerformance, t]);

  const exportToPDF = useCallback(() => {
    const reportData = {
      generatedAt: dayjs().toISOString(),
      period: {
        start: timeRange[0].format('YYYY-MM-DD'),
        end: timeRange[1].format('YYYY-MM-DD'),
      },
      summary: statsData,
      userPerformance,
      trends: taskTrends,
    };
    
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `task_report_${dayjs().format('YYYY-MM-DD')}.json`;
    link.click();
    message.success(t('dashboard:export.pdfSuccess'));
  }, [statsData, userPerformance, taskTrends, timeRange, t]);

  const userColumns = [
    { title: t('tasks.user'), dataIndex: 'userName', key: 'userName' },
    { title: t('tasks.completed'), dataIndex: 'tasksCompleted', key: 'tasksCompleted', sorter: (a: UserPerformance, b: UserPerformance) => a.tasksCompleted - b.tasksCompleted },
    { 
      title: t('dashboard:metrics.qualityScore'), 
      dataIndex: 'avgQualityScore', 
      key: 'avgQualityScore',
      render: (val: number) => <Progress percent={val * 100} size="small" status={val >= 0.85 ? 'success' : 'normal'} />,
      sorter: (a: UserPerformance, b: UserPerformance) => a.avgQualityScore - b.avgQualityScore,
    },
    { 
      title: t('tasks.avgTimePerItem'), 
      dataIndex: 'avgCompletionTime', 
      key: 'avgCompletionTime',
      render: (val: number) => `${val.toFixed(1)} ${t('tasks.days') || 'days'}`,
      sorter: (a: UserPerformance, b: UserPerformance) => a.avgCompletionTime - b.avgCompletionTime,
    },
    { 
      title: t('tasks.efficiency'), 
      dataIndex: 'efficiency', 
      key: 'efficiency',
      render: (val: number) => <Progress percent={val * 100} size="small" strokeColor={val >= 0.85 ? '#52c41a' : val >= 0.7 ? '#faad14' : '#ff4d4f'} />,
      sorter: (a: UserPerformance, b: UserPerformance) => a.efficiency - b.efficiency,
    },
  ];

  return (
    <div>
      {/* Controls */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <RangePicker
              value={timeRange}
              onChange={(dates) => dates && setTimeRange(dates as [Dayjs, Dayjs])}
              format="YYYY-MM-DD"
            />
            <Select
              value={selectedUser}
              onChange={setSelectedUser}
              style={{ width: 150 }}
              options={[
                { value: 'all', label: t('tasks.allUsers') || 'All Users' },
                ...userPerformance.map(u => ({ value: u.userId, label: u.userName })),
              ]}
            />
          </Space>
          {showExport && (
            <Space>
              <Button icon={<FileExcelOutlined />} onClick={exportToCSV}>
                {t('dashboard:export.csv')}
              </Button>
              <Button icon={<FilePdfOutlined />} onClick={exportToPDF}>
                {t('dashboard:export.pdf')}
              </Button>
            </Space>
          )}
        </Space>
      </Card>

      {/* Summary Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('tasks.totalTasks')}
              value={statsData.totalTasks}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('tasks.completed')}
              value={statsData.completedTasks}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix={<span style={{ fontSize: 14, color: '#999' }}>({((statsData.completedTasks / statsData.totalTasks) * 100).toFixed(1)}%)</span>}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('dashboard:metrics.qualityScore')}
              value={(statsData.avgQualityScore * 100).toFixed(1)}
              prefix={<TrophyOutlined />}
              suffix="%"
              valueStyle={{ color: statsData.avgQualityScore >= 0.85 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={t('tasks.totalAnnotations') || 'Total Annotations'}
              value={statsData.totalAnnotations}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card title={t('tasks.taskTrends') || 'Task Trends'}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={taskTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="completed" stroke="#52c41a" name={t('tasks.completed')} />
                <Line type="monotone" dataKey="created" stroke="#1890ff" name={t('tasks.created') || 'Created'} />
                <Line type="monotone" dataKey="inProgress" stroke="#faad14" name={t('tasks.inProgress')} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={t('tasks.statusDistribution') || 'Status Distribution'}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  dataKey="value"
                >
                  {statusDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* User Performance Table */}
      <Card title={t('tasks.userPerformance') || 'User Performance'}>
        <Table
          dataSource={userPerformance}
          columns={userColumns}
          rowKey="userId"
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default TaskStats;
