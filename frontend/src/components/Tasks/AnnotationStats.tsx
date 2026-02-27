/**
 * AnnotationStats Component
 * Displays annotation progress statistics and task list preview.
 * 
 * Performance optimizations:
 * - Wrapped with React.memo to prevent unnecessary re-renders
 * - Uses useMemo for computed values (remaining, task list items)
 * - Uses useCallback for click handlers
 * - Memoized style objects to avoid creating new objects on each render
 */
import React, { useMemo, useCallback, memo } from 'react';
import { Card, Progress, Statistic, Row, Col, Divider, Typography, Space, Badge } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AnnotationStatsProps, LabelStudioTask } from '@/types/task';

const { Text } = Typography;

// Memoized style constants to avoid creating new objects on each render
const cardStyle = { flex: 1 };
const progressContainerStyle = { marginBottom: 16 };
const taskListContainerStyle = { maxHeight: '200px', overflow: 'auto' as const };
const taskListTitleStyle = { marginBottom: 8, display: 'block' as const };
const completedValueStyle = { fontSize: '18px', color: '#52c41a' };
const remainingValueStyle = { fontSize: '18px', color: '#faad14' };
const currentValueStyle = { fontSize: '18px', color: '#1890ff' };
const defaultValueStyle = { fontSize: '18px' };
const checkIconStyle = { color: '#52c41a', fontSize: 12 };
const taskTextStyle = { fontSize: 12 };
const moreTasksStyle = { fontSize: 12 };

// Helper function to get task item style based on selection state
const getTaskItemStyle = (isSelected: boolean) => ({
  padding: '4px 8px',
  marginBottom: '4px',
  background: isSelected ? '#e6f7ff' : '#f5f5f5',
  borderRadius: '4px',
  cursor: 'pointer' as const,
  border: isSelected ? '1px solid #1890ff' : '1px solid transparent'
});

// Memoized task item component to prevent re-renders of unchanged items
interface TaskItemProps {
  task: LabelStudioTask;
  index: number;
  isSelected: boolean;
  onJumpToTask: (index: number) => void;
  taskLabel: string;
}

const TaskItem = memo<TaskItemProps>(({ task, index, isSelected, onJumpToTask, taskLabel }) => {
  const handleClick = useCallback(() => {
    onJumpToTask(index);
  }, [onJumpToTask, index]);

  const itemStyle = useMemo(() => getTaskItemStyle(isSelected), [isSelected]);

  return (
    <div 
      key={task.id}
      style={itemStyle}
      onClick={handleClick}
    >
      <Space size={4}>
        <Badge 
          status={task.is_labeled ? 'success' : 'processing'} 
          size="small"
        />
        <Text style={taskTextStyle}>
          {taskLabel} {index + 1}
        </Text>
        {task.is_labeled && (
          <CheckCircleOutlined style={checkIconStyle} />
        )}
      </Space>
    </div>
  );
});

TaskItem.displayName = 'TaskItem';

const AnnotationStatsComponent: React.FC<AnnotationStatsProps> = ({
  totalTasks,
  completedCount,
  currentTaskIndex,
  progress,
  tasks,
  onJumpToTask,
}) => {
  const { t } = useTranslation(['tasks', 'common']);
  
  // Memoize computed values
  const remaining = useMemo(() => totalTasks - completedCount, [totalTasks, completedCount]);
  const currentDisplay = useMemo(() => currentTaskIndex + 1, [currentTaskIndex]);
  const progressStatus = useMemo(() => progress === 100 ? 'success' : 'active', [progress]);
  
  // Memoize the visible tasks (first 10)
  const visibleTasks = useMemo(() => tasks.slice(0, 10), [tasks]);
  const hasMoreTasks = useMemo(() => tasks.length > 10, [tasks.length]);
  const moreTasksCount = useMemo(() => tasks.length - 10, [tasks.length]);

  // Memoize the task label for reuse
  const taskLabel = useMemo(() => t('annotate.task'), [t]);

  return (
    <Card title={t('annotate.annotationProgress')} style={cardStyle}>
      <div style={progressContainerStyle}>
        <Progress
          percent={progress}
          status={progressStatus}
          size="small"
          showInfo={false}
        />
      </div>
      
      <Row gutter={16}>
        <Col span={12}>
          <Statistic
            title={t('annotate.totalTasks')}
            value={totalTasks}
            valueStyle={defaultValueStyle}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={t('annotate.completed')}
            value={completedCount}
            valueStyle={completedValueStyle}
          />
        </Col>
      </Row>
      
      <Divider />
      
      <Row gutter={16}>
        <Col span={12}>
          <Statistic
            title={t('annotate.remaining')}
            value={remaining}
            valueStyle={remainingValueStyle}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={t('annotate.current')}
            value={currentDisplay}
            valueStyle={currentValueStyle}
          />
        </Col>
      </Row>

      <Divider />
      
      {/* Task list preview */}
      <div style={taskListContainerStyle}>
        <Text strong style={taskListTitleStyle}>
          {t('annotate.taskList')}:
        </Text>
        {visibleTasks.map((task, index) => (
          <TaskItem
            key={task.id}
            task={task}
            index={index}
            isSelected={index === currentTaskIndex}
            onJumpToTask={onJumpToTask}
            taskLabel={taskLabel}
          />
        ))}
        {hasMoreTasks && (
          <Text type="secondary" style={moreTasksStyle}>
            ... {t('annotate.moreTasks', { count: moreTasksCount })}
          </Text>
        )}
      </div>
    </Card>
  );
};

// Wrap with React.memo to prevent re-renders when props haven't changed
export const AnnotationStats = memo(AnnotationStatsComponent);

export default AnnotationStats;
