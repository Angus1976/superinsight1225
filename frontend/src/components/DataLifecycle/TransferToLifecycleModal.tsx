/**
 * Transfer to Lifecycle Modal Component
 * 
 * Unified modal for transferring AI processing results to data lifecycle stages.
 * Supports 4 processing methods: structuring, vectorization, semantic, ai_annotation
 */

import React, { useState, useEffect } from 'react';
import { Modal, Form, Select, Input, Tag, Space, Typography, Divider, Alert, Badge, message, Progress, Card, Row, Col, Statistic } from 'antd';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { useTransferToLifecycle } from '@/hooks/useTransferToLifecycle';

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

export type PermissionLevel = 'administrator' | 'direct_transfer' | 'approval_required' | 'no_permission';

export interface TransferDataItem {
  id: string;
  name: string;
  content: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface TransferToLifecycleModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  sourceType: 'structuring' | 'vectorization' | 'semantic' | 'ai_annotation';
  selectedData: TransferDataItem[];
}

export interface TransferFormValues {
  targetStage: 'temp_data' | 'sample_library' | 'annotated' | 'enhanced';
  dataType?: 'text' | 'image' | 'audio' | 'video';
  tags?: string[];
  remark?: string;
  qualityThreshold?: number;
  approvalReason?: string; // For approval workflow
}

interface SemanticTypeGroup {
  type: string;
  count: number;
  items: TransferDataItem[];
}

const TransferToLifecycleModal: React.FC<TransferToLifecycleModalProps> = ({
  visible,
  onClose,
  onSuccess,
  sourceType,
  selectedData,
}) => {
  const { t } = useTranslation('aiProcessing');
  const [form] = Form.useForm<TransferFormValues>();
  const [permissionLevel, setPermissionLevel] = useState<PermissionLevel>('approval_required');
  const { user } = useAuthStore();
  const { transferData, loading: transferLoading, progress } = useTransferToLifecycle();
  const [loading, setLoading] = useState(false);
  const [isTransferring, setIsTransferring] = useState(false);

  // Group semantic data by type
  const semanticTypeGroups: SemanticTypeGroup[] = React.useMemo(() => {
    if (sourceType !== 'semantic') return [];
    
    const groups = new Map<string, TransferDataItem[]>();
    selectedData.forEach(item => {
      const recordType = item.metadata?.recordType as string || 'unknown';
      if (!groups.has(recordType)) {
        groups.set(recordType, []);
      }
      groups.get(recordType)!.push(item);
    });

    return Array.from(groups.entries()).map(([type, items]) => ({
      type,
      count: items.length,
      items,
    }));
  }, [sourceType, selectedData]);

  // Get AI annotation quality distribution
  const qualityDistribution = React.useMemo(() => {
    if (sourceType !== 'ai_annotation' || selectedData.length === 0) {
      return { high: 0, medium: 0, low: 0 };
    }

    const avgConfidence = selectedData[0]?.metadata?.averageConfidence as number || 0;
    
    // Simulate distribution based on average confidence
    if (avgConfidence >= 0.8) {
      return { high: 70, medium: 25, low: 5 };
    } else if (avgConfidence >= 0.6) {
      return { high: 40, medium: 45, low: 15 };
    } else {
      return { high: 20, medium: 50, low: 30 };
    }
  }, [sourceType, selectedData]);

  // Check user permission level when modal opens
  useEffect(() => {
    if (visible && user) {
      checkPermissionLevel();
    }
  }, [visible, user]);

  const checkPermissionLevel = async () => {
    // TODO: Call permission service to get user's permission level
    // For now, check if user is admin
    const isAdmin = user?.role === 'admin' || user?.role === 'administrator';
    setPermissionLevel(isAdmin ? 'administrator' : 'approval_required');
  };

  // Reset form when modal opens
  useEffect(() => {
    if (visible) {
      form.resetFields();
    }
  }, [visible, form]);

  // Get available target stages based on source type
  const getAvailableStages = (): Array<{ value: string; label: string }> => {
    const stageMap: Record<string, string[]> = {
      structuring: ['temp_data', 'sample_library'],
      vectorization: ['temp_data', 'sample_library', 'enhanced'],
      semantic: ['temp_data', 'sample_library', 'enhanced'],
      ai_annotation: ['annotated', 'sample_library'],
    };

    const stages = stageMap[sourceType] || [];
    return stages.map(stage => ({
      value: stage,
      label: t(`transfer.stages.${stage}`),
    }));
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      setIsTransferring(true);

      if (permissionLevel === 'administrator' || permissionLevel === 'direct_transfer') {
        // Direct transfer for admin or users with direct transfer permission
        const result = await transferData({
          sourceType,
          data: selectedData,
          targetStage: values.targetStage,
          options: {
            dataType: values.dataType,
            tags: values.tags,
            remark: values.remark,
            qualityThreshold: values.qualityThreshold,
          },
        });

        setIsTransferring(false);

        if (result.success) {
          message.success(
            t('transfer.messages.success', {
              count: result.successCount,
              stage: t(`transfer.stages.${values.targetStage}`),
            })
          );
          form.resetFields();
          onClose();
          onSuccess?.();
        } else if (result.failedCount > 0 && result.successCount > 0) {
          // Partial success
          message.warning(
            t('transfer.messages.partialSuccess', {
              success: result.successCount,
              failed: result.failedCount,
            })
          );
          form.resetFields();
          onClose();
          onSuccess?.();
        } else {
          // Complete failure
          const firstError = result.failedItems[0]?.reason || 'Unknown error';
          message.error(
            t('transfer.messages.failed', {
              reason: firstError,
            })
          );
        }
      } else {
        // Create approval request for regular users
        // TODO: Call approval service
        console.log('Create approval request:', {
          sourceType,
          selectedData,
          ...values,
        });

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));

        setIsTransferring(false);
        message.info(t('transfer.approval.messages.submitted'));
        form.resetFields();
        onClose();
      }
    } catch (err) {
      setIsTransferring(false);
      console.error('Transfer failed:', err);
      if (err instanceof Error) {
        message.error(
          t('transfer.messages.failed', {
            reason: err.message,
          })
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onClose();
  };

  const getModalTitle = () => {
    if (permissionLevel === 'administrator' || permissionLevel === 'direct_transfer') {
      return t('transfer.modal.title');
    }
    return t('transfer.approval.title');
  };

  const getOkButtonText = () => {
    if (permissionLevel === 'administrator' || permissionLevel === 'direct_transfer') {
      return t('transfer.approval.directTransfer');
    }
    return t('transfer.approval.submitApproval');
  };

  return (
    <Modal
      title={getModalTitle()}
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading || transferLoading}
      okText={getOkButtonText()}
      cancelText={t('common:action.cancel')}
      width={600}
      closable={!isTransferring}
      maskClosable={!isTransferring}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Permission level badge */}
        <Alert
          message={
            <Space>
              <Text>{t('transfer.permission.yourLevel', { level: t(`transfer.permission.level.${permissionLevel}`) })}</Text>
              {permissionLevel === 'administrator' && (
                <Badge status="success" text={t('transfer.approval.directTransfer')} />
              )}
              {permissionLevel === 'approval_required' && (
                <Badge status="warning" text={t('transfer.approval.status.pending')} />
              )}
            </Space>
          }
          type={permissionLevel === 'administrator' ? 'success' : 'info'}
          showIcon
        />

        {/* Selected data count */}
        <Alert
          message={t('transfer.modal.selectedCount', { count: selectedData.length })}
          type="info"
          showIcon
        />

        {/* Semantic type grouping info */}
        {sourceType === 'semantic' && semanticTypeGroups.length > 0 && (
          <Alert
            message={
              <Space direction="vertical" size="small">
                <Text strong>{t('transfer.modal.typeGrouping', { defaultValue: '按类型分组' })}</Text>
                <Space wrap>
                  {semanticTypeGroups.map(group => (
                    <Tag key={group.type} color={group.type === 'entity' ? 'blue' : group.type === 'relationship' ? 'green' : 'orange'}>
                      {group.type}: {group.count}
                    </Tag>
                  ))}
                </Space>
              </Space>
            }
            type="info"
          />
        )}

        {/* AI Annotation task info and quality distribution */}
        {sourceType === 'ai_annotation' && selectedData.length > 0 && (
          <Card size="small" title={t('transfer.modal.annotationInfo', { defaultValue: '标注任务信息' })}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text type="secondary">{t('transfer.modal.taskName', { defaultValue: '任务名称' })}: </Text>
                <Text strong>{selectedData[0].name}</Text>
              </div>
              <div>
                <Text type="secondary">{t('transfer.modal.annotationCount', { defaultValue: '标注数据数量' })}: </Text>
                <Text strong>{String(selectedData[0].metadata?.annotatedCount || 0)}</Text>
              </div>
              <Divider style={{ margin: '8px 0' }} />
              <div>
                <Text strong>{t('transfer.modal.qualityDistribution', { defaultValue: '质量分布' })}</Text>
                <Row gutter={16} style={{ marginTop: 8 }}>
                  <Col span={8}>
                    <Statistic 
                      title={t('transfer.modal.highQuality', { defaultValue: '高质量' })} 
                      value={qualityDistribution.high} 
                      suffix="%" 
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic 
                      title={t('transfer.modal.mediumQuality', { defaultValue: '中等质量' })} 
                      value={qualityDistribution.medium} 
                      suffix="%" 
                      valueStyle={{ color: '#faad14' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic 
                      title={t('transfer.modal.lowQuality', { defaultValue: '低质量' })} 
                      value={qualityDistribution.low} 
                      suffix="%" 
                      valueStyle={{ color: '#cf1322' }}
                    />
                  </Col>
                </Row>
              </div>
            </Space>
          </Card>
        )}

        {/* Progress bar for batch transfer */}
        {isTransferring && progress.total > 0 && (
          <div>
            <Text strong>{t('transfer.progress.title')}</Text>
            <Progress
              percent={progress.percentage}
              status={progress.failed > 0 ? 'exception' : 'active'}
              format={() => `${progress.completed + progress.failed}/${progress.total}`}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('transfer.progress.processing', { 
                current: progress.completed + progress.failed, 
                total: progress.total 
              })}
            </Text>
          </div>
        )}

        <Form
          form={form}
          layout="vertical"
        >
          {/* Target stage selection */}
          <Form.Item
            name="targetStage"
            label={t('transfer.modal.selectStage')}
            rules={[{ required: true, message: t('transfer.messages.noStageSelected') }]}
          >
            <Select
              placeholder={t('transfer.modal.selectStage')}
              options={getAvailableStages()}
            />
          </Form.Item>

          {/* Data type (optional) */}
          <Form.Item
            name="dataType"
            label={t('transfer.modal.dataType')}
          >
            <Select
              placeholder={t('transfer.modal.dataType')}
              allowClear
            >
              <Option value="text">{t('transfer.dataTypes.text')}</Option>
              <Option value="image">{t('transfer.dataTypes.image')}</Option>
              <Option value="audio">{t('transfer.dataTypes.audio')}</Option>
              <Option value="video">{t('transfer.dataTypes.video')}</Option>
            </Select>
          </Form.Item>

          {/* Tags (optional) */}
          <Form.Item
            name="tags"
            label={t('transfer.modal.tags')}
          >
            <Select
              mode="tags"
              placeholder={t('transfer.modal.tagsPlaceholder')}
              style={{ width: '100%' }}
            />
          </Form.Item>

          {/* Remark (optional) */}
          <Form.Item
            name="remark"
            label={t('transfer.modal.remark')}
          >
            <TextArea
              rows={3}
              placeholder={t('transfer.modal.remarkPlaceholder')}
            />
          </Form.Item>

          {/* Quality threshold (for AI annotation only) */}
          {sourceType === 'ai_annotation' && (
            <Form.Item
              name="qualityThreshold"
              label={t('transfer.modal.qualityThreshold')}
              tooltip={t('transfer.modal.qualityThresholdTooltip', { defaultValue: '只转存置信度高于此阈值的标注结果' })}
            >
              <Input
                type="number"
                min={0}
                max={1}
                step={0.1}
                placeholder="0.7"
                addonAfter={t('transfer.modal.confidenceRange', { defaultValue: '(0-1)' })}
              />
            </Form.Item>
          )}

          {/* Approval reason (for regular users only) */}
          {permissionLevel === 'approval_required' && (
            <Form.Item
              name="approvalReason"
              label={t('transfer.approval.reason')}
              rules={[{ required: true, message: t('transfer.approval.reasonPlaceholder') }]}
            >
              <TextArea
                rows={3}
                placeholder={t('transfer.approval.reasonPlaceholder')}
              />
            </Form.Item>
          )}
        </Form>

        {/* Data preview */}
        {selectedData.length > 0 && (
          <>
            <Divider style={{ margin: '8px 0' }} />
            <div>
              <Text type="secondary">{t('transfer.modal.preview')}</Text>
              <div style={{ marginTop: 8, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
                <Text ellipsis style={{ fontSize: 12 }}>
                  {selectedData[0].name}
                </Text>
              </div>
            </div>
          </>
        )}
      </Space>
    </Modal>
  );
};

export default TransferToLifecycleModal;
