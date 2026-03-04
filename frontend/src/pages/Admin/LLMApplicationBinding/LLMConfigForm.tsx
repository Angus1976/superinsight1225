/**
 * LLM Configuration Form Component
 * Create and edit LLM configurations
 */

import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Divider,
} from 'antd';
import { useLLMConfigStore } from '@/stores/llmConfigStore';
import type { LLMConfig, LLMConfigCreate, LLMConfigUpdate } from '@/types/llmConfig';

interface LLMConfigFormProps {
  visible: boolean;
  config: LLMConfig | null;
  onClose: () => void;
}

const LLMConfigForm: React.FC<LLMConfigFormProps> = ({
  visible,
  config,
  onClose,
}) => {
  const { t } = useTranslation('llmConfig');
  const [form] = Form.useForm();
  const { createConfig, updateConfig, loading } = useLLMConfigStore();

  useEffect(() => {
    if (visible) {
      if (config) {
        form.setFieldsValue({
          name: config.name,
          provider: config.provider,
          base_url: config.base_url,
          model_name: config.model_name,
          parameters: JSON.stringify(config.parameters, null, 2),
          is_active: config.is_active,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({ is_active: true });
      }
    }
  }, [visible, config, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      let parameters = {};
      if (values.parameters) {
        try {
          parameters = JSON.parse(values.parameters);
        } catch (error) {
          message.error(t('configForm.fields.parameters.invalid'));
          return;
        }
      }

      const data = {
        ...values,
        parameters,
      };

      if (config) {
        await updateConfig(config.id, data as LLMConfigUpdate);
        message.success(t('configForm.messages.updateSuccess'));
      } else {
        await createConfig(data as LLMConfigCreate);
        message.success(t('configForm.messages.createSuccess'));
      }
      
      onClose();
    } catch (error) {
      const errorMsg = config
        ? t('configForm.messages.updateFailed')
        : t('configForm.messages.createFailed');
      message.error(errorMsg);
    }
  };

  return (
    <Modal
      title={
        config
          ? t('configForm.editTitle')
          : t('configForm.createTitle')
      }
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={loading}
      okText={t('configForm.buttons.submit')}
      cancelText={t('configForm.buttons.cancel')}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Divider orientation="left">{t('configForm.basicInfo')}</Divider>
        
        <Form.Item
          name="name"
          label={t('configForm.fields.name.label')}
          rules={[
            { required: true, message: t('configForm.fields.name.required') },
          ]}
        >
          <Input placeholder={t('configForm.fields.name.placeholder')} />
        </Form.Item>

        <Form.Item
          name="provider"
          label={t('configForm.fields.provider.label')}
          rules={[
            { required: true, message: t('configForm.fields.provider.required') },
          ]}
        >
          <Select placeholder={t('configForm.fields.provider.placeholder')}>
            <Select.Option value="openai">{t('providers.openai')}</Select.Option>
            <Select.Option value="azure">{t('providers.azure')}</Select.Option>
            <Select.Option value="anthropic">{t('providers.anthropic')}</Select.Option>
            <Select.Option value="ollama">{t('providers.ollama')}</Select.Option>
            <Select.Option value="custom">{t('providers.custom')}</Select.Option>
          </Select>
        </Form.Item>

        {!config && (
          <Form.Item
            name="api_key"
            label={t('configForm.fields.apiKey.label')}
            rules={[
              { required: true, message: t('configForm.fields.apiKey.required') },
            ]}
            extra={t('configForm.fields.apiKey.hint')}
          >
            <Input.Password placeholder={t('configForm.fields.apiKey.placeholder')} />
          </Form.Item>
        )}

        <Form.Item
          name="model_name"
          label={t('configForm.fields.modelName.label')}
          rules={[
            { required: true, message: t('configForm.fields.modelName.required') },
          ]}
          extra={t('configForm.fields.modelName.hint')}
        >
          <Input placeholder={t('configForm.fields.modelName.placeholder')} />
        </Form.Item>

        <Divider orientation="left">{t('configForm.advancedSettings')}</Divider>

        <Form.Item
          name="base_url"
          label={t('configForm.fields.baseUrl.label')}
          extra={t('configForm.fields.baseUrl.hint')}
          rules={[
            {
              type: 'url',
              message: t('configForm.fields.baseUrl.invalid'),
            },
          ]}
        >
          <Input placeholder={t('configForm.fields.baseUrl.placeholder')} />
        </Form.Item>

        <Form.Item
          name="parameters"
          label={t('configForm.fields.parameters.label')}
          extra={t('configForm.fields.parameters.hint')}
        >
          <Input.TextArea
            rows={4}
            placeholder={t('configForm.fields.parameters.placeholder')}
          />
        </Form.Item>

        <Form.Item
          name="is_active"
          label={t('configForm.fields.isActive.label')}
          valuePropName="checked"
        >
          <Switch
            checkedChildren={t('configForm.fields.isActive.active')}
            unCheckedChildren={t('configForm.fields.isActive.inactive')}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default LLMConfigForm;
