/**
 * A/B Testing Panel Component
 *
 * Provides A/B testing configuration and results visualization:
 * - Create and manage A/B tests between engines
 * - Traffic split configuration
 * - Metrics selection
 * - Real-time test results
 * - Statistical significance analysis
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  Slider,
  InputNumber,
  Button,
  Space,
  Row,
  Col,
  Statistic,
  Alert,
  Divider,
  Tag,
  Table,
  Progress,
  Switch,
  Modal,
  message,
  Tooltip,
  Badge,
} from 'antd';
import {
  ExperimentOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  LineChartOutlined,
  PercentageOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  DeleteOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';

import type { EngineConfig } from '@/pages/AIAnnotation/EngineConfiguration';

interface ABTestingPanelProps {
  engines: EngineConfig[];
  loading?: boolean;
}

interface ABTest {
  id: string;
  name: string;
  engineA: string;
  engineB: string;
  trafficSplit: number;
  sampleSize: number;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'stopped';
  metrics: string[];
  startedAt?: string;
  completedAt?: string;
  results?: ABTestResults;
}

interface ABTestResults {
  engineA: {
    name: string;
    samples: number;
    accuracy: number;
    consistency: number;
    completeness: number;
    recall: number;
    avgLatency: number;
    totalCost: number;
  };
  engineB: {
    name: string;
    samples: number;
    accuracy: number;
    consistency: number;
    completeness: number;
    recall: number;
    avgLatency: number;
    totalCost: number;
  };
  winner?: 'A' | 'B' | 'tie';
  confidence: number;
  pValue: number;
}

const ABTestingPanel: React.FC<ABTestingPanelProps> = ({ engines, loading = false }) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [form] = Form.useForm();
  const [tests, setTests] = useState<ABTest[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTest, setEditingTest] = useState<ABTest | null>(null);
  const [resultsModalVisible, setResultsModalVisible] = useState(false);
  const [selectedResults, setSelectedResults] = useState<ABTestResults | null>(null);

  const availableMetrics = [
    { value: 'accuracy', label: t('ai_annotation:metrics.accuracy') },
    { value: 'consistency', label: t('ai_annotation:metrics.consistency') },
    { value: 'completeness', label: t('ai_annotation:metrics.completeness') },
    { value: 'recall', label: t('ai_annotation:metrics.recall') },
    { value: 'latency', label: t('ai_annotation:metrics.latency') },
    { value: 'cost', label: t('ai_annotation:metrics.cost') },
  ];

  useEffect(() => {
    loadTests();
  }, []);

  const loadTests = async () => {
    try {
      const response = await fetch('/api/v1/annotation/ab-tests');
      if (!response.ok) return;
      const data = await response.json();
      setTests(data.tests || []);
    } catch (error) {
      console.error('Failed to load A/B tests:', error);
    }
  };

  const handleCreateTest = () => {
    setEditingTest(null);
    form.resetFields();
    form.setFieldsValue({
      trafficSplit: 50,
      sampleSize: 1000,
      metrics: ['accuracy', 'consistency', 'completeness', 'recall'],
    });
    setModalVisible(true);
  };

  const handleEditTest = (test: ABTest) => {
    setEditingTest(test);
    form.setFieldsValue(test);
    setModalVisible(true);
  };

  const handleSaveTest = async () => {
    try {
      const values = await form.validateFields();
      const testData: ABTest = editingTest
        ? { ...editingTest, ...values }
        : { ...values, status: 'draft' };

      const method = editingTest ? 'PUT' : 'POST';
      const url = editingTest
        ? `/api/v1/annotation/ab-tests/${editingTest.id}`
        : '/api/v1/annotation/ab-tests';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(testData),
      });

      if (!response.ok) throw new Error('Failed to save test');

      message.success(t('ai_annotation:messages.test_saved'));
      setModalVisible(false);
      await loadTests();
    } catch (error) {
      message.error(t('ai_annotation:errors.save_test_failed'));
      console.error('Failed to save test:', error);
    }
  };

  const handleStartTest = async (testId: string) => {
    try {
      const response = await fetch(`/api/v1/annotation/ab-tests/${testId}/start`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to start test');
      message.success(t('ai_annotation:messages.test_started'));
      await loadTests();
    } catch (error) {
      message.error(t('ai_annotation:errors.start_test_failed'));
      console.error('Failed to start test:', error);
    }
  };

  const handlePauseTest = async (testId: string) => {
    try {
      const response = await fetch(`/api/v1/annotation/ab-tests/${testId}/pause`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to pause test');
      message.success(t('ai_annotation:messages.test_paused'));
      await loadTests();
    } catch (error) {
      message.error(t('ai_annotation:errors.pause_test_failed'));
      console.error('Failed to pause test:', error);
    }
  };

  const handleStopTest = async (testId: string) => {
    Modal.confirm({
      title: t('ai_annotation:confirm.stop_test_title'),
      content: t('ai_annotation:confirm.stop_test_content'),
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/annotation/ab-tests/${testId}/stop`, {
            method: 'POST',
          });
          if (!response.ok) throw new Error('Failed to stop test');
          message.success(t('ai_annotation:messages.test_stopped'));
          await loadTests();
        } catch (error) {
          message.error(t('ai_annotation:errors.stop_test_failed'));
          console.error('Failed to stop test:', error);
        }
      },
    });
  };

  const handleDeleteTest = async (testId: string) => {
    Modal.confirm({
      title: t('ai_annotation:confirm.delete_test_title'),
      content: t('ai_annotation:confirm.delete_test_content'),
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/annotation/ab-tests/${testId}`, {
            method: 'DELETE',
          });
          if (!response.ok) throw new Error('Failed to delete test');
          message.success(t('ai_annotation:messages.test_deleted'));
          await loadTests();
        } catch (error) {
          message.error(t('ai_annotation:errors.delete_test_failed'));
          console.error('Failed to delete test:', error);
        }
      },
    });
  };

  const handleViewResults = (test: ABTest) => {
    if (test.results) {
      setSelectedResults(test.results);
      setResultsModalVisible(true);
    }
  };

  const getStatusColor = (status: ABTest['status']): string => {
    switch (status) {
      case 'running':
        return 'processing';
      case 'completed':
        return 'success';
      case 'paused':
        return 'warning';
      case 'stopped':
        return 'error';
      default:
        return 'default';
    }
  };

  const getEngineName = (engineId: string): string => {
    const engine = engines.find((e) => e.id === engineId);
    return engine ? `${engine.engineType} (${engine.model})` : engineId;
  };

  const columns: ColumnsType<ABTest> = [
    {
      title: t('ai_annotation:columns.test_name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: ABTest) => (
        <Space direction="vertical" size={0}>
          <strong>{name}</strong>
          <Tag color={getStatusColor(record.status)}>
            {t(`ai_annotation:test_status.${record.status}`)}
          </Tag>
        </Space>
      ),
    },
    {
      title: t('ai_annotation:columns.engines'),
      key: 'engines',
      render: (_, record: ABTest) => (
        <Space direction="vertical" size="small">
          <div>
            <Tag color="blue">A:</Tag> {getEngineName(record.engineA)}
          </div>
          <div>
            <Tag color="green">B:</Tag> {getEngineName(record.engineB)}
          </div>
        </Space>
      ),
    },
    {
      title: t('ai_annotation:columns.traffic_split'),
      dataIndex: 'trafficSplit',
      key: 'trafficSplit',
      render: (split: number) => (
        <Tooltip title={`A: ${split}% / B: ${100 - split}%`}>
          <Progress
            percent={split}
            success={{ percent: 100 - split }}
            showInfo={false}
            strokeWidth={20}
          />
        </Tooltip>
      ),
    },
    {
      title: t('ai_annotation:columns.progress'),
      key: 'progress',
      render: (_, record: ABTest) => {
        const samplesCollected =
          (record.results?.engineA.samples || 0) + (record.results?.engineB.samples || 0);
        const percent = (samplesCollected / record.sampleSize) * 100;
        return (
          <div>
            <Progress percent={percent} />
            <div style={{ fontSize: 12, color: '#999' }}>
              {samplesCollected} / {record.sampleSize} {t('ai_annotation:labels.samples')}
            </div>
          </div>
        );
      },
    },
    {
      title: t('ai_annotation:columns.winner'),
      key: 'winner',
      render: (_, record: ABTest) => {
        if (!record.results || record.status !== 'completed') {
          return <Tag color="default">{t('ai_annotation:labels.pending')}</Tag>;
        }
        if (record.results.winner === 'tie') {
          return <Tag color="default">{t('ai_annotation:labels.tie')}</Tag>;
        }
        return (
          <Tag color="success">
            <CheckCircleOutlined />{' '}
            {record.results.winner === 'A'
              ? getEngineName(record.engineA)
              : getEngineName(record.engineB)}
          </Tag>
        );
      },
    },
    {
      title: t('common:columns.actions'),
      key: 'actions',
      render: (_, record: ABTest) => (
        <Space>
          {record.status === 'draft' && (
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartTest(record.id)}
            >
              {t('ai_annotation:actions.start')}
            </Button>
          )}
          {record.status === 'running' && (
            <Button
              type="link"
              icon={<PauseCircleOutlined />}
              onClick={() => handlePauseTest(record.id)}
            >
              {t('ai_annotation:actions.pause')}
            </Button>
          )}
          {record.status === 'paused' && (
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStartTest(record.id)}
            >
              {t('ai_annotation:actions.resume')}
            </Button>
          )}
          {['running', 'paused'].includes(record.status) && (
            <Button
              type="link"
              danger
              icon={<StopOutlined />}
              onClick={() => handleStopTest(record.id)}
            >
              {t('ai_annotation:actions.stop')}
            </Button>
          )}
          {record.results && (
            <Button
              type="link"
              icon={<BarChartOutlined />}
              onClick={() => handleViewResults(record)}
            >
              {t('ai_annotation:actions.view_results')}
            </Button>
          )}
          {record.status === 'draft' && (
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteTest(record.id)}
            >
              {t('common:actions.delete')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const runningTests = tests.filter((t) => t.status === 'running');
  const completedTests = tests.filter((t) => t.status === 'completed');

  return (
    <div className="ab-testing-panel">
      <Card>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.total_tests')}
              value={tests.length}
              prefix={<ExperimentOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.running_tests')}
              value={runningTests.length}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.completed_tests')}
              value={completedTests.length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateTest}
              block
              size="large"
            >
              {t('ai_annotation:actions.create_test')}
            </Button>
          </Col>
        </Row>

        {runningTests.length > 0 && (
          <Alert
            message={t('ai_annotation:alerts.tests_running_title')}
            description={t('ai_annotation:alerts.tests_running_desc', {
              count: runningTests.length,
            })}
            type="info"
            showIcon
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        <Table
          columns={columns}
          dataSource={tests}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create/Edit Test Modal */}
      <Modal
        title={
          editingTest
            ? t('ai_annotation:modals.edit_test')
            : t('ai_annotation:modals.create_test')
        }
        open={modalVisible}
        onOk={handleSaveTest}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        width={700}
        okText={t('common:actions.save')}
        cancelText={t('common:actions.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('ai_annotation:fields.test_name')}
            rules={[{ required: true }]}
          >
            <InputNumber placeholder={t('ai_annotation:placeholders.test_name')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="engineA"
                label={t('ai_annotation:fields.engine_a')}
                rules={[{ required: true }]}
              >
                <Select placeholder={t('ai_annotation:placeholders.select_engine')}>
                  {engines.map((engine) => (
                    <Select.Option key={engine.id} value={engine.id}>
                      {getEngineName(engine.id!)}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="engineB"
                label={t('ai_annotation:fields.engine_b')}
                rules={[{ required: true }]}
              >
                <Select placeholder={t('ai_annotation:placeholders.select_engine')}>
                  {engines.map((engine) => (
                    <Select.Option key={engine.id} value={engine.id}>
                      {getEngineName(engine.id!)}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="trafficSplit"
            label={t('ai_annotation:fields.traffic_split')}
            tooltip={t('ai_annotation:tooltips.traffic_split')}
          >
            <Slider
              min={0}
              max={100}
              marks={{
                0: t('ai_annotation:labels.all_b'),
                50: t('ai_annotation:labels.equal'),
                100: t('ai_annotation:labels.all_a'),
              }}
              tooltip={{
                formatter: (value) => `A: ${value}% / B: ${100 - (value || 0)}%`,
              }}
            />
          </Form.Item>

          <Form.Item
            name="sampleSize"
            label={t('ai_annotation:fields.sample_size')}
            tooltip={t('ai_annotation:tooltips.sample_size')}
            rules={[{ required: true, type: 'number', min: 100, max: 100000 }]}
          >
            <InputNumber
              min={100}
              max={100000}
              step={100}
              style={{ width: '100%' }}
              addonAfter={t('ai_annotation:labels.samples')}
            />
          </Form.Item>

          <Form.Item
            name="metrics"
            label={t('ai_annotation:fields.metrics_to_track')}
            tooltip={t('ai_annotation:tooltips.metrics_to_track')}
            rules={[{ required: true, type: 'array', min: 1 }]}
          >
            <Select mode="multiple" options={availableMetrics} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Results Modal */}
      <Modal
        title={
          <Space>
            <BarChartOutlined />
            {t('ai_annotation:modals.test_results')}
          </Space>
        }
        open={resultsModalVisible}
        onCancel={() => setResultsModalVisible(false)}
        width={1000}
        footer={[
          <Button key="close" onClick={() => setResultsModalVisible(false)}>
            {t('common:actions.close')}
          </Button>,
        ]}
      >
        {selectedResults && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title={t('ai_annotation:stats.winner')}
                    value={
                      selectedResults.winner === 'tie'
                        ? t('ai_annotation:labels.tie')
                        : selectedResults.winner === 'A'
                        ? t('ai_annotation:labels.engine_a')
                        : t('ai_annotation:labels.engine_b')
                    }
                    prefix={
                      selectedResults.winner === 'tie' ? (
                        <WarningOutlined />
                      ) : (
                        <CheckCircleOutlined />
                      )
                    }
                    valueStyle={{
                      color: selectedResults.winner === 'tie' ? '#faad14' : '#52c41a',
                    }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title={t('ai_annotation:stats.confidence')}
                    value={selectedResults.confidence * 100}
                    precision={1}
                    suffix="%"
                    prefix={<PercentageOutlined />}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title={t('ai_annotation:stats.p_value')}
                    value={selectedResults.pValue}
                    precision={4}
                    prefix={<LineChartOutlined />}
                    valueStyle={{
                      color: selectedResults.pValue < 0.05 ? '#52c41a' : '#faad14',
                    }}
                  />
                </Card>
              </Col>
            </Row>

            <Divider>{t('ai_annotation:sections.detailed_metrics')}</Divider>

            <Row gutter={16}>
              <Col span={12}>
                <Card
                  title={
                    <Space>
                      <Tag color="blue">A</Tag>
                      {selectedResults.engineA.name}
                    </Space>
                  }
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Statistic
                      title={t('ai_annotation:metrics.accuracy')}
                      value={selectedResults.engineA.accuracy * 100}
                      precision={2}
                      suffix="%"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.consistency')}
                      value={selectedResults.engineA.consistency * 100}
                      precision={2}
                      suffix="%"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.completeness')}
                      value={selectedResults.engineA.completeness * 100}
                      precision={2}
                      suffix="%"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.latency')}
                      value={selectedResults.engineA.avgLatency}
                      suffix="ms"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.total_cost')}
                      value={selectedResults.engineA.totalCost}
                      precision={2}
                      prefix="$"
                    />
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  title={
                    <Space>
                      <Tag color="green">B</Tag>
                      {selectedResults.engineB.name}
                    </Space>
                  }
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Statistic
                      title={t('ai_annotation:metrics.accuracy')}
                      value={selectedResults.engineB.accuracy * 100}
                      precision={2}
                      suffix="%"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.consistency')}
                      value={selectedResults.engineB.consistency * 100}
                      precision={2}
                      suffix="%"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.completeness')}
                      value={selectedResults.engineB.completeness * 100}
                      precision={2}
                      suffix="%"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.latency')}
                      value={selectedResults.engineB.avgLatency}
                      suffix="ms"
                    />
                    <Statistic
                      title={t('ai_annotation:metrics.total_cost')}
                      value={selectedResults.engineB.totalCost}
                      precision={2}
                      prefix="$"
                    />
                  </Space>
                </Card>
              </Col>
            </Row>

            {selectedResults.pValue >= 0.05 && (
              <Alert
                message={t('ai_annotation:alerts.not_statistically_significant_title')}
                description={t('ai_annotation:alerts.not_statistically_significant_desc')}
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ABTestingPanel;
