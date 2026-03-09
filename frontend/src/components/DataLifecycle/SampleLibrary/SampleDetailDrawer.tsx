/**
 * SampleDetailDrawer Component
 * 
 * Displays detailed information about a sample in a drawer with tabs.
 * Shows content preview, metadata, quality scores, version history, and usage history.
 * 
 * Requirements: 4.1, 8.2, 18.1
 */

import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Tabs,
  Descriptions,
  Tag,
  Button,
  Space,
  Spin,
  Alert,
  Typography,
  Card,
  Timeline,
  Statistic,
  Row,
  Col,
  message,
  Modal,
} from 'antd';
import {
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { dataLifecycleApi, Sample } from '@/services/dataLifecycle';

const { Title, Text, Paragraph } = Typography;
const { confirm } = Modal;

// ============================================================================
// Types
// ============================================================================

export interface SampleDetailDrawerProps {
  sampleId: string | null;
  open: boolean;
  onClose: () => void;
  onEdit?: (id: string) => void;
  onAddToTask?: (id: string) => void;
  onDelete?: (id: string) => void;
}

interface VersionHistory {
  version: number;
  timestamp: string;
  changes: Record<string, unknown>;
  created_by?: string;
}

interface UsageHistory {
  task_id: string;
  task_name: string;
  used_at: string;
  used_by: string;
}

// ============================================================================
// State Transition Visualizer Component (Placeholder)
// ============================================================================

const StateTransitionVisualizer: React.FC<{ state: string }> = ({ state }) => {
  const { t } = useTranslation('dataLifecycle');
  
  const getStateColor = (currentState: string): string => {
    const stateColors: Record<string, string> = {
      draft: 'default',
      processing: 'processing',
      ready: 'success',
      in_sample_library: 'cyan',
      annotation_pending: 'warning',
      annotating: 'processing',
      annotated: 'success',
      enhancing: 'processing',
      enhanced: 'purple',
      archived: 'default',
    };
    return stateColors[currentState] || 'default';
  };

  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Text strong>{t('common.status.current')}</Text>
        <Tag color={getStateColor(state)} style={{ fontSize: 14, padding: '4px 12px' }}>
          {state}
        </Tag>
      </Space>
    </Card>
  );
};

// ============================================================================
// Component
// ============================================================================

const SampleDetailDrawer: React.FC<SampleDetailDrawerProps> = ({
  sampleId,
  open,
  onClose,
  onEdit,
  onAddToTask,
  onDelete,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [loading, setLoading] = useState(false);
  const [sample, setSample] = useState<Sample | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [versionHistory, setVersionHistory] = useState<VersionHistory[]>([]);
  const [usageHistory, setUsageHistory] = useState<UsageHistory[]>([]);
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch sample details
  useEffect(() => {
    if (open && sampleId) {
      fetchSampleDetails();
    }
  }, [open, sampleId]);

  const fetchSampleDetails = async () => {
    if (!sampleId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await dataLifecycleApi.getSample(sampleId);
      setSample(data);
      
      // Mock version history (will be replaced with real API call)
      setVersionHistory([
        {
          version: 1,
          timestamp: data.created_at,
          changes: { action: 'created' },
          created_by: data.created_by,
        },
      ]);
      
      // Mock usage history (will be replaced with real API call)
      setUsageHistory([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sample details');
      message.error(t('common.messages.operationFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    if (sample && onEdit) {
      onEdit(sample.id);
    }
  };

  const handleAddToTask = () => {
    if (sample && onAddToTask) {
      onAddToTask(sample.id);
    }
  };

  const handleDelete = () => {
    if (!sample) return;

    confirm({
      title: t('sampleLibrary.messages.confirmRemove'),
      icon: <ExclamationCircleOutlined />,
      content: sample.name || sample.id,
      okText: t('common.actions.confirm'),
      okType: 'danger',
      cancelText: t('common.actions.cancel'),
      onOk: () => {
        if (onDelete) {
          onDelete(sample.id);
          onClose();
        }
      },
    });
  };

  const getQualityColor = (score: number): string => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'processing';
    if (score >= 0.4) return 'warning';
    return 'error';
  };

  const getQualityLabel = (score: number): string => {
    if (score >= 0.8) return t('sampleLibrary.quality.excellent');
    if (score >= 0.6) return t('sampleLibrary.quality.good');
    if (score >= 0.4) return t('sampleLibrary.quality.average');
    return t('sampleLibrary.quality.poor');
  };

  // Render Overview Tab
  const renderOverviewTab = () => {
    if (!sample) return null;

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* State Visualizer */}
        <StateTransitionVisualizer state={sample.metadata?.state as string || 'in_sample_library'} />

        {/* Quality Metrics */}
        <Card size="small">
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title={t('sampleLibrary.columns.qualityScore')}
                value={sample.quality_score}
                precision={2}
                valueStyle={{ color: getQualityColor(sample.quality_score) === 'success' ? '#3f8600' : undefined }}
                suffix={
                  <Tag color={getQualityColor(sample.quality_score)}>
                    {getQualityLabel(sample.quality_score)}
                  </Tag>
                }
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={t('sampleLibrary.columns.usageCount')}
                value={sample.usage_count}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={t('common.status.current')}
                value={sample.metadata?.state as string || 'active'}
              />
            </Col>
          </Row>
        </Card>

        {/* Basic Information */}
        <Descriptions
          title={t('sampleLibrary.columns.description')}
          bordered
          column={1}
          size="small"
        >
          <Descriptions.Item label={t('sampleLibrary.columns.id')}>
            <Text copyable style={{ fontFamily: 'monospace', fontSize: '12px' }}>
              {sample.id}
            </Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('sampleLibrary.columns.name')}>
            {sample.name}
          </Descriptions.Item>
          <Descriptions.Item label={t('sampleLibrary.columns.dataType')}>
            <Tag color="blue">{sample.data_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('sampleLibrary.columns.description')}>
            {sample.description || '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('sampleLibrary.columns.createdAt')}>
            {new Date(sample.created_at).toLocaleString()}
          </Descriptions.Item>
          {sample.updated_at && (
            <Descriptions.Item label={t('sampleLibrary.columns.updatedAt')}>
              {new Date(sample.updated_at).toLocaleString()}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Space>
    );
  };

  // Render Content Tab
  const renderContentTab = () => {
    if (!sample) return null;

    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Card
          size="small"
          title={t('tempData.columns.content')}
        >
          <Paragraph>
            <pre style={{
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 4,
              overflow: 'auto',
              maxHeight: 400,
            }}>
              {JSON.stringify(sample.metadata, null, 2)}
            </pre>
          </Paragraph>
        </Card>
      </Space>
    );
  };

  // Render Versions Tab
  const renderVersionsTab = () => {
    if (versionHistory.length === 0) {
      return (
        <Alert
          message={t('common.status.empty')}
          description={t('common.messages.noData')}
          type="info"
          showIcon
        />
      );
    }

    return (
      <Timeline
        items={versionHistory.map((version) => ({
          color: version.version === 1 ? 'green' : 'blue',
          dot: version.version === 1 ? <CheckCircleOutlined /> : <ClockCircleOutlined />,
          children: (
            <Card size="small" style={{ marginBottom: 8 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <Tag color="blue">{t('enhancement.columns.version')} {version.version}</Tag>
                  <Text type="secondary">{new Date(version.timestamp).toLocaleString()}</Text>
                </Space>
                {version.created_by && (
                  <Text type="secondary">
                    {t('tempData.columns.uploadedBy')}: {version.created_by}
                  </Text>
                )}
                <Paragraph>
                  <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                    {JSON.stringify(version.changes, null, 2)}
                  </pre>
                </Paragraph>
              </Space>
            </Card>
          ),
        }))}
      />
    );
  };

  // Render Usage Tab
  const renderUsageTab = () => {
    if (usageHistory.length === 0) {
      return (
        <Alert
          message={t('common.status.empty')}
          description={t('sampleLibrary.messages.noUsageHistory')}
          type="info"
          showIcon
        />
      );
    }

    return (
      <Timeline
        items={usageHistory.map((usage) => ({
          children: (
            <Card size="small" style={{ marginBottom: 8 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Title level={5}>{usage.task_name}</Title>
                <Space>
                  <Text type="secondary">{new Date(usage.used_at).toLocaleString()}</Text>
                  <Text type="secondary">
                    {t('tempData.columns.uploadedBy')}: {usage.used_by}
                  </Text>
                </Space>
                <Text copyable style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                  {usage.task_id}
                </Text>
              </Space>
            </Card>
          ),
        }))}
      />
    );
  };

  // Tab items
  const tabItems = [
    {
      key: 'overview',
      label: t('sampleLibrary.tabs.overview'),
      children: renderOverviewTab(),
    },
    {
      key: 'content',
      label: t('sampleLibrary.tabs.content'),
      children: renderContentTab(),
    },
    {
      key: 'versions',
      label: t('sampleLibrary.tabs.versions'),
      children: renderVersionsTab(),
    },
    {
      key: 'usage',
      label: t('sampleLibrary.tabs.usage'),
      children: renderUsageTab(),
    },
  ];

  return (
    <Drawer
      title={t('tempData.actions.viewDetails')}
      placement="right"
      width={720}
      open={open}
      onClose={onClose}
      extra={
        <Space>
          {onEdit && (
            <Button
              icon={<EditOutlined />}
              onClick={handleEdit}
              disabled={!sample}
            >
              {t('common.actions.edit')}
            </Button>
          )}
          {onAddToTask && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddToTask}
              disabled={!sample}
            >
              {t('sampleLibrary.actions.addToTask')}
            </Button>
          )}
          {onDelete && (
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
              disabled={!sample}
            >
              {t('common.actions.delete')}
            </Button>
          )}
        </Space>
      }
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" tip={t('common.status.loading')} />
        </div>
      )}

      {error && (
        <Alert
          message={t('common.status.error')}
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      {!loading && !error && sample && (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      )}

      {!loading && !error && !sample && (
        <Alert
          message={t('common.status.empty')}
          description={t('errors.dataNotFound')}
          type="warning"
          showIcon
        />
      )}
    </Drawer>
  );
};

export default SampleDetailDrawer;
