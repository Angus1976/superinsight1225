import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Select,
  DatePicker,
  Button,
  Space,
  Tag,
  Progress,
  Typography,
  Tabs,
  Alert,
  List,
  Avatar,
  Tooltip,
  message,
} from 'antd';
import {
  TrophyOutlined,
  UserOutlined,
  TeamOutlined,
  RiseOutlined,
  FallOutlined,
  ExportOutlined,
  CalendarOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const { RangePicker } = DatePicker;
const { Text, Title } = Typography;

export interface QualityAssessment {
  id: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  period: string;
  qualityScore: number;
  tasksCompleted: number;
  issuesFound: number;
  issuesFixed: number;
  averageResolutionTime: number; // in hours
  trend: 'up' | 'down' | 'stable';
  rank: number;
  department: string;
  achievements: string[];
  improvements: string[];
}

export interface QualityTrend {
  date: string;
  qualityScore: number;
  issuesFound: number;
  issuesFixed: number;
  efficiency: number;
}

export interface IssueDistribution {
  category: string;
  count: number;
  percentage: number;
  color: string;
}

export interface ActionPlan {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  assignee: string;
  dueDate: string;
  status: 'pending' | 'inProgress' | 'completed';
  progress: number;
}

interface QualityReportsAnalysisProps {
  assessments: QualityAssessment[];
  trends: QualityTrend[];
  issueDistribution: IssueDistribution[];
  actionPlans: ActionPlan[];
  onExportReport: (type: string, period: string) => Promise<void>;
  onScheduleReport: (config: Record<string, unknown>) => Promise<void>;
  loading?: boolean;
}

const QualityReportsAnalysis: React.FC<QualityReportsAnalysisProps> = ({
  assessments,
  trends,
  issueDistribution,
  actionPlans,
  onExportReport,
  onScheduleReport,
  loading = false,
}) => {
  const { t } = useTranslation(['quality', 'common']);
  const [selectedPeriod, setSelectedPeriod] = useState('thisMonth');
  const [selectedDepartment, setSelectedDepartment] = useState('all');

  const handleExportReport = async (type: string) => {
    try {
      await onExportReport(type, selectedPeriod);
      message.success(t('exportSuccess'));
    } catch (error) {
      message.error(t('operationFailed'));
    }
  };

  const handleScheduleReport = async () => {
    try {
      await onScheduleReport({
        period: selectedPeriod,
        department: selectedDepartment,
        frequency: 'weekly',
      });
      message.success(t('messages.reportScheduled'));
    } catch (error) {
      message.error(t('operationFailed'));
    }
  };

  // Assessment table columns
  const assessmentColumns: ColumnsType<QualityAssessment> = [
    {
      title: t('rank'),
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank) => (
        <div style={{ textAlign: 'center' }}>
          {rank <= 3 ? (
            <TrophyOutlined style={{ color: rank === 1 ? '#ffd700' : rank === 2 ? '#c0c0c0' : '#cd7f32' }} />
          ) : (
            <Text strong>#{rank}</Text>
          )}
        </div>
      ),
    },
    {
      title: t('user'),
      dataIndex: 'userName',
      key: 'user',
      render: (name, record) => (
        <Space>
          <Avatar size="small" src={record.userAvatar} icon={<UserOutlined />} />
          <div>
            <Text strong>{name}</Text>
            <div style={{ fontSize: '12px', color: '#666' }}>
              {record.department}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: t('stats.qualityScore'),
      dataIndex: 'qualityScore',
      key: 'qualityScore',
      width: 120,
      render: (score, record) => (
        <Space>
          <Progress
            type="circle"
            size={40}
            percent={score}
            format={() => score}
            strokeColor={score >= 90 ? '#52c41a' : score >= 70 ? '#faad14' : '#ff4d4f'}
          />
          {record.trend === 'up' && <RiseOutlined style={{ color: '#52c41a' }} />}
          {record.trend === 'down' && <FallOutlined style={{ color: '#ff4d4f' }} />}
        </Space>
      ),
    },
    {
      title: t('tasksCompleted'),
      dataIndex: 'tasksCompleted',
      key: 'tasksCompleted',
      width: 100,
    },
    {
      title: t('stats.fixedIssues'),
      dataIndex: 'issuesFixed',
      key: 'issuesFixed',
      width: 100,
      render: (fixed, record) => (
        <Space>
          <Text>{fixed}</Text>
          <Text type="secondary">/ {record.issuesFound}</Text>
        </Space>
      ),
    },
    {
      title: t('stats.averageResolutionTime'),
      dataIndex: 'averageResolutionTime',
      key: 'averageResolutionTime',
      width: 120,
      render: (hours) => `${hours}h`,
    },
    {
      title: t('achievements'),
      dataIndex: 'achievements',
      key: 'achievements',
      render: (achievements: string[]) => (
        <Space wrap>
          {achievements.slice(0, 2).map((achievement, index) => (
            <Tag key={index} color="green" size="small">
              {achievement}
            </Tag>
          ))}
          {achievements.length > 2 && (
            <Tooltip title={achievements.slice(2).join(', ')}>
              <Tag size="small">+{achievements.length - 2}</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // Action plan columns
  const actionPlanColumns: ColumnsType<ActionPlan> = [
    {
      title: t('reports.actionPlan'),
      dataIndex: 'title',
      key: 'title',
      render: (title, record) => (
        <div>
          <Text strong>{title}</Text>
          <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
            {record.description}
          </div>
        </div>
      ),
    },
    {
      title: t('workOrders.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority) => (
        <Tag color={priority === 'high' ? 'red' : priority === 'medium' ? 'orange' : 'green'}>
          {t(`quality.workOrders.priorities.${priority}`)}
        </Tag>
      ),
    },
    {
      title: t('workOrders.assignee'),
      dataIndex: 'assignee',
      key: 'assignee',
      width: 120,
    },
    {
      title: t('workOrders.progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress) => (
        <Progress percent={progress} size="small" />
      ),
    },
    {
      title: t('workOrders.dueDate'),
      dataIndex: 'dueDate',
      key: 'dueDate',
      width: 120,
      render: (date) => new Date(date).toLocaleDateString(),
    },
  ];

  // Calculate overall statistics
  const overallStats = {
    averageScore: Math.round(assessments.reduce((sum, a) => sum + a.qualityScore, 0) / assessments.length),
    totalTasks: assessments.reduce((sum, a) => sum + a.tasksCompleted, 0),
    totalIssuesFixed: assessments.reduce((sum, a) => sum + a.issuesFixed, 0),
    improvingUsers: assessments.filter(a => a.trend === 'up').length,
  };

  return (
    <div>
      {/* Controls */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <Text strong>{t('reports.period')}:</Text>
              <Select
                value={selectedPeriod}
                onChange={setSelectedPeriod}
                style={{ width: 120 }}
              >
                <Select.Option value="thisWeek">{t('thisWeek')}</Select.Option>
                <Select.Option value="thisMonth">{t('thisMonth')}</Select.Option>
                <Select.Option value="lastMonth">{t('lastMonth')}</Select.Option>
                <Select.Option value="thisQuarter">{t('thisQuarter')}</Select.Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Text strong>{t('department')}:</Text>
              <Select
                value={selectedDepartment}
                onChange={setSelectedDepartment}
                style={{ width: 120 }}
              >
                <Select.Option value="all">{t('all')}</Select.Option>
                <Select.Option value="annotation">{t('annotation')}</Select.Option>
                <Select.Option value="quality">{t('quality')}</Select.Option>
                <Select.Option value="review">{t('review')}</Select.Option>
              </Select>
            </Space>
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button
                icon={<ExportOutlined />}
                onClick={() => handleExportReport('pdf')}
              >
                {t('reports.export')}
              </Button>
              <Button
                icon={<CalendarOutlined />}
                onClick={handleScheduleReport}
              >
                {t('reports.schedule')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Overall Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.qualityScore')}
              value={overallStats.averageScore}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('totalTasks')}
              value={overallStats.totalTasks}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('stats.fixedIssues')}
              value={overallStats.totalIssuesFixed}
              prefix={<BulbOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('improvingUsers')}
              value={overallStats.improvingUsers}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content Tabs */}
      <Card>
        <Tabs
          defaultActiveKey="assessment"
          items={[
            {
              key: 'assessment',
              label: (
                <span>
                  <TrophyOutlined />
                  {t('reports.assessment')}
                </span>
              ),
              children: (
                <Table
                  columns={assessmentColumns}
                  dataSource={assessments}
                  rowKey="id"
                  loading={loading}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showQuickJumper: true,
                  }}
                />
              ),
            },
            {
              key: 'trends',
              label: (
                <span>
                  <LineChartOutlined />
                  {t('reports.trends')}
                </span>
              ),
              children: (
                <div>
                  <Row gutter={16}>
                    <Col span={24}>
                      <Card title={t('reports.trends')} style={{ marginBottom: 16 }}>
                        <ResponsiveContainer width="100%" height={300}>
                          <LineChart data={trends}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <RechartsTooltip />
                            <Legend />
                            <Line
                              type="monotone"
                              dataKey="qualityScore"
                              stroke="#52c41a"
                              name={t('stats.qualityScore')}
                            />
                            <Line
                              type="monotone"
                              dataKey="efficiency"
                              stroke="#1890ff"
                              name={t('efficiency')}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </Card>
                    </Col>
                  </Row>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card title={t('reports.distribution')}>
                        <ResponsiveContainer width="100%" height={250}>
                          <PieChart>
                            <Pie
                              data={issueDistribution}
                              cx="50%"
                              cy="50%"
                              outerRadius={80}
                              fill="#8884d8"
                              dataKey="count"
                              label={({ name, percentage }) => `${name} ${percentage}%`}
                            >
                              {issueDistribution.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                              ))}
                            </Pie>
                            <RechartsTooltip />
                          </PieChart>
                        </ResponsiveContainer>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title={t('reports.performance')}>
                        <ResponsiveContainer width="100%" height={250}>
                          <BarChart data={trends.slice(-7)}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" />
                            <YAxis />
                            <RechartsTooltip />
                            <Bar dataKey="issuesFixed" fill="#52c41a" name={t('stats.fixedIssues')} />
                            <Bar dataKey="issuesFound" fill="#faad14" name={t('issuesFound')} />
                          </BarChart>
                        </ResponsiveContainer>
                      </Card>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'improvement',
              label: (
                <span>
                  <BulbOutlined />
                  {t('reports.improvement')}
                </span>
              ),
              children: (
                <div>
                  <Row gutter={16}>
                    <Col span={16}>
                      <Card title={t('reports.actionPlan')}>
                        <Table
                          columns={actionPlanColumns}
                          dataSource={actionPlans}
                          rowKey="id"
                          pagination={false}
                          size="small"
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card title={t('reports.improvement')} style={{ marginBottom: 16 }}>
                        <List
                          size="small"
                          dataSource={[
                            {
                              icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
                              title: t('strengthenTraining'),
                              description: t('improveAnnotationQuality'),
                            },
                            {
                              icon: <WarningOutlined style={{ color: '#faad14' }} />,
                              title: t('optimizeProcess'),
                              description: t('reduceResolutionTime'),
                            },
                            {
                              icon: <BulbOutlined style={{ color: '#1890ff' }} />,
                              title: t('automateChecks'),
                              description: t('preventCommonIssues'),
                            },
                          ]}
                          renderItem={(item) => (
                            <List.Item>
                              <List.Item.Meta
                                avatar={item.icon}
                                title={item.title}
                                description={item.description}
                              />
                            </List.Item>
                          )}
                        />
                      </Card>
                      
                      <Alert
                        type="info"
                        message={t('recommendation')}
                        description={t('focusOnTopIssues')}
                        showIcon
                      />
                    </Col>
                  </Row>
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default QualityReportsAnalysis;