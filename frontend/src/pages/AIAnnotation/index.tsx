/**
 * AI Annotation Module Index Page
 *
 * Main entry point for AI-assisted annotation features:
 * - Dashboard overview
 * - Task management
 * - Quality monitoring
 * - Real-time collaboration
 * - Engine configuration
 */

import React, { useState } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Card, Menu, Row, Col, Statistic, Space, Badge, Alert, Button } from 'antd';
import {
  DashboardOutlined,
  ThunderboltOutlined,
  TeamOutlined,
  BarChartOutlined,
  SettingOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { MenuProps } from 'antd';

// Import AI Annotation components
import TaskManagement from '@/components/AIAnnotation/TaskManagement';
import QualityDashboard from '@/components/AIAnnotation/QualityDashboard';
import AnnotationCollaboration from '@/components/AIAnnotation/AnnotationCollaboration';
import EngineConfiguration from './EngineConfiguration';

// Types
interface AIAnnotationStats {
  totalTasks: number;
  completedTasks: number;
  activeAnnotators: number;
  aiAccuracy: number;
  pendingReviews: number;
  activeConflicts: number;
}

const AIAnnotationIndex: React.FC = () => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const location = useLocation();
  const navigate = useNavigate();
  const [stats, setStats] = useState<AIAnnotationStats>({
    totalTasks: 150,
    completedTasks: 87,
    activeAnnotators: 12,
    aiAccuracy: 0.92,
    pendingReviews: 23,
    activeConflicts: 5,
  });

  // Get current menu key from path
  const getMenuKey = () => {
    const path = location.pathname;
    if (path.includes('/tasks')) return 'tasks';
    if (path.includes('/quality')) return 'quality';
    if (path.includes('/collaboration')) return 'collaboration';
    if (path.includes('/engines')) return 'engines';
    return 'dashboard';
  };

  // Menu items
  const menuItems: MenuProps['items'] = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: t('ai_annotation:menu.dashboard'),
    },
    {
      key: 'tasks',
      icon: <ThunderboltOutlined />,
      label: (
        <Space>
          {t('ai_annotation:menu.tasks')}
          {stats.pendingReviews > 0 && (
            <Badge count={stats.pendingReviews} size="small" />
          )}
        </Space>
      ),
    },
    {
      key: 'quality',
      icon: <BarChartOutlined />,
      label: t('ai_annotation:menu.quality'),
    },
    {
      key: 'collaboration',
      icon: <TeamOutlined />,
      label: (
        <Space>
          {t('ai_annotation:menu.collaboration')}
          {stats.activeConflicts > 0 && (
            <Badge count={stats.activeConflicts} size="small" color="orange" />
          )}
        </Space>
      ),
    },
    {
      key: 'engines',
      icon: <SettingOutlined />,
      label: t('ai_annotation:menu.engines'),
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    if (e.key === 'dashboard') {
      navigate('/ai-annotation');
    } else {
      navigate(`/ai-annotation/${e.key}`);
    }
  };

  // Check if we're on a sub-route
  const isSubRoute = location.pathname !== '/ai-annotation';

  // Dashboard content
  const DashboardContent = () => (
    <div className="ai-annotation-dashboard">
      {/* Stats Overview */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title={t('ai_annotation:stats.total_tasks')}
              value={stats.totalTasks}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title={t('ai_annotation:stats.completed')}
              value={stats.completedTasks}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title={t('ai_annotation:stats.active_annotators')}
              value={stats.activeAnnotators}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title={t('ai_annotation:stats.ai_accuracy')}
              value={(stats.aiAccuracy * 100).toFixed(1)}
              suffix="%"
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title={t('ai_annotation:stats.pending_reviews')}
              value={stats.pendingReviews}
              prefix={<SyncOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title={t('ai_annotation:stats.conflicts')}
              value={stats.activeConflicts}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: stats.activeConflicts > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Alerts */}
      {stats.activeConflicts > 0 && (
        <Alert
          message={t('ai_annotation:alerts.conflicts_title')}
          description={t('ai_annotation:alerts.conflicts_description', { count: stats.activeConflicts })}
          type="warning"
          showIcon
          action={
            <Button size="small" onClick={() => navigate('/ai-annotation/collaboration')}>
              {t('ai_annotation:actions.resolve_conflicts')}
            </Button>
          }
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Quick Actions */}
      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined />
                {t('ai_annotation:dashboard.recent_tasks')}
              </Space>
            }
            extra={
              <Button type="link" onClick={() => navigate('/ai-annotation/tasks')}>
                {t('common:actions.view_all')}
              </Button>
            }
          >
            <TaskManagement
              onTaskSelect={(task) => navigate(`/ai-annotation/tasks/${task.taskId}`)}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <BarChartOutlined />
                {t('ai_annotation:dashboard.quality_overview')}
              </Space>
            }
            extra={
              <Button type="link" onClick={() => navigate('/ai-annotation/quality')}>
                {t('common:actions.view_details')}
              </Button>
            }
          >
            <QualityDashboard projectId="default" compact />
          </Card>
        </Col>
      </Row>
    </div>
  );

  // If on sub-route, render the child component
  if (isSubRoute) {
    return (
      <div className="ai-annotation-page">
        <Card style={{ marginBottom: 16 }}>
          <Menu
            mode="horizontal"
            selectedKeys={[getMenuKey()]}
            items={menuItems}
            onClick={handleMenuClick}
          />
        </Card>
        <Routes>
          <Route path="tasks" element={<TaskManagement />} />
          <Route path="tasks/:taskId" element={<TaskManagement />} />
          <Route path="quality" element={<QualityDashboard projectId="default" />} />
          <Route path="collaboration" element={<AnnotationCollaboration projectId="default" />} />
          <Route path="engines" element={<EngineConfiguration />} />
          <Route path="*" element={<Navigate to="/ai-annotation" replace />} />
        </Routes>
      </div>
    );
  }

  // Main dashboard view
  return (
    <div className="ai-annotation-page">
      <Card style={{ marginBottom: 16 }}>
        <Menu
          mode="horizontal"
          selectedKeys={[getMenuKey()]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Card>
      <DashboardContent />
    </div>
  );
};

export default AIAnnotationIndex;
