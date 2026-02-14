/**
 * Workflow Visualizer - 工作流可视化
 * Visual representation of workflow steps
 */

import React from 'react';
import { Card } from 'antd';
import { WorkflowDefinition } from '../../../services/aiIntegrationApi';

interface WorkflowVisualizerProps {
  workflow: WorkflowDefinition;
}

const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({ workflow }) => {
  return (
    <Card size="small" style={{ marginTop: 16 }}>
      <svg width="100%" height="300" style={{ background: '#fafafa' }}>
        {workflow.steps.map((step, idx) => {
          const x = 50;
          const y = 50 + idx * 60;
          const nextY = y + 60;

          return (
            <g key={step.id}>
              {/* Step box */}
              <rect
                x={x}
                y={y}
                width="200"
                height="40"
                fill="#1890ff"
                stroke="#096dd9"
                strokeWidth="2"
                rx="4"
              />
              <text x={x + 100} y={y + 25} textAnchor="middle" fill="white" fontSize="14">
                {step.name}
              </text>

              {/* Arrow to next step */}
              {idx < workflow.steps.length - 1 && (
                <>
                  <line
                    x1={x + 100}
                    y1={y + 40}
                    x2={x + 100}
                    y2={nextY}
                    stroke="#096dd9"
                    strokeWidth="2"
                  />
                  <polygon
                    points={`${x + 100},${nextY} ${x + 95},${nextY - 5} ${x + 105},${nextY - 5}`}
                    fill="#096dd9"
                  />
                </>
              )}
            </g>
          );
        })}
      </svg>
    </Card>
  );
};

export default WorkflowVisualizer;
