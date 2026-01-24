/**
 * AI Annotation Engine Configuration Page
 *
 * Provides comprehensive configuration interface for AI annotation engines:
 * - Engine selection (Pre-annotation, Mid-coverage, Post-validation)
 * - LLM provider configuration
 * - Quality thresholds
 * - A/B testing setup
 * - Performance comparison
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Select,
  Slider,
  Switch,
  Button,
  Space,
  Alert,
  Divider,
  Row,
  Col,
  Statistic,
  Tag,
  message,
  Modal,
} from 'antd';
import {
  SettingOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { TabsProps } from 'antd';

import EngineSelector from '@/components/AIAnnotation/EngineSelector';
import LLMProviderConfig from '@/components/AIAnnotation/LLMProviderConfig';
import QualityThresholds from '@/components/AIAnnotation/QualityThresholds';
import ABTestingPanel from '@/components/AIAnnotation/ABTestingPanel';
import EnginePerformanceComparison from '@/components/AIAnnotation/EnginePerformanceComparison';

// Types
export interface EngineConfig {
  id?: string;
  engineType: 'pre-annotation' | 'mid-coverage' | 'post-validation';
  enabled: boolean;
  provider: 'ollama' | 'openai' | 'azure' | 'qwen' | 'zhipu' | 'baidu' | 'hunyuan';
  model: string;
  confidenceThreshold: number;
  qualityThresholds: {
    accuracy: number;
    consistency: number;
    completeness: number;
    recall: number;
  };
  performanceSettings: {
    batchSize: number;
    maxWorkers: number;
    timeout: number;
    enableCaching: boolean;
  };
}

export interface ABTestConfig {
  enabled: boolean;
  testName: string;
  engineA: string;
  engineB: string;
  trafficSplit: number; // 0-100, percentage for engine A
  sampleSize: number;
  metrics: string[];
}

export interface EngineStatus {
  engineId: string;
  engineType: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  lastCheckAt: string;
  responseTimeMs: number;
  consecutiveFailures: number;
}

const EngineConfiguration: React.FC = () => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [engines, setEngines] = useState<EngineConfig[]>([]);
  const [engineStatuses, setEngineStatuses] = useState<EngineStatus[]>([]);
  const [activeTab, setActiveTab] = useState('engines');
  const [selectedEngine, setSelectedEngine] = useState<EngineConfig | null>(null);
  const [showPerformanceModal, setShowPerformanceModal] = useState(false);

  // Load engines on mount
  useEffect(() => {
    loadEngines();
    loadEngineStatuses();
    // Poll engine status every 30 seconds
    const interval = setInterval(loadEngineStatuses, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadEngines = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/annotation/engines');
      if (!response.ok) throw new Error('Failed to load engines');
      const data = await response.json();
      setEngines(data.engines || []);
    } catch (error) {
      message.error(t('ai_annotation:errors.load_engines_failed'));
      console.error('Failed to load engines:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadEngineStatuses = async () => {
    try {
      const response = await fetch('/api/v1/annotation/engines/status');
      if (!response.ok) return;
      const data = await response.json();
      setEngineStatuses(data.statuses || []);
    } catch (error) {
      console.error('Failed to load engine statuses:', error);
    }
  };

  const handleSaveEngine = async (config: EngineConfig) => {
    try {
      setLoading(true);
      const method = config.id ? 'PUT' : 'POST';
      const url = config.id
        ? `/api/v1/annotation/engines/${config.id}`
        : '/api/v1/annotation/engines';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!response.ok) throw new Error('Failed to save engine');

      message.success(t('ai_annotation:messages.engine_saved'));
      await loadEngines();
    } catch (error) {
      message.error(t('ai_annotation:errors.save_engine_failed'));
      console.error('Failed to save engine:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEngine = async (engineId: string) => {
    Modal.confirm({
      title: t('ai_annotation:confirm.delete_engine_title'),
      content: t('ai_annotation:confirm.delete_engine_content'),
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/annotation/engines/${engineId}`, {
            method: 'DELETE',
          });
          if (!response.ok) throw new Error('Failed to delete engine');
          message.success(t('ai_annotation:messages.engine_deleted'));
          await loadEngines();
        } catch (error) {
          message.error(t('ai_annotation:errors.delete_engine_failed'));
          console.error('Failed to delete engine:', error);
        }
      },
    });
  };

  const handleEngineToggle = async (engineId: string, enabled: boolean) => {
    try {
      const response = await fetch(`/api/v1/annotation/engines/${engineId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error('Failed to toggle engine');
      message.success(
        enabled
          ? t('ai_annotation:messages.engine_enabled')
          : t('ai_annotation:messages.engine_disabled')
      );
      await loadEngines();
    } catch (error) {
      message.error(t('ai_annotation:errors.toggle_engine_failed'));
      console.error('Failed to toggle engine:', error);
    }
  };

  const handleHotReload = async (engineId: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/annotation/engines/${engineId}/reload`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to reload engine');
      message.success(t('ai_annotation:messages.engine_reloaded'));
      await loadEngines();
    } catch (error) {
      message.error(t('ai_annotation:errors.reload_engine_failed'));
      console.error('Failed to reload engine:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEngineStatus = (engineId: string): EngineStatus | undefined => {
    return engineStatuses.find((s) => s.engineId === engineId);
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'unhealthy':
        return 'error';
      default:
        return 'default';
    }
  };

  // Tab items
  const tabItems: TabsProps['items'] = [
    {
      key: 'engines',
      label: (
        <span>
          <ThunderboltOutlined /> {t('ai_annotation:tabs.engines')}
        </span>
      ),
      children: (
        <EngineSelector
          engines={engines}
          engineStatuses={engineStatuses}
          onSave={handleSaveEngine}
          onDelete={handleDeleteEngine}
          onToggle={handleEngineToggle}
          onHotReload={handleHotReload}
          loading={loading}
        />
      ),
    },
    {
      key: 'llm_config',
      label: (
        <span>
          <SettingOutlined /> {t('ai_annotation:tabs.llm_configuration')}
        </span>
      ),
      children: (
        <LLMProviderConfig
          engines={engines}
          onSave={handleSaveEngine}
          loading={loading}
        />
      ),
    },
    {
      key: 'quality',
      label: (
        <span>
          <CheckCircleOutlined /> {t('ai_annotation:tabs.quality_thresholds')}
        </span>
      ),
      children: (
        <QualityThresholds
          engines={engines}
          onSave={handleSaveEngine}
          loading={loading}
        />
      ),
    },
    {
      key: 'ab_testing',
      label: (
        <span>
          <ExperimentOutlined /> {t('ai_annotation:tabs.ab_testing')}
        </span>
      ),
      children: <ABTestingPanel engines={engines} loading={loading} />,
    },
    {
      key: 'performance',
      label: (
        <span>
          <LineChartOutlined /> {t('ai_annotation:tabs.performance')}
        </span>
      ),
      children: (
        <EnginePerformanceComparison
          engines={engines}
          engineStatuses={engineStatuses}
        />
      ),
    },
  ];

  return (
    <div className="engine-configuration-page">
      <Card>
        <div style={{ marginBottom: 24 }}>
          <Row justify="space-between" align="middle">
            <Col>
              <h2>
                <ThunderboltOutlined /> {t('ai_annotation:page_title')}
              </h2>
              <p style={{ color: '#666', marginTop: 8 }}>
                {t('ai_annotation:page_description')}
              </p>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<LineChartOutlined />}
                  onClick={() => setShowPerformanceModal(true)}
                >
                  {t('ai_annotation:actions.compare_engines')}
                </Button>
                <Button
                  type="primary"
                  icon={<SettingOutlined />}
                  onClick={() => {
                    form.resetFields();
                    setSelectedEngine(null);
                  }}
                >
                  {t('ai_annotation:actions.add_engine')}
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {/* Engine Status Summary */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.total_engines')}
              value={engines.length}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.healthy_engines')}
              value={engineStatuses.filter((s) => s.status === 'healthy').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.degraded_engines')}
              value={engineStatuses.filter((s) => s.status === 'degraded').length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title={t('ai_annotation:stats.enabled_engines')}
              value={engines.filter((e) => e.enabled).length}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
        </Row>

        {/* Health Alerts */}
        {engineStatuses.some((s) => s.status !== 'healthy') && (
          <Alert
            message={t('ai_annotation:alerts.unhealthy_engines_title')}
            description={t('ai_annotation:alerts.unhealthy_engines_description', {
              count: engineStatuses.filter((s) => s.status !== 'healthy').length,
            })}
            type="warning"
            showIcon
            closable
            style={{ marginBottom: 24 }}
          />
        )}

        <Divider />

        {/* Configuration Tabs */}
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      {/* Performance Comparison Modal */}
      <Modal
        title={t('ai_annotation:modals.performance_comparison')}
        open={showPerformanceModal}
        onCancel={() => setShowPerformanceModal(false)}
        width={1200}
        footer={null}
      >
        <EnginePerformanceComparison
          engines={engines}
          engineStatuses={engineStatuses}
          fullView
        />
      </Modal>
    </div>
  );
};

export default EngineConfiguration;
