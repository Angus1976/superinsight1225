/**
 * Create Temp Data Modal Component
 * 
 * Modal for creating new temporary data entries.
 */

import { Modal, Form, Input, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useTempData } from '@/hooks/useDataLifecycle';

const { TextArea } = Input;

interface CreateTempDataModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const CreateTempDataModal: React.FC<CreateTempDataModalProps> = ({ visible, onClose, onSuccess }) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const { createTempData, loading } = useTempData();

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // Parse content as JSON
      let content: Record<string, unknown>;
      try {
        content = JSON.parse(values.content);
      } catch (err) {
        message.error(t('tempData.messages.createFailed') + ': ' + t('common.messages.validationError'));
        return;
      }

      // Parse metadata if provided
      let metadata: Record<string, unknown> | undefined;
      if (values.metadata) {
        try {
          metadata = JSON.parse(values.metadata);
        } catch (err) {
          message.error(t('tempData.messages.createFailed') + ': ' + t('common.messages.validationError'));
          return;
        }
      }

      await createTempData({
        name: values.name,
        content,
        metadata,
      });

      form.resetFields();
      onClose();
      onSuccess?.();
    } catch (err) {
      // Error already handled by hook
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onClose();
  };

  return (
    <Modal
      title={t('tempData.actions.create')}
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading}
      okText={t('common.actions.submit')}
      cancelText={t('common.actions.cancel')}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          name="name"
          label={t('tempData.columns.name')}
          rules={[{ required: true, message: t('common.placeholders.input', { field: t('tempData.columns.name') }) }]}
        >
          <Input placeholder={t('common.placeholders.input', { field: t('tempData.columns.name') })} />
        </Form.Item>

        <Form.Item
          name="content"
          label={t('tempData.columns.content')}
          rules={[{ required: true, message: t('common.placeholders.input', { field: t('tempData.columns.content') }) }]}
        >
          <TextArea
            rows={6}
            placeholder='{"key": "value"}'
          />
        </Form.Item>

        <Form.Item
          name="metadata"
          label={t('common.placeholders.remark')}
        >
          <TextArea
            rows={4}
            placeholder='{"key": "value"}'
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateTempDataModal;
