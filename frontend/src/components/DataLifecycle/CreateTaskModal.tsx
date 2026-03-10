/**
 * Create Task Modal Component
 * 
 * Modal for creating annotation tasks with data source selection.
 * Supports flexible data flow - users can select data from any stage.
 */

import { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Table, DatePicker, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useTempData, useAnnotationTask } from '@/hooks/useDataLifecycle';

const { TextArea } = Input;
const { Option } = Select;

interface CreateTaskModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const CreateTaskModal: React.FC<CreateTaskModalProps> = ({ visible, onClose, onSuccess }) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  const { data: tempData, fetchTempData } = useTempData();
  const { createTask, loading } = useAnnotationTask();
  
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

      // Create task for each selected data item
      for (const dataId of selectedRowKeys) {
        await createTask({
          name: values.name,
          description: values.description,
          data_id: dataId as string,
          priority: values.priority,
          assignee: values.assignee,
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
      title={t('annotationTask.actions.create')}
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
          label={t('annotationTask.columns.name')}
          rules={[{ required: true, message: t('annotationTask.validation.nameRequired') }]}
        >
          <Input placeholder={t('annotationTask.placeholders.name')} />
        </Form.Item>

        <Form.Item
          name="description"
          label={t('annotationTask.columns.description')}
        >
          <TextArea
            rows={3}
            placeholder={t('annotationTask.placeholders.description')}
          />
        </Form.Item>

        <Form.Item
          name="sourceStage"
          label={t('aiTrial.columns.dataStage')}
          initialValue="temp_data"
        >
          <Select onChange={setSourceStage}>
            <Option value="temp_data">{t('tabs.tempData')}</Option>
            <Option value="sample_library">{t('tabs.sampleLibrary')}</Option>
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
            scroll={{ y: 250 }}
          />
        </Form.Item>

        <Form.Item
          name="priority"
          label={t('annotationTask.columns.priority')}
          initialValue="medium"
        >
          <Select>
            <Option value="low">{t('annotationTask.priority.low')}</Option>
            <Option value="medium">{t('annotationTask.priority.medium')}</Option>
            <Option value="high">{t('annotationTask.priority.high')}</Option>
            <Option value="urgent">{t('annotationTask.priority.urgent')}</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="assignee"
          label={t('annotationTask.columns.assignee')}
        >
          <Input placeholder={t('annotationTask.messages.assignee')} />
        </Form.Item>

        <Form.Item
          name="dueDate"
          label={t('annotationTask.columns.dueDate')}
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Form>

      <div style={{ marginTop: 8, color: '#8c8c8c' }}>
        {t('annotationTask.messages.samplesSelected', { count: selectedRowKeys.length })}
      </div>
    </Modal>
  );
};

export default CreateTaskModal;
