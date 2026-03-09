/**
 * AnnotationTasks Page Component
 * 
 * Displays annotation task management interface with filters, statistics, and task table.
 * Allows users to create, assign, and monitor annotation tasks.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Breadcrumb,
  Row,
  Col,
  Statistic,
  Select,
  DatePicker,
} from 'antd';
import {
  HomeOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  PlusOutlined,
  FilterOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ============================================================================
// Types
// ============================================================================

interface FilterState {
  status?: string;
  assignee?: string;
  deadlineRange?: [string, string];
}

interface StatisticsData {
  totalTasks: number;
  tasksByStatus: {
    created: number;
    inProgress: number;
    completed: number;
    cancelled: number;
  };
  completionRate: number;
}

// ============================================================================
// Component
// ============================================================================

const AnnotationTasksPage: React.FC = () => {
  const { t } = useTranslation('dataLifecycle');
  const navigate = useNavigate();
  const location = useLocation();
  
  const [filters, setFilters] = useState<FilterState>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [statistics, setStatistics] = useState<StatisticsData>({
    totalTasks: 0,
    tasksByStatus: {
      created: 0,
      inProgress: 0,
      completed: 0,
      cancelled: 0,
    },
    completionRate: 0,
  });

  // Check if we have selected samples from navigation state
  useEffect(() => {
    const state = location.state as { selectedSamples?: string[] };
    if (state?.selectedSamples && state.selectedSamples.length > 0) {
      // TODO: Open create task modal with pre-selected samples
      // This will be implemented when TaskManagement component is created
    }
  }, [location.state]);

  // Handle filter changes
  const handleFilterChange = useCallback((key: keyof FilterState, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  // Apply filters
  const handleApplyFilters = useCallback(() => {
    // TODO: Apply filters to task list when TaskManagement component is created
    setRefreshKey(prev => prev + 1);
  }, [filters]);

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setFilters({});
    setRefreshKey(prev => prev + 1);
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);

  // Handle create new task
  const handleCreateTask = useCallback(() => {
    // TODO: Open create task modal when TaskManagement component is created
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Breadcrumb */}
        <Breadcrumb
          items={[
            {
              href: '/',
              title: (
                <Space>
                  <HomeOutlined />
                  <span>{t('common.actions.back')}</span>
                </Space>
              ),
            },
            {
              href: '/data-lifecycle',
              title: (
                <Space>
                  <DatabaseOutlined />
                  <span>{t('interface.title')}</span>
                </Space>
              ),
            },
            {
              title: t('tabs.annotation'),
            },
          ]}
        />

        {/* Page Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              {t('annotationTask.title')}
            </Title>
            <Text type="secondary">{t('annotationTask.description')}</Text>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
            >
              {t('common.actions.refresh')}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateTask}
            >
              {t('annotationTask.actions.create')}
            </Button>
          </Space>
        </div>

        {/* Filters */}
        <Card size="small">
          <Space wrap style={{ width: '100%' }}>
            <Select
              placeholder={t('annotationTask.columns.status')}
              style={{ width: 150 }}
              value={filters.status}
              onChange={(value) => handleFilterChange('status', value)}
              allowClear
            >
              <Select.Option value="all">{t('tempData.filters.all')}</Select.Option>
              <Select.Option value="created">{t('annotationTask.status.pending')}</Select.Option>
              <Select.Option value="in_progress">{t('annotationTask.status.inProgress')}</Select.Option>
              <Select.Option value="completed">{t('annotationTask.status.completed')}</Select.Option>
              <Select.Option value="cancelled">{t('annotationTask.status.cancelled')}</Select.Option>
            </Select>

            <Select
              placeholder={t('annotationTask.columns.assignee')}
              style={{ width: 200 }}
              value={filters.assignee}
              onChange={(value) => handleFilterChange('assignee', value)}
              allowClear
            >
              {/* TODO: Populate with actual assignees from API */}
              <Select.Option value="user1">User 1</Select.Option>
              <Select.Option value="user2">User 2</Select.Option>
            </Select>

            <RangePicker
              placeholder={[t('annotationTask.columns.dueDate'), t('annotationTask.columns.dueDate')]}
              onChange={(dates, dateStrings) => {
                if (dates && dates[0] && dates[1]) {
                  handleFilterChange('deadlineRange', dateStrings as [string, string]);
                } else {
                  handleFilterChange('deadlineRange', undefined);
                }
              }}
            />

            <Button
              type="primary"
              icon={<FilterOutlined />}
              onClick={handleApplyFilters}
            >
              {t('common.actions.filter')}
            </Button>

            <Button onClick={handleClearFilters}>
              {t('common.actions.reset')}
            </Button>
          </Space>
        </Card>

        {/* Statistics Cards */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('annotationTask.columns.status')}
                value={statistics.totalTasks}
                suffix={t('annotationTask.messages.noTasks').includes('暂无') ? '个任务' : 'tasks'}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('annotationTask.status.pending')}
                value={statistics.tasksByStatus.created}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('annotationTask.status.inProgress')}
                value={statistics.tasksByStatus.inProgress}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={t('annotationTask.progress.percentage')}
                value={statistics.completionRate}
                precision={1}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>

        {/* Task Management Component - Placeholder for task 26.2 */}
        <Card>
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Text type="secondary">
              {t('sampleLibrary.messages.componentPlaceholder').replace('25.2', '26.2')}
            </Text>
          </div>
        </Card>

        {/* Summary */}
        <Card size="small">
          <Space split="|">
            <Text type="secondary">
              {t('common.pagination.total', { total: statistics.totalTasks })}
            </Text>
            <Text type="secondary">
              {t('annotationTask.columns.status')}: {filters.status || t('tempData.filters.all')}
            </Text>
          </Space>
        </Card>
      </Space>
    </div>
  );
};

export default AnnotationTasksPage;
