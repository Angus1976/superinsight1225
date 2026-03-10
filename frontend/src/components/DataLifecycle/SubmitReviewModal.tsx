/**
 * Submit Review Modal Component
 * 
 * Modal for submitting data for review with target stage selection.
 * Supports flexible data flow - users can select any target stage.
 */

import { useState, useEffect } from 'react';
import { Modal, Form, Select, Table, Input, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useTempData, useReview } from '@/hooks/useDataLifecycle';

const { TextArea } = Input;
const { Option } = Select;

interface SubmitReviewModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const SubmitReviewModal: React.FC<SubmitReviewModalProps> = ({ visible, onClose, onSuccess }) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const { data: tempData, fetchTempData } = useTempData();
  const { submitForReview, loading } = useReview();
  
  const [sourceStage, setSourceStage] = useState<string>('temp_data');
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  useEffect(() => {
    if (visible) {
      fetchTempData();
    }
  }, [visible, fetchTempData]);

  const columns = [
    {
      title: t('tempData.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 100,
    },
    {
      title: t('tempData.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('tempData.columns.state'),
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => t(`tempData.states.${state}`),
    },
  ];

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (selectedRowKeys.length === 0) {
        message.warning(t('sampleLibrary.messages.noSamplesSelected'));
        return;
      }

      // Submit each selected item for review
      for (const dataId of selectedRowKeys) {
        await submitForReview(values.targetStage, dataId as string);
      }

      form.resetFields();
      setSelectedRowKeys([]);
      onClose();
      onSuccess?.();
    } catch (err) {
      // Error already handled by hook
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setSelectedRowKeys([]);
    onClose();
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  return (
    <Modal
      title={t('review.actions.submit')}
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading}
      okText={t('common.actions.submit')}
      cancelText={t('common.actions.cancel')}
      width={800}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          name="sourceStage"
          label={t('aiTrial.columns.dataStage')}
          initialValue="temp_data"
        >
          <Select onChange={setSourceStage}>
            <Option value="temp_data">{t('tabs.tempData')}</Option>
            <Option value="sample_library">{t('tabs.sampleLibrary')}</Option>
            <Option value="annotated">{t('states.annotated')}</Option>
            <Option value="enhanced">{t('states.enhanced')}</Option>
          </Select>
        </Form.Item>

        <Form.Item label={t('sampleLibrary.actions.search')}>
          <Table
            rowSelection={rowSelection}
            columns={columns}
            dataSource={tempData}
            rowKey="id"
            pagination={{ pageSize: 5 }}
            scroll={{ y: 300 }}
          />
        </Form.Item>

        <Form.Item
          name="targetStage"
          label={t('stateTransition.transitionTo')}
          rules={[{ required: true, message: t('common.placeholders.select') }]}
        >
          <Select placeholder={t('common.placeholders.select')}>
            <Option value="sample_library">{t('tabs.sampleLibrary')}</Option>
            <Option value="annotation_task">{t('tabs.annotation')}</Option>
            <Option value="enhancement">{t('tabs.enhancement')}</Option>
            <Option value="ai_trial">{t('tabs.aiTrial')}</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="comments"
          label={t('common.placeholders.remark')}
        >
          <TextArea
            rows={3}
            placeholder={t('common.placeholders.remark')}
          />
        </Form.Item>
      </Form>

      <div style={{ marginTop: 8, color: '#8c8c8c' }}>
        {t('sampleLibrary.statistics.selected', { count: selectedRowKeys.length })}
      </div>
    </Modal>
  );
};

export default SubmitReviewModal;
