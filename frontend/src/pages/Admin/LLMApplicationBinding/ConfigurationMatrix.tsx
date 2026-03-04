/**
 * Configuration Matrix Component
 * Displays LLM-Application binding status in a matrix view
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Table,
  Tag,
  Button,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Alert,
  Tooltip,
  Badge,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useLLMConfigStore } from '@/stores/llmConfigStore';
import type { Application, LLMBinding, LLMConfig } from '@/types/llmConfig';

interface MatrixData {
  application: Application;
  bindings: LLMBinding[];
  status: 'configured' | 'partial' | 'none';
  primaryLLM?: LLMConfig;
  backupCount: number;
}

const ConfigurationMatrix: React.FC = () => {
  const { t } = useTranslation('llmConfig');
  const { applications, bindings, loading, fetchAll } = useLLMConfigStore();
  const [matrixData, setMatrixData] = useState<MatrixData[]>([]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    // Build matrix data
    const data: MatrixData[] = applications.map((app) => {
      const appBindings = bindings
        .filter((b) => b.application.id === app.id && b.is_active)
        .sort((a, b) => a.priority - b.priority);

      let status: 'configured' | 'partial' | 'none' = 'none';
      if (appBindings.length >= 3) {
        status = 'configured';
      } else if (appBindings.length > 0) {
        status = 'partial';
      }

      return {
        application: app,
        bindings: appBindings,
        status,
        primaryLLM: appBindings[0]?.llm_config,
        backupCount: appBindings.length - 1,
      };
    });

    setMatrixData(data);
  }, [applications, bindings]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'configured':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'partial':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      default:
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      configured: { color: 'success', text: t('matrix.status.configured') },
      partial: { color: 'warning', text: t('matrix.status.partial') },
      none: { color: 'error', text: t('matrix.status.none') },
    };
    const config = statusMap[status] || statusMap.none;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getPriorityBadge = (priority: number) => {
    const colors = ['#52c41a', '#1890ff', '#faad14'];
    return (
      <Badge
        count={priority}
        style={{ backgroundColor: colors[priority - 1] || '#d9d9d9' }}
      />
    );
  };

  // Statistics
  const stats = {
    total: applications.length,
    configured: matrixData.filter((d) => d.status === 'configured').length,
    partial: matrixData.filter((d) => d.status === 'partial').length,
    none: matrixData.filter((d) => d.status === 'none').length,
  };

  const columns = [
    {
      title: t('matrix.columns.application'),
      dataIndex: 'application',
      key: 'application',
      width: 200,
      render: (app: Application) => (
        <Space direction="vertical" size="small">
          <strong>{t(`applications.${app.code}.name`)}</strong>
          <Tag>{app.code}</Tag>
        </Space>
      ),
    },
    {
      title: t('matrix.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
          {getStatusTag(status)}
        </Space>
      ),
    },
    {
      title: t('matrix.columns.primary'),
      dataIndex: 'primaryLLM',
      key: 'primary',
      width: 200,
      render: (llm: LLMConfig | undefined) => {
        if (!llm) {
          return <Tag color="default">{t('matrix.notConfigured')}</Tag>;
        }
        return (
          <Space direction="vertical" size="small">
            <Space>
              <ApiOutlined />
              <span>{llm.name}</span>
            </Space>
            <Tag color="blue">{t(`providers.${llm.provider}`)}</Tag>
          </Space>
        );
      },
    },
    {
      title: t('matrix.columns.backups'),
      dataIndex: 'bindings',
      key: 'backups',
      render: (bindings: LLMBinding[]) => {
        if (bindings.length <= 1) {
          return <Tag color="default">{t('matrix.noBackup')}</Tag>;
        }
        return (
          <Space wrap>
            {bindings.slice(1).map((binding) => (
              <Tooltip
                key={binding.id}
                title={`${binding.llm_config.name} (${t('matrix.priority')} ${binding.priority})`}
              >
                <Tag color="processing">
                  {getPriorityBadge(binding.priority)}
                  {binding.llm_config.name}
                </Tag>
              </Tooltip>
            ))}
          </Space>
        );
      },
    },
    {
      title: t('matrix.columns.config'),
      key: 'config',
      width: 150,
      render: (record: MatrixData) => (
        <Space direction="vertical" size="small">
          <span>
            {t('matrix.retries')}: {record.bindings[0]?.max_retries || '-'}
          </span>
          <span>
            {t('matrix.timeout')}: {record.bindings[0]?.timeout_seconds || '-'}s
          </span>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('matrix.stats.total')}
              value={stats.total}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('matrix.stats.configured')}
              value={stats.configured}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('matrix.stats.partial')}
              value={stats.partial}
              valueStyle={{ color: '#faad14' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('matrix.stats.notConfigured')}
              value={stats.none}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Alerts */}
      {stats.none > 0 && (
        <Alert
          message={t('matrix.alerts.notConfigured.title')}
          description={t('matrix.alerts.notConfigured.description', { count: stats.none })}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" type="primary" icon={<ThunderboltOutlined />}>
              {t('matrix.quickSetup')}
            </Button>
          }
        />
      )}

      {stats.partial > 0 && (
        <Alert
          message={t('matrix.alerts.partial.title')}
          description={t('matrix.alerts.partial.description', { count: stats.partial })}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Matrix Table */}
      <Card title={t('matrix.title')}>
        <Table
          columns={columns}
          dataSource={matrixData}
          rowKey={(record) => record.application.id}
          loading={loading}
          pagination={false}
        />
      </Card>
    </div>
  );
};

export default ConfigurationMatrix;
