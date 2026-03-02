/**
 * AI Processing Tab — 统一管理结构化、向量化、语义化三种数据处理流程
 *
 * Sub-tabs:
 *   1. 结构化 (Structuring) — links to existing data-structuring workflow
 *   2. 向量化 (Vectorization) — file upload, job list, vector records
 *   3. 语义化 (Semantic) — file upload, job list, semantic records with filtering
 */

import React, { useState } from 'react';
import { Card, Tabs, Typography, Space, Button } from 'antd';
import {
  TableOutlined,
  ApartmentOutlined,
  NodeIndexOutlined,
  RocketOutlined,
  TagsOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import VectorizationContent from './VectorizationContent';
import SemanticContent from './SemanticContent';
import AIAnnotationWorkflowContent from './AIAnnotationWorkflowContent';
import AIAnnotationTaskList from './AIAnnotationTaskList';

const { Title, Paragraph } = Typography;

// ============================================================================
// Sub-tab content components
// ============================================================================

const StructuringContent: React.FC = () => {
  const { t } = useTranslation(['structuring', 'common']);
  const navigate = useNavigate();

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <div>
        <Title level={4}>
          <TableOutlined style={{ marginRight: 8 }} />
          {t('structuring:upload.title', { defaultValue: '结构化处理' })}
        </Title>
        <Paragraph type="secondary">
          {t('structuring:upload.description', {
            defaultValue: '上传非结构化文件，系统将通过 AI 自动分析并提取结构化数据。',
          })}
        </Paragraph>
      </div>
      <Button
        type="primary"
        icon={<RocketOutlined />}
        onClick={() => navigate('/data-structuring/upload')}
      >
        {t('common:action.goToUpload', { defaultValue: '前往上传页面' })}
      </Button>
    </Space>
  );
};

// ============================================================================
// AI Annotation Content with sub-tabs
// ============================================================================

const AIAnnotationContent: React.FC = () => {
  const { t } = useTranslation(['common']);
  const [annotationActiveKey, setAnnotationActiveKey] = useState('workflow');

  const annotationTabItems = [
    {
      key: 'workflow',
      label: t('common:aiProcessing.aiAnnotation.workflow', { defaultValue: '工作流' }),
      children: <AIAnnotationWorkflowContent />,
    },
    {
      key: 'tasks',
      label: t('common:aiProcessing.aiAnnotation.taskList', { defaultValue: '任务清单' }),
      children: <AIAnnotationTaskList />,
    },
  ];

  return (
    <Tabs
      activeKey={annotationActiveKey}
      onChange={setAnnotationActiveKey}
      items={annotationTabItems}
      tabBarStyle={{ marginBottom: 16 }}
    />
  );
};

// ============================================================================
// Main component
// ============================================================================

const AIProcessingTab: React.FC = () => {
  const { t } = useTranslation(['common']);
  const [activeKey, setActiveKey] = useState('structuring');

  const tabItems = [
    {
      key: 'structuring',
      label: (
        <Space>
          <TableOutlined />
          {t('common:aiProcessing.tabs.structuring', { defaultValue: '结构化' })}
        </Space>
      ),
      children: <StructuringContent />,
    },
    {
      key: 'vectorization',
      label: (
        <Space>
          <ApartmentOutlined />
          {t('common:aiProcessing.tabs.vectorization', { defaultValue: '向量化' })}
        </Space>
      ),
      children: <VectorizationContent />,
    },
    {
      key: 'semantic',
      label: (
        <Space>
          <NodeIndexOutlined />
          {t('common:aiProcessing.tabs.semantic', { defaultValue: '语义化' })}
        </Space>
      ),
      children: <SemanticContent />,
    },
    {
      key: 'ai-annotation',
      label: (
        <Space>
          <TagsOutlined />
          {t('common:aiProcessing.tabs.aiAnnotation', { defaultValue: 'AI 智能标注' })}
        </Space>
      ),
      children: <AIAnnotationContent />,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={2}>
            <RocketOutlined style={{ marginRight: 8 }} />
            {t('common:aiProcessing.title', { defaultValue: 'AI 数据处理' })}
          </Title>
          <Paragraph type="secondary">
            {t('common:aiProcessing.description', {
              defaultValue: '统一管理结构化、向量化、语义化三种数据处理流程。',
            })}
          </Paragraph>
        </div>

        <Card>
          <Tabs
            activeKey={activeKey}
            onChange={setActiveKey}
            size="large"
            items={tabItems}
            tabBarStyle={{ marginBottom: 24 }}
          />
        </Card>
      </Space>
    </div>
  );
};

export default AIProcessingTab;
