import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Upload, message, Modal, Form, Input, Select } from 'antd';
import { PlusOutlined, UploadOutlined, DownloadOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

interface AugmentationSample {
  id: string;
  name: string;
  type: 'text' | 'image' | 'audio' | 'video';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  originalCount: number;
  augmentedCount: number;
  createdAt: string;
  updatedAt: string;
}

const AugmentationSamples: React.FC = () => {
  const { t } = useTranslation('augmentation');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingSample, setEditingSample] = useState<AugmentationSample | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const statusKeyMap: Record<string, string> = {
    pending: 'status.pending',
    processing: 'status.running',
    completed: 'status.completed',
    failed: 'status.failed',
  };

  const typeKeyMap: Record<string, string> = {
    text: 'sampleManagement.type.text',
    image: 'sampleManagement.type.image',
    audio: 'sampleManagement.type.audio',
    video: 'sampleManagement.type.video',
  };

  const { data: samples, isLoading } = useQuery<AugmentationSample[]>({
    queryKey: ['augmentation-samples'],
    queryFn: () => api.get('/api/v1/augmentation/samples').then(res => res.data),
  });

  const createSampleMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/augmentation/samples', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-samples'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('sampleManagement.createSuccess'));
    },
    onError: () => {
      message.error(t('sampleManagement.createFailed'));
    },
  });

  const deleteSampleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/augmentation/samples/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-samples'] });
      message.success(t('sampleManagement.deleteSuccess'));
    },
    onError: () => {
      message.error(t('sampleManagement.deleteFailed'));
    },
  });

  const columns: ColumnsType<AugmentationSample> = [
    {
      title: t('sampleManagement.sampleName'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <a>{text}</a>,
    },
    {
      title: t('sampleManagement.sampleType'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          text: 'blue',
          image: 'green',
          audio: 'orange',
          video: 'purple',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{t(typeKeyMap[type])}</Tag>;
      },
    },
    {
      title: t('jobs.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          pending: 'default',
          processing: 'processing',
          completed: 'success',
          failed: 'error',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{t(statusKeyMap[status])}</Tag>;
      },
    },
    {
      title: t('sampleManagement.originalCount'),
      dataIndex: 'originalCount',
      key: 'originalCount',
    },
    {
      title: t('sampleManagement.augmentedCount'),
      dataIndex: 'augmentedCount',
      key: 'augmentedCount',
    },
    {
      title: t('sampleManagement.createdAt'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: t('sampleManagement.actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingSample(record);
              form.setFieldsValue(record);
              setIsModalVisible(true);
            }}
          >
            {t('sampleManagement.edit')}
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => {
              message.info(t('sampleManagement.downloadInDev'));
            }}
          >
            {t('sampleManagement.download')}
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: t('sampleManagement.confirmDelete'),
                content: t('sampleManagement.confirmDeleteMessage', { name: record.name }),
                onOk: () => deleteSampleMutation.mutate(record.id),
              });
            }}
          >
            {t('common:delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    createSampleMutation.mutate(values);
  };

  const uploadProps = {
    name: 'file',
    action: '/api/v1/augmentation/samples/upload',
    headers: {
      authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    onChange(info: any) {
      if (info.file.status === 'done') {
        message.success(t('sampleManagement.uploadSuccess', { name: info.file.name }));
        queryClient.invalidateQueries({ queryKey: ['augmentation-samples'] });
      } else if (info.file.status === 'error') {
        message.error(t('sampleManagement.uploadFailed', { name: info.file.name }));
      }
    },
  };

  return (
    <div className="augmentation-samples">
      <Card
        title={t('sampleManagement.title')}
        extra={
          <Space>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>{t('sampleManagement.batchUpload')}</Button>
            </Upload>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingSample(null);
                form.resetFields();
                setIsModalVisible(true);
              }}
            >
              {t('sampleManagement.createSample')}
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={samples}
          loading={isLoading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => t('sampleManagement.pagination', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      <Modal
        title={editingSample ? t('sampleManagement.editSample') : t('sampleManagement.createSample')}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createSampleMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label={t('sampleManagement.sampleName')}
            rules={[{ required: true, message: t('sampleManagement.sampleNameRequired') }]}
          >
            <Input placeholder={t('sampleManagement.sampleNamePlaceholder')} />
          </Form.Item>
          <Form.Item
            name="type"
            label={t('sampleManagement.sampleType')}
            rules={[{ required: true, message: t('sampleManagement.sampleTypeRequired') }]}
          >
            <Select placeholder={t('sampleManagement.sampleTypePlaceholder')}>
              <Select.Option value="text">{t('sampleManagement.type.text')}</Select.Option>
              <Select.Option value="image">{t('sampleManagement.type.image')}</Select.Option>
              <Select.Option value="audio">{t('sampleManagement.type.audio')}</Select.Option>
              <Select.Option value="video">{t('sampleManagement.type.video')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="description"
            label={t('sampleManagement.sampleDescription')}
          >
            <Input.TextArea rows={4} placeholder={t('sampleManagement.sampleDescriptionPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AugmentationSamples;
