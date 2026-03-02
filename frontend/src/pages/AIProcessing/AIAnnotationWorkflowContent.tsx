/**
 * AI Annotation Workflow Content
 * 
 * AI 智能标注工作流内容组件
 * 实现完整的循环工作流：数据来源 → 人工样本 → AI 学习 → 批量标注 → 效果验证 → 迭代循环
 */

import React, { useState, useEffect } from 'react';
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
      message.error('加载数据源失败');
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
      message.error('加载样本信息失败');
    } finally {
      setLoading(false);
    }
  };

  const startAILearning = async () => {
    if (!sampleInfo || sampleInfo.total_count < 10) {
      message.warning('至少需要 10 个已标注样本才能开始 AI 学习');
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
      message.success('AI 学习已启动');
    } catch (error) {
      message.error('启动 AI 学习失败');
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
        message.success('AI 学习完成');
      }
    } catch (error) {
      console.error('获取学习进度失败', error);
    }
  };

  const startBatchAnnotation = async () => {
    if (!learningJobId) {
      message.warning('请先完成 AI 学习');
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
      message.success('批量标注已启动');
    } catch (error) {
      message.error('启动批量标注失败');
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
        message.success('批量标注完成');
      }
    } catch (error) {
      console.error('获取批量标注进度失败', error);
    }
  };

  const validateEffect = async () => {
    if (!batchJobId) {
      message.warning('请先完成批量标注');
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
      message.success('效果验证完成');
    } catch (error) {
      message.error('效果验证失败');
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
      message.warning('请先选择数据源');
      return;
    }
    setCurrentStep('samples');
  };

  const steps = [
    {
      title: '数据来源',
      icon: <DatabaseOutlined />,
      key: 'data-source' as WorkflowStep,
    },
    {
      title: '人工样本',
      icon: <ExperimentOutlined />,
      key: 'samples' as WorkflowStep,
    },
    {
      title: 'AI 学习',
      icon: <RobotOutlined />,
      key: 'learning' as WorkflowStep,
    },
    {
      title: '批量标注',
      icon: <SyncOutlined />,
      key: 'annotation' as WorkflowStep,
    },
    {
      title: '效果验证',
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
            AI 智能标注工作流
          </Title>
          <Paragraph type="secondary">
            通过 AI 学习人工标注样本，实现批量自动标注，并持续迭代优化标注质量。
          </Paragraph>
        </div>

        <Alert
          message="工作流说明"
          description="完整的 AI 标注循环：选择数据来源 → 提供人工标注样本（至少 10 个）→ AI 学习标注模式 → 批量自动标注 → 验证标注效果 → 开始新一轮迭代"
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
                <Title level={5}>选择数据来源</Title>
                <Paragraph type="secondary">
                  选择需要进行 AI 标注的数据源（非结构化处理后的数据或原始数据）
                </Paragraph>
                
                <Select
                  style={{ width: '100%' }}
                  placeholder="选择数据源"
                  value={selectedDataSource}
                  onChange={handleDataSourceSelect}
                >
                  {dataSources.map(ds => (
                    <Option key={ds.id} value={ds.id}>
                      {ds.name} ({ds.record_count} 条记录)
                    </Option>
                  ))}
                </Select>

                {selectedDataSource && (
                  <Alert
                    message="数据源已选择"
                    description={`已选择数据源，包含 ${dataSources.find(ds => ds.id === selectedDataSource)?.record_count} 条记录`}
                    type="success"
                    showIcon
                  />
                )}

                <Button 
                  type="primary" 
                  onClick={handleNextFromDataSource}
                  disabled={!selectedDataSource}
                >
                  下一步：查看人工样本
                </Button>
              </Space>
            )}

            {/* Step 2: Annotated Samples */}
            {currentStep === 'samples' && sampleInfo && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>人工标注样本</Title>
                <Paragraph type="secondary">
                  提供至少 10 个高质量的人工标注样本，AI 将学习这些样本的标注模式
                </Paragraph>

                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic title="样本总数" value={sampleInfo.total_count} />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="平均质量" 
                      value={sampleInfo.average_quality} 
                      precision={2}
                      suffix="/ 1.0"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="覆盖率" 
                      value={sampleInfo.coverage_rate * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="高质量样本" 
                      value={sampleInfo.quality_distribution.high} 
                    />
                  </Col>
                </Row>

                {sampleInfo.total_count < 10 && (
                  <Alert
                    message="样本数量不足"
                    description={`当前只有 ${sampleInfo.total_count} 个样本，至少需要 10 个样本才能开始 AI 学习`}
                    type="warning"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('data-source')}>上一步</Button>
                  <Button 
                    type="primary" 
                    onClick={startAILearning}
                    disabled={sampleInfo.total_count < 10}
                  >
                    开始 AI 学习
                  </Button>
                </Space>
              </Space>
            )}

            {/* Step 3: AI Learning */}
            {currentStep === 'learning' && learningProgress && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>
                  AI 学习中
                  {learningProgress.status === 'running' && (
                    <Tag color="processing" style={{ marginLeft: 8 }}>进行中</Tag>
                  )}
                  {learningProgress.status === 'completed' && (
                    <Tag color="success" style={{ marginLeft: 8 }}>已完成</Tag>
                  )}
                  {learningProgress.status === 'failed' && (
                    <Tag color="error" style={{ marginLeft: 8 }}>失败</Tag>
                  )}
                </Title>
                <Paragraph type="secondary">
                  AI 正在分析人工标注样本，识别标注模式和特征...
                </Paragraph>

                <Card>
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong>学习进度</Text>
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
                        预计剩余时间：{Math.round((100 - learningProgress.progress_percentage) / 25)} 秒
                      </Text>
                    )}
                  </Space>
                </Card>

                <Row gutter={16}>
                  <Col span={8}>
                    <Card>
                      <Statistic 
                        title="样本数量" 
                        value={learningProgress.sample_count}
                        prefix={<ExperimentOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic 
                        title="识别模式" 
                        value={learningProgress.patterns_identified}
                        prefix={<RobotOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic 
                        title="平均置信度" 
                        value={learningProgress.average_confidence} 
                        precision={2}
                        prefix={<CheckCircleOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                {learningProgress.recommended_method && (
                  <Alert
                    message="推荐方法"
                    description={`通过分析 ${learningProgress.sample_count} 个样本，识别出 ${learningProgress.patterns_identified} 个标注模式，推荐使用 ${learningProgress.recommended_method} 方法进行标注`}
                    type="success"
                    showIcon
                  />
                )}

                {learningProgress.status === 'failed' && learningProgress.error_message && (
                  <Alert
                    message="学习失败"
                    description={learningProgress.error_message}
                    type="error"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('samples')}>上一步</Button>
                  <Button 
                    type="primary" 
                    onClick={startBatchAnnotation}
                    disabled={learningProgress.status !== 'completed'}
                    loading={learningProgress.status === 'running'}
                  >
                    {learningProgress.status === 'completed' ? '开始批量标注' : '学习中...'}
                  </Button>
                </Space>
              </Space>
            )}

            {/* Step 4: Batch Annotation */}
            {currentStep === 'annotation' && batchProgress && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>
                  批量标注
                  {batchProgress.status === 'running' && (
                    <Tag color="processing" style={{ marginLeft: 8 }}>进行中</Tag>
                  )}
                  {batchProgress.status === 'completed' && (
                    <Tag color="success" style={{ marginLeft: 8 }}>已完成</Tag>
                  )}
                  {batchProgress.status === 'failed' && (
                    <Tag color="error" style={{ marginLeft: 8 }}>失败</Tag>
                  )}
                </Title>
                <Paragraph type="secondary">
                  AI 正在对目标数据集进行批量自动标注...
                </Paragraph>

                <Card>
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong>标注进度</Text>
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
                        预计剩余时间：{Math.round((batchProgress.total_count - batchProgress.annotated_count) / 50)} 秒
                      </Text>
                    )}
                  </Space>
                </Card>

                <Row gutter={16}>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="总任务数" 
                        value={batchProgress.total_count}
                        prefix={<DatabaseOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="已标注" 
                        value={batchProgress.annotated_count}
                        prefix={<CheckCircleOutlined />}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="需要审核" 
                        value={batchProgress.needs_review_count}
                        prefix={<ExclamationCircleOutlined />}
                        valueStyle={{ color: '#cf1322' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="平均置信度" 
                        value={batchProgress.average_confidence} 
                        precision={2}
                        prefix={<RobotOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                {batchProgress.status === 'failed' && batchProgress.error_message && (
                  <Alert
                    message="标注失败"
                    description={batchProgress.error_message}
                    type="error"
                    showIcon
                  />
                )}

                <Space>
                  <Button onClick={() => setCurrentStep('learning')}>上一步</Button>
                  <Button 
                    type="primary" 
                    onClick={validateEffect}
                    disabled={batchProgress.status !== 'completed'}
                    loading={batchProgress.status === 'running'}
                  >
                    {batchProgress.status === 'completed' ? '验证效果' : '标注中...'}
                  </Button>
                </Space>
              </Space>
            )}

            {/* Step 5: Effect Validation */}
            {currentStep === 'validation' && validationResult && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Title level={5}>效果验证</Title>
                <Paragraph type="secondary">
                  验证 AI 标注效果，查看准确率、召回率、F1 分数等指标
                </Paragraph>

                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic 
                      title="准确率" 
                      value={validationResult.metrics.accuracy * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="召回率" 
                      value={validationResult.metrics.recall * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="F1 分数" 
                      value={validationResult.metrics.f1_score * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic 
                      title="一致性" 
                      value={validationResult.metrics.consistency * 100} 
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                </Row>

                {validationResult.improvement_suggestions && validationResult.improvement_suggestions.length > 0 && (
                  <Alert
                    message="改进建议"
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
                  <Button onClick={() => setCurrentStep('annotation')}>上一步</Button>
                  <Button 
                    type="primary" 
                    icon={<ReloadOutlined />}
                    onClick={() => {
                      // Reset state for new iteration
                      setCurrentStep('data-source');
                      setLearningJobId(null);
                      setBatchJobId(null);
                      setValidationResult(null);
                      message.info('开始新一轮迭代');
                    }}
                  >
                    开始新迭代
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
