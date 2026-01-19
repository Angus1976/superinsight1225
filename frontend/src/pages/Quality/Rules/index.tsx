import React, { useState } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('quality');
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
      message.success(t('messages.ruleCreated'));
    },
    onError: () => {
      message.error(t('messages.ruleCreateFailed'));
    },
  });

  const updateRuleMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      api.put(`/api/v1/quality/rules/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      setIsModalVisible(false);
      form.resetFields();
      message.success(t('messages.ruleUpdated'));
    },
    onError: () => {
      message.error(t('messages.ruleUpdateFailed'));
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/quality/rules/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      message.success(t('messages.ruleDeleted'));
    },
    onError: () => {
      message.error(t('messages.ruleDeleteFailed'));
    },
  });

  const toggleRuleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => 
      api.patch(`/api/v1/quality/rules/${id}/toggle`, { enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality-rules'] });
      message.success(t('messages.ruleStatusUpdated'));
    },
    onError: () => {
      message.error(t('messages.ruleStatusUpdateFailed'));
    },
  });

  const columns: ColumnsType<QualityRule> = [
    {
      title: t('rules.name'),
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
      title: t('rules.type'),
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
        return <Tag color={colors[type as keyof typeof colors]}>{t(`rules.types.${type}`)}</Tag>;
      },
    },
    {
      title: t('rules.priority'),
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => {
        const colors = {
          low: 'default',
          medium: 'processing',
          high: 'warning',
          critical: 'error',
        };
        return <Tag color={colors[priority as keyof typeof colors]}>{t(`rules.severities.${priority}`)}</Tag>;
      },
    },
    {
      title: t('rules.threshold'),
      dataIndex: 'threshold',
      key: 'threshold',
      render: (threshold: number) => `${(threshold * 100).toFixed(1)}%`,
    },
    {
      title: t('issues.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record) => (
        <Switch
          checked={enabled}
          onChange={(checked) => toggleRuleMutation.mutate({ id: record.id, enabled: checked })}
          checkedChildren={t('rules.enable')}
          unCheckedChildren={t('rules.disable')}
        />
      ),
    },
    {
      title: t('rules.executionCount'),
      dataIndex: 'executionCount',
      key: 'executionCount',
    },
    {
      title: t('rules.lastExecuted'),
      dataIndex: 'lastExecuted',
      key: 'lastExecuted',
      render: (date: string) => date ? new Date(date).toLocaleString() : t('rules.notExecuted'),
    },
    {
      title: t('rules.actions'),
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Tooltip title={t('rules.editRule')}>
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
          <Tooltip title={t('rules.executeRule')}>
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => {
                message.info(t('rules.executeInDev'));
              }}
            />
          </Tooltip>
          <Tooltip title={t('rules.delete')}>
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => {
                Modal.confirm({
                  title: t('messages.confirmDelete'),
                  content: t('rules.confirmDeleteContent', { name: record.name }),
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
        title={t('rules.management')}
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
            {t('rules.newRule')}
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
            showTotal: (total, range) => t('reports.pagination', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      <Modal
        title={editingRule ? t('rules.editRule') : t('rules.newRule')}
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
            label={t('rules.name')}
            rules={[{ required: true, message: t('rules.inputRuleName') }]}
          >
            <Input placeholder={t('rules.inputRuleName')} />
          </Form.Item>
          
          <Form.Item
            name="description"
            label={t('rules.description')}
            rules={[{ required: true, message: t('rules.inputRuleDesc') }]}
          >
            <Input.TextArea rows={3} placeholder={t('rules.inputRuleDesc')} />
          </Form.Item>
          
          <Form.Item
            name="type"
            label={t('rules.type')}
            rules={[{ required: true, message: t('rules.selectRuleType') }]}
          >
            <Select placeholder={t('rules.selectRuleType')}>
              <Select.Option value="semantic">{t('rules.types.semantic')}</Select.Option>
              <Select.Option value="syntactic">{t('rules.types.syntactic')}</Select.Option>
              <Select.Option value="completeness">{t('rules.types.completeness')}</Select.Option>
              <Select.Option value="consistency">{t('rules.types.consistency')}</Select.Option>
              <Select.Option value="accuracy">{t('rules.types.accuracy')}</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="priority"
            label={t('rules.priority')}
            rules={[{ required: true, message: t('rules.selectPriority') }]}
          >
            <Select placeholder={t('rules.selectPriority')}>
              <Select.Option value="low">{t('rules.severities.low')}</Select.Option>
              <Select.Option value="medium">{t('rules.severities.medium')}</Select.Option>
              <Select.Option value="high">{t('rules.severities.high')}</Select.Option>
              <Select.Option value="critical">{t('rules.severities.critical')}</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="threshold"
            label={t('rules.qualityThreshold')}
            rules={[{ required: true, message: t('rules.inputThreshold') }]}
          >
            <Input
              type="number"
              min={0}
              max={1}
              step={0.01}
              placeholder={t('rules.thresholdRange')}
              addonAfter="%"
            />
          </Form.Item>
          
          <Form.Item
            name="enabled"
            label={t('rules.enabledStatus')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren={t('rules.enable')} unCheckedChildren={t('rules.disable')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default QualityRules;
