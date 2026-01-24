/**
 * Version History Viewer Component (版本历史查看器)
 * 
 * Timeline of all ontology versions with ability to view details,
 * compare versions, and restore to previous versions.
 * 
 * Requirements: Task 22.4 - Collaborative Editing
 * Validates: Requirements 7.5
 */

import React, { useState } from 'react';
import {
  Card,
  Timeline,
  Typography,
  Space,
  Button,
  Tag,
  Modal,
  Descriptions,
  Divider,
  Empty,
  Spin,
  Popconfirm,
  message,
  Select,
  Row,
  Col,
  Alert,
} from 'antd';
import {
  HistoryOutlined,
  UserOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  RollbackOutlined,
  SwapOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const { Title, Text, Paragraph } = Typography;

interface VersionEntry {
  id: string;
  version_number: number;
  change_type: 'ADD' | 'MODIFY' | 'DELETE' | 'ROLLBACK';
  changed_by: string;
  changed_by_name?: string;
  changed_at: string;
  description?: string;
  changes: Record<string, unknown>;
  before_state?: Record<string, unknown>;
  after_state?: Record<string, unknown>;
}

interface VersionHistoryViewerProps {
  ontologyId: string;
  elementId?: string;
  onRestore?: (versionId: string) => void;
}

// Mock API functions - replace with actual API calls
const fetchVersionHistory = async (
  ontologyId: string,
  elementId?: string
): Promise<VersionEntry[]> => {
  // This would be replaced with actual API call
  // return ontologyApi.getVersionHistory(ontologyId, elementId);
  return [];
};

const restoreVersion = async (
  ontologyId: string,
  versionId: string
): Promise<void> => {
  // This would be replaced with actual API call
  // return ontologyApi.restoreVersion(ontologyId, versionId);
};

const VersionHistoryViewer: React.FC<VersionHistoryViewerProps> = ({
  ontologyId,
  elementId,
  onRestore,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const queryClient = useQueryClient();
  
  // State
  const [selectedVersion, setSelectedVersion] = useState<VersionEntry | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [compareModalVisible, setCompareModalVisible] = useState(false);
  const [compareVersions, setCompareVersions] = useState<{
    from: string | null;
    to: string | null;
  }>({ from: null, to: null });

  // Fetch version history
  const {
    data: versions,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['version-history', ontologyId, elementId],
    queryFn: () => fetchVersionHistory(ontologyId, elementId),
  });

  // Restore mutation
  const restoreMutation = useMutation({
    mutationFn: (versionId: string) => restoreVersion(ontologyId, versionId),
    onSuccess: () => {
      message.success(t('ontology:version.restoreSuccess'));
      queryClient.invalidateQueries({ queryKey: ['version-history', ontologyId] });
      queryClient.invalidateQueries({ queryKey: ['ontology', ontologyId] });
      onRestore?.(selectedVersion?.id || '');
    },
    onError: () => {
      message.error(t('ontology:version.restoreFailed'));
    },
  });

  // Get change type config
  const getChangeTypeConfig = (changeType: VersionEntry['change_type']) => {
    const configs: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      ADD: {
        color: 'green',
        icon: <PlusOutlined />,
        label: t('ontology:version.changeTypeAdd'),
      },
      MODIFY: {
        color: 'blue',
        icon: <EditOutlined />,
        label: t('ontology:version.changeTypeModify'),
      },
      DELETE: {
        color: 'red',
        icon: <DeleteOutlined />,
        label: t('ontology:version.changeTypeDelete'),
      },
      ROLLBACK: {
        color: 'orange',
        icon: <RollbackOutlined />,
        label: t('ontology:version.changeTypeRollback'),
      },
    };
    return configs[changeType] || configs.MODIFY;
  };

  // Handle view version details
  const handleViewDetails = (version: VersionEntry) => {
    setSelectedVersion(version);
    setDetailModalVisible(true);
  };

  // Handle restore version
  const handleRestore = (version: VersionEntry) => {
    setSelectedVersion(version);
    restoreMutation.mutate(version.id);
  };

  // Handle compare versions
  const handleCompare = () => {
    if (compareVersions.from && compareVersions.to) {
      setCompareModalVisible(true);
    }
  };

  // Get versions for comparison
  const getCompareVersions = () => {
    if (!versions || !compareVersions.from || !compareVersions.to) {
      return { fromVersion: null, toVersion: null };
    }
    return {
      fromVersion: versions.find((v) => v.id === compareVersions.from),
      toVersion: versions.find((v) => v.id === compareVersions.to),
    };
  };

  // Format value for display
  const formatValue = (value: unknown): React.ReactNode => {
    if (value === undefined || value === null) {
      return <Text type="secondary" italic>{t('ontology:version.empty')}</Text>;
    }
    if (typeof value === 'object') {
      return (
        <pre style={{ margin: 0, fontSize: 12, maxHeight: 200, overflow: 'auto' }}>
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    return <Text>{String(value)}</Text>;
  };

  // Render timeline item
  const renderTimelineItem = (version: VersionEntry) => {
    const config = getChangeTypeConfig(version.change_type);
    
    return (
      <Timeline.Item
        key={version.id}
        color={config.color}
        dot={config.icon}
      >
        <Card size="small" hoverable>
          <Row justify="space-between" align="middle">
            <Col>
              <Space direction="vertical" size={0}>
                <Space>
                  <Tag color={config.color}>{config.label}</Tag>
                  <Text strong>v{version.version_number}</Text>
                </Space>
                <Space>
                  <UserOutlined />
                  <Text type="secondary">
                    {version.changed_by_name || version.changed_by}
                  </Text>
                  <ClockCircleOutlined />
                  <Text type="secondary">
                    {new Date(version.changed_at).toLocaleString()}
                  </Text>
                </Space>
                {version.description && (
                  <Paragraph
                    type="secondary"
                    ellipsis={{ rows: 1, tooltip: version.description }}
                    style={{ margin: 0, maxWidth: 400 }}
                  >
                    {version.description}
                  </Paragraph>
                )}
              </Space>
            </Col>
            <Col>
              <Space>
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => handleViewDetails(version)}
                >
                  {t('ontology:version.viewDetails')}
                </Button>
                <Popconfirm
                  title={t('ontology:version.confirmRestore')}
                  description={t('ontology:version.confirmRestoreDesc')}
                  onConfirm={() => handleRestore(version)}
                  okText={t('common:confirm')}
                  cancelText={t('common:cancel')}
                >
                  <Button
                    size="small"
                    icon={<RollbackOutlined />}
                    loading={restoreMutation.isPending && selectedVersion?.id === version.id}
                  >
                    {t('ontology:version.restore')}
                  </Button>
                </Popconfirm>
              </Space>
            </Col>
          </Row>
        </Card>
      </Timeline.Item>
    );
  };

  // Render version detail modal
  const renderDetailModal = () => {
    if (!selectedVersion) return null;
    const config = getChangeTypeConfig(selectedVersion.change_type);

    return (
      <Modal
        title={
          <Space>
            <HistoryOutlined />
            {t('ontology:version.detailTitle')}
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={
          <Space>
            <Button onClick={() => setDetailModalVisible(false)}>
              {t('common:close')}
            </Button>
            <Popconfirm
              title={t('ontology:version.confirmRestore')}
              onConfirm={() => {
                handleRestore(selectedVersion);
                setDetailModalVisible(false);
              }}
            >
              <Button type="primary" icon={<RollbackOutlined />}>
                {t('ontology:version.restoreToThis')}
              </Button>
            </Popconfirm>
          </Space>
        }
      >
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label={t('ontology:version.versionNumber')}>
            <Text strong>v{selectedVersion.version_number}</Text>
          </Descriptions.Item>
          <Descriptions.Item label={t('ontology:version.changeType')}>
            <Tag color={config.color} icon={config.icon}>
              {config.label}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('ontology:version.changedBy')}>
            <Space>
              <UserOutlined />
              {selectedVersion.changed_by_name || selectedVersion.changed_by}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label={t('ontology:version.changedAt')}>
            <Space>
              <ClockCircleOutlined />
              {new Date(selectedVersion.changed_at).toLocaleString()}
            </Space>
          </Descriptions.Item>
          {selectedVersion.description && (
            <Descriptions.Item label={t('ontology:version.description')} span={2}>
              {selectedVersion.description}
            </Descriptions.Item>
          )}
        </Descriptions>

        <Divider>{t('ontology:version.changes')}</Divider>

        <Row gutter={16}>
          <Col span={12}>
            <Card
              size="small"
              title={
                <Text type="danger">{t('ontology:version.beforeState')}</Text>
              }
            >
              {formatValue(selectedVersion.before_state)}
            </Card>
          </Col>
          <Col span={12}>
            <Card
              size="small"
              title={
                <Text type="success">{t('ontology:version.afterState')}</Text>
              }
            >
              {formatValue(selectedVersion.after_state)}
            </Card>
          </Col>
        </Row>
      </Modal>
    );
  };

  // Render compare modal
  const renderCompareModal = () => {
    const { fromVersion, toVersion } = getCompareVersions();

    return (
      <Modal
        title={
          <Space>
            <SwapOutlined />
            {t('ontology:version.compareTitle')}
          </Space>
        }
        open={compareModalVisible}
        onCancel={() => setCompareModalVisible(false)}
        width={900}
        footer={
          <Button onClick={() => setCompareModalVisible(false)}>
            {t('common:close')}
          </Button>
        }
      >
        {fromVersion && toVersion ? (
          <Row gutter={16}>
            <Col span={12}>
              <Card
                size="small"
                title={
                  <Space>
                    <Text>v{fromVersion.version_number}</Text>
                    <Text type="secondary">
                      ({new Date(fromVersion.changed_at).toLocaleDateString()})
                    </Text>
                  </Space>
                }
              >
                {formatValue(fromVersion.after_state)}
              </Card>
            </Col>
            <Col span={12}>
              <Card
                size="small"
                title={
                  <Space>
                    <Text>v{toVersion.version_number}</Text>
                    <Text type="secondary">
                      ({new Date(toVersion.changed_at).toLocaleDateString()})
                    </Text>
                  </Space>
                }
              >
                {formatValue(toVersion.after_state)}
              </Card>
            </Col>
          </Row>
        ) : (
          <Empty description={t('ontology:version.selectVersionsToCompare')} />
        )}
      </Modal>
    );
  };

  if (isLoading) {
    return (
      <Card>
        <Spin tip={t('ontology:version.loading')}>
          <div style={{ height: 200 }} />
        </Spin>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert
          message={t('ontology:version.loadError')}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  return (
    <div className="version-history-viewer">
      <Card
        title={
          <Space>
            <HistoryOutlined />
            {t('ontology:version.title')}
          </Space>
        }
        extra={
          <Space>
            <Select
              placeholder={t('ontology:version.selectFromVersion')}
              style={{ width: 150 }}
              value={compareVersions.from}
              onChange={(value) =>
                setCompareVersions((prev) => ({ ...prev, from: value }))
              }
              options={versions?.map((v) => ({
                value: v.id,
                label: `v${v.version_number}`,
              }))}
              allowClear
            />
            <Select
              placeholder={t('ontology:version.selectToVersion')}
              style={{ width: 150 }}
              value={compareVersions.to}
              onChange={(value) =>
                setCompareVersions((prev) => ({ ...prev, to: value }))
              }
              options={versions?.map((v) => ({
                value: v.id,
                label: `v${v.version_number}`,
              }))}
              allowClear
            />
            <Button
              icon={<SwapOutlined />}
              onClick={handleCompare}
              disabled={!compareVersions.from || !compareVersions.to}
            >
              {t('ontology:version.compare')}
            </Button>
          </Space>
        }
      >
        {versions && versions.length > 0 ? (
          <Timeline mode="left">
            {versions.map(renderTimelineItem)}
          </Timeline>
        ) : (
          <Empty description={t('ontology:version.noHistory')} />
        )}
      </Card>

      {renderDetailModal()}
      {renderCompareModal()}
    </div>
  );
};

export default VersionHistoryViewer;
