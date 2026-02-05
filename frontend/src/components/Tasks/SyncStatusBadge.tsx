/**
 * SyncStatusBadge Component
 * Displays Label Studio sync status with tooltip and sync button.
 * 
 * Extracted from TasksPage for reusability and better separation of concerns.
 */
import React, { memo, useMemo, useCallback } from 'react';
import { Space, Tag, Tooltip, Button } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Task, LabelStudioSyncStatus } from '@/types/task';

export interface SyncStatusBadgeProps {
  task: Task;
  onSyncTask?: (task: Task) => void;
}

interface SyncStatusConfig {
  icon: React.ReactNode;
  color: string;
  text: string;
  tooltip: string;
  showLastSync: boolean;
  showError: boolean;
}

/**
 * Format relative time (e.g., "5 minutes ago")
 */
const formatRelativeTime = (dateString: string, t: (key: string, options?: Record<string, unknown>) => string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) {
    return t('syncTimeJustNow');
  } else if (diffMin < 60) {
    return t('syncTimeMinutesAgo', { count: diffMin });
  } else if (diffHour < 24) {
    return t('syncTimeHoursAgo', { count: diffHour });
  } else if (diffDay < 7) {
    return t('syncTimeDaysAgo', { count: diffDay });
  } else {
    return date.toLocaleDateString();
  }
};

const SyncStatusBadgeComponent: React.FC<SyncStatusBadgeProps> = ({ task, onSyncTask }) => {
  const { t } = useTranslation('tasks');
  
  const hasProjectId = !!task.label_studio_project_id;
  const syncStatus = task.label_studio_sync_status;
  const lastSync = task.label_studio_last_sync;
  const syncError = task.label_studio_sync_error;

  // Get sync status configuration
  const config = useMemo((): SyncStatusConfig => {
    if (!hasProjectId) {
      return {
        icon: <DisconnectOutlined />,
        color: 'default',
        text: t('syncStatusNotLinked'),
        tooltip: t('syncStatusNotLinkedTip'),
        showLastSync: false,
        showError: false,
      };
    }
    
    switch (syncStatus) {
      case 'synced':
        return {
          icon: <CheckCircleOutlined />,
          color: 'success',
          text: t('syncStatusSynced'),
          tooltip: t('syncStatusSyncedTip'),
          showLastSync: true,
          showError: false,
        };
      case 'pending':
        return {
          icon: <ClockCircleOutlined spin />,
          color: 'warning',
          text: t('syncStatusPending'),
          tooltip: t('syncStatusPendingTip'),
          showLastSync: true,
          showError: false,
        };
      case 'failed':
        return {
          icon: <ExclamationCircleOutlined />,
          color: 'error',
          text: t('syncStatusFailed'),
          tooltip: syncError || t('syncStatusFailedTip'),
          showLastSync: true,
          showError: true,
        };
      default:
        return {
          icon: <ClockCircleOutlined />,
          color: 'default',
          text: t('syncStatusNotSynced'),
          tooltip: t('syncStatusNotSyncedTip'),
          showLastSync: false,
          showError: false,
        };
    }
  }, [hasProjectId, syncStatus, syncError, t]);

  // Format last sync time
  const formattedLastSync = useMemo(() => {
    if (!lastSync) return null;
    return formatRelativeTime(lastSync, t);
  }, [lastSync, t]);

  // Handle sync button click
  const handleSyncClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (onSyncTask) {
      onSyncTask(task);
    }
  }, [onSyncTask, task]);

  // Build tooltip content
  const tooltipContent = useMemo(() => (
    <div style={{ maxWidth: 250 }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
        {config.text}
      </div>
      {config.showLastSync && formattedLastSync && (
        <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
          {t('syncStatusLastSync', { time: formattedLastSync })}
        </div>
      )}
      {config.showError && syncError && (
        <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>
          {t('syncErrorInfo')}: {syncError}
        </div>
      )}
      {!config.showLastSync && (
        <div style={{ fontSize: 12, color: '#999' }}>
          {config.tooltip}
        </div>
      )}
    </div>
  ), [config, formattedLastSync, syncError, t]);

  return (
    <Space direction="vertical" size={0} style={{ width: '100%' }}>
      <Space size={4}>
        <Tooltip title={tooltipContent} placement="topLeft">
          <Tag 
            color={config.color} 
            icon={config.icon}
            style={{ cursor: 'pointer', marginRight: 0 }}
          >
            {config.text}
          </Tag>
        </Tooltip>
        {hasProjectId && onSyncTask && (
          <Tooltip title={t('syncSingleTask')}>
            <Button
              type="text"
              size="small"
              icon={<SyncOutlined />}
              onClick={handleSyncClick}
              style={{ padding: '0 4px' }}
            />
          </Tooltip>
        )}
      </Space>
      {/* Show last sync time in relative format */}
      {config.showLastSync && formattedLastSync && (
        <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
          {formattedLastSync}
        </div>
      )}
      {/* Show error indicator for failed sync */}
      {config.showError && syncError && (
        <Tooltip title={syncError}>
          <div style={{ 
            fontSize: 11, 
            color: '#ff4d4f', 
            marginTop: 2,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            maxWidth: 150,
            cursor: 'help'
          }}>
            {t('syncErrorShort')}
          </div>
        </Tooltip>
      )}
    </Space>
  );
};

export const SyncStatusBadge = memo(SyncStatusBadgeComponent);
export default SyncStatusBadge;
