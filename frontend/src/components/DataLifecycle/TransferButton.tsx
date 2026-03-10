/**
 * TransferButton Component
 * 
 * Reusable button component for triggering data transfer operations.
 * Integrates with permission checking and displays appropriate disabled states.
 */

import React, { useState, useEffect } from 'react';
import { Button, Tooltip } from 'antd';
import { ExportOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { checkPermissionAPI } from '@/api/dataLifecycleAPI';
import type { TransferRecord } from '@/api/dataLifecycleAPI';
import { TransferModal } from './TransferModal';

export interface TransferButtonProps {
  sourceType: 'structuring' | 'augmentation' | 'sync' | 'annotation' | 'ai_assistant' | 'manual';
  sourceId: string;
  records: TransferRecord[];
  disabled?: boolean;
  onTransferComplete?: (result: any) => void;
}

export const TransferButton: React.FC<TransferButtonProps> = ({
  sourceType,
  sourceId,
  records,
  disabled = false,
  onTransferComplete,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const [modalVisible, setModalVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasPermission, setHasPermission] = useState(false);
  const [disabledReason, setDisabledReason] = useState<string>('');

  // Check permissions on mount
  useEffect(() => {
    checkPermissions();
  }, [sourceType, records]);

  const checkPermissions = async () => {
    setIsLoading(true);
    
    try {
      // Check if records are empty
      if (!records || records.length === 0) {
        setHasPermission(false);
        setDisabledReason(t('transfer.validation.minRecords'));
        setIsLoading(false);
        return;
      }

      // Check user permissions
      const permissionResult = await checkPermissionAPI({
        source_type: sourceType,
        operation: 'transfer',
      });

      setHasPermission(permissionResult.allowed);
      
      if (!permissionResult.allowed) {
        setDisabledReason(t('transfer.messages.permissionDenied'));
      } else if (permissionResult.requires_approval) {
        setDisabledReason('');
      } else {
        setDisabledReason('');
      }
    } catch (error) {
      console.error('Permission check failed:', error);
      setHasPermission(false);
      setDisabledReason(t('common.messages.networkError'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleClick = () => {
    if (!isDisabled) {
      setModalVisible(true);
    }
  };

  const handleClose = () => {
    setModalVisible(false);
  };

  const handleSuccess = (result: any) => {
    setModalVisible(false);
    onTransferComplete?.(result);
  };

  // Determine if button should be disabled
  const isDisabled = disabled || !hasPermission || records.length === 0;

  return (
    <>
      <Tooltip title={isDisabled ? disabledReason : ''}>
        <Button
          type="primary"
          icon={<ExportOutlined />}
          onClick={handleClick}
          disabled={isDisabled}
          loading={isLoading}
        >
          {t('transfer.button')}
        </Button>
      </Tooltip>
      
      {/* TransferModal */}
      <TransferModal
        visible={modalVisible}
        onClose={handleClose}
        sourceType={sourceType}
        sourceId={sourceId}
        records={records}
        onSuccess={handleSuccess}
      />
    </>
  );
};

export default TransferButton;
