/**
 * AI Annotation Workflow Content
 * 
 * AI 智能标注工作流内容组件
 * 实现完整的循环工作流：数据来源 → 人工样本 → AI 学习 → 批量标注 → 效果验证 → 迭代循环
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Card, 
  Steps, 
  Space, 
  Typography, 
  Button, 
  Alert, 
  Select, 
  Table, 
  Progress, 
  Statistic, 
  Row, 
  Col,
  Tag,
  message,
  Spin
} from 'antd';
import {
  DatabaseOutlined,
  ExclamationCircleOutlined,
  ExperimentOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;
const { Option } = Select;

type WorkflowStep = 'data-source' | 'samples' | 'learning' | 'annotation' | 'validation';

interface DataSource {
  id: string;
  name: string;
  type: string;
  record_count: number;
  created_at: string;
}

interface SampleInfo {
  total_count: number;
  average_quality: number;
  annotation_types: string[];
  coverage_rate: number;
  quality_distribution: {
    high: number;
    medium: number;
    low: number;
  };
}

interface LearningProgress {
  job_id: string;
  status: string;
  error_message?: string;
  sample_count: number;
  patterns_identified: number;
  average_confidence: number;
  recommended_method: string | null;
  progress_percentage: number;
}

interface BatchProgress {
  job_id: string;
  status: string;
  error_message?: string;
  total_count: number;
  annotated_count: number;
  needs_review_count: number;
  average_confidence: number;
}

const AIAnnotationWorkflowContent: React.FC = () => {
  const { t } = useTranslation('aiAnnotation');
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('data-source');
  const [loading, setLoading] = useState(false);
  
  // Data source state
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [selectedDataSource, setSelectedDataSource] = useState<string | null>(null);
  
  // Sample state
  const [sampleInfo, setSampleInfo] = useState<SampleInfo | null>(null);
  
  // Learning state
  const [learningJobId, setLearningJobId] = useState<string | null>(null);
  const [learningProgress, setLearningProgress] = useState<LearningProgress | null>(null);
  
  // Batch annotation state
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  
  // Validation state
  const [validationResult, setValidationResult] = useState<any>(null);

  // Load data sources on mount
  useEffect(() => {
    loadDataSources();
  }, []);

  // Poll learning progress
  useEffect(() => {
    if (learningJobId && currentStep === 'learning') {
      const interval = setInterval(() => {
        fetchLearningProgress(learningJobId);
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [learningJobId, currentStep]);

  // Poll batch progress
  useEffect(() => {
    if (batchJobId && currentStep === 'annotation') {
      const interval = setInterval(() => {
        fetchBatchProgress(batchJobId);
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [batchJobId, currentStep]);

  const loadDataSources = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/annotation/workflow/data-sources');
      const data = await response.json();
      setDataSources(data.data_sources || []);
    } catch (error) {
      message.error(t('workflow.common.load_datasource_failed'));
    } finally {
      setLoading(false);
    }
  };

  const loadSampleInfo = async (dataSourceId: string) => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/annotation/workflow/annotated-samples?project_id=default&data_source_id=${dataSourceId}`
      );
      const data = await response.json();
      setSampleInfo(data);
    } catch (error) {
      message.error(t('workflow.common.load_samples_failed'));
    } finally {
      setLoading(false);
    }
  };

  const startAILearning = async () => {
    if (!sampleInfo || sampleInfo.total_count < 10) {
      message.warning(t('workflow.samples.min_samples_warning'));
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/annotation/workflow/ai-learn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'default',
          sample_ids: Array.from({ length: sampleInfo.total_count }, (_, i) => `sample_${i}`),
          annotation_type: 'entity',
        }),
      });
      const data = await response.json();
      setLearningJobId(data.job_id);
      setCurrentStep('learning');
      message.success(t('workflow.learning.started'));
    } catch (error) {
      message.error(t('workflow.learning.start_failed'));
    } finally {
      setLoading(false);
    }
  };

  const fetchLearningProgress = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/annotation/workflow/ai-learn/${jobId}`);
      const data = await response.json();
      setLearningProgress(data);
      
      if (data.status === 'completed') {
        message.success(t('workflow.learning.completed'));
      }
    } catch (error) {
      console.error('获取学习进度失败', error);
    }
  };

  const startBatchAnnotation = async () => {
    if (!learningJobId) {
      message.warning(t('workflow.learning.complete_first'));
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/annotation/workflow/batch-annotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'default',
          learning_job_id: learningJobId,
          target_dataset_id: selectedDataSource || 'ds_1',
          annotation_type: 'entity',
          confidence_threshold: 0.7,
        }),
      });
      const data = await response.json();
      setBatchJobId(data.job_id);
      setCurrentStep('annotation');
      message.success(t('workflow.batch.started'));
    } catch (error) {
      message.error(t('workflow.batch.start_failed'));
    } finally {
      setLoading(false);
    }
  };

  const fetchBatchProgress = async (jobId: string) => {
    try {
      const response = await fetch(`/api/v1/annotation/workflow/batch-annotate/${jobId}`);
      const data = await response.json();
      setBatchProgress(data);
      
      if (data.status === 'completed') {
        message.success(t('workflow.batch.completed'));
      }
    } catch (error) {
      console.error('获取批量标注进度失败', error);
    }
  };

  const validateEffect = async () => {
    if (!batchJobId) {
      message.warning(t('workflow.batch.complete_first'));
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/annotation/workflow/validate-effect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'default',
          batch_job_id: batchJobId,
          test_sample_count: 50,
          test_method: 'random',
        }),
      });
      const data = await response.json();
      setValidationResult(data);
      setCurrentStep('validation');
      message.success(t('workflow.validation.completed'));
    } catch (error) {
      message.error(t('workflow.validation.failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleDataSourceSelect = (dataSourceId: string) => {
    setSelectedDataSource(dataSourceId);
    loadSampleInfo(dataSourceId);
  };

  const handleNextFromDataSource = () => {
    if (!selectedDataSource) {
      message.warning(t('workflow.data_source.select_warning'));
      return;
    }
    setCurrentStep('samples');
  };

  const steps = [
    {
      title: t('workflow.steps.data_source'),
      icon: <DatabaseOutlined />,
      key: 'data-source' as WorkflowStep,
    },
    {
      title: t('workflow.steps.samples'),
      icon: <ExperimentOutlined />,
      key: 'samples' as WorkflowStep,
    },
    {
      title: t('workflow.steps.learning'),
      icon: <RobotOutlined />,
      key: 'learning' as WorkflowStep,
    },
    {
      title: t('workflow.steps.annotation'),
      icon: <SyncOutlined />,
      key: 'annotation' as WorkflowStep,
    },
    {
      title: t('workflow.steps.validation'),
      icon: <CheckCircleOutlined />,
      key: 'validation' as WorkflowStep,
    },
  ];

  const getCurrentStepIndex = () => {
    return steps.findIndex(step => step.key === currentStep);
  };

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={4}>
            <RobotOutlined style={{ marginRight: 8 }} />
            {t('workflow.title')}
          </Title>
          <Paragraph type="secondary">
            {t('workflow.description')}
          </Paragraph>
        </div>

        <Alert
          message={t('workflow.info_title')}
          description={t('workflow.info_description')}
          type="info"
          showIcon
        />

        <Card>
          <Steps
            current={getCurrentStepIndex()}
            items={steps.map(step => ({
              title: step.title,
              icon: step.icon,
            }))}
            style={{ marginBottom: 32 }}
          />

          <div style={{ minHeight: 400, padding: '24px 0' }}>
            {/* Step 1: Data Source Selection */}
            {currentStep === 'data-source' && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>{t('workflow.data_source.title')}</Title>
                <Paragraph type="secondary">
                  {t('workflow.data_source.description')}
                </Paragraph>
                
                <Select
                  style={{ width: '100%' }}
                  placeholder={t('workflow.data_source.placeholder')}
                  value={selectedDataSource}
                  onChange={handleDataSourceSelect}
                >
                  {dataSources.map(ds => (
                    <Option key={ds.id} value={ds.id}>
                      {ds.name} ({ds.record_count} {t('workflow.data_source.records')})
                    </Option>
                  ))}
                </Select>

                {selectedDataSource && (
                  <Alert
                    message={t('workflow.data_source.selected_title')}
                    description={t('workflow.data_source.selected_desc', { count: dataSources.find(ds => ds.id === selectedDataSource)?.record_count })}
                    type="success"
                    showIcon
                  />
                )}

                <Button 
                  type="primary" 
                  onClick={handleNextFromDataSource}
                  disabled={!selectedDataSource}
                >
                  {t('workflow.data_source.next_button')}
                </Button>
              </Space>
            )}

            {/* Step 2: Annotated Samples */}
            {currentStep === 'samples' && sampleInfo && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>{t('workflow.samples.title')}</Title>
                <Paragraph type="secondary">
                  {t('workflow.samples.description')}
                </Paragraph>

                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic title={t('workflow.samples.total_count')} value={sampleInfo.total_count} />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.samples.average_quality')} 
                      value={sampleInfo.average_quality} 
                      precision={2}
                      suffix="/ 1.0"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.samples.coverage_rate')} 
                      value={sampleInfo.coverage_rate * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.samples.high_quality')} 
                      value={sampleInfo.quality_distribution.high} 
                    />
                  </Col>
                </Row>

                {sampleInfo.total_count < 10 && (
                  <Alert
                    message={t('workflow.samples.insufficient_title')}
                    description={t('workflow.samples.insufficient_desc', { count: sampleInfo.total_count })}
                    type="warning"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('data-source')}>{t('workflow.common.previous_step')}</Button>
                  <Button 
                    type="primary" 
                    onClick={startAILearning}
                    disabled={sampleInfo.total_count < 10}
                  >
                    {t('workflow.samples.start_learning')}
                  </Button>
                </Space>
              </Space>
            )}

            {/* Step 3: AI Learning */}
            {currentStep === 'learning' && learningProgress && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>
                  {t('workflow.learning.title')}
                  {learningProgress.status === 'running' && (
                    <Tag color="processing" style={{ marginLeft: 8 }}>{t('workflow.common.running')}</Tag>
                  )}
                  {learningProgress.status === 'completed' && (
                    <Tag color="success" style={{ marginLeft: 8 }}>{t('workflow.common.completed')}</Tag>
                  )}
                  {learningProgress.status === 'failed' && (
                    <Tag color="error" style={{ marginLeft: 8 }}>{t('workflow.common.failed')}</Tag>
                  )}
                </Title>
                <Paragraph type="secondary">
                  {t('workflow.learning.description')}
                </Paragraph>

                <Card>
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong>{t('workflow.learning.progress_label')}</Text>
                      <Text type="secondary">{Math.round(learningProgress.progress_percentage)}%</Text>
                    </div>
                    <Progress 
                      percent={Math.round(learningProgress.progress_percentage)} 
                      status={learningProgress.status === 'completed' ? 'success' : learningProgress.status === 'failed' ? 'exception' : 'active'}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                    {learningProgress.status === 'running' && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('workflow.learning.estimated_time', { seconds: Math.round((100 - learningProgress.progress_percentage) / 25) })}
                      </Text>
                    )}
                  </Space>
                </Card>

                <Row gutter={16}>
                  <Col span={8}>
                    <Card>
                      <Statistic 
                        title={t('workflow.learning.sample_count')} 
                        value={learningProgress.sample_count}
                        prefix={<ExperimentOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic 
                        title={t('workflow.learning.patterns_identified')} 
                        value={learningProgress.patterns_identified}
                        prefix={<RobotOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic 
                        title={t('workflow.learning.average_confidence')} 
                        precision={2}
                        prefix={<CheckCircleOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                {learningProgress.recommended_method && (
                  <Alert
                    message={t('workflow.learning.recommended_method')}
                    description={t('workflow.learning.recommended_desc', { sampleCount: learningProgress.sample_count, patterns: learningProgress.patterns_identified, method: learningProgress.recommended_method })}
                    type="success"
                    showIcon
                  />
                )}

                {learningProgress.status === 'failed' && learningProgress.error_message && (
                  <Alert
                    message={t('workflow.learning.failed_title')}
                    description={learningProgress.error_message}
                    type="error"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('samples')}>{t('workflow.common.previous_step')}</Button>
                  <Button 
                    type="primary" 
                    onClick={startBatchAnnotation}
                    disabled={learningProgress.status !== 'completed'}
                    loading={learningProgress.status === 'running'}
                  >
                    {learningProgress.status === 'completed' ? t('workflow.learning.start_batch') : t('workflow.learning.in_progress')}
                  </Button>
                </Space>
              </Space>
            )}

            {/* Step 4: Batch Annotation */}
            {currentStep === 'annotation' && batchProgress && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>
                  {t('workflow.batch.title')}
                  {batchProgress.status === 'running' && (
                    <Tag color="processing" style={{ marginLeft: 8 }}>{t('workflow.common.running')}</Tag>
                  )}
                  {batchProgress.status === 'completed' && (
                    <Tag color="success" style={{ marginLeft: 8 }}>{t('workflow.common.completed')}</Tag>
                  )}
                  {batchProgress.status === 'failed' && (
                    <Tag color="error" style={{ marginLeft: 8 }}>{t('workflow.common.failed')}</Tag>
                  )}
                </Title>
                <Paragraph type="secondary">
                  {t('workflow.batch.description')}
                </Paragraph>

                <Card>
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong>{t('workflow.batch.progress_label')}</Text>
                      <Text type="secondary">
                        {batchProgress.annotated_count} / {batchProgress.total_count}
                      </Text>
                    </div>
                    <Progress 
                      percent={Math.round((batchProgress.annotated_count / batchProgress.total_count) * 100)} 
                      status={batchProgress.status === 'completed' ? 'success' : batchProgress.status === 'failed' ? 'exception' : 'active'}
                      strokeColor={{
                        '0%': '#108ee9',
                        '100%': '#87d068',
                      }}
                    />
                    {batchProgress.status === 'running' && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('workflow.batch.estimated_time', { seconds: Math.round((batchProgress.total_count - batchProgress.annotated_count) / 50) })}
                      </Text>
                    )}
                  </Space>
                </Card>

                <Row gutter={16}>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title={t('workflow.batch.total_tasks')} 
                        value={batchProgress.total_count}
                        prefix={<DatabaseOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title={t('workflow.batch.annotated')} 
                        value={batchProgress.annotated_count}
                        prefix={<CheckCircleOutlined />}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title={t('workflow.batch.needs_review')} 
                        value={batchProgress.needs_review_count}
                        prefix={<ExclamationCircleOutlined />}
                        valueStyle={{ color: '#cf1322' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title={t('workflow.batch.average_confidence')} 
                        precision={2}
                        prefix={<RobotOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                {batchProgress.status === 'failed' && batchProgress.error_message && (
                  <Alert
                    message={t('workflow.batch.failed_title')}
                    description={batchProgress.error_message}
                    type="error"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('learning')}>{t('workflow.common.previous_step')}</Button>
                  <Button 
                    type="primary" 
                    onClick={validateEffect}
                    disabled={batchProgress.status !== 'completed'}
                    loading={batchProgress.status === 'running'}
                  >
                    {batchProgress.status === 'completed' ? t('workflow.batch.validate_effect') : t('workflow.batch.in_progress')}
                  </Button>
                </Space>
              </Space>
            )}

            {/* Step 5: Effect Validation */}
            {currentStep === 'validation' && validationResult && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>{t('workflow.validation.title')}</Title>
                <Paragraph type="secondary">
                  {t('workflow.validation.description')}
                </Paragraph>

                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.validation.accuracy')} 
                      value={validationResult.metrics.accuracy * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.validation.recall')} 
                      value={validationResult.metrics.recall * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.validation.f1_score')} 
                      value={validationResult.metrics.f1_score * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title={t('workflow.validation.consistency')} 
                      value={validationResult.metrics.consistency * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                </Row>

                {validationResult.improvement_suggestions && validationResult.improvement_suggestions.length > 0 && (
                  <Alert
                    message={t('workflow.validation.suggestions_title')}
                    description={
                      <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                        {validationResult.improvement_suggestions.map((suggestion: string, index: number) => (
                          <li key={index}>{suggestion}</li>
                        ))}
                      </ul>
                    }
                    type="info"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('annotation')}>{t('workflow.common.previous_step')}</Button>
                  <Button 
                    type="primary" 
                    icon={<ReloadOutlined />}
                    onClick={() => {
                      // Reset state for new iteration
                      setCurrentStep('data-source');
                      setLearningJobId(null);
                      setBatchJobId(null);
                      setValidationResult(null);
                      message.info(t('workflow.validation.new_iteration_started'));
                    }}
                  >
                    {t('workflow.validation.start_new_iteration')}
                  </Button>
                </Space>
              </Space>
            )}
          </div>
        </Card>
      </Space>
    </Spin>
  );
};

export default AIAnnotationWorkflowContent;
