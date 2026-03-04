/**
 * Application Bindings Component
 * Displays and manages LLM bindings for each application
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Button,
  List,
  Tag,
  Space,
  Modal,
  message,
  Empty,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { useLLMConfigStore } from '@/stores/llmConfigStore';
import type { LLMBinding } from '@/types/llmConfig';
import BindingForm from './BindingForm';

interface BindingItemProps {
  binding: LLMBinding;
  onEdit: (binding: LLMBinding) => void;
  onDelete: (binding: LLMBinding) => void;
}

const BindingItem: React.FC<BindingItemProps> = ({
  binding,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation('llmConfig');

  const getPriorityLabel = (priority: number) => {
    if (priority === 1) return t('bindings.primaryLLM');
    return `${t('bindings.backupLLM')} ${priority - 1}`;
  };

  return (
    <List.Item
      actions={[
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => onEdit(binding)}
        >
          {t('bindings.actions.edit')}
        </Button>,
        <Button
          type="link"
          danger
          icon={<DeleteOutlined />}
          onClick={() => onDelete(binding)}
        >
          {t('bindings.actions.delete')}
        </Button>,
      ]}
    >
      <List.Item.Meta
        avatar={
          <Badge
            count={binding.priority}
            style={{ backgroundColor: binding.priority === 1 ? '#52c41a' : '#1890ff' }}
          />
        }
        title={
          <Space>
            <span>{binding.llm_config.name}</span>
            <Tag>{t(`providers.${binding.llm_config.provider}`)}</Tag>
          </Space>
        }
        description={
          <Space>
            <span>{getPriorityLabel(binding.priority)}</span>
            <span>•</span>
            <span>
              {t('bindingForm.fields.maxRetries.label')}: {binding.max_retries}
            </span>
            <span>•</span>
            <span>
              {t('bindingForm.fields.timeoutSeconds.label')}: {binding.timeout_seconds}s
            </span>
          </Space>
        }
      />
    </List.Item>
  );
};

const ApplicationBindings: React.FC = () => {
  const { t } = useTranslation('llmConfig');
  const {
    applications,
    bindings,
    deleteBinding,
    reorderBindings,
  } = useLLMConfigStore();
  const [formVisible, setFormVisible] = useState(false);
  const [editingBinding, setEditingBinding] = useState<LLMBinding | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);

  const handleAdd = (appId: string) => {
    setSelectedAppId(appId);
    setEditingBinding(null);
    setFormVisible(true);
  };

  const handleEdit = (binding: LLMBinding) => {
    setSelectedAppId(binding.application.id);
    setEditingBinding(binding);
    setFormVisible(true);
  };

  const handleDelete = (binding: LLMBinding) => {
    Modal.confirm({
      title: t('bindings.deleteConfirm.title'),
      content: t('bindings.deleteConfirm.content'),
      onOk: async () => {
        try {
          await deleteBinding(binding.id);
          message.success(t('bindingForm.messages.deleteSuccess'));
        } catch (error) {
          message.error(t('errors.deleteBindingFailed'));
        }
      },
    });
  };

  const handleFormClose = () => {
    setFormVisible(false);
    setEditingBinding(null);
    setSelectedAppId(null);
  };

  const getAppBindings = (appId: string) => {
    return bindings
      .filter((b) => b.application.id === appId)
      .sort((a, b) => a.priority - b.priority);
  };

  return (
    <div>
      <p style={{ marginBottom: 16 }}>{t('bindings.description')}</p>

      {applications.length === 0 ? (
        <Empty description={t('errors.loadApplicationsFailed')} />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {applications.map((app) => {
            const appBindings = getAppBindings(app.id);
            
            return (
              <Card
                key={app.id}
                title={
                  <Space>
                    <span>{t(`applications.${app.code}.name`)}</span>
                    <Tag>{app.code}</Tag>
                  </Space>
                }
                extra={
                  <Button
                    type="primary"
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={() => handleAdd(app.id)}
                  >
                    {t('bindings.addButton')}
                  </Button>
                }
              >
                <p style={{ color: '#666', marginBottom: 16 }}>
                  {t(`applications.${app.code}.description`)}
                </p>

                {appBindings.length === 0 ? (
                  <Empty
                    description={t('bindings.noBoundLLMs')}
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ) : (
                  <List
                    dataSource={appBindings}
                    renderItem={(binding) => (
                      <BindingItem
                        key={binding.id}
                        binding={binding}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                      />
                    )}
                  />
                )}
              </Card>
            );
          })}
        </Space>
      )}

      <BindingForm
        visible={formVisible}
        binding={editingBinding}
        applicationId={selectedAppId}
        onClose={handleFormClose}
      />
    </div>
  );
};

export default ApplicationBindings;
