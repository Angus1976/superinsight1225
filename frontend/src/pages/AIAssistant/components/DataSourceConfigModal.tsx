import React, { useEffect, useState } from 'react';
import { Modal, List, Switch, Select, Tag, Space, Button, Spin, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { getDataSourceConfig, updateDataSourceConfig } from '@/services/aiAssistantApi';
import type { AIDataSource } from '@/types/aiAssistant';

interface DataSourceConfigModalProps {
  open: boolean;
  onClose: () => void;
}

const DataSourceConfigModal: React.FC<DataSourceConfigModalProps> = ({ open, onClose }) => {
  const { t } = useTranslation('aiAssistant');
  const [sources, setSources] = useState<AIDataSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    getDataSourceConfig()
      .then(setSources)
      .catch(() => message.error(t('dataSourceLoadFailed')))
      .finally(() => setLoading(false));
  }, [open, t]);

  const handleToggle = (id: string, checked: boolean) => {
    setSources((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: checked } : s)),
    );
  };

  const handleAccessModeChange = (id: string, mode: string) => {
    setSources((prev) =>
      prev.map((s) => (s.id === id ? { ...s, access_mode: mode } : s)),
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateDataSourceConfig(
        sources.map(({ id, enabled, access_mode }) => ({ id, enabled, access_mode })),
      );
      message.success(t('configSaved'));
      onClose();
    } catch {
      message.error(t('configSaveFailed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={t('dataSourceModal.title')}
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          {t('dataSourceModal.cancel')}
        </Button>,
        <Button key="save" type="primary" loading={saving} onClick={handleSave}>
          {t('dataSourceModal.save')}
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
        <List
          dataSource={sources}
          renderItem={(src) => (
            <List.Item>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Space>
                  <span>{t(`source.${src.id}`)}</span>
                  <Tag>{t(`category.${src.category}`)}</Tag>
                </Space>
                <Space>
                  <Switch
                    checked={src.enabled}
                    onChange={(checked) => handleToggle(src.id, checked)}
                    checkedChildren={t('dataSourceModal.enableSwitch')}
                  />
                  <Select
                    value={src.access_mode}
                    onChange={(val) => handleAccessModeChange(src.id, val)}
                    style={{ width: 100 }}
                    options={[
                      { value: 'read', label: t('accessRead') },
                      { value: 'read_write', label: t('accessReadWrite') },
                    ]}
                  />
                </Space>
              </Space>
            </List.Item>
          )}
        />
      </Spin>
    </Modal>
  );
};

export default DataSourceConfigModal;