// Progress tracking and time statistics component
import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Progress,
  Statistic,
  Row,
  Col,
  Timeline,
  Table,
  Tag,
  Space,
  Button,
  Alert,
  Tooltip,
  Badge,
  Divider,
  Select,
  DatePicker,
  message,
} from 'antd';
import {
  ClockCircleOutlined,
  TrophyOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  BarChartOutlined,
  ExportOutlined,
  ReloadOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import duration from 'dayjs/plugin/duration';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(duration);
dayjs.extend(relativeTime);

interface ProgressData {
  taskId: string;
  taskName: string;
  totalItems: number;
  completedItems: number;
  progress: number;
  timeSpent: number; // in minutes
  estimatedTime: number; // in minutes
  efficiency: number; // items per hour
  status: 'pending' | 'in_progress' | 'completed' | 'paused';
  assignee: string;
  startTime?: string;
  lastActivity?: string;
  milestones: Milestone[];
}

interface Milestone {
  id: string;
  name: string;
  targetDate: string;
  completedDate?: string;
  progress: number;
  status: 'pending' | 'in_progress' | 'completed' | 'overdue';
}

interface TimeEntry {
  id: string;
  taskId: string;
  userId: string;
  userName: string;
  startTime: string;
  endTime?: string;
  duration: number; // in minutes
  activity: string;
  itemsCompleted: number;
}

interface ProgressTrackerProps {
  taskId: string;
  realtime?: boolean;
  showTimeEntries?: boolean;
  showMilestones?: boolean;
  onProgressUpdate?: (progress: ProgressData) => void;
  onAnomalyDetected?: (anomaly: { type: string; message: string; severity: 'low' | 'medium' | 'high' }) => void;
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  taskId,
  realtime = true,
  showTimeEntries = true,
  showMilestones = true,
  onProgressUpdate,
  onAnomalyDetected,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  const [progressData, setProgressData] = useState<ProgressData | null>(null);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTimer, setActiveTimer] = useState<string | null>(null);
  const [selectedDateRange, setSelectedDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  // Mock data for development
  const mockProgressData: ProgressData = {
    taskId: taskId,
    taskName: 'Customer Review Classification',
    totalItems: 1000,
    completedItems: 650,
    progress: 65,
    timeSpent: 480, // 8 hours
    estimatedTime: 720, // 12 hours
    efficiency: 81.25, // items per hour
    status: 'in_progress',
    assignee: 'John Doe',
    startTime: '2025-01-15T09:00:00Z',
    lastActivity: '2025-01-20T14:30:00Z',
    milestones: [
      {
        id: 'ms1',
        name: 'First 25% Complete',
        targetDate: '2025-01-18T00:00:00Z',
        completedDate: '2025-01-17T16:30:00Z',
        progress: 100,
        status: 'completed',
      },
      {
        id: 'ms2',
        name: 'Halfway Point',
        targetDate: '2025-01-22T00:00:00Z',
        completedDate: '2025-01-21T10:15:00Z',
        progress: 100,
        status: 'completed',
      },
      {
        id: 'ms3',
        name: '75% Complete',
        targetDate: '2025-01-25T00:00:00Z',
        progress: 86,
        status: 'in_progress',
      },
      {
        id: 'ms4',
        name: 'Final Completion',
        targetDate: '2025-01-28T00:00:00Z',
        progress: 0,
        status: 'pending',
      },
    ],
  };

  const mockTimeEntries: TimeEntry[] = [
    {
      id: 'te1',
      taskId: taskId,
      userId: 'user1',
      userName: 'John Doe',
      startTime: '2025-01-20T09:00:00Z',
      endTime: '2025-01-20T12:30:00Z',
      duration: 210,
      activity: 'Text Classification',
      itemsCompleted: 85,
    },
    {
      id: 'te2',
      taskId: taskId,
      userId: 'user1',
      userName: 'John Doe',
      startTime: '2025-01-20T13:30:00Z',
      endTime: '2025-01-20T17:00:00Z',
      duration: 210,
      activity: 'Quality Review',
      itemsCompleted: 65,
    },
    {
      id: 'te3',
      taskId: taskId,
      userId: 'user1',
      userName: 'John Doe',
      startTime: '2025-01-21T09:00:00Z',
      duration: 60,
      activity: 'Text Classification',
      itemsCompleted: 20,
    },
  ];

  // Fetch progress data
  const fetchProgressData = useCallback(async () => {
    try {
      setLoading(true);
      // In a real implementation, this would be an API call
      // const response = await apiClient.get(`/api/tasks/${taskId}/progress`);
      // setProgressData(response.data);
      
      // Mock implementation
      setProgressData(mockProgressData);
      setTimeEntries(mockTimeEntries);
      
      onProgressUpdate?.(mockProgressData);
    } catch (error) {
      console.error('Failed to fetch progress data:', error);
      message.error(t('fetchProgressError'));
    } finally {
      setLoading(false);
    }
  }, [taskId, onProgressUpdate, t]);

  // Real-time updates
  useEffect(() => {
    fetchProgressData();

    if (realtime) {
      const interval = setInterval(fetchProgressData, 30000); // Update every 30 seconds
      return () => clearInterval(interval);
    }
  }, [fetchProgressData, realtime]);

  // Anomaly detection
  useEffect(() => {
    if (!progressData) return;

    const anomalies = [];

    // Check for low efficiency
    if (progressData.efficiency < 20) {
      anomalies.push({
        type: 'low_efficiency',
        message: t('anomalyLowEfficiency', { efficiency: progressData.efficiency.toFixed(1) }),
        severity: 'high' as const,
      });
    }

    // Check for overdue milestones
    const overdueMilestones = progressData.milestones.filter(
      milestone => milestone.status === 'overdue'
    );
    if (overdueMilestones.length > 0) {
      anomalies.push({
        type: 'overdue_milestones',
        message: t('anomalyOverdueMilestones', { count: overdueMilestones.length }),
        severity: 'medium' as const,
      });
    }

    // Check for stalled progress
    if (progressData.lastActivity) {
      const lastActivityTime = dayjs(progressData.lastActivity);
      const hoursSinceActivity = dayjs().diff(lastActivityTime, 'hour');
      if (hoursSinceActivity > 24 && progressData.status === 'in_progress') {
        anomalies.push({
          type: 'stalled_progress',
          message: t('anomalyStalledProgress', { hours: hoursSinceActivity }),
          severity: 'medium' as const,
        });
      }
    }

    // Report anomalies
    anomalies.forEach(anomaly => {
      onAnomalyDetected?.(anomaly);
    });
  }, [progressData, onAnomalyDetected, t]);

  // Calculate statistics
  const getStatistics = () => {
    if (!progressData) return null;

    const remainingItems = progressData.totalItems - progressData.completedItems;
    const estimatedRemainingTime = progressData.efficiency > 0 
      ? remainingItems / progressData.efficiency * 60 // convert to minutes
      : 0;
    const estimatedCompletionDate = dayjs().add(estimatedRemainingTime, 'minute');
    
    return {
      remainingItems,
      estimatedRemainingTime,
      estimatedCompletionDate,
      averageTimePerItem: progressData.completedItems > 0 
        ? progressData.timeSpent / progressData.completedItems 
        : 0,
    };
  };

  const statistics = getStatistics();

  // Time entries table columns
  const timeEntriesColumns: ColumnsType<TimeEntry> = [
    {
      title: t('user'),
      dataIndex: 'userName',
      key: 'userName',
      render: (name) => (
        <Space>
          <Badge status="processing" />
          {name}
        </Space>
      ),
    },
    {
      title: t('startTime'),
      dataIndex: 'startTime',
      key: 'startTime',
      render: (time) => dayjs(time).format('MM-DD HH:mm'),
    },
    {
      title: t('duration'),
      dataIndex: 'duration',
      key: 'duration',
      render: (duration) => {
        const hours = Math.floor(duration / 60);
        const minutes = duration % 60;
        return `${hours}h ${minutes}m`;
      },
    },
    {
      title: t('activity'),
      dataIndex: 'activity',
      key: 'activity',
      render: (activity) => <Tag color="blue">{activity}</Tag>,
    },
    {
      title: t('itemsCompleted'),
      dataIndex: 'itemsCompleted',
      key: 'itemsCompleted',
      render: (items) => (
        <Statistic
          value={items}
          valueStyle={{ fontSize: 14 }}
          prefix={<CheckCircleOutlined />}
        />
      ),
    },
    {
      title: t('efficiency'),
      key: 'efficiency',
      render: (_, record) => {
        const efficiency = record.duration > 0 ? (record.itemsCompleted / record.duration) * 60 : 0;
        return (
          <Tooltip title={t('itemsPerHour')}>
            <Tag color={efficiency > 50 ? 'green' : efficiency > 20 ? 'orange' : 'red'}>
              {efficiency.toFixed(1)}/h
            </Tag>
          </Tooltip>
        );
      },
    },
  ];

  if (loading) {
    return (
      <Card loading={loading}>
        <div style={{ height: 200 }} />
      </Card>
    );
  }

  if (!progressData) {
    return (
      <Alert
        type="warning"
        message={t('noProgressData')}
        description={t('noProgressDataDescription')}
        showIcon
      />
    );
  }

  return (
    <div>
      {/* Progress Overview */}
      <Card
        title={
          <Space>
            <BarChartOutlined />
            {t('progressOverview')}
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchProgressData}
              loading={loading}
            >
              {t('common.refresh')}
            </Button>
            <Button icon={<ExportOutlined />}>
              {t('exportReport')}
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ marginBottom: 16 }}>
              <Progress
                type="circle"
                percent={progressData.progress}
                size={120}
                status={progressData.status === 'completed' ? 'success' : 'active'}
                format={(percent) => (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 20, fontWeight: 'bold' }}>{percent}%</div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      {progressData.completedItems} / {progressData.totalItems}
                    </div>
                  </div>
                )}
              />
            </div>
          </Col>
          <Col span={12}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title={t('timeSpent')}
                  value={Math.floor(progressData.timeSpent / 60)}
                  suffix="h"
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('efficiency')}
                  value={progressData.efficiency}
                  suffix="/h"
                  prefix={<TrophyOutlined />}
                  valueStyle={{ 
                    color: progressData.efficiency > 50 ? '#52c41a' : 
                           progressData.efficiency > 20 ? '#faad14' : '#ff4d4f' 
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('estimatedRemaining')}
                  value={statistics ? Math.floor(statistics.estimatedRemainingTime / 60) : 0}
                  suffix="h"
                  prefix={<CalendarOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('avgTimePerItem')}
                  value={statistics ? statistics.averageTimePerItem : 0}
                  suffix="min"
                  precision={1}
                  valueStyle={{ color: '#13c2c2' }}
                />
              </Col>
            </Row>
          </Col>
        </Row>

        {statistics && (
          <Alert
            type="info"
            message={t('estimatedCompletion')}
            description={t('estimatedCompletionDate', {
              date: statistics.estimatedCompletionDate.format('YYYY-MM-DD HH:mm')
            })}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {/* Milestones */}
      {showMilestones && (
        <Card
          title={
            <Space>
              <CheckCircleOutlined />
              {t('milestones')}
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Timeline>
            {progressData.milestones.map((milestone) => {
              const isOverdue = milestone.status === 'overdue';
              const isCompleted = milestone.status === 'completed';
              
              return (
                <Timeline.Item
                  key={milestone.id}
                  color={
                    isCompleted ? 'green' :
                    isOverdue ? 'red' :
                    milestone.status === 'in_progress' ? 'blue' : 'gray'
                  }
                  dot={
                    isCompleted ? <CheckCircleOutlined /> :
                    isOverdue ? <WarningOutlined /> :
                    milestone.status === 'in_progress' ? <PlayCircleOutlined /> :
                    <PauseCircleOutlined />
                  }
                >
                  <div>
                    <Space direction="vertical" size={4}>
                      <Space>
                        <span style={{ fontWeight: 500 }}>{milestone.name}</span>
                        <Tag color={
                          isCompleted ? 'green' :
                          isOverdue ? 'red' :
                          milestone.status === 'in_progress' ? 'blue' : 'default'
                        }>
                          {t(`tasks.milestone${milestone.status.charAt(0).toUpperCase() + milestone.status.slice(1)}`)}
                        </Tag>
                      </Space>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        {t('targetDate')}: {dayjs(milestone.targetDate).format('YYYY-MM-DD')}
                        {milestone.completedDate && (
                          <span style={{ marginLeft: 8 }}>
                            | {t('completedDate')}: {dayjs(milestone.completedDate).format('YYYY-MM-DD')}
                          </span>
                        )}
                      </div>
                      {milestone.progress < 100 && (
                        <Progress
                          percent={milestone.progress}
                          size="small"
                          status={isOverdue ? 'exception' : 'active'}
                        />
                      )}
                    </Space>
                  </div>
                </Timeline.Item>
              );
            })}
          </Timeline>
        </Card>
      )}

      {/* Time Entries */}
      {showTimeEntries && (
        <Card
          title={
            <Space>
              <ClockCircleOutlined />
              {t('timeEntries')}
            </Space>
          }
          extra={
            <Space>
              <DatePicker.RangePicker
                value={selectedDateRange}
                onChange={setSelectedDateRange}
                placeholder={[t('startDate'), t('endDate')]}
              />
              <Select
                placeholder={t('filterByUser')}
                style={{ width: 120 }}
                allowClear
              >
                <Select.Option value="user1">John Doe</Select.Option>
                <Select.Option value="user2">Jane Smith</Select.Option>
              </Select>
            </Space>
          }
        >
          <Table
            columns={timeEntriesColumns}
            dataSource={timeEntries}
            rowKey="id"
            size="small"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
            }}
            summary={(data) => {
              const totalDuration = data.reduce((sum, entry) => sum + entry.duration, 0);
              const totalItems = data.reduce((sum, entry) => sum + entry.itemsCompleted, 0);
              const avgEfficiency = totalDuration > 0 ? (totalItems / totalDuration) * 60 : 0;

              return (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}>
                    <strong>{t('total')}</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1}>-</Table.Summary.Cell>
                  <Table.Summary.Cell index={2}>
                    <strong>
                      {Math.floor(totalDuration / 60)}h {totalDuration % 60}m
                    </strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3}>-</Table.Summary.Cell>
                  <Table.Summary.Cell index={4}>
                    <strong>{totalItems}</strong>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={5}>
                    <strong>
                      <Tag color={avgEfficiency > 50 ? 'green' : avgEfficiency > 20 ? 'orange' : 'red'}>
                        {avgEfficiency.toFixed(1)}/h
                      </Tag>
                    </strong>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              );
            }}
          />
        </Card>
      )}
    </div>
  );
};

export default ProgressTracker;