/**
 * Diff Viewer Component
 * 
 * Displays differences between two versions:
 * - Field-level diff view
 * - Line-level diff view
 * - Three-way merge support
 * - Conflict resolution
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Table,
  Tag,
  Space,
  Button,
  Typography,
  Alert,
  Radio,
  Divider,
  Empty,
  Spin,
  message,
} from 'antd';
import {
  DiffOutlined,
  PlusOutlined,
  MinusOutlined,
  EditOutlined,
  MergeCellsOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { versioningApi, DiffResult, MergeResult } from '../../services/versioningApi';

const { Text, Title } = Typography;
const { TabPane } = Tabs;

interface DiffViewerProps {
  oldData?: Record<string, unknown>;
  newData?: Record<string, unknown>;
  baseData?: Record<string, unknown>;
  showMerge?: boolean;
  onMergeComplete?: (mergedData: Record<string, unknown>) => void;
}

const DiffViewer: React.FC<DiffViewerProps> = ({
  oldData,
  newData,
  baseData,
  showMerge = false,
  onMergeComplete,
}) => {
  const { t } = useTranslation();
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [mergeResult, setMergeResult] = useState<MergeResult | null>(null);
  const [diffLevel, setDiffLevel] = useState<'field' | 'line'>('field');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (oldData && newData) {
      computeDiff();
    }
  }, [oldData, newData, diffLevel]);

  useEffect(() => {
    if (showMerge && baseData && oldData && newData) {
      computeMerge();
    }
  }, [showMerge, baseData, oldData, newData]);

  const computeDiff = async () => {
    if (!oldData || !newData) return;
    
    setLoading(true);
    try {
      const result = await versioningApi.computeDiff(oldData, newData, diffLevel);
      setDiffResult(result.diff);
    } catch (error) {
      message.error(t('versioning.diffError', 'Failed to compute diff'));
    } finally {
      setLoading(false);
    }
  };

  const computeMerge = async () => {
    if (!baseData || !oldData || !newData) return;
    
    setLoading(true);
    try {
      const result = await versioningApi.threeWayMerge(baseData, oldData, newData);
      setMergeResult(result.merge_result);
    } catch (error) {
      message.error(t('versioning.mergeError', 'Failed to compute merge'));
    } finally {
      setLoading(false);
    }
  };

  const handleResolveConflict = async (
    field: string,
    resolution: 'ours' | 'theirs' | 'base'
  ) => {
    if (!mergeResult) return;
    
    try {
      const result = await versioningApi.resolveConflict(
        mergeResult.merged,
        mergeResult.conflicts,
        field,
        resolution
      );
      setMergeResult(result.merge_result);
      message.success(t('versioning.conflictResolved', 'Conflict resolved'));
    } catch (error) {
      message.error(t('versioning.resolveError', 'Failed to resolve conflict'));
    }
  };

  const handleMergeComplete = () => {
    if (mergeResult && !mergeResult.has_conflicts && onMergeComplete) {
      onMergeComplete(mergeResult.merged);
    }
  };

  const getChangeIcon = (changeType: string) => {
    switch (changeType) {
      case 'added':
        return <PlusOutlined style={{ color: '#52c41a' }} />;
      case 'removed':
        return <MinusOutlined style={{ color: '#ff4d4f' }} />;
      case 'modified':
        return <EditOutlined style={{ color: '#faad14' }} />;
      default:
        return null;
    }
  };

  const getChangeColor = (changeType: string) => {
    switch (changeType) {
      case 'added':
        return 'success';
      case 'removed':
        return 'error';
      case 'modified':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatValue = (value: unknown): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  const fieldDiffColumns = [
    {
      title: t('versioning.field', 'Field'),
      dataIndex: 'field',
      key: 'field',
      width: 200,
    },
    {
      title: t('versioning.changeType', 'Change'),
      dataIndex: 'change_type',
      key: 'change_type',
      width: 120,
      render: (type: string) => (
        <Tag color={getChangeColor(type)} icon={getChangeIcon(type)}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: t('versioning.oldValue', 'Old Value'),
      dataIndex: 'old_value',
      key: 'old_value',
      render: (value: unknown) => (
        <Text code style={{ maxWidth: 300, display: 'block', overflow: 'auto' }}>
          {formatValue(value)}
        </Text>
      ),
    },
    {
      title: t('versioning.newValue', 'New Value'),
      dataIndex: 'new_value',
      key: 'new_value',
      render: (value: unknown) => (
        <Text code style={{ maxWidth: 300, display: 'block', overflow: 'auto' }}>
          {formatValue(value)}
        </Text>
      ),
    },
  ];

  const conflictColumns = [
    {
      title: t('versioning.field', 'Field'),
      dataIndex: 'field',
      key: 'field',
      width: 150,
    },
    {
      title: t('versioning.baseValue', 'Base'),
      dataIndex: 'base_value',
      key: 'base_value',
      render: (value: unknown) => (
        <Text code>{formatValue(value)}</Text>
      ),
    },
    {
      title: t('versioning.oursValue', 'Ours'),
      dataIndex: 'ours_value',
      key: 'ours_value',
      render: (value: unknown) => (
        <Text code>{formatValue(value)}</Text>
      ),
    },
    {
      title: t('versioning.theirsValue', 'Theirs'),
      dataIndex: 'theirs_value',
      key: 'theirs_value',
      render: (value: unknown) => (
        <Text code>{formatValue(value)}</Text>
      ),
    },
    {
      title: t('versioning.resolution', 'Resolution'),
      key: 'resolution',
      width: 200,
      render: (_: unknown, record: MergeResult['conflicts'][0]) => (
        <Space>
          <Button
            size="small"
            onClick={() => handleResolveConflict(record.field, 'ours')}
          >
            {t('versioning.useOurs', 'Ours')}
          </Button>
          <Button
            size="small"
            onClick={() => handleResolveConflict(record.field, 'theirs')}
          >
            {t('versioning.useTheirs', 'Theirs')}
          </Button>
          <Button
            size="small"
            onClick={() => handleResolveConflict(record.field, 'base')}
          >
            {t('versioning.useBase', 'Base')}
          </Button>
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  if (!oldData || !newData) {
    return (
      <Card>
        <Empty description={t('versioning.selectVersions', 'Select two versions to compare')} />
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <DiffOutlined />
          <span>{t('versioning.diffViewer', 'Diff Viewer')}</span>
        </Space>
      }
      extra={
        <Radio.Group
          value={diffLevel}
          onChange={(e) => setDiffLevel(e.target.value)}
          optionType="button"
          buttonStyle="solid"
        >
          <Radio.Button value="field">
            {t('versioning.fieldLevel', 'Field')}
          </Radio.Button>
          <Radio.Button value="line">
            {t('versioning.lineLevel', 'Line')}
          </Radio.Button>
        </Radio.Group>
      }
    >
      <Tabs defaultActiveKey="diff">
        <TabPane
          tab={
            <span>
              <DiffOutlined />
              {t('versioning.differences', 'Differences')}
            </span>
          }
          key="diff"
        >
          {diffResult && (
            <>
              <Space style={{ marginBottom: 16 }}>
                <Tag color="success">
                  +{diffResult.summary.added} {t('versioning.added', 'added')}
                </Tag>
                <Tag color="error">
                  -{diffResult.summary.removed} {t('versioning.removed', 'removed')}
                </Tag>
                <Tag color="warning">
                  ~{diffResult.summary.modified} {t('versioning.modified', 'modified')}
                </Tag>
              </Space>

              {diffLevel === 'field' ? (
                <Table
                  dataSource={diffResult.changes}
                  columns={fieldDiffColumns}
                  rowKey="field"
                  pagination={false}
                  size="small"
                />
              ) : (
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 16,
                    borderRadius: 4,
                    overflow: 'auto',
                    maxHeight: 500,
                  }}
                >
                  {diffResult.unified_diff.map((line, index) => {
                    let color = 'inherit';
                    if (line.startsWith('+')) color = '#52c41a';
                    if (line.startsWith('-')) color = '#ff4d4f';
                    if (line.startsWith('@')) color = '#1890ff';
                    
                    return (
                      <div key={index} style={{ color }}>
                        {line}
                      </div>
                    );
                  })}
                </pre>
              )}
            </>
          )}
        </TabPane>

        {showMerge && mergeResult && (
          <TabPane
            tab={
              <span>
                <MergeCellsOutlined />
                {t('versioning.merge', 'Merge')}
                {mergeResult.has_conflicts && (
                  <Tag color="error" style={{ marginLeft: 8 }}>
                    {mergeResult.conflicts.length}
                  </Tag>
                )}
              </span>
            }
            key="merge"
          >
            {mergeResult.has_conflicts ? (
              <>
                <Alert
                  type="warning"
                  message={t(
                    'versioning.conflictsFound',
                    `${mergeResult.conflicts.length} conflicts found`
                  )}
                  style={{ marginBottom: 16 }}
                />
                <Table
                  dataSource={mergeResult.conflicts}
                  columns={conflictColumns}
                  rowKey="field"
                  pagination={false}
                  size="small"
                />
              </>
            ) : (
              <>
                <Alert
                  type="success"
                  message={t('versioning.noConflicts', 'No conflicts - ready to merge')}
                  style={{ marginBottom: 16 }}
                />
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={handleMergeComplete}
                >
                  {t('versioning.completeMerge', 'Complete Merge')}
                </Button>
                <Divider />
                <Title level={5}>{t('versioning.mergedResult', 'Merged Result')}</Title>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: 16,
                    borderRadius: 4,
                    overflow: 'auto',
                    maxHeight: 400,
                  }}
                >
                  {JSON.stringify(mergeResult.merged, null, 2)}
                </pre>
              </>
            )}
          </TabPane>
        )}
      </Tabs>
    </Card>
  );
};

export default DiffViewer;
