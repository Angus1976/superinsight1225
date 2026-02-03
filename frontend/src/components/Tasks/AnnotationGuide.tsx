/**
 * AnnotationGuide Component
 * 
 * Displays guidance information for Label Studio annotation workflow.
 * Shows instructions for users on how to use Label Studio in a new window.
 * 
 * Performance optimizations:
 * - Wrapped with React.memo to prevent unnecessary re-renders
 * - Uses useMemo for computed values (subTitle content)
 * - Callback props should be stable (wrapped with useCallback in parent)
 */
import React, { useMemo, memo } from 'react';
import { Result, Button } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AnnotationGuideProps } from '@/types/task';

// Memoized icon style to avoid creating new object on each render
const iconStyle = { color: '#1890ff' };

const AnnotationGuideComponent: React.FC<AnnotationGuideProps> = ({
  projectId,
  currentTaskIndex,
  totalTasks,
  onOpenLabelStudio,
  onBackToTask,
}) => {
  const { t } = useTranslation(['tasks', 'common']);

  // Memoize the subTitle content to avoid recreating on each render
  const subTitleContent = useMemo(() => (
    <div style={{ maxWidth: 600 }}>
      <p>{t('annotate.description')}</p>
      <p style={{ marginTop: 16, fontSize: 14, color: '#666' }}>
        {t('annotate.instructions')}
      </p>
      <ul style={{ textAlign: 'left', display: 'inline-block', marginTop: 8 }}>
        <li>{t('tasks.annotate.features.viewTasks')}</li>
        <li>{t('tasks.annotate.features.labelAll')}</li>
        <li>{t('tasks.annotate.features.labelSingle')}</li>
        <li>{t('tasks.annotate.features.shortcuts')}</li>
      </ul>
      <p style={{ marginTop: 16, fontSize: 12, color: '#999' }}>
        {t('tasks.annotate.projectInfo', { 
          projectId, 
          current: currentTaskIndex + 1, 
          total: totalTasks 
        })}
      </p>
    </div>
  ), [t, projectId, currentTaskIndex, totalTasks]);

  // Memoize the extra buttons array to avoid recreating on each render
  const extraButtons = useMemo(() => [
    <Button
      key="open"
      type="primary"
      size="large"
      onClick={onOpenLabelStudio}
    >
      {t('tasks.annotate.openLabelStudio')}
    </Button>,
    <Button
      key="back"
      onClick={onBackToTask}
    >
      {t('annotate.backToTask')}
    </Button>,
  ], [t, onOpenLabelStudio, onBackToTask]);

  // Memoize the icon to avoid recreating on each render
  const icon = useMemo(() => <InfoCircleOutlined style={iconStyle} />, []);

  return (
    <Result
      icon={icon}
      title={t('annotate.title')}
      subTitle={subTitleContent}
      extra={extraButtons}
    />
  );
};

// Wrap with React.memo to prevent re-renders when props haven't changed
export const AnnotationGuide = memo(AnnotationGuideComponent);

export default AnnotationGuide;
