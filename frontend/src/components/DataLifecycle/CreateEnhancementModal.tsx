/**
 * Create Enhancement Modal Component
 * 
 * Modal for creating data enhancement tasks.
 * Supports flexible data flow - users can select data from any stage.
 */

import { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Table, InputNumber, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useTempData, useEnhancement } from '@/hooks/useDataLifecycle';

const { TextArea } = Input;
const { Option } = Select;

interface CreateEnhancementModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const CreateEnhancementModal: React.FC<CreateEnhancementModalProps> = ({ visible, onClose, onSuccess }) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const { data: tempData, fetchTempData } = useTempData();
  const { createJob, loading } = useEnhancement();
  
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
          message.error(t('enhancement.messages.createFailed') + ': ' + t('common.messages.validationError'));
          return;
        }
      }

      // Create enhancement job for each selected data item
      for (const dataId of selectedRowKeys) {
        await createJob({
          data_id: dataId as string,
          enhancement_type: values.type,
          created_by: 'current_user',
          parameters: config,
          target_quality: values.targetQuality,
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
      title={t('enhancement.actions.create')}
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
          label={t('enhancement.columns.name')}
          rules={[{ required: true, message: t('common.placeholders.input', { field: t('enhancement.columns.name') }) }]}
        >
          <Input placeholder={t('common.placeholders.input', { field: t('enhancement.columns.name') })} />
        </Form.Item>

        <Form.Item
          name="type"
          label={t('enhancement.columns.type')}
          rules={[{ required: true, message: t('enhancement.messages.selectType') }]}
        >
          <Select placeholder={t('enhancement.messages.selectType')}>
            <Option value="data_augmentation">{t('enhancement.type.dataAugmentation', { defaultValue: '数据增强' })}</Option>
            <Option value="quality_improvement">{t('enhancement.type.qualityImprovement', { defaultValue: '质量提升' })}</Option>
            <Option value="noise_reduction">{t('enhancement.type.noiseReduction', { defaultValue: '降噪' })}</Option>
            <Option value="feature_extraction">{t('enhancement.type.featureExtraction', { defaultValue: '特征提取' })}</Option>
            <Option value="normalization">{t('enhancement.type.normalization', { defaultValue: '归一化' })}</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="sourceStage"
          label={t('aiTrial.columns.dataStage')}
          initialValue="temp_data"
        >
          <Select onChange={setSourceStage}>
            <Option value="temp_data">{t('tabs.tempData')}</Option>
            <Option value="sample_library">{t('tabs.sampleLibrary')}</Option>
            <Option value="annotated">{t('states.annotated')}</Option>
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
          name="maxIterations"
          label={t('enhancement.columns.iterations')}
          initialValue={3}
        >
          <InputNumber min={1} max={10} style={{ width: '100%' }} />
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

export default CreateEnhancementModal;
