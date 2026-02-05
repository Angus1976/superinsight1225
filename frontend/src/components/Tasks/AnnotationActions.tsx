/**
 * AnnotationActions Component
 * Action buttons for annotation workflow (next, skip, sync).
 * 
 * Performance optimizations:
 * - Wrapped with React.memo to prevent unnecessary re-renders
 * - Uses useMemo for computed values (isNextDisabled)
 * - Memoized style objects to avoid creating new objects on each render
 * - Callback props should be stable (wrapped with useCallback in parent)
 */
import React, { useMemo, memo } from 'react';
import { Card, Button, Space } from 'antd';
import { CheckCircleOutlined, StepForwardOutlined, SaveOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AnnotationActionsProps } from '@/types/task';

// Memoized style constants to avoid creating new objects on each render
const cardStyle = { marginBottom: 16 };
const spaceStyle = { width: '100%' };

const AnnotationActionsComponent: React.FC<AnnotationActionsProps> = ({
  currentTask,
  syncInProgress,
  onNextTask,
  onSkipTask,
  onSyncProgress,
}) => {
  const { t } = useTranslation(['tasks', 'common']);

  // Memoize the disabled state for next button
  const isNextDisabled = useMemo(() => !currentTask.is_labeled, [currentTask.is_labeled]);

  return (
    <Card title={t('annotate.operations')} style={cardStyle}>
      <Space direction="vertical" style={spaceStyle}>
        <Button
          type="primary"
          icon={<CheckCircleOutlined />}
          block
          disabled={isNextDisabled}
          onClick={onNextTask}
        >
          {t('annotate.nextTask')}
        </Button>
        
        <Button
          icon={<StepForwardOutlined />}
          block
          onClick={onSkipTask}
        >
          {t('annotate.skipTask')}
        </Button>
        
        <Button
          icon={<SaveOutlined />}
          block
          loading={syncInProgress}
          onClick={onSyncProgress}
        >
          {t('annotate.manualSync')}
        </Button>
      </Space>
    </Card>
  );
};

// Wrap with React.memo to prevent re-renders when props haven't changed
export const AnnotationActions = memo(AnnotationActionsComponent);

export default AnnotationActions;
