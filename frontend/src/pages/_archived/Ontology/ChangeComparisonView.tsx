/**
 * Change Comparison View Component (变更对比视图)
 * 
 * Side-by-side before/after comparison for ontology changes.
 * Highlights changed fields and shows change metadata.
 * 
 * Requirements: Task 22.2 - Collaborative Editing
 * Validates: Requirements 4.2
 */

import React, { useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Typography,
  Space,
  Tag,
  Divider,
  Descriptions,
  Empty,
  Badge,
  Tooltip,
} from 'antd';
import {
  SwapOutlined,
  PlusOutlined,
  MinusOutlined,
  EditOutlined,
  UserOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { ChangeRequest } from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;

interface ChangeField {
  field: string;
  oldValue: unknown;
  newValue: unknown;
  changeType: 'added' | 'removed' | 'modified' | 'unchanged';
}

interface ChangeComparisonViewProps {
  changeRequest: ChangeRequest;
  beforeState?: Record<string, unknown>;
  afterState?: Record<string, unknown>;
  showMetadata?: boolean;
}

const ChangeComparisonView: React.FC<ChangeComparisonViewProps> = ({
  changeRequest,
  beforeState,
  afterState,
  showMetadata = true,
}) => {
  const { t } = useTranslation(['ontology', 'common']);

  // Calculate field changes
  const fieldChanges = useMemo((): ChangeField[] => {
    const changes: ChangeField[] = [];
    const allFields = new Set<string>();

    // Collect all fields from both states
    if (beforeState) {
      Object.keys(beforeState).forEach((key) => allFields.add(key));
    }
    if (afterState) {
      Object.keys(afterState).forEach((key) => allFields.add(key));
    }

    // Compare each field
    allFields.forEach((field) => {
      const oldValue = beforeState?.[field];
      const newValue = afterState?.[field];

      if (oldValue === undefined && newValue !== undefined) {
        changes.push({ field, oldValue, newValue, changeType: 'added' });
      } else if (oldValue !== undefined && newValue === undefined) {
        changes.push({ field, oldValue, newValue, changeType: 'removed' });
      } else if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
        changes.push({ field, oldValue, newValue, changeType: 'modified' });
      } else {
        changes.push({ field, oldValue, newValue, changeType: 'unchanged' });
      }
    });

    // Sort: modified first, then added, then removed, then unchanged
    const order = { modified: 0, added: 1, removed: 2, unchanged: 3 };
    return changes.sort((a, b) => order[a.changeType] - order[b.changeType]);
  }, [beforeState, afterState]);

  // Get change type color
  const getChangeTypeColor = (changeType: ChangeField['changeType']): string => {
    switch (changeType) {
      case 'added':
        return '#52c41a';
      case 'removed':
        return '#f5222d';
      case 'modified':
        return '#faad14';
      default:
        return '#d9d9d9';
    }
  };

  // Get change type icon
  const getChangeTypeIcon = (changeType: ChangeField['changeType']) => {
    switch (changeType) {
      case 'added':
        return <PlusOutlined style={{ color: '#52c41a' }} />;
      case 'removed':
        return <MinusOutlined style={{ color: '#f5222d' }} />;
      case 'modified':
        return <EditOutlined style={{ color: '#faad14' }} />;
      default:
        return null;
    }
  };

  // Format value for display
  const formatValue = (value: unknown): React.ReactNode => {
    if (value === undefined || value === null) {
      return <Text type="secondary" italic>{t('ontology:comparison.empty')}</Text>;
    }
    if (typeof value === 'boolean') {
      return <Tag color={value ? 'green' : 'red'}>{value ? 'true' : 'false'}</Tag>;
    }
    if (typeof value === 'object') {
      return (
        <pre style={{ margin: 0, fontSize: 12, maxHeight: 100, overflow: 'auto' }}>
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    return <Text>{String(value)}</Text>;
  };

  // Render change type tag
  const renderChangeTypeTag = (changeType: string) => {
    const config: Record<string, { color: string; label: string }> = {
      ADD: { color: 'green', label: t('ontology:comparison.changeTypeAdd') },
      MODIFY: { color: 'orange', label: t('ontology:comparison.changeTypeModify') },
      DELETE: { color: 'red', label: t('ontology:comparison.changeTypeDelete') },
    };
    const { color, label } = config[changeType] || { color: 'default', label: changeType };
    return <Tag color={color}>{label}</Tag>;
  };

  // Render status tag
  const renderStatusTag = (status: string) => {
    const config: Record<string, { color: string; label: string }> = {
      draft: { color: 'default', label: t('ontology:comparison.statusDraft') },
      submitted: { color: 'blue', label: t('ontology:comparison.statusSubmitted') },
      in_review: { color: 'orange', label: t('ontology:comparison.statusInReview') },
      approved: { color: 'green', label: t('ontology:comparison.statusApproved') },
      rejected: { color: 'red', label: t('ontology:comparison.statusRejected') },
      changes_requested: { color: 'purple', label: t('ontology:comparison.statusChangesRequested') },
    };
    const { color, label } = config[status] || { color: 'default', label: status };
    return <Tag color={color}>{label}</Tag>;
  };

  // Count changes by type
  const changeCounts = useMemo(() => {
    return fieldChanges.reduce(
      (acc, change) => {
        acc[change.changeType]++;
        return acc;
      },
      { added: 0, removed: 0, modified: 0, unchanged: 0 }
    );
  }, [fieldChanges]);

  return (
    <div className="change-comparison-view">
      {/* Metadata Section */}
      {showMetadata && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item
              label={
                <Space>
                  <FileTextOutlined />
                  {t('ontology:comparison.changeType')}
                </Space>
              }
            >
              {renderChangeTypeTag(changeRequest.change_type)}
            </Descriptions.Item>
            <Descriptions.Item
              label={
                <Space>
                  <SwapOutlined />
                  {t('ontology:comparison.status')}
                </Space>
              }
            >
              {renderStatusTag(changeRequest.status)}
            </Descriptions.Item>
            <Descriptions.Item
              label={
                <Space>
                  <UserOutlined />
                  {t('ontology:comparison.requester')}
                </Space>
              }
            >
              {changeRequest.requester_id}
            </Descriptions.Item>
            <Descriptions.Item
              label={
                <Space>
                  <ClockCircleOutlined />
                  {t('ontology:comparison.createdAt')}
                </Space>
              }
            >
              {new Date(changeRequest.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item
              label={t('ontology:comparison.targetElement')}
              span={2}
            >
              <Text code>{changeRequest.target_element}</Text>
            </Descriptions.Item>
            {changeRequest.description && (
              <Descriptions.Item
                label={t('ontology:comparison.description')}
                span={2}
              >
                <Paragraph style={{ margin: 0 }}>{changeRequest.description}</Paragraph>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}

      {/* Change Summary */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space size="large">
          <Badge count={changeCounts.modified} style={{ backgroundColor: '#faad14' }}>
            <Tag icon={<EditOutlined />}>{t('ontology:comparison.modified')}</Tag>
          </Badge>
          <Badge count={changeCounts.added} style={{ backgroundColor: '#52c41a' }}>
            <Tag icon={<PlusOutlined />}>{t('ontology:comparison.added')}</Tag>
          </Badge>
          <Badge count={changeCounts.removed} style={{ backgroundColor: '#f5222d' }}>
            <Tag icon={<MinusOutlined />}>{t('ontology:comparison.removed')}</Tag>
          </Badge>
          <Text type="secondary">
            {t('ontology:comparison.unchangedCount', { count: changeCounts.unchanged })}
          </Text>
        </Space>
      </Card>

      {/* Comparison View */}
      <Card
        title={
          <Space>
            <SwapOutlined />
            {t('ontology:comparison.title')}
          </Space>
        }
      >
        {fieldChanges.length > 0 ? (
          <div>
            {/* Header */}
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={4}>
                <Text strong>{t('ontology:comparison.field')}</Text>
              </Col>
              <Col span={10}>
                <Text strong style={{ color: '#f5222d' }}>
                  {t('ontology:comparison.before')}
                </Text>
              </Col>
              <Col span={10}>
                <Text strong style={{ color: '#52c41a' }}>
                  {t('ontology:comparison.after')}
                </Text>
              </Col>
            </Row>

            <Divider style={{ margin: '8px 0' }} />

            {/* Field Comparisons */}
            {fieldChanges
              .filter((change) => change.changeType !== 'unchanged')
              .map((change, index) => (
                <Row
                  key={change.field}
                  gutter={16}
                  style={{
                    padding: '8px 0',
                    backgroundColor: index % 2 === 0 ? '#fafafa' : 'transparent',
                    borderLeft: `3px solid ${getChangeTypeColor(change.changeType)}`,
                    paddingLeft: 12,
                    marginBottom: 4,
                  }}
                >
                  <Col span={4}>
                    <Space>
                      {getChangeTypeIcon(change.changeType)}
                      <Tooltip title={change.field}>
                        <Text strong ellipsis style={{ maxWidth: 100 }}>
                          {change.field}
                        </Text>
                      </Tooltip>
                    </Space>
                  </Col>
                  <Col span={10}>
                    <div
                      style={{
                        padding: 8,
                        backgroundColor: change.changeType === 'removed' || change.changeType === 'modified'
                          ? '#fff1f0'
                          : '#f5f5f5',
                        borderRadius: 4,
                        minHeight: 32,
                      }}
                    >
                      {formatValue(change.oldValue)}
                    </div>
                  </Col>
                  <Col span={10}>
                    <div
                      style={{
                        padding: 8,
                        backgroundColor: change.changeType === 'added' || change.changeType === 'modified'
                          ? '#f6ffed'
                          : '#f5f5f5',
                        borderRadius: 4,
                        minHeight: 32,
                      }}
                    >
                      {formatValue(change.newValue)}
                    </div>
                  </Col>
                </Row>
              ))}

            {/* Show unchanged fields (collapsed) */}
            {changeCounts.unchanged > 0 && (
              <>
                <Divider style={{ margin: '16px 0 8px' }}>
                  <Text type="secondary">
                    {t('ontology:comparison.unchangedFields', { count: changeCounts.unchanged })}
                  </Text>
                </Divider>
                {fieldChanges
                  .filter((change) => change.changeType === 'unchanged')
                  .slice(0, 5)
                  .map((change) => (
                    <Row
                      key={change.field}
                      gutter={16}
                      style={{
                        padding: '4px 0',
                        opacity: 0.6,
                      }}
                    >
                      <Col span={4}>
                        <Text type="secondary">{change.field}</Text>
                      </Col>
                      <Col span={20}>
                        <Text type="secondary">{formatValue(change.oldValue)}</Text>
                      </Col>
                    </Row>
                  ))}
                {changeCounts.unchanged > 5 && (
                  <Text type="secondary" style={{ display: 'block', textAlign: 'center' }}>
                    {t('ontology:comparison.andMoreUnchanged', { count: changeCounts.unchanged - 5 })}
                  </Text>
                )}
              </>
            )}
          </div>
        ) : (
          <Empty description={t('ontology:comparison.noChanges')} />
        )}
      </Card>
    </div>
  );
};

export default ChangeComparisonView;
