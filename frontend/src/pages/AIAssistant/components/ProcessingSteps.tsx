/**
 * ProcessingSteps — shows scrolling status messages + progress bar
 * during AI response generation.
 */
import React, { useEffect, useRef } from 'react';
import { Progress, Typography } from 'antd';
import {
  CheckCircleFilled,
  LoadingOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface StatusStep {
  text: string;
  progress?: number;
  ts: number;
}

interface ProcessingStepsProps {
  steps: StatusStep[];
  visible: boolean;
}

const ProcessingSteps: React.FC<ProcessingStepsProps> = ({ steps, visible }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps.length]);

  if (!visible || steps.length === 0) return null;

  const latest = steps[steps.length - 1];
  const pct = latest.progress ?? 0;

  return (
    <div className="processing-steps">
      <Progress
        percent={pct}
        size="small"
        showInfo={false}
        strokeColor={{ from: '#1890ff', to: '#52c41a' }}
        style={{ marginBottom: 8 }}
      />
      <div className="processing-steps-list">
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;
          return (
            <div
              key={step.ts}
              className={`processing-step ${isLast ? 'processing-step-active' : 'processing-step-done'}`}
            >
              {isLast ? (
                <LoadingOutlined style={{ color: '#1890ff', marginRight: 6 }} />
              ) : (
                <CheckCircleFilled style={{ color: '#52c41a', marginRight: 6 }} />
              )}
              <Text
                type={isLast ? undefined : 'secondary'}
                style={{ fontSize: 12 }}
              >
                {step.text}
              </Text>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default ProcessingSteps;
