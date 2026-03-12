import React, { useEffect, useState } from 'react';
import { Modal, Checkbox, Radio, Tag, Space, Button, Spin, Empty, Divider, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { getAvailableDataSources } from '@/services/aiAssistantApi';
import type { AIDataSource, OutputMode } from '@/types/aiAssistant';

const { Text } = Typography;

interface OutputModeModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (sourceIds: string[], mode: OutputMode) => void;
  initialSourceIds?: string[];
  initialMode?: OutputMode;
}

const OutputModeModal: React.FC<OutputModeModalProps> = ({
  open,
  onClose,
  onConfirm,
  initialSourceIds = [],
  initialMode = 'merge',
}) => {
  const { t } = useTranslation('aiAssistant');
  const [sources, setSources] = useState<AIDataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSourceIds);
  const [mode, setMode] = useState<OutputMode>(initialMode);

  useEffect(() => {
    if (!open) return;
    setSelectedIds(initialSourceIds);
    setMode(initialMode);
    setLoading(true);
    getAvailableDataSources()
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setLoading(false));
  }, [open, initialSourceIds, initialMode]);

  const handleConfirm = () => {
    onConfirm(selectedIds, mode);
    onClose();
  };

  return (
    <Modal
      title={t('outputModeModal.title')}
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('outputModeModal.cancel')}
        </Button>,
        <Button key="confirm" type="primary" onClick={handleConfirm}>
          {t('outputModeModal.confirm')}
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
        {sources.length === 0 && !loading ? (
          <Empty description={t('outputModeModal.noAvailableSources')} />
        ) : (
          <>
            <Text strong>{t('outputModeModal.selectSources')}</Text>
            <Checkbox.Group
              value={selectedIds}
              onChange={(vals) => setSelectedIds(vals as string[])}
              style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}
            >
              {sources.map((src) => (
                <Checkbox key={src.id} value={src.id}>
                  <Space>
                    <span>{t(`source.${src.id}`)}</span>
                    <Tag>{t(`category.${src.category}`)}</Tag>
                  </Space>
                </Checkbox>
              ))}
            </Checkbox.Group>

            <Divider />

            <Radio.Group
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
            >
              <Radio value="merge">
                <Space direction="vertical" size={0}>
                  <span>{t('outputModeModal.mergeMode')}</span>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {t('outputModeModal.mergeDesc')}
                  </Text>
                </Space>
              </Radio>
              <Radio value="compare">
                <Space direction="vertical" size={0}>
                  <span>{t('outputModeModal.compareMode')}</span>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {t('outputModeModal.compareDesc')}
                  </Text>
                </Space>
              </Radio>
            </Radio.Group>
          </>
        )}
      </Spin>
    </Modal>
  );
};

export default OutputModeModal;
