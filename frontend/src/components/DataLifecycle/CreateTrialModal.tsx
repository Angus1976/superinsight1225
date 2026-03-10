/**
 * Create Trial Modal Component
 * 
 * Modal for creating AI trial tasks with flexible stage selection.
 * Supports data selection from any of the 5 stages.
 */

import { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Table, InputNumber, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useTempData, useAITrial } from '@/hooks/useDataLifecycle';

const { TextArea } = Input;
const { Option } = Select;

interface CreateTrialModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const CreateTrialModal: React.FC<CreateTrialModalProps> = ({ visible, onClose, onSuccess }) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const { data: tempData, fetchTempData } = useTempData();
  const { createTrial, loading } = useAITrial();
  
  const [dataStage, setDataStage] = useState<string>('temp_table');
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
  ];

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (selectedRowKeys.length === 0) {
        message.warning(t('annotationTask.messages.noSamplesSelected'));
        return;
      }

      // Parse config if provided
      let config: Record<string, unknown> | undefined;
      if (values.config) {
        try {
          config = JSON.parse(values.config);
        } catch (err) {
          message.error(t('aiTrial.messages.createFailed') + ': ' + t('common.messages.validationError'));
          return;
        }
      }

      // Create AI trial for each selected data item
      for (const dataId of selectedRowKeys) {
        await createTrial({
          name: values.name,
          model: values.model,
          target_data_id: dataId as string,
          config,
        });
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
      title={t('aiTrial.actions.create')}
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
          name="name"
          label={t('aiTrial.columns.name')}
          rules={[{ required: true, message: t('common.placeholders.input', { field: t('aiTrial.columns.name') }) }]}
        >
          <Input placeholder={t('common.placeholders.input', { field: t('aiTrial.columns.name') })} />
        </Form.Item>

        <Form.Item
          name="model"
          label={t('aiTrial.columns.aiModel')}
          rules={[{ required: true, message: t('aiTrial.messages.selectModel') }]}
        >
          <Select placeholder={t('aiTrial.messages.selectModel')}>
            <Option value="gpt-4">GPT-4</Option>
            <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
            <Option value="claude-3">Claude 3</Option>
            <Option value="llama-2">Llama 2</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="dataStage"
          label={t('aiTrial.columns.dataStage')}
          initialValue="temp_table"
        >
          <Select onChange={setDataStage}>
            <Option value="temp_table">{t('aiTrial.dataStages.temp_table')}</Option>
            <Option value="sample_library">{t('aiTrial.dataStages.sample_library')}</Option>
            <Option value="data_source">{t('aiTrial.dataStages.data_source')}</Option>
            <Option value="annotated">{t('aiTrial.dataStages.annotated')}</Option>
            <Option value="enhanced">{t('aiTrial.dataStages.enhanced')}</Option>
          </Select>
        </Form.Item>

        <Form.Item label={t('sampleLibrary.actions.search')}>
          <Table
            rowSelection={rowSelection}
            columns={columns}
            dataSource={tempData}
            rowKey="id"
            pagination={{ pageSize: 5 }}
            scroll={{ y: 200 }}
          />
        </Form.Item>

        <Form.Item
          name="trialCount"
          label={t('aiTrial.columns.trialCount')}
          initialValue={10}
        >
          <InputNumber min={1} max={100} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item
          name="config"
          label={t('common.placeholders.remark')}
        >
          <TextArea
            rows={3}
            placeholder='{"key": "value"}'
          />
        </Form.Item>
      </Form>

      <div style={{ marginTop: 8, color: '#8c8c8c' }}>
        {t('annotationTask.messages.samplesSelected', { count: selectedRowKeys.length })}
      </div>
    </Modal>
  );
};

export default CreateTrialModal;
