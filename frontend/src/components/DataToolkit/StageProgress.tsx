import React from 'react';
import { Steps, Progress } from 'antd';
import { useTranslation } from 'react-i18next';

interface Stage {
  name: string;
  status: 'wait' | 'process' | 'finish' | 'error';
}

interface StageProgressProps {
  stages: Stage[];
  currentStage: number;
  overallProgress: number;
}

export const StageProgress: React.FC<StageProgressProps> = ({
  stages,
  currentStage,
  overallProgress,
}) => {
  const { t } = useTranslation('dataToolkit');

  return (
    <div>
      <Progress
        percent={overallProgress}
        status={overallProgress === 100 ? 'success' : 'active'}
      />
      <Steps
        current={currentStage}
        size="small"
        style={{ marginTop: 16 }}
        items={stages.map((stage) => ({
          title: stage.name,
          status: stage.status,
        }))}
      />
    </div>
  );
};
