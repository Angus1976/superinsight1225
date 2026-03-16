/**
 * Conflict Resolution Dialog Component (冲突解决对话框)
 * 
 * Displays conflicting changes and provides resolution options:
 * accept_theirs, accept_mine, or manual_merge.
 * 
 * Requirements: Task 22.3 - Collaborative Editing
 * Validates: Requirements 1.4, 7.3
 */

import React, { useState, useMemo } from 'react';
import {
  Modal,
  Card,
  Row,
  Col,
  Typography,
  Space,
  Button,
  Radio,
  Input,
  Alert,
  Divider,
  Tag,
  Tooltip,
  message,
} from 'antd';
import {
  WarningOutlined,
  UserOutlined,
  TeamOutlined,
  MergeCellsOutlined,
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { ontologyCollaborationApi } from '@/services/ontologyExpertApi';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

type ResolutionStrategy = 'accept_theirs' | 'accept_mine' | 'manual_merge';

interface ConflictField {
  field: string;
  myValue: unknown;
  theirValue: unknown;
  baseValue?: unknown;
}

interface EditConflict {
  id: string;
  element_id: string;
  element_type: string;
  my_changes: Record<string, unknown>;
  their_changes: Record<string, unknown>;
  base_state: Record<string, unknown>;
  their_user_id: string;
  their_user_name: string;
  detected_at: string;
}

interface ConflictResolutionDialogProps {
  conflict: EditConflict | null;
  visible: boolean;
  onClose: () => void;
  onResolved?: () => void;
}

const ConflictResolutionDialog: React.FC<ConflictResolutionDialogProps> = ({
  conflict,
  visible,
  onClose,
  onResolved,
}) => {
  const { t } = useTranslation(['ontology', 'common']);
  const [selectedStrategy, setSelectedStrategy] = useState<ResolutionStrategy>('accept_theirs');
  const [manualMergeContent, setManualMergeContent] = useState<Record<string, unknown>>({});
  const [showMergeEditor, setShowMergeEditor] = useState(false);

  // Resolve conflict mutation
  const resolveMutation = useMutation({
    mutationFn: ({
      conflictId,
      resolution,
      mergedContent,
    }: {
      conflictId: string;
      resolution: ResolutionStrategy;
      mergedContent?: Record<string, unknown>;
    }) => ontologyCollaborationApi.resolveConflict(conflictId, resolution, mergedContent),
    onSuccess: () => {
      message.success(t('ontology:conflict.resolveSuccess'));
      onResolved?.();
      handleClose();
    },
    onError: () => {
      message.error(t('ontology:conflict.resolveFailed'));
    },
  });

  // Reset state when modal closes
  const handleClose = () => {
    setSelectedStrategy('accept_theirs');
    setManualMergeContent({});
    setShowMergeEditor(false);
    onClose();
  };

  // Calculate conflicting fields
  const conflictingFields = useMemo((): ConflictField[] => {
    if (!conflict) return [];

    const fields: ConflictField[] = [];
    const allFields = new Set<string>();

    Object.keys(conflict.my_changes).forEach((key) => allFields.add(key));
    Object.keys(conflict.their_changes).forEach((key) => allFields.add(key));

    allFields.forEach((field) => {
      const myValue = conflict.my_changes[field];
      const theirValue = conflict.their_changes[field];
      const baseValue = conflict.base_state[field];

      // Only show fields where both users made changes
      if (myValue !== undefined && theirValue !== undefined) {
        if (JSON.stringify(myValue) !== JSON.stringify(theirValue)) {
          fields.push({ field, myValue, theirValue, baseValue });
        }
      }
    });

    return fields;
  }, [conflict]);

  // Initialize manual merge content
  const initializeManualMerge = () => {
    if (!conflict) return;

    // Start with base state, then apply non-conflicting changes
    const merged: Record<string, unknown> = { ...conflict.base_state };

    // Apply my changes for non-conflicting fields
    Object.entries(conflict.my_changes).forEach(([key, value]) => {
      if (!conflictingFields.some((f) => f.field === key)) {
        merged[key] = value;
      }
    });

    // For conflicting fields, default to their value (can be edited)
    conflictingFields.forEach((field) => {
      merged[field.field] = field.theirValue;
    });

    setManualMergeContent(merged);
    setShowMergeEditor(true);
  };

  // Handle strategy change
  const handleStrategyChange = (strategy: ResolutionStrategy) => {
    setSelectedStrategy(strategy);
    if (strategy === 'manual_merge') {
      initializeManualMerge();
    } else {
      setShowMergeEditor(false);
    }
  };

  // Handle resolve
  const handleResolve = () => {
    if (!conflict) return;

    resolveMutation.mutate({
      conflictId: conflict.id,
      resolution: selectedStrategy,
      mergedContent: selectedStrategy === 'manual_merge' ? manualMergeContent : undefined,
    });
  };

  // Format value for display
  const formatValue = (value: unknown): string => {
    if (value === undefined || value === null) return '-';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  // Update manual merge field
  const updateMergeField = (field: string, value: string) => {
    try {
      // Try to parse as JSON first
      const parsed = JSON.parse(value);
      setManualMergeContent((prev) => ({ ...prev, [field]: parsed }));
    } catch {
      // If not valid JSON, use as string
      setManualMergeContent((prev) => ({ ...prev, [field]: value }));
    }
  };

  // Render conflict field comparison
  const renderFieldComparison = (field: ConflictField) => (
    <Card
      key={field.field}
      size="small"
      style={{ marginBottom: 12 }}
      title={
        <Space>
          <WarningOutlined style={{ color: '#faad14' }} />
          <Text strong>{field.field}</Text>
        </Space>
      }
    >
      <Row gutter={16}>
        <Col span={8}>
          <div style={{ marginBottom: 8 }}>
            <Tag color="default">{t('ontology:conflict.baseValue')}</Tag>
          </div>
          <div
            style={{
              padding: 8,
              backgroundColor: '#f5f5f5',
              borderRadius: 4,
              minHeight: 60,
              maxHeight: 120,
              overflow: 'auto',
            }}
          >
            <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>
              {formatValue(field.baseValue)}
            </pre>
          </div>
        </Col>
        <Col span={8}>
          <div style={{ marginBottom: 8 }}>
            <Tag color="blue" icon={<UserOutlined />}>
              {t('ontology:conflict.myChanges')}
            </Tag>
          </div>
          <div
            style={{
              padding: 8,
              backgroundColor: '#e6f7ff',
              borderRadius: 4,
              border: '1px solid #91d5ff',
              minHeight: 60,
              maxHeight: 120,
              overflow: 'auto',
            }}
          >
            <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>
              {formatValue(field.myValue)}
            </pre>
          </div>
        </Col>
        <Col span={8}>
          <div style={{ marginBottom: 8 }}>
            <Tag color="orange" icon={<TeamOutlined />}>
              {t('ontology:conflict.theirChanges')}
            </Tag>
          </div>
          <div
            style={{
              padding: 8,
              backgroundColor: '#fff7e6',
              borderRadius: 4,
              border: '1px solid #ffd591',
              minHeight: 60,
              maxHeight: 120,
              overflow: 'auto',
            }}
          >
            <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>
              {formatValue(field.theirValue)}
            </pre>
          </div>
        </Col>
      </Row>
    </Card>
  );

  // Render manual merge editor
  const renderManualMergeEditor = () => (
    <Card
      title={
        <Space>
          <MergeCellsOutlined />
          {t('ontology:conflict.manualMergeEditor')}
        </Space>
      }
      style={{ marginTop: 16 }}
    >
      <Alert
        message={t('ontology:conflict.manualMergeInfo')}
        description={t('ontology:conflict.manualMergeInfoDesc')}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {conflictingFields.map((field) => (
        <div key={field.field} style={{ marginBottom: 16 }}>
          <Text strong>{field.field}</Text>
          <TextArea
            rows={3}
            value={formatValue(manualMergeContent[field.field])}
            onChange={(e) => updateMergeField(field.field, e.target.value)}
            style={{ marginTop: 8 }}
          />
          <Space style={{ marginTop: 8 }}>
            <Button
              size="small"
              onClick={() =>
                setManualMergeContent((prev) => ({
                  ...prev,
                  [field.field]: field.myValue,
                }))
              }
            >
              {t('ontology:conflict.useMyValue')}
            </Button>
            <Button
              size="small"
              onClick={() =>
                setManualMergeContent((prev) => ({
                  ...prev,
                  [field.field]: field.theirValue,
                }))
              }
            >
              {t('ontology:conflict.useTheirValue')}
            </Button>
          </Space>
        </div>
      ))}
    </Card>
  );

  if (!conflict) return null;

  return (
    <Modal
      title={
        <Space>
          <WarningOutlined style={{ color: '#faad14' }} />
          {t('ontology:conflict.title')}
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={900}
      footer={
        <Space>
          <Button onClick={handleClose}>{t('common:cancel')}</Button>
          <Button
            type="primary"
            onClick={handleResolve}
            loading={resolveMutation.isPending}
            icon={<CheckOutlined />}
          >
            {t('ontology:conflict.resolve')}
          </Button>
        </Space>
      }
    >
      {/* Conflict Info */}
      <Alert
        message={t('ontology:conflict.detected')}
        description={
          <Space direction="vertical">
            <Text>
              {t('ontology:conflict.detectedDesc', {
                user: conflict.their_user_name,
                element: conflict.element_id,
              })}
            </Text>
            <Text type="secondary">
              {t('ontology:conflict.detectedAt', {
                time: new Date(conflict.detected_at).toLocaleString(),
              })}
            </Text>
          </Space>
        }
        type="warning"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* Conflicting Fields */}
      <Title level={5}>
        <Space>
          <SwapOutlined />
          {t('ontology:conflict.conflictingFields')}
          <Tag>{conflictingFields.length}</Tag>
        </Space>
      </Title>

      {conflictingFields.map(renderFieldComparison)}

      <Divider />

      {/* Resolution Strategy */}
      <Title level={5}>{t('ontology:conflict.selectStrategy')}</Title>

      <Radio.Group
        value={selectedStrategy}
        onChange={(e) => handleStrategyChange(e.target.value)}
        style={{ width: '100%' }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Card
            size="small"
            hoverable
            style={{
              borderColor: selectedStrategy === 'accept_theirs' ? '#1890ff' : undefined,
            }}
            onClick={() => handleStrategyChange('accept_theirs')}
          >
            <Radio value="accept_theirs">
              <Space>
                <TeamOutlined style={{ color: '#faad14' }} />
                <div>
                  <Text strong>{t('ontology:conflict.acceptTheirs')}</Text>
                  <br />
                  <Text type="secondary">{t('ontology:conflict.acceptTheirsDesc')}</Text>
                </div>
              </Space>
            </Radio>
          </Card>

          <Card
            size="small"
            hoverable
            style={{
              borderColor: selectedStrategy === 'accept_mine' ? '#1890ff' : undefined,
            }}
            onClick={() => handleStrategyChange('accept_mine')}
          >
            <Radio value="accept_mine">
              <Space>
                <UserOutlined style={{ color: '#1890ff' }} />
                <div>
                  <Text strong>{t('ontology:conflict.acceptMine')}</Text>
                  <br />
                  <Text type="secondary">{t('ontology:conflict.acceptMineDesc')}</Text>
                </div>
              </Space>
            </Radio>
          </Card>

          <Card
            size="small"
            hoverable
            style={{
              borderColor: selectedStrategy === 'manual_merge' ? '#1890ff' : undefined,
            }}
            onClick={() => handleStrategyChange('manual_merge')}
          >
            <Radio value="manual_merge">
              <Space>
                <MergeCellsOutlined style={{ color: '#52c41a' }} />
                <div>
                  <Text strong>{t('ontology:conflict.manualMerge')}</Text>
                  <br />
                  <Text type="secondary">{t('ontology:conflict.manualMergeDesc')}</Text>
                </div>
              </Space>
            </Radio>
          </Card>
        </Space>
      </Radio.Group>

      {/* Manual Merge Editor */}
      {showMergeEditor && renderManualMergeEditor()}
    </Modal>
  );
};

export default ConflictResolutionDialog;
