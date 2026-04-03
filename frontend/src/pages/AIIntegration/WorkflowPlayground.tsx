/**
 * Workflow Playground - 工作流实验场
 * Interactive playground for designing and testing workflows through conversation
 */

import React, { useState } from 'react';
import { Row, Col, message } from 'antd';
import { useTranslation } from 'react-i18next';
import ChatPanel from './components/ChatPanel';
import WorkflowPanel from './components/WorkflowPanel';
import ResultsPanel from './components/ResultsPanel';
import HistoryPanel from './components/HistoryPanel';
import {
  WorkflowDefinition,
  WorkflowExecutionResult,
  parseWorkflow,
  executeWorkflow,
  saveWorkflow,
  compareWorkflowResults,
} from '../../services/aiIntegrationApi';

const WorkflowPlayground: React.FC = () => {
  const { t } = useTranslation('aiIntegration');
  const [workflow, setWorkflow] = useState<WorkflowDefinition | null>(null);
  const [generating, setGenerating] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [dataSource, setDataSource] = useState<'governed' | 'raw'>('governed');
  const [result, setResult] = useState<WorkflowExecutionResult | null>(null);
  const [comparisonResult, setComparisonResult] = useState<{
    governed: WorkflowExecutionResult;
    raw: WorkflowExecutionResult;
  } | null>(null);
  const [history, setHistory] = useState<WorkflowExecutionResult[]>([]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    setGenerating(true);
    try {
      const parsedWorkflow = await parseWorkflow(text);
      setWorkflow(parsedWorkflow);
      message.success(t('workflowPlayground.messages.workflowGenerated'));
    } catch (error) {
      message.error(t('workflowPlayground.errors.generateFailed'));
      console.error('Failed to parse workflow:', error);
    } finally {
      setGenerating(false);
    }
  };

  const handleExecute = async () => {
    if (!workflow?.id) {
      message.warning('Please generate a workflow first');
      return;
    }

    setExecuting(true);
    setResult(null);
    try {
      const executionResult = await executeWorkflow(workflow.id, dataSource);
      setResult(executionResult);
      setHistory([executionResult, ...history]);
      message.success(t('workflowPlayground.messages.executionCompleted'));
    } catch (error) {
      message.error(t('workflowPlayground.errors.executeFailed'));
      console.error('Failed to execute workflow:', error);
    } finally {
      setExecuting(false);
    }
  };

  const handleSaveToProduction = async () => {
    if (!workflow) return;

    try {
      await saveWorkflow(workflow);
      message.success(t('workflowPlayground.messages.workflowSaved'));
    } catch (error) {
      message.error(t('workflowPlayground.errors.saveFailed'));
      console.error('Failed to save workflow:', error);
    }
  };

  const handleCompare = async () => {
    if (!workflow?.id) {
      message.warning('Please generate a workflow first');
      return;
    }

    setComparing(true);
    try {
      const comparison = await compareWorkflowResults(workflow.id);
      setComparisonResult(comparison);
      message.success('Comparison completed');
    } catch (error) {
      message.error('Failed to compare results');
      console.error('Failed to compare:', error);
    } finally {
      setComparing(false);
    }
  };

  return (
    <div style={{ padding: 24, height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
      <h2>{t('workflowPlayground.title')}</h2>
      <p style={{ color: '#666', marginBottom: 16 }}>{t('workflowPlayground.subtitle')}</p>

      <Row gutter={16} style={{ height: 'calc(100% - 80px)' }}>
        <Col span={8} style={{ height: '100%' }}>
          <ChatPanel onSendMessage={handleSendMessage} generating={generating} />
        </Col>

        <Col span={8} style={{ height: '100%' }}>
          <WorkflowPanel
            workflow={workflow}
            generating={generating}
            dataSource={dataSource}
            onDataSourceChange={setDataSource}
          />
        </Col>

        <Col span={8} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, marginBottom: 16, overflow: 'hidden' }}>
            <ResultsPanel
              result={result}
              executing={executing}
              comparing={comparing}
              comparisonResult={comparisonResult}
              onExecute={handleExecute}
              onCompare={handleCompare}
              onSave={handleSaveToProduction}
            />
          </div>
          <div style={{ height: '40%', overflow: 'hidden' }}>
            <HistoryPanel history={history} />
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default WorkflowPlayground;
