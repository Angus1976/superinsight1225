/**
 * CurrentTaskInfo Component
 * Displays current task information including text content and status.
 * 
 * Performance optimizations:
 * - Wrapped with React.memo to prevent unnecessary re-renders
 * - Uses useMemo for computed values (tag color, status text)
 * - Memoized style objects to avoid creating new objects on each render
 */
import React, { useMemo, memo } from 'react';
import { Card, Typography, Space, Tag } from 'antd';
import { useTranslation } from 'react-i18next';
import type { CurrentTaskInfoProps } from '@/types/task';

const { Text } = Typography;

// Memoized style constants to avoid creating new objects on each render
const cardStyle = { marginBottom: 16 };
const textContainerStyle = { marginBottom: 16 };
const textBoxStyle = { 
  padding: '12px', 
  background: '#f5f5f5', 
  borderRadius: '6px',
  marginTop: '8px',
  maxHeight: '120px',
  overflow: 'auto' as const
};

const CurrentTaskInfoComponent: React.FC<CurrentTaskInfoProps> = ({ task }) => {
  const { t } = useTranslation(['tasks', 'common']);

  // Memoize computed values based on task.is_labeled
  const tagColor = useMemo(() => task.is_labeled ? 'green' : 'orange', [task.is_labeled]);
  const statusText = useMemo(
    () => task.is_labeled ? t('annotate.annotated') : t('annotate.toAnnotate'),
    [task.is_labeled, t]
  );

  // Memoize the task text to avoid unnecessary re-renders
  const taskText = useMemo(() => task.data.text, [task.data.text]);

  return (
    <Card title={t('annotate.currentTask')} style={cardStyle}>
      <div style={textContainerStyle}>
        <Text strong>{t('annotate.textToAnnotate')}:</Text>
        <div style={textBoxStyle}>
          {taskText}
        </div>
      </div>
      
      <Space>
        <Text strong>{t('annotate.annotationStatus')}:</Text>
        <Tag color={tagColor}>
          {statusText}
        </Tag>
      </Space>
    </Card>
  );
};

// Wrap with React.memo to prevent re-renders when props haven't changed
export const CurrentTaskInfo = memo(CurrentTaskInfoComponent);

export default CurrentTaskInfo;
