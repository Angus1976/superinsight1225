/**
 * LLM Configuration List Component
 * Displays LLM configurations in card layout with actions
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Row,
  Col,
  Card,
  Button,
  Tag,
  Space,
  App,
  message,
  Input,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ApiOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useLLMConfigStore } from '@/stores/llmConfigStore';
import type { LLMConfig } from '@/types/llmConfig';
import LLMConfigForm from './LLMConfigForm';
import TestConnectionButton from './TestConnectionButton';

const LLMConfigList: React.FC = () => {
  const { t } = useTranslation('llmConfig');
  const { modal } = App.useApp();
  const { configs, loading, deleteConfig } = useLLMConfigStore();
  const [searchText, setSearchText] = useState('');
  const [formVisible, setFormVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null);

  const handleAdd = () => {
    setEditingConfig(null);
    setFormVisible(true);
  };

  const handleEdit = (config: LLMConfig) => {
    setEditingConfig(config);
    setFormVisible(true);
  };

  const handleDelete = (config: LLMConfig) => {
    modal.confirm({
      title: t('configList.deleteConfirm.title'),
      content: t('configList.deleteConfirm.content', { name: config.name }),
      onOk: async () => {
        try {
          await deleteConfig(config.id);
          message.success(t('configForm.messages.deleteSuccess'));
        } catch (error: any) {
          if (error.response?.status === 409) {
            message.error(t('configList.deleteConfirm.hasBindings'));
          } else {
            message.error(t('errors.deleteConfigFailed'));
          }
        }
      },
    });
  };

  const handleFormClose = () => {
    setFormVisible(false);
    setEditingConfig(null);
  };

  const filteredConfigs = configs.filter(
    (config) =>
      config.name.toLowerCase().includes(searchText.toLowerCase()) ||
      config.model_name.toLowerCase().includes(searchText.toLowerCase())
  );

  const getProviderIcon = (provider: string) => {
    return <ApiOutlined />;
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Input
          placeholder={t('configList.searchPlaceholder')}
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 300 }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          {t('configList.addButton')}
        </Button>
      </div>

      {filteredConfigs.length === 0 ? (
        <Empty description={t('configList.emptyState')} />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredConfigs.map((config) => (
            <Col key={config.id} xs={24} sm={12} lg={8}>
              <Card
                title={
                  <Space>
                    {getProviderIcon(config.provider)}
                    <span>{config.name}</span>
                  </Space>
                }
                extra={
                  <Tag color={config.is_active ? 'green' : 'default'}>
                    {config.is_active
                      ? t('configList.status.active')
                      : t('configList.status.inactive')}
                  </Tag>
                }
                actions={[
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    onClick={() => handleEdit(config)}
                  >
                    {t('configList.actions.edit')}
                  </Button>,
                  <TestConnectionButton configId={config.id} />,
                  <Button
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDelete(config)}
                  >
                    {t('configList.actions.delete')}
                  </Button>,
                ]}
              >
                <div>
                  <p>
                    <strong>{t('configList.columns.provider')}:</strong>{' '}
                    {t(`providers.${config.provider}`)}
                  </p>
                  <p>
                    <strong>{t('configList.columns.model')}:</strong>{' '}
                    {config.model_name}
                  </p>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <LLMConfigForm
        visible={formVisible}
        config={editingConfig}
        onClose={handleFormClose}
      />
    </div>
  );
};

export default LLMConfigList;
