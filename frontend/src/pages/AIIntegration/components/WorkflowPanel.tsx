/**
 * Workflow Panel - 工作流面板
 * Displays workflow definition and allows data source toggle
 */

import React, { useState } from 'react';
import { Card, Radio, Steps, Empty, Spin, Tag, Space, Button } from 'antd';
import { DatabaseOutlined, FileTextOutlined, EyeOutlined, EditOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { WorkflowDefinition } from '../../../services/aiIntegrationApi';
import WorkflowVisualizer from './WorkflowVisualizer';

interface WorkflowPanelProps {
  workflow: WorkflowDefinition | null;
  generating: boolean;
  dataSource: 'governed' | 'raw';
  onDataSourceChange: (source: 'governed' | 'raw') => void;
}

const WorkflowPanel: React.FC<WorkflowPanelProps> = ({
  workflow,
  generating,
  dataSource,
  onDataSourceChange,
}) => {
  const { t } = useTranslation('aiIntegration');
  const [viewMode, setViewMode] = useState<'steps' | 'visual'>('steps');

  return (
    <Card
      title={t('workflowPlayground.workflow.title')}
      extra={
        workflow && (
          <Radio.Group value={dataSource} onChange={(e) => onDataSourceChange(e.target.value)}>
            <Radio.Button value="governed">
              <DatabaseOutlined /> {t('workflowPlayground.workflow.governed')}
            </Radio.Button>
            <Radio.Button value="raw">
              <FileTextOutlined /> {t('workflowPlayground.workflow.raw')}
            </Radio.Button>
          </Radio.Group>
        )
      }
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflowY: 'auto', padding: 16 }}
    >
      {generating && (
        <div style={{ textAlign: 'center', padding: 64 }}>
          <Spin size="large" tip={t('workflowPlayground.workflow.generating')} />
        </div>
      )}

      {!generating && !workflow && (
        <Empty
          description={t('workflowPlayground.workflow.noWorkflow')}
          style={{ marginTop: 64 }}
        />
      )}

      {!generating && workflow && (
        <div>
          <div style={{ marginBottom: 24 }}>
            <h3>{workflow.name}</h3>
            <p style={{ color: '#666' }}>{workflow.description}</p>
            <Space style={{ marginTop: 8 }}>
              <Tag color="blue">
                {t('workflowPlayground.workflow.dataSource')}: {dataSource === 'governed' ? t('workflowPlayground.workflow.governed') : t('workflowPlayground.workflow.raw')}
              </Tag>
              <Tag color="green">
                {workflow.steps.length} {t('workflowPlayground.workflow.steps')}
              </Tag>
            </Space>
            <div style={{ marginTop: 12 }}>
              <Button.Group>
                <Button
                  icon={<EditOutlined />}
                  type={viewMode === 'steps' ? 'primary' : 'default'}
                  onClick={() => setViewMode('steps')}
                >
                  {t('workflowPlayground.workflow.steps')}
                </Button>
                <Button
                  icon={<EyeOutlined />}
                  type={viewMode === 'visual' ? 'primary' : 'default'}
                  onClick={() => setViewMode('visual')}
                >
                  {t('workflowPlayground.workflow.visualize')}
                </Button>
              </Button.Group>
            </div>
          </div>

          {viewMode === 'steps' ? (
            <Steps
              direction="vertical"
              current={-1}
              items={workflow.steps.map((step, idx) => ({
                title: step.name,
                description: step.type,
                status: 'wait',
              }))}
            />
          ) : (
            <WorkflowVisualizer workflow={workflow} />
          )}
        </div>
      )}
    </Card>
  );
};

export default WorkflowPanel;
