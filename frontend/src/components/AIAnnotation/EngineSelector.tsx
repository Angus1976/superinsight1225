/**
 * Engine Selector Component
 *
 * Displays and manages AI annotation engines:
 * - List of configured engines
 * - Enable/disable engines
 * - Edit engine configuration
 * - Hot-reload engines
 * - View engine health status
 */

import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Tooltip,
  Switch,
  Badge,
  Dropdown,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Card,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  MoreOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';

import type { EngineConfig, EngineStatus } from '@/pages/AIAnnotation/EngineConfiguration';

interface EngineSelectorProps {
  engines: EngineConfig[];
  engineStatuses: EngineStatus[];
  onSave: (config: EngineConfig) => Promise<void>;
  onDelete: (engineId: string) => Promise<void>;
  onToggle: (engineId: string, enabled: boolean) => Promise<void>;
  onHotReload: (engineId: string) => Promise<void>;
  loading?: boolean;
}

const EngineSelector: React.FC<EngineSelectorProps> = ({
  engines,
  engineStatuses,
  onSave,
  onDelete,
  onToggle,
  onHotReload,
  loading = false,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEngine, setEditingEngine] = useState<EngineConfig | null>(null);

  const handleEdit = (engine: EngineConfig) => {
    setEditingEngine(engine);
    form.setFieldsValue(engine);
    setModalVisible(true);
  };

  const handleAdd = () => {
    setEditingEngine(null);
    form.resetFields();
    form.setFieldsValue({
      enabled: true,
      engineType: 'pre-annotation',
      provider: 'openai',
      confidenceThreshold: 0.7,
      qualityThresholds: {
        accuracy: 0.85,
        consistency: 0.80,
        completeness: 0.90,
        recall: 0.75,
      },
      performanceSettings: {
        batchSize: 100,
        maxWorkers: 10,
        timeout: 300,
        enableCaching: true,
      },
    });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const config: EngineConfig = editingEngine
        ? { ...editingEngine, ...values }
        : values;
      await onSave(config);
      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      console.error('Form validation failed:', error);
    }
  };

  const getEngineStatus = (engineId?: string): EngineStatus | undefined => {
    if (!engineId) return undefined;
    return engineStatuses.find((s) => s.engineId === engineId);
  };

  const getStatusBadge = (status?: string) => {
    if (!status) return <Badge status="default" text={t('common:status.unknown')} />;

    switch (status) {
      case 'healthy':
        return <Badge status="success" text={t('common:status.healthy')} />;
      case 'degraded':
        return <Badge status="warning" text={t('common:status.degraded')} />;
      case 'unhealthy':
        return <Badge status="error" text={t('common:status.unhealthy')} />;
      default:
        return <Badge status="default" text={status} />;
    }
  };

  const getEngineTypeTag = (type: string) => {
    const colors = {
      'pre-annotation': 'blue',
      'mid-coverage': 'green',
      'post-validation': 'orange',
    };
    return <Tag color={colors[type as keyof typeof colors] || 'default'}>{type}</Tag>;
  };

  const getProviderTag = (provider: string) => {
    const colors = {
      ollama: 'purple',
      openai: 'cyan',
      azure: 'blue',
      qwen: 'orange',
      zhipu: 'green',
      baidu: 'red',
      hunyuan: 'magenta',
    };
    return <Tag color={colors[provider as keyof typeof colors] || 'default'}>{provider}</Tag>;
  };

  const getActionsMenu = (engine: EngineConfig): MenuProps['items'] => [
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: t('common:actions.edit'),
      onClick: () => handleEdit(engine),
    },
    {
      key: 'reload',
      icon: <ReloadOutlined />,
      label: t('ai_annotation:actions.hot_reload'),
      onClick: () => engine.id && onHotReload(engine.id),
    },
    {
      type: 'divider',
    },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: t('common:actions.delete'),
      danger: true,
      onClick: () => engine.id && onDelete(engine.id),
    },
  ];

  const columns: ColumnsType<EngineConfig> = [
    {
      title: t('ai_annotation:columns.engine_name'),
      dataIndex: 'engineType',
      key: 'engineType',
      render: (type: string, record: EngineConfig) => (
        <Space direction="vertical" size="small">
          {getEngineTypeTag(type)}
          <span style={{ fontSize: 12, color: '#666' }}>
            {record.model || t('common:not_configured')}
          </span>
        </Space>
      ),
    },
    {
      title: t('ai_annotation:columns.provider'),
      dataIndex: 'provider',
      key: 'provider',
      render: (provider: string) => getProviderTag(provider),
    },
    {
      title: t('ai_annotation:columns.confidence_threshold'),
      dataIndex: 'confidenceThreshold',
      key: 'confidenceThreshold',
      render: (threshold: number) => `${(threshold * 100).toFixed(0)}%`,
    },
    {
      title: t('ai_annotation:columns.status'),
      key: 'status',
      render: (_, record: EngineConfig) => {
        const status = getEngineStatus(record.id);
        return (
          <Tooltip
            title={
              status
                ? `${t('ai_annotation:tooltips.response_time')}: ${status.responseTimeMs}ms\n${t('ai_annotation:tooltips.last_check')}: ${status.lastCheckAt}`
                : t('ai_annotation:tooltips.no_status')
            }
          >
            {getStatusBadge(status?.status)}
          </Tooltip>
        );
      },
    },
    {
      title: t('ai_annotation:columns.enabled'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record: EngineConfig) => (
        <Switch
          checked={enabled}
          onChange={(checked) => record.id && onToggle(record.id, checked)}
          loading={loading}
        />
      ),
    },
    {
      title: t('common:columns.actions'),
      key: 'actions',
      render: (_, record: EngineConfig) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('common:actions.edit')}
          </Button>
          <Dropdown menu={{ items: getActionsMenu(record) }}>
            <Button type="text" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleAdd}
          loading={loading}
        >
          {t('ai_annotation:actions.add_engine')}
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={engines}
        rowKey={(record) => record.id || `temp-${Math.random()}`}
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      {/* Engine Configuration Modal */}
      <Modal
        title={
          editingEngine
            ? t('ai_annotation:modals.edit_engine')
            : t('ai_annotation:modals.add_engine')
        }
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        width={800}
        okText={t('common:actions.save')}
        cancelText={t('common:actions.cancel')}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="engineType"
                label={t('ai_annotation:fields.engine_type')}
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="pre-annotation">
                    {t('ai_annotation:engine_types.pre_annotation')}
                  </Select.Option>
                  <Select.Option value="mid-coverage">
                    {t('ai_annotation:engine_types.mid_coverage')}
                  </Select.Option>
                  <Select.Option value="post-validation">
                    {t('ai_annotation:engine_types.post_validation')}
                  </Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="provider"
                label={t('ai_annotation:fields.llm_provider')}
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="ollama">Ollama</Select.Option>
                  <Select.Option value="openai">OpenAI</Select.Option>
                  <Select.Option value="azure">Azure OpenAI</Select.Option>
                  <Select.Option value="qwen">Qwen (通义千问)</Select.Option>
                  <Select.Option value="zhipu">Zhipu (智谱)</Select.Option>
                  <Select.Option value="baidu">Baidu (百度)</Select.Option>
                  <Select.Option value="hunyuan">Hunyuan (腾讯混元)</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="model"
            label={t('ai_annotation:fields.model_name')}
            rules={[{ required: true }]}
          >
            <Input placeholder="gpt-4, llama2, qwen-turbo, etc." />
          </Form.Item>

          <Form.Item
            name="confidenceThreshold"
            label={t('ai_annotation:fields.confidence_threshold')}
            tooltip={t('ai_annotation:tooltips.confidence_threshold')}
          >
            <InputNumber
              min={0}
              max={1}
              step={0.05}
              style={{ width: '100%' }}
              formatter={(value) => `${((value || 0) * 100).toFixed(0)}%`}
            />
          </Form.Item>

          <Card title={t('ai_annotation:sections.quality_thresholds')} size="small">
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name={['qualityThresholds', 'accuracy']}
                  label={t('ai_annotation:fields.accuracy_threshold')}
                >
                  <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name={['qualityThresholds', 'consistency']}
                  label={t('ai_annotation:fields.consistency_threshold')}
                >
                  <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name={['qualityThresholds', 'completeness']}
                  label={t('ai_annotation:fields.completeness_threshold')}
                >
                  <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name={['qualityThresholds', 'recall']}
                  label={t('ai_annotation:fields.recall_threshold')}
                >
                  <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card
            title={t('ai_annotation:sections.performance_settings')}
            size="small"
            style={{ marginTop: 16 }}
          >
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name={['performanceSettings', 'batchSize']}
                  label={t('ai_annotation:fields.batch_size')}
                >
                  <InputNumber min={1} max={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name={['performanceSettings', 'maxWorkers']}
                  label={t('ai_annotation:fields.max_workers')}
                >
                  <InputNumber min={1} max={50} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name={['performanceSettings', 'timeout']}
                  label={t('ai_annotation:fields.timeout_seconds')}
                >
                  <InputNumber min={10} max={600} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item
              name={['performanceSettings', 'enableCaching']}
              valuePropName="checked"
            >
              <Switch /> {t('ai_annotation:fields.enable_caching')}
            </Form.Item>
          </Card>

          <Form.Item name="enabled" valuePropName="checked">
            <Switch /> {t('ai_annotation:fields.enable_engine')}
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default EngineSelector;
