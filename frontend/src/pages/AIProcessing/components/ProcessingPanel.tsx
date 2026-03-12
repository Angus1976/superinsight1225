/**
 * ProcessingPanel — 统一处理面板
 *
 * Main container that integrates StrategySelector + StorageIndicator.
 * Supports auto/manual mode toggle, execution progress, and error retry.
 */

import React, { useCallback, useState } from 'react';
import {
  Card,
  Radio,
  Button,
  Progress,
  Alert,
  Space,
  Typography,
  Result,
} from 'antd';
import {
  PlayCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useToolkitStore } from '@/stores/toolkitStore';
import type { ProcessingMode } from '@/types/toolkit';
import TransferToLifecycleModal from '@/components/DataLifecycle/TransferToLifecycleModal';
import type { TransferDataItem } from '@/components/DataLifecycle/TransferToLifecycleModal';
import StrategySelector from './StrategySelector';
import StorageIndicator from './StorageIndicator';

const { Text } = Typography;

interface ProcessingPanelProps {
  origin: 'vectorization' | 'semantic';
}

/** Render execution progress bar with stage name */
const ProgressSection: React.FC = () => {
  const { t } = useTranslation(['common']);
  const { executionStatus } = useToolkitStore();

  if (!executionStatus || executionStatus.status !== 'running') return null;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={4}>
      {executionStatus.currentStage && (
        <Text type="secondary" style={{ fontSize: 13 }}>
          {t('common:aiProcessing.processing.stage', {
            stage: executionStatus.currentStage,
          })}
        </Text>
      )}
      <Progress
        percent={executionStatus.progress}
        status="active"
        size="small"
      />
    </Space>
  );
};

/** Render success result with transfer-to-lifecycle button */
const SuccessSection: React.FC<{ origin: ProcessingPanelProps['origin'] }> = ({ origin }) => {
  const { t } = useTranslation(['common']);
  const { executionStatus, fileId } = useToolkitStore();
  const [transferOpen, setTransferOpen] = useState(false);

  if (!executionStatus || executionStatus.status !== 'completed') return null;

  const transferData: TransferDataItem[] = fileId
    ? [{
        id: fileId,
        name: executionStatus.storageLocation || fileId,
        content: { storageLocation: executionStatus.storageLocation },
        metadata: { origin, executionId: executionStatus.executionId },
      }]
    : [];

  return (
    <>
      <Result
        status="success"
        icon={<CheckCircleOutlined />}
        title={t('common:aiProcessing.processing.successTitle')}
        subTitle={
          executionStatus.storageLocation
            ? t('common:aiProcessing.processing.successDesc', {
                location: executionStatus.storageLocation,
              })
            : undefined
        }
        extra={
          <Button
            type="primary"
            icon={<CloudUploadOutlined />}
            onClick={() => setTransferOpen(true)}
          >
            {t('common:aiProcessing.processing.transferToLifecycle')}
          </Button>
        }
        style={{ padding: '16px 0' }}
      />
      <TransferToLifecycleModal
        visible={transferOpen}
        onClose={() => setTransferOpen(false)}
        onSuccess={() => setTransferOpen(false)}
        sourceType={origin === 'vectorization' ? 'vectorization' : 'semantic'}
        selectedData={transferData}
      />
    </>
  );
};

/** Render failure alert with retry button */
const FailureSection: React.FC<{ onRetry: () => void }> = ({ onRetry }) => {
  const { t } = useTranslation(['common']);
  const { executionStatus } = useToolkitStore();

  if (!executionStatus || executionStatus.status !== 'failed') return null;

  return (
    <Alert
      type="error"
      showIcon
      message={t('common:aiProcessing.processing.failedTitle')}
      description={executionStatus.error}
      action={
        <Button
          size="small"
          icon={<ReloadOutlined />}
          onClick={onRetry}
        >
          {t('common:aiProcessing.processing.retry')}
        </Button>
      }
    />
  );
};

const ProcessingPanel: React.FC<ProcessingPanelProps> = ({ origin }) => {
  const { t } = useTranslation(['common']);
  const {
    candidates,
    mode,
    fileId,
    isRouting,
    isExecuting,
    setMode,
    routeFile,
    executePipeline,
  } = useToolkitStore();

  const handleModeChange = useCallback(
    (newMode: ProcessingMode) => {
      setMode(newMode);
    },
    [setMode],
  );

  const handleConfirm = useCallback(async () => {
    if (!fileId) return;
    if (candidates.length === 0) {
      await routeFile(origin);
    }
    await executePipeline();
  }, [fileId, candidates, routeFile, origin, executePipeline]);

  const handleRetry = useCallback(() => {
    executePipeline();
  }, [executePipeline]);

  if (!fileId) return null;

  return (
    <Card
      size="small"
      title={t('common:aiProcessing.processing.title')}
      loading={isRouting}
      extra={<StorageIndicator />}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Space>
          <Text>{t('common:aiProcessing.processing.modeLabel')}</Text>
          <Radio.Group
            value={mode}
            onChange={(e) => handleModeChange(e.target.value)}
            size="small"
            optionType="button"
            buttonStyle="solid"
          >
            <Radio.Button value="auto">
              {t('common:aiProcessing.processing.modeAuto')}
            </Radio.Button>
            <Radio.Button value="manual">
              {t('common:aiProcessing.processing.modeManual')}
            </Radio.Button>
          </Radio.Group>
        </Space>

        {candidates.length > 0 && <StrategySelector />}

        <ProgressSection />
        <SuccessSection origin={origin} />
        <FailureSection onRetry={handleRetry} />

        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          loading={isExecuting}
          disabled={!fileId || candidates.length === 0}
          onClick={handleConfirm}
        >
          {t('common:aiProcessing.processing.confirm')}
        </Button>
      </Space>
    </Card>
  );
};

export default ProcessingPanel;
