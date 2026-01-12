import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

interface QualityRule {
  id: string;
  name: string;
  description: string;
  type: 'semantic' | 'syntactic' | 'completeness' | 'consistency' | 'accuracy';
  enabled: boolean;
  priority: 'low' | 'medium' | 'high' | 'critical';
  threshold: number;
  conditions: any[];
  actions: string[];
  createdAt: string;
  updatedAt: string;
  lastExecuted?: string;
  executionCount: number;
}

const QualityRules: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<QualityRule | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: rules, isLoading } = useQuery({
    queryKey: ['quality-rules'],
    queryFn: () => api.get('/api/v1/quality/rules').then(res => res.data),
  });

  const createRuleMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/quality/rules', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('质量规则创建成功');
    },
    onError: () => {
      message.error('质量规则创建失败');
    },
  });

  const updateRuleMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.put(`/api/v1/quality/rules/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success('质量规则更新成功');
    },
    onError: () => {
      message.error('质量规则更新失败');
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/quality/rules/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      message.success('质量规则删除成功');
    },
    onError: () => {
      message.error('质量规则删除失败');
    },
  });

  const toggleRuleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      api.patch(`/api/v1/quality/rules/${id}/toggle`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      message.success('规则状态更新成功');
    },
    onError: () => {
      message.error('规则状态更新失败');
    },
  });

  const columns: ColumnsType<QualityRule> = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record) => (
        <div>
          <div>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>{record.description}</div>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colors = {
          semantic: 'blue',
          syntactic: 'green',
          completeness: 'orange',
          consistency: 'purple',
          accuracy: 'red',
        };
        const labels = {
          semantic: '语义',
          syntactic: '语法',
          completeness: '完整性',
          consistency: '一致性',
          accuracy: '准确性',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{labels[type as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => {
        const colors = {
          low: 'default',
          medium: 'processing',
          high: 'warning',
          critical: 'error',
        };
        const labels = {
          low: '低',
          medium: '中',
          high: '高',
          critical: '严重',
        };
        return <Tag color={colors[priority as keyof typeof colors]}>{labels[priority as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      render: (threshold: number) => `${(threshold * 100).toFixed(1)}%`,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => toggleRuleMutation.mutate({ id: record.id, enabled: checked })}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '执行次数',
      dataIndex: 'executionCount',
      key: 'executionCount',
    },
    {
      title: '最后执行',
      dataIndex: 'lastExecuted',
      key: 'lastExecuted',
      render: (date: string) => date ? new Date(date).toLocaleString() : '未执行',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title="编辑规则">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingRule(record);
                form.setFieldsValue(record);
                setIsModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="立即执行">
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => {
                // 执行规则逻辑
                message.info('规则执行功能开发中');
              }}
            />
          </Tooltip>
          <Tooltip title="删除规则">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: '确认删除',
                  content: `确定要删除规则 "${record.name}" 吗？`,
                  onOk: () => deleteRuleMutation.mutate(record.id),
                });
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const handleSubmit = (values: any) => {
    if (editingRule) {
      updateRuleMutation.mutate({ id: editingRule.id, data: values });
    } else {
      createRuleMutation.mutate(values);
    }
  };

  return (
    <div className="quality-rules">
      <Card
        title="质量规则管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingRule(null);
              form.resetFields();
              setIsModalVisible(true);
            }}
          >
            新建规则
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={rules}
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
        title={editingRule ? '编辑质量规则' : '新建质量规则'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createRuleMutation.isPending || updateRuleMutation.isPending}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="请输入规则名称" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="规则描述"
            rules={[{ required: true, message: '请输入规则描述' }]}
          >
            <Input.TextArea rows={3} placeholder="请输入规则描述" />
          </Form.Item>
          
          <Form.Item
            name="type"
            label="规则类型"
            rules={[{ required: true, message: '请选择规则类型' }]}
          >
            <Select placeholder="请选择规则类型">
              <Select.Option value="semantic">语义质量</Select.Option>
              <Select.Option value="syntactic">语法质量</Select.Option>
              <Select.Option value="completeness">完整性</Select.Option>
              <Select.Option value="consistency">一致性</Select.Option>
              <Select.Option value="accuracy">准确性</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="priority"
            label="优先级"
            rules={[{ required: true, message: '请选择优先级' }]}
          >
            <Select placeholder="请选择优先级">
              <Select.Option value="low">低</Select.Option>
              <Select.Option value="medium">中</Select.Option>
              <Select.Option value="high">高</Select.Option>
              <Select.Option value="critical">严重</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="threshold"
            label="质量阈值"
            rules={[{ required: true, message: '请输入质量阈值' }]}
          >
            <Input
              type="number"
              min={0}
              max={1}
              step={0.01}
              placeholder="0.0 - 1.0"
              addonAfter="%"
            />
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

export default QualityRules;