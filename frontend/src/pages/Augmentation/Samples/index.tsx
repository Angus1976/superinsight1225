import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Upload, message, Modal, Form, Input, Select } from 'antd';
import { PlusOutlined, UploadOutlined, DownloadOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
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
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingSample, setEditingSample] = useState<AugmentationSample | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: samples, isLoading } = useQuery({
    queryKey: ['augmentation-samples'],
    queryFn: () => api.get('/api/v1/augmentation/samples').then(res => res.data),
  });

  const createSampleMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/augmentation/samples', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-samples'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('样本创建成功');
    },
    onError: () => {
      message.error('样本创建失败');
    },
  });

  const deleteSampleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/augmentation/samples/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['augmentation-samples'] });
      message.success('样本删除成功');
    },
    onError: () => {
      message.error('样本删除失败');
    },
  });

  const columns: ColumnsType<AugmentationSample> = [
    {
      title: '样本名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <a>{text}</a>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          text: 'blue',
          image: 'green',
          audio: 'orange',
          video: 'purple',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{type.toUpperCase()}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          pending: 'default',
          processing: 'processing',
          completed: 'success',
          failed: 'error',
        };
        const labels = {
          pending: '待处理',
          processing: '处理中',
          completed: '已完成',
          failed: '失败',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{labels[status as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '原始数量',
      dataIndex: 'originalCount',
      key: 'originalCount',
    },
    {
      title: '增强数量',
      dataIndex: 'augmentedCount',
      key: 'augmentedCount',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
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
            编辑
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => {
              // 下载样本逻辑
              message.info('下载功能开发中');
            }}
          >
            下载
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确认删除',
                content: `确定要删除样本 "${record.name}" 吗？`,
                onOk: () => deleteSampleMutation.mutate(record.id),
              });
            }}
          >
            删除
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
        message.success(`${info.file.name} 文件上传成功`);
        queryClient.invalidateQueries({ queryKey: ['augmentation-samples'] });
      } else if (info.file.status === 'error') {
        message.error(`${info.file.name} 文件上传失败`);
      }
    },
  };

  return (
    <div className="augmentation-samples">
      <Card
        title="数据增强样本管理"
        extra={
          <Space>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>批量上传</Button>
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
              新建样本
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
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingSample ? '编辑样本' : '新建样本'}
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
            label="样本名称"
            rules={[{ required: true, message: '请输入样本名称' }]}
          >
            <Input placeholder="请输入样本名称" />
          </Form.Item>
          <Form.Item
            name="type"
            label="样本类型"
            rules={[{ required: true, message: '请选择样本类型' }]}
          >
            <Select placeholder="请选择样本类型">
              <Select.Option value="text">文本</Select.Option>
              <Select.Option value="image">图像</Select.Option>
              <Select.Option value="audio">音频</Select.Option>
              <Select.Option value="video">视频</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={4} placeholder="请输入样本描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AugmentationSamples;