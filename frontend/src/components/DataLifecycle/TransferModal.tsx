/**
 * TransferModal Component
 * 
 * Comprehensive modal for configuring and executing data transfer operations.
 * Implements permission checking, form validation, and error handling.
 */

import React, { useState, useEffect } from 'react';
import { Modal, Form, Select, Input, InputNumber, Tag, Space, message, Spin, Alert } from 'antd';
import { useTranslation } from 'react-i18next';
import { 
  transferDataAPI, 
  checkPermissionAPI,
  DataTransferError,
  type TransferRecord,
  type TransferResponse,
  type DataAttributes
} from '@/api/dataLifecycleAPI';

const { TextArea } = Input;
const { Option } = Select;

// ============================================================================
// Types
// ============================================================================

export interface TransferModalProps {
  visible: boolean;
  onClose: () => void;
  sourceType: 'structuring' | 'augmentation' | 'sync' | 'annotation' | 'ai_assistant' | 'manual';
  sourceId: string;
  records: TransferRecord[];
  onSuccess?: (result: TransferResponse) => void;
}

interface TargetStateOption {
  value: 'temp_stored' | 'in_sample_library' | 'annotation_pending';
  allowed: boolean;
  requiresApproval: boolean;
}

interface FormValues {
  targetState: 'temp_stored' | 'in_sample_library' | 'annotation_pending';
  category: string;
  tags: string[];
  qualityScore?: number;
  description?: string;
}

// ============================================================================
// Component
// ============================================================================

export const TransferModal: React.FC<TransferModalProps> = ({
  visible,
  onClose,
  sourceType,
  sourceId,
  records,
  onSuccess,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm<FormValues>();
  
  // State
  const [submitting, setSubmitting] = useState(false);
  const [checkingPermissions, setCheckingPermissions] = useState(false);
  const [targetStates, setTargetStates] = useState<TargetStateOption[]>([]);
  const [tags, setTags] = useState<string[]>([]);

  // Check permissions when modal opens
  useEffect(() => {
    if (visible) {
      checkAllPermissions();
      form.resetFields();
      setTags([]);
    }
  }, [visible, sourceType]);

  // ============================================================================
  // Permission Checking
  // ============================================================================

  const checkAllPermissions = async () => {
    setCheckingPermissions(true);
    
    try {
      const states: Array<'temp_stored' | 'in_sample_library' | 'annotation_pending'> = [
        'temp_stored',
        'in_sample_library',
        'annotation_pending'
      ];
      
      const results = await Promise.all(
        states.map(state => 
          checkPermissionAPI({
            source_type: sourceType,
            target_state: state,
          })
        )
      );
      
      setTargetStates(
        states.map((state, index) => ({
          value: state,
          allowed: results[index].allowed,
          requiresApproval: results[index].requires_approval,
        }))
      );
    } catch (error) {
      console.error('Permission check failed:', error);
      message.error(t('common.messages.networkError'));
    } finally {
      setCheckingPermissions(false);
    }
  };

  // ============================================================================
  // Form Handlers
  // ============================================================================

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      
      const dataAttributes: DataAttributes = {
        category: values.category,
        tags: tags,
        quality_score: values.qualityScore,
        description: values.description,
      };
      
      const result = await transferDataAPI({
        source_type: sourceType,
        source_id: sourceId,
        target_state: values.targetState,
        data_attributes: dataAttributes,
        records,
      });
      
      // Handle approval required
      if (result.approval_required) {
        message.info(
          t('transfer.messages.approvalRequired') + 
          (result.estimated_approval_time 
            ? ` ${t('transfer.messages.approvalEstimatedTime', { time: result.estimated_approval_time })}`
            : '')
        );
      } else {
        // Handle success
        message.success(
          t('transfer.messages.success', {
            count: result.transferred_count,
            state: t(`transfer.targetStates.${result.target_state}`),
          })
        );
      }
      
      onSuccess?.(result);
      onClose();
    } catch (error) {
      if (error instanceof DataTransferError) {
        message.error(t('transfer.messages.error', { error: error.message }));
      } else {
        message.error(t('transfer.messages.internalError'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setTags([]);
    onClose();
  };

  // ============================================================================
  // Tag Handlers
  // ============================================================================

  const handleTagChange = (value: string[]) => {
    setTags(value);
  };

  // ============================================================================
  // Render Helpers
  // ============================================================================

  const getPermissionIndicator = (state: TargetStateOption) => {
    if (!state.allowed) {
      return ` ${t('transfer.permissions.noPermission')}`;
    }
    if (state.requiresApproval) {
      return ` ${t('transfer.permissions.requiresApproval')}`;
    }
    return '';
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <Modal
      title={t('transfer.modal.title')}
      open={visible}
      onCancel={handleCancel}
      onOk={handleSubmit}
      confirmLoading={submitting}
      okText={t('transfer.actions.confirm')}
      cancelText={t('transfer.actions.cancel')}
      width={600}
      destroyOnClose
    >
      <Spin spinning={checkingPermissions} tip={t('common.status.loading')}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* Data Summary */}
          <Alert
            message={t('transfer.summary.title')}
            description={
              <Space direction="vertical" size="small">
                <div>
                  <strong>{t('transfer.summary.source')}:</strong>{' '}
                  {t(`transfer.sourceTypes.${sourceType}`)}
                </div>
                <div>
                  <strong>{t('transfer.summary.recordCount')}:</strong> {records.length}
                </div>
              </Space>
            }
            type="info"
            showIcon
          />

          {/* Form */}
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              qualityScore: 0.8,
            }}
          >
            {/* Target State */}
            <Form.Item
              label={t('transfer.fields.targetState')}
              name="targetState"
              rules={[
                { required: true, message: t('transfer.validation.targetStateRequired') }
              ]}
            >
              <Select
                placeholder={t('transfer.fields.targetStateRequired')}
                disabled={checkingPermissions}
              >
                {targetStates.map(state => (
                  <Option
                    key={state.value}
                    value={state.value}
                    disabled={!state.allowed}
                  >
                    {t(`transfer.targetStates.${state.value}`)}
                    {getPermissionIndicator(state)}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {/* Category */}
            <Form.Item
              label={t('transfer.fields.category')}
              name="category"
              rules={[
                { required: true, message: t('transfer.validation.categoryRequired') },
                { min: 1, message: t('transfer.validation.categoryRequired') },
                { max: 100, message: t('transfer.validation.categoryRequired') }
              ]}
            >
              <Input placeholder={t('transfer.fields.categoryPlaceholder')} />
            </Form.Item>

            {/* Tags */}
            <Form.Item
              label={t('transfer.fields.tags')}
            >
              <Select
                mode="tags"
                value={tags}
                onChange={handleTagChange}
                placeholder={t('transfer.fields.tagsPlaceholder')}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* Quality Score */}
            <Form.Item
              label={t('transfer.fields.qualityScore')}
              name="qualityScore"
              rules={[
                {
                  type: 'number',
                  min: 0,
                  max: 1,
                  message: t('transfer.validation.invalidQualityScore')
                }
              ]}
            >
              <InputNumber
                min={0}
                max={1}
                step={0.05}
                style={{ width: '100%' }}
              />
            </Form.Item>

            {/* Description */}
            <Form.Item
              label={t('transfer.fields.description')}
              name="description"
            >
              <TextArea
                rows={3}
                placeholder={t('transfer.fields.descriptionPlaceholder')}
                maxLength={500}
                showCount
              />
            </Form.Item>
          </Form>
        </Space>
      </Spin>
    </Modal>
  );
};

export default TransferModal;
