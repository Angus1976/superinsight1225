/**
 * Version Timeline Component
 * 
 * Displays version history as an interactive timeline:
 * - Version list with details
 * - Version comparison
 * - Rollback functionality
 * - Tag management
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Timeline,
  Button,
  Tag,
  Space,
  Modal,
  Input,
  message,
  Spin,
  Empty,
  Tooltip,
  Typography,
  Popconfirm,
  Select,
} from 'antd';
import {
  HistoryOutlined,
  RollbackOutlined,
  TagOutlined,
  DiffOutlined,
  ClockCircleOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { versioningApi, Version } from '../../services/versioningApi';

const { Text, Title } = Typography;

interface VersionTimelineProps {
  entityType: string;
  entityId: string;
  tenantId?: string;
  onVersionSelect?: (version: Version) => void;
  onCompare?: (version1: Version, version2: Version) => void;
}

const VersionTimeline: React.FC<VersionTimelineProps> = ({
  entityType,
  entityId,
  tenantId,
  onVersionSelect,
  onCompare,
}) => {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedVersions, setSelectedVersions] = useState<Version[]>([]);
  const [tagModalVisible, setTagModalVisible] = useState(false);
  const [tagInput, setTagInput] = useState('');
  const [tagVersionId, setTagVersionId] = useState<string | null>(null);

  useEffect(() => {
    loadVersions();
  }, [entityType, entityId, tenantId]);

  const loadVersions = async () => {
    setLoading(true);
    try {
      const result = await versioningApi.getVersionHistory(
        entityType,
        entityId,
        50,
        tenantId
      );
      setVersions(result.versions);
    } catch (error) {
      message.error(t('versioning.loadError', 'Failed to load version history'));
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (version: Version) => {
    try {
      await versioningApi.rollbackVersion(
        entityType,
        entityId,
        version.version
      );
      message.success(t('versioning.rollbackSuccess', 'Rolled back successfully'));
      loadVersions();
    } catch (error) {
      message.error(t('versioning.rollbackError', 'Rollback failed'));
    }
  };

  const handleAddTag = async () => {
    if (!tagVersionId || !tagInput.trim()) return;
    
    try {
      await versioningApi.addTag(tagVersionId, tagInput.trim());
      message.success(t('versioning.tagAdded', 'Tag added successfully'));
      setTagModalVisible(false);
      setTagInput('');
      setTagVersionId(null);
      loadVersions();
    } catch (error) {
      message.error(t('versioning.tagError', 'Failed to add tag'));
    }
  };

  const handleVersionSelect = (version: Version) => {
    if (selectedVersions.length < 2) {
      setSelectedVersions([...selectedVersions, version]);
    } else {
      setSelectedVersions([version]);
    }
    onVersionSelect?.(version);
  };

  const handleCompare = () => {
    if (selectedVersions.length === 2 && onCompare) {
      onCompare(selectedVersions[0], selectedVersions[1]);
    }
  };

  const getVersionColor = (version: Version) => {
    if (version.version.startsWith('1.0.0')) return 'green';
    if (version.version.includes('.0.0')) return 'blue';
    if (version.version.includes('.0')) return 'orange';
    return 'default';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  if (versions.length === 0) {
    return (
      <Card>
        <Empty description={t('versioning.noVersions', 'No versions found')} />
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          <span>{t('versioning.timeline', 'Version Timeline')}</span>
        </Space>
      }
      extra={
        <Space>
          {selectedVersions.length === 2 && (
            <Button
              type="primary"
              icon={<DiffOutlined />}
              onClick={handleCompare}
            >
              {t('versioning.compare', 'Compare')}
            </Button>
          )}
          <Button onClick={() => setSelectedVersions([])}>
            {t('versioning.clearSelection', 'Clear Selection')}
          </Button>
        </Space>
      }
    >
      <Timeline mode="left">
        {versions.map((version, index) => (
          <Timeline.Item
            key={version.id}
            color={getVersionColor(version)}
            label={
              <Text type="secondary">
                <ClockCircleOutlined /> {formatDate(version.created_at)}
              </Text>
            }
          >
            <Card
              size="small"
              style={{
                cursor: 'pointer',
                border: selectedVersions.includes(version)
                  ? '2px solid #1890ff'
                  : undefined,
              }}
              onClick={() => handleVersionSelect(version)}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space>
                  <Tag color={getVersionColor(version)}>v{version.version}</Tag>
                  <Text strong>#{version.version_number}</Text>
                  {version.tags?.map((tag) => (
                    <Tag key={tag} icon={<TagOutlined />}>
                      {tag}
                    </Tag>
                  ))}
                </Space>
                
                {version.message && (
                  <Text>{version.message}</Text>
                )}
                
                <Space size="small">
                  <Tooltip title={version.created_by}>
                    <Text type="secondary">
                      <UserOutlined /> {version.created_by || 'system'}
                    </Text>
                  </Tooltip>
                  <Text type="secondary">
                    {version.data_size_bytes} bytes
                  </Text>
                </Space>
                
                <Space>
                  <Tooltip title={t('versioning.addTag', 'Add Tag')}>
                    <Button
                      size="small"
                      icon={<TagOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        setTagVersionId(version.id);
                        setTagModalVisible(true);
                      }}
                    />
                  </Tooltip>
                  
                  {index > 0 && (
                    <Popconfirm
                      title={t('versioning.rollbackConfirm', 'Rollback to this version?')}
                      onConfirm={() => handleRollback(version)}
                      okText={t('common.yes', 'Yes')}
                      cancelText={t('common.no', 'No')}
                    >
                      <Tooltip title={t('versioning.rollback', 'Rollback')}>
                        <Button
                          size="small"
                          icon={<RollbackOutlined />}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Tooltip>
                    </Popconfirm>
                  )}
                </Space>
              </Space>
            </Card>
          </Timeline.Item>
        ))}
      </Timeline>

      <Modal
        title={t('versioning.addTag', 'Add Tag')}
        open={tagModalVisible}
        onOk={handleAddTag}
        onCancel={() => {
          setTagModalVisible(false);
          setTagInput('');
          setTagVersionId(null);
        }}
      >
        <Input
          placeholder={t('versioning.tagPlaceholder', 'Enter tag name')}
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onPressEnter={handleAddTag}
        />
      </Modal>
    </Card>
  );
};

export default VersionTimeline;
