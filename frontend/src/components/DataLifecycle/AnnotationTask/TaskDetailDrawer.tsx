/**
 * TaskDetailDrawer Component
 * 
 * Displays detailed information about an annotation task with tabs for
 * overview, samples, annotations, and activity log.
 * 
 * Requirements: 5.3, 5.4, 14.3
 */

import React, { useState } from 'react';
import {
  Drawer,
  Tabs,
  Descriptions,
  Tag,
  Progress,
  Button,
  Space,
  List,
  Typography,
  Empty,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  EditOutlined,
  UserAddOutlined,
  CheckCircleOutlined,
  StopOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AnnotationTask } from '@/services/dataLifecycle';

const { Text } = Typography;

type AnnotationMetadata = {
  completed_at?: string;
  annotations?: Array<{ annotator_id: string; sample_id: string; comments?: string }>;
};

function getAnnotationMetadata(task: AnnotationTask): AnnotationMetadata {
  const m = task.metadata;
  if (m && typeof m === 'object') return m as AnnotationMetadata;
  return {};
}

// ============================================================================
// Types
// ============================================================================

export interface TaskDetailDrawerProps {
  visible: boolean;
  task: AnnotationTask | null;
  onClose: () => void;
  onEdit: (id: string) => void;
  onAssign: (id: string) => void;
  onComplete: (id: string) => void;
  onCancel: (id: string) => void;
}

// ============================================================================
// Component
// ============================================================================

const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({
  visible,
  task,
  onClose,
  onEdit,
  onAssign,
  onComplete,
  onCancel,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [activeTab, setActiveTab] = useState('overview');

  if (!task) return null;

  const meta = getAnnotationMetadata(task);
  const sampleTotal = task.sample_ids?.length ?? 0;
  const progressPercent = Math.min(100, Math.max(0, Math.round(Number(task.progress) || 0)));
  const labeledCount =
    sampleTotal > 0 ? Math.round((progressPercent / 100) * sampleTotal) : 0;

  // Get status color
  const getStatusColor = (status: AnnotationTask['status']): string => {
    const colorMap: Record<AnnotationTask['status'], string> = {
      created: 'default',
      in_progress: 'processing',
      completed: 'success',
      cancelled: 'error',
    };
    return colorMap[status] || 'default';
  };

  const calculateProgress = (): number => progressPercent;

  // Render overview tab
  const renderOverview = () => (
    <div>
      {/* Progress Statistics */}
      <div style={{ marginBottom: 24, padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title={t('annotationTask.progress.total')}
              value={sampleTotal}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('annotationTask.progress.labeled')}
              value={labeledCount}
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title={t('annotationTask.progress.percentage')}
              value={calculateProgress()}
              suffix="%"
            />
          </Col>
        </Row>
        <div style={{ marginTop: 16 }}>
          <Progress
            percent={calculateProgress()}
            status={task.status === 'completed' ? 'success' : 'active'}
          />
        </div>
      </div>

      {/* Task Details */}
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label={t('annotationTask.columns.name')}>
          {task.name}
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.columns.description')}>
          {task.description || '-'}
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.columns.status')}>
          <Tag color={getStatusColor(task.status)}>
            {t(`annotationTask.status.${task.status}`)}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.fields.annotationType')}>
          {t(`annotationTask.types.${task.annotation_type}`)}
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.fields.instructions')}>
          <Text style={{ whiteSpace: 'pre-wrap' }}>{task.instructions}</Text>
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.columns.assignee')}>
          {task.assigned_to?.map(user => (
            <Tag key={user}>{user}</Tag>
          )) || '-'}
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.columns.createdAt')}>
          {new Date(task.created_at).toLocaleString()}
        </Descriptions.Item>
        <Descriptions.Item label={t('annotationTask.columns.dueDate')}>
          {task.deadline ? (
            <Text type={new Date(task.deadline) < new Date() ? 'danger' : undefined}>
              {new Date(task.deadline).toLocaleString()}
            </Text>
          ) : '-'}
        </Descriptions.Item>
        {meta.completed_at && (
          <Descriptions.Item label={t('annotationTask.fields.completedAt')}>
            {new Date(meta.completed_at).toLocaleString()}
          </Descriptions.Item>
        )}
      </Descriptions>
    </div>
  );

  // Render samples tab
  const renderSamples = () => (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Text strong>
          {t('sampleLibrary.statistics.totalSamples')}: {task.sample_ids?.length || 0}
        </Text>
      </div>
      {task.sample_ids && task.sample_ids.length > 0 ? (
        <List
          dataSource={task.sample_ids}
          renderItem={(sampleId, index) => (
            <List.Item>
              <List.Item.Meta
                title={`${t('sampleLibrary.title')} ${index + 1}`}
                description={
                  <Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>
                    {sampleId}
                  </Text>
                }
              />
            </List.Item>
          )}
          pagination={{
            pageSize: 10,
            size: 'small',
          }}
        />
      ) : (
        <Empty description={t('sampleLibrary.messages.noSamples')} />
      )}
    </div>
  );

  // Render annotations tab
  const annotations = meta.annotations ?? [];

  const renderAnnotations = () => (
    <div>
      {annotations.length > 0 ? (
        <List
          dataSource={annotations}
          renderItem={(annotation) => (
            <List.Item>
              <List.Item.Meta
                title={annotation.annotator_id}
                description={
                  <Space direction="vertical" size="small">
                    <Text type="secondary">
                      {t('sampleLibrary.title')}: {annotation.sample_id}
                    </Text>
                    {annotation.comments && (
                      <Text>{annotation.comments}</Text>
                    )}
                  </Space>
                }
              />
            </List.Item>
          )}
          pagination={{
            pageSize: 10,
            size: 'small',
          }}
        />
      ) : (
        <Empty description={t('annotationTask.messages.noAnnotations')} />
      )}
    </div>
  );

  // Render activity log tab
  const renderActivityLog = () => (
    <div>
      <Empty description={t('annotationTask.messages.noActivityLog')} />
    </div>
  );

  // Tab items
  const tabItems = [
    {
      key: 'overview',
      label: t('sampleLibrary.tabs.overview'),
      children: renderOverview(),
    },
    {
      key: 'samples',
      label: t('annotationTask.tabs.samples'),
      children: renderSamples(),
    },
    {
      key: 'annotations',
      label: t('annotationTask.tabs.annotations'),
      children: renderAnnotations(),
    },
    {
      key: 'activity',
      label: t('annotationTask.tabs.activityLog'),
      children: renderActivityLog(),
    },
  ];

  // Action buttons
  const renderActions = () => {
    const actions: React.ReactNode[] = [];

    if (task.status !== 'completed' && task.status !== 'cancelled') {
      actions.push(
        <Button
          key="edit"
          icon={<EditOutlined />}
          onClick={() => onEdit(task.id)}
        >
          {t('common.actions.edit')}
        </Button>
      );

      actions.push(
        <Button
          key="assign"
          icon={<UserAddOutlined />}
          onClick={() => onAssign(task.id)}
        >
          {t('annotationTask.actions.assign')}
        </Button>
      );

      if (task.status === 'in_progress' && calculateProgress() === 100) {
        actions.push(
          <Button
            key="complete"
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => onComplete(task.id)}
          >
            {t('annotationTask.actions.complete')}
          </Button>
        );
      }

      actions.push(
        <Button
          key="cancel"
          danger
          icon={<StopOutlined />}
          onClick={() => onCancel(task.id)}
        >
          {t('annotationTask.actions.cancel')}
        </Button>
      );
    }

    return actions;
  };

  return (
    <Drawer
      title={
        <Space>
          <ClockCircleOutlined />
          {task.name}
        </Space>
      }
      placement="right"
      width={720}
      open={visible}
      onClose={onClose}
      extra={
        <Space>
          {renderActions()}
        </Space>
      }
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
      />
    </Drawer>
  );
};

export default TaskDetailDrawer;
