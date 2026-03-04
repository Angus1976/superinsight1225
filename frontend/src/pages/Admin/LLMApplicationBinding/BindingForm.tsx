/**
 * Binding Form Component
 * Create and edit LLM-Application bindings
 */

import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
  message,
} from 'antd';
import { useLLMConfigStore } from '@/stores/llmConfigStore';
import type { LLMBinding, LLMBindingCreate, LLMBindingUpdate } from '@/types/llmConfig';

interface BindingFormProps {
  visible: boolean;
  binding: LLMBinding | null;
  applicationId: string | null;
  onClose: () => void;
}

const BindingForm: React.FC<BindingFormProps> = ({
  visible,
  binding,
  applicationId,
  onClose,
}) => {
  const { t } = useTranslation('llmConfig');
  const [form] = Form.useForm();
  const {
    applications,
    configs,
    bindings,
    createBinding,
    updateBinding,
    loading,
  } = useLLMConfigStore();

  useEffect(() => {
    if (visible) {
      if (binding) {
        form.setFieldsValue({
          application_id: binding.application.id,
          llm_config_id: binding.llm_config.id,
          priority: binding.priority,
          max_retries: binding.max_retries,
          timeout_seconds: binding.timeout_seconds,
          is_active: binding.is_active,
        });
      } else {
        form.resetFields();
        if (applicationId) {
          form.setFieldsValue({ application_id: applicationId });
        }
        form.setFieldsValue({
          priority: 1,
          max_retries: 3,
          timeout_seconds: 30,
          is_active: true,
        });
      }
    }
  }, [visible, binding, applicationId, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      if (binding) {
        const updateData: LLMBindingUpdate = {
          priority: values.priority,
          max_retries: values.max_retries,
          timeout_seconds: values.timeout_seconds,
          is_active: values.is_active,
        };
        await updateBinding(binding.id, updateData);
        message.success(t('bindingForm.messages.updateSuccess'));
      } else {
        const createData: LLMBindingCreate = {
          application_id: values.application_id,
          llm_config_id: values.llm_config_id,
          priority: values.priority,
          max_retries: values.max_retries,
          timeout_seconds: values.timeout_seconds,
        };
        await createBinding(createData);
        message.success(t('bindingForm.messages.createSuccess'));
      }

      onClose();
    } catch (error: any) {
      if (error.response?.status === 409) {
        message.error(t('bindingForm.fields.priority.duplicate'));
      } else {
        const errorMsg = binding
          ? t('bindingForm.messages.updateFailed')
          : t('bindingForm.messages.createFailed');
        message.error(errorMsg);
      }
    }
  };

  const getUsedPriorities = (appId: string) => {
    return bindings
      .filter(
        (b) =>
          b.application.id === appId &&
          (!binding || b.id !== binding.id)
      )
      .map((b) => b.priority);
  };

  const validatePriority = (_: any, value: number) => {
    const appId = form.getFieldValue('application_id');
    if (!appId) {
      return Promise.resolve();
    }

    const usedPriorities = getUsedPriorities(appId);
    if (usedPriorities.includes(value)) {
      return Promise.reject(new Error(t('bindingForm.fields.priority.duplicate')));
    }

    return Promise.resolve();
  };

  return (
    <Modal
      title={
        binding
          ? t('bindingForm.editTitle')
          : t('bindingForm.createTitle')
      }
      open={visible}
      onOk={handleSubmit}
      onCancel={onClose}
      confirmLoading={loading}
      okText={t('bindingForm.buttons.submit')}
      cancelText={t('bindingForm.buttons.cancel')}
      width={600}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="application_id"
          label={t('bindingForm.fields.application.label')}
          rules={[
            { required: true, message: t('bindingForm.fields.application.required') },
          ]}
        >
          <Select
            placeholder={t('bindingForm.fields.application.placeholder')}
            disabled={!!binding}
          >
            {applications.map((app) => (
              <Select.Option key={app.id} value={app.id}>
                {t(`applications.${app.code}.name`)} ({app.code})
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="llm_config_id"
          label={t('bindingForm.fields.llmConfig.label')}
          rules={[
            { required: true, message: t('bindingForm.fields.llmConfig.required') },
          ]}
        >
          <Select
            placeholder={t('bindingForm.fields.llmConfig.placeholder')}
            disabled={!!binding}
          >
            {configs
              .filter((c) => c.is_active)
              .map((config) => (
                <Select.Option key={config.id} value={config.id}>
                  {config.name} ({t(`providers.${config.provider}`)} - {config.model_name})
                </Select.Option>
              ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="priority"
          label={t('bindingForm.fields.priority.label')}
          rules={[
            { required: true, message: t('bindingForm.fields.priority.required') },
            { type: 'number', min: 1, max: 99, message: t('bindingForm.fields.priority.range') },
            { validator: validatePriority },
          ]}
          extra={t('bindingForm.fields.priority.hint')}
        >
          <InputNumber
            min={1}
            max={99}
            style={{ width: '100%' }}
            placeholder={t('bindingForm.fields.priority.placeholder')}
          />
        </Form.Item>

        <Form.Item
          name="max_retries"
          label={t('bindingForm.fields.maxRetries.label')}
          rules={[
            { type: 'number', min: 0, max: 10, message: t('bindingForm.fields.maxRetries.range') },
          ]}
          extra={t('bindingForm.fields.maxRetries.hint')}
        >
          <InputNumber
            min={0}
            max={10}
            style={{ width: '100%' }}
            placeholder={t('bindingForm.fields.maxRetries.placeholder')}
          />
        </Form.Item>

        <Form.Item
          name="timeout_seconds"
          label={t('bindingForm.fields.timeoutSeconds.label')}
          rules={[
            { type: 'number', min: 1, message: t('bindingForm.fields.timeoutSeconds.positive') },
          ]}
          extra={t('bindingForm.fields.timeoutSeconds.hint')}
        >
          <InputNumber
            min={1}
            style={{ width: '100%' }}
            placeholder={t('bindingForm.fields.timeoutSeconds.placeholder')}
          />
        </Form.Item>

        <Form.Item
          name="is_active"
          label={t('bindingForm.fields.isActive.label')}
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default BindingForm;
