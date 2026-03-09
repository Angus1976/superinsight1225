/**
 * ReviewModal Component
 * 
 * Modal component for reviewing data with approve/reject functionality.
 */

import { useState, useEffect, useCallback } from 'react';
import { Modal, Descriptions, Tag, Button, Space, Input, Form, message, Spin, Alert } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useReview } from '@/hooks/useDataLifecycle';
import { useAuthStore } from '@/stores/authStore';
import type { Review } from '@/services/dataLifecycle';

const { TextArea } = Input;

// ============================================================================
// Types
// ============================================================================

interface ReviewModalProps {
  visible: boolean;
  review: Review | null;
  onClose: () => void;
  onSuccess?: () => void;
}

interface ReviewFormData {
  rejectionReason?: string;
}

// ============================================================================
// Component
// ============================================================================

const ReviewModal: React.FC<ReviewModalProps> = ({ visible, review, onClose, onSuccess }) => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<'approve' | 'reject' | null>(null);

  const { approveReview, rejectReview } = useReview();

  // Reset form when modal opens/closes
  useEffect(() => {
    if (visible) {
      form.resetFields();
      setAction(null);
    }
  }, [visible, form]);

  // Handle approve
  const handleApprove = useCallback(async () => {
    if (!review) return;
    
    setLoading(true);
    setAction('approve');
    try {
      await approveReview(review.id);
      message.success(t('review.messages.approveSuccess'));
      onSuccess?.();
      onClose();
    } catch {
      message.error(t('review.messages.approveFailed'));
    } finally {
      setLoading(false);
      setAction(null);
    }
  }, [review, approveReview, t, onSuccess, onClose]);

  // Handle reject
  const handleReject = useCallback(async () => {
    if (!review) return;
    
    try {
      const values = await form.validateFields();
      setLoading(true);
      setAction('reject');
      
      await rejectReview(review.id, values.rejectionReason || 'Rejected by reviewer');
      message.success(t('review.messages.rejectSuccess'));
      onSuccess?.();
      onClose();
    } catch (error) {
      if (error instanceof Error) {
        message.error(t('review.messages.rejectFailed'));
      }
    } finally {
      setLoading(false);
      setAction(null);
    }
  }, [review, rejectReview, form, t, onSuccess, onClose]);

  // Get status color
  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      pending: 'processing',
      approved: 'success',
      rejected: 'error',
      cancelled: 'default',
    };
    return colorMap[status] || 'default';
  };

  // Render target details based on target type
  const renderTargetDetails = () => {
    if (!review) return null;

    switch (review.target_type) {
      case 'temp_data':
        return (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('review.columns.targetId')}>
              {review.target_id}
            </Descriptions.Item>
            <Descriptions.Item label={t('common.type')}>
              {t('tabs.tempData')}
            </Descriptions.Item>
          </Descriptions>
        );
      case 'sample':
        return (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('review.columns.targetId')}>
              {review.target_id}
            </Descriptions.Item>
            <Descriptions.Item label={t('common.type')}>
              {t('tabs.sampleLibrary')}
            </Descriptions.Item>
          </Descriptions>
        );
      case 'enhancement':
        return (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('review.columns.targetId')}>
              {review.target_id}
            </Descriptions.Item>
            <Descriptions.Item label={t('common.type')}>
              {t('tabs.enhancement')}
            </Descriptions.Item>
          </Descriptions>
        );
      default:
        return (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('review.columns.targetType')}>
              {review.target_type}
            </Descriptions.Item>
            <Descriptions.Item label={t('review.columns.targetId')}>
              {review.target_id}
            </Descriptions.Item>
          </Descriptions>
        );
    }
  };

  if (!review) return null;

  const canApprove = hasPermission('review.approve') && review.status === 'pending';
  const canReject = hasPermission('review.reject') && review.status === 'pending';

  return (
    <Modal
      title={
        <Space>
          <ExclamationCircleOutlined />
          <span>{t('review.title')}</span>
          <Tag color={getStatusColor(review.status)}>
            {t(`review.status.${review.status}`)}
          </Tag>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={null}
      destroyOnClose
    >
      <Spin spinning={loading}>
        {/* Review Info */}
        <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label={t('review.columns.id')}>
            {review.id}
          </Descriptions.Item>
          <Descriptions.Item label={t('review.columns.requester')}>
            {review.requester}
          </Descriptions.Item>
          <Descriptions.Item label={t('review.columns.submittedAt')}>
            {new Date(review.submitted_at).toLocaleString()}
          </Descriptions.Item>
          {review.reviewer && (
            <Descriptions.Item label={t('review.columns.reviewer')}>
              {review.reviewer}
            </Descriptions.Item>
          )}
          {review.reviewed_at && (
            <Descriptions.Item label={t('review.columns.reviewedAt')}>
              {new Date(review.reviewed_at).toLocaleString()}
            </Descriptions.Item>
          )}
        </Descriptions>

        {/* Target Details */}
        <Alert
          message={t('review.targetDetails')}
          description={renderTargetDetails()}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* Rejection Reason Input (shown when rejecting) */}
        <Form form={form} layout="vertical">
          <Form.Item
            name="rejectionReason"
            label={t('review.messages.rejectionReason')}
            rules={[
              { required: true, message: t('review.messages.rejectionReasonRequired') },
            ]}
          >
            <TextArea
              rows={4}
              placeholder={t('placeholders.input', { field: t('review.messages.rejectionReason') })}
            />
          </Form.Item>
        </Form>

        {/* Action Buttons */}
        <div style={{ textAlign: 'right', marginTop: 16 }}>
          <Space>
            <Button onClick={onClose} disabled={loading}>
              {t('common.actions.cancel')}
            </Button>
            {canReject && (
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={handleReject}
                loading={action === 'reject'}
              >
                {t('review.actions.reject')}
              </Button>
            )}
            {canApprove && (
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={handleApprove}
                loading={action === 'approve'}
              >
                {t('review.actions.approve')}
              </Button>
            )}
          </Space>
        </div>
      </Spin>
    </Modal>
  );
};

export default ReviewModal;