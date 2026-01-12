import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Progress, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SyncOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

interface DataSource {
  id: string;
  name: string;
  type: 'database' | 'file' | 'api' | 'stream';
  status: 'active' | 'inactive' | 'error' | 'syncing';
  connectionString: string;
  lastSyncTime: string;
  nextSyncTime: string;
  syncInterval: number;
  totalRecords: number;
  syncedRecords: number;
  errorCount: number;
  enabled: boolean;
  createdAt: string;
  config: any;
}

const DataSyncSources: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: sources, isLoading } = useQuery({
    queryKey: ['data-sources'],
    queryFn: () => api.get('/api/v1/data-sync/sources').then(res => res.data),
  });

  const createSourceMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/data-sync/sources', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('数据源创建成功');
    },
    onError: () => {
      message.error('数据源创建失败');
    },
  });

  const updateSourceMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.put(`/api/v1/data-sync/sources/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('数据源更新成功');
    },
    onError: () => {
      message.error('数据源更新失败');
    },
  });

  const deleteSourceMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/data-sync/sources/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      message.success('数据源删除成功');
    },
    onError: () => {
      message.error('数据源删除失败');
    },
  });

  const syncSourceMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/data-sync/sources/${id}/sync`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      message.success('同步任务已启动');
    },
    onError: () => {
      message.error('同步任务启动失败');
    },
  });

  const toggleSourceMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      api.patch(`/api/v1/data-sync/sources/${id}/toggle`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources'] });
      message.success('数据源状态更新成功');
    },
    onError: () => {
      message.error('数据源状态更新失败');
    },
  });

  const columns: ColumnsType<DataSource> = [
    {
      title: '数据源名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record) => (
        <div>
          <div>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.connectionString.length > 50 
              ? `${record.connectionString.substring(0, 50)}...` 
              : record.connectionString}
          </div>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          database: 'blue',
          file: 'green',
          api: 'orange',
          stream: 'purple',
        };
        const labels = {
          database: '数据库',
          file: '文件',
          api: 'API',
          stream: '流',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{labels[type as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          active: 'success',
          inactive: 'default',
          error: 'error',
          syncing: 'processing',
        };
        const labels = {
          active: '活跃',
          inactive: '非活跃',
          error: '错误',
          syncing: '同步中',
        };
        return <Tag color={colors[status as keyof typeof colors]}>{labels[status as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '同步进度',
      key: 'progress',
      render: (_, record) => {
        const progress = record.totalRecords > 0 ? (record.syncedRecords / record.totalRecords) * 100 : 0;
        return (
          <div>
            <Progress 
              percent={progress} 
              size="small" 
              status={record.errorCount > 0 ? 'exception' : 'normal'}
            />
            <div style={{ fontSize: '12px', color: '#666' }}>
              {record.syncedRecords}/{record.totalRecords} 条记录
            </div>
          </div>
        );
      },
    },
    {
      title: '同步间隔',
      dataIndex: 'syncInterval',
      key: 'syncInterval',
      render: (interval: number) => `${interval} 分钟`,
    },
    {
      title: '最后同步',
      dataIndex: 'lastSyncTime',
      key: 'lastSyncTime',
      render: (time: string) => time ? new Date(time).toLocaleString() : '从未同步',
    },
    {
      title: '下次同步',
      dataIndex: 'nextSyncTime',
      key: 'nextSyncTime',
      render: (time: string) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '启用状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => toggleSourceMutation.mutate({ id: record.id, enabled: checked })}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="立即同步">
            <Button
              type="link"
              icon={<SyncOutlined />}
              onClick={() => syncSourceMutation.mutate(record.id)}
              loading={syncSourceMutation.isPending}
            />
          </Tooltip>
          <Tooltip title="编辑数据源">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingSource(record);
                form.setFieldsValue(record);
                setIsModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="删除数据源">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: '确认删除',
                  content: `确定要删除数据源 "${record.name}" 吗？`,
                  onOk: () => deleteSourceMutation.mutate(record.id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    if (editingSource) {
      updateSourceMutation.mutate({ id: editingSource.id, data: values });
    } else {
      createSourceMutation.mutate(values);
    }
  };

  const renderConfigForm = (type: string) => {
    switch (type) {
      case 'database':
        return (
          <>
            <Form.Item
              name={['config', 'host']}
              label="主机地址"
              rules={[{ required: true, message: '请输入主机地址' }]}
            >
              <Input placeholder="localhost" />
            </Form.Item>
            <Form.Item
              name={['config', 'port']}
              label="端口"
              rules={[{ required: true, message: '请输入端口' }]}
            >
              <Input placeholder="5432" />
            </Form.Item>
            <Form.Item
              name={['config', 'database']}
              label="数据库名"
              rules={[{ required: true, message: '请输入数据库名' }]}
            >
              <Input placeholder="database_name" />
            </Form.Item>
            <Form.Item
              name={['config', 'username']}
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input placeholder="username" />
            </Form.Item>
            <Form.Item
              name={['config', 'password']}
              label="密码"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password placeholder="password" />
            </Form.Item>
          </>
        );
      case 'file':
        return (
          <>
            <Form.Item
              name={['config', 'path']}
              label="文件路径"
              rules={[{ required: true, message: '请输入文件路径' }]}
            >
              <Input placeholder="/path/to/file" />
            </Form.Item>
            <Form.Item
              name={['config', 'format']}
              label="文件格式"
              rules={[{ required: true, message: '请选择文件格式' }]}
            >
              <Select placeholder="请选择文件格式">
                <Select.Option value="csv">CSV</Select.Option>
                <Select.Option value="json">JSON</Select.Option>
                <Select.Option value="xml">XML</Select.Option>
                <Select.Option value="excel">Excel</Select.Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'api':
        return (
          <>
            <Form.Item
              name={['config', 'url']}
              label="API地址"
              rules={[{ required: true, message: '请输入API地址' }]}
            >
              <Input placeholder="https://api.example.com/data" />
            </Form.Item>
            <Form.Item
              name={['config', 'method']}
              label="请求方法"
              rules={[{ required: true, message: '请选择请求方法' }]}
            >
              <Select placeholder="请选择请求方法">
                <Select.Option value="GET">GET</Select.Option>
                <Select.Option value="POST">POST</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item
              name={['config', 'headers']}
              label="请求头"
            >
              <Input.TextArea rows={3} placeholder='{"Authorization": "Bearer token"}' />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div className="data-sync-sources">
      <Card
        title="数据源管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingSource(null);
              form.resetFields();
              setIsModalVisible(true);
            }}
          >
            新建数据源
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={sources}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1400 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingSource ? '编辑数据源' : '新建数据源'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createSourceMutation.isPending || updateSourceMutation.isPending}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="数据源名称"
            rules={[{ required: true, message: '请输入数据源名称' }]}
          >
            <Input placeholder="请输入数据源名称" />
          </Form.Item>
          
          <Form.Item
            name="type"
            label="数据源类型"
            rules={[{ required: true, message: '请选择数据源类型' }]}
          >
            <Select placeholder="请选择数据源类型">
              <Select.Option value="database">数据库</Select.Option>
              <Select.Option value="file">文件</Select.Option>
              <Select.Option value="api">API</Select.Option>
              <Select.Option value="stream">数据流</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="syncInterval"
            label="同步间隔（分钟）"
            rules={[{ required: true, message: '请输入同步间隔' }]}
          >
            <Input type="number" min={1} placeholder="60" />
          </Form.Item>

          <Form.Item dependencies={['type']}>
            {({ getFieldValue }) => {
              const type = getFieldValue('type');
              return type ? renderConfigForm(type) : null;
            }}
          </Form.Item>

          <Form.Item
            name="enabled"
            label="启用状态"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DataSyncSources;