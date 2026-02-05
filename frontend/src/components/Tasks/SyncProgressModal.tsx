/**
 * SyncProgressModal Component
 * Displays sync progress in a modal dialog.
 * 
 * Extracted from TasksPage for reusability.
 */
import React, { memo } from 'react';
import { Modal, Progress, Tag, Space } from 'antd';
import { SyncOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

export type SyncStatus = 'idle' | 'syncing' | 'completed' | 'error';

export interface SyncProgress {
  current: number;
  total: number;
  status: SyncStatus;
  message: string;
}

export interface SyncProgressModalProps {
  open: boolean;
  progress: SyncProgress;
  onClose: () => void;
}

const SyncProgressModalComponent: React.FC<SyncProgressModalProps> = ({
  open,
  progress,
  onClose,
}) => {
  const { t } = useTranslation('tasks');
  const isSyncing = progress.status === 'syncing';

  const handleClose = () => {
    if (!isSyncing) {
      onClose();
    }
  };

  const getProgressStatus = () => {
    switch (progress.status) {
      case 'error':
        return 'exception';
      case 'completed':
        return 'success';
      default:
        return 'active';
    }
  };

  const getProgressPercent = () => {
    if (progress.total === 0) {
      return progress.status === 'completed' ? 100 : 0;
    }
    return Math.round((progress.current / progress.total) * 100);
  };

  const getProgressFormat = () => {
    if (progress.total === 0) {
      return undefined;
    }
    return () => `${progress.current}/${progress.total}`;
  };

  return (
    <Modal
      title={
        <Space>
          <SyncOutlined spin={isSyncing} />
          {t('syncProgressTitle') || 'Sync Progress'}
        </Space>
      }
      open={open}
      onCancel={handleClose}
      footer={
        isSyncing ? null : (
          <button 
            type="button"
            className="ant-btn ant-btn-primary"
            onClick={handleClose}
          >
            {t('close') || 'Close'}
          </button>
        )
      }
      closable={!isSyncing}
      maskClosable={!isSyncing}
    >
      <div style={{ textAlign: 'center', padding: '20px 0' }}>
        <Progress
          type="circle"
          percent={getProgressPercent()}
          status={getProgressStatus()}
          format={getProgressFormat()}
        />
        <p style={{ marginTop: 16, color: '#666' }}>
          {progress.message}
        </p>
        {progress.status === 'completed' && progress.total > 0 && (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            {t('syncCompleted') || 'Sync Completed'}
          </Tag>
        )}
        {progress.status === 'error' && (
          <Tag color="error" icon={<ExclamationCircleOutlined />}>
            {t('syncHasErrors') || 'Sync Has Errors'}
          </Tag>
        )}
      </div>
    </Modal>
  );
};

export const SyncProgressModal = memo(SyncProgressModalComponent);
export default SyncProgressModal;
