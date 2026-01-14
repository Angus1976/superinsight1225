/**
 * Masking Configuration Page
 * 
 * Configure data masking rules and preview masking effects.
 */

import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Row,
  Col,
  Statistic,
  message,
  Descriptions,
  Tooltip,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  dataPermissionApi,
  MaskingRule,
  MaskingAlgorithmType,
  MaskingPreview,
} from '@/services/dataPermissionApi';

const { Option } = Select;
const { TextArea } = Input;

const algorithmColors: Record<MaskingAlgorithmType, string> = {
  replacement: 'blue',
  partial: 'cyan',
  encryption: 'purple',
  hash: 'orange',
  nullify: 'red',
};

const algorithmDescriptions: Record<MaskingAlgorithmType, string> = {
  replacement: 'Replace entire value with asterisks (***)',
  partial: 'Show first and last characters, mask middle (Jo***hn)',
  encryption: 'Encrypt value with reversible encryption',
  hash: 'One-way hash of the value (SHA-256)',
  nullify: 'Replace with NULL/empty value',
};

const MaskingConfigPage: React.FC = () => {
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<MaskingRule | null>(null);
  const [previewResult, setPreviewResult] = useState<MaskingPreview | null>(null);

  const [ruleForm] = Form.useForm();
  const [previewForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch masking rules
  const { data: rules, isLoading } = useQuery({
    queryKey: ['maskingRules'],
    queryFn: () => dataPermissionApi.listMaskingRules(),
  });

  // Create rule mutation
  const createMutation = useMutation({
    mutationFn: (rule: Omit<MaskingRule, 'id' | 'created_at'>) =>
      dataPermissionApi.createMaskingRule(rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maskingRules'] });
      setRuleModalOpen(false);
      ruleForm.resetFields();
      setEditingRule(null);
      message.success('Rule created successfully');
    },
    onError: () => {
      message.error('Failed to create rule');
    },
  });

  // Update rule mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, rule }: { id: string; rule: Partial<MaskingRule> }) =>
      dataPermissionApi.updateMaskingRule(id, rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maskingRules'] });
      setRuleModalOpen(false);
      ruleForm.resetFields();
      setEditingRule(null);
      message.success('Rule updated successfully');
    },
    onError: () => {
      message.error('Failed to update rule');
    },
  });

  // Delete rule mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => dataPermissionApi.deleteMaskingRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maskingRules'] });
      message.success('Rule deleted successfully');
    },
    onError: () => {
      message.error('Failed to delete rule');
    },
  });

  // Preview mutation
  const previewMutation = useMutation({
    mutationFn: ({
      value,
      algorithm,
      config,
    }: {
      value: string;
      algorithm: MaskingAlgorithmType;
      config?: Record<string, unknown>;
    }) => dataPermissionApi.previewMasking(value, algorithm, config),
    onSuccess: (result) => {
      setPreviewResult(result);
    },
    onError: () => {
      message.error('Preview failed');
    },
  });

  const handleCreate = () => {
    setEditingRule(null);
    ruleForm.resetFields();
    setRuleModalOpen(true);
  };

  const handleEdit = (rule: MaskingRule) => {
    setEditingRule(rule);
    ruleForm.setFieldsValue({
      name: rule.name,
      description: rule.description,
      field_pattern: rule.field_pattern,
      algorithm: rule.algorithm,
      applicable_roles: rule.applicable_roles,
      priority: rule.priority,
      is_active: rule.is_active,
    });
    setRuleModalOpen(true);
  };

  const handleSubmit = (values: Omit<MaskingRule, 'id' | 'created_at'>) => {
    if (editingRule?.id) {
      updateMutation.mutate({ id: editingRule.id, rule: values });
    } else {
      createMutation.mutate(values);
    }
  };

  const handlePreview = (values: { value: string; algorithm: MaskingAlgorithmType }) => {
    previewMutation.mutate({
      value: values.value,
      algorithm: values.algorithm,
    });
  };

  const columns: ColumnsType<MaskingRule> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Field Pattern',
      dataIndex: 'field_pattern',
      key: 'field_pattern',
      render: (pattern) => <code>{pattern}</code>,
    },
    {
      title: 'Algorithm',
      dataIndex: 'algorithm',
      key: 'algorithm',
      width: 120,
      render: (algo: MaskingAlgorithmType) => (
        <Tooltip title={algorithmDescriptions[algo]}>
          <Tag color={algorithmColors[algo]}>{algo.toUpperCase()}</Tag>
        </Tooltip>
      ),
    },
    {
      title: 'Applicable Roles',
      dataIndex: 'applicable_roles',
      key: 'applicable_roles',
      render: (roles: string[] | undefined) =>
        roles?.length ? roles.map((r) => <Tag key={r}>{r}</Tag>) : <Tag>All Roles</Tag>,
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active) => (
        <Tag color={active ? 'success' : 'default'}>{active ? 'Active' : 'Inactive'}</Tag>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="Edit">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this rule?"
            onConfirm={() => record.id && deleteMutation.mutate(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete">
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const activeRules = rules?.filter((r) => r.is_active).length || 0;

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Rules"
              value={rules?.length || 0}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Active Rules"
              value={activeRules}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Encryption Rules"
              value={rules?.filter((r) => r.algorithm === 'encryption').length || 0}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Hash Rules"
              value={rules?.filter((r) => r.algorithm === 'hash').length || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        title="Masking Rules"
        extra={
          <Space>
            <Button icon={<ExperimentOutlined />} onClick={() => setPreviewModalOpen(true)}>
              Preview Masking
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Add Rule
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={rules || []}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1100 }}
        />
      </Card>

      {/* Algorithm Reference */}
      <Card title="Masking Algorithms Reference" style={{ marginTop: 24 }}>
        <Row gutter={16}>
          {Object.entries(algorithmDescriptions).map(([algo, desc]) => (
            <Col xs={24} sm={12} md={8} key={algo}>
              <Card size="small" style={{ marginBottom: 16 }}>
                <Tag color={algorithmColors[algo as MaskingAlgorithmType]}>
                  {algo.toUpperCase()}
                </Tag>
                <p style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>{desc}</p>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Rule Modal */}
      <Modal
        title={editingRule ? 'Edit Masking Rule' : 'Add Masking Rule'}
        open={ruleModalOpen}
        onCancel={() => {
          setRuleModalOpen(false);
          setEditingRule(null);
        }}
        onOk={() => ruleForm.submit()}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        width={600}
      >
        <Form form={ruleForm} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="Rule Name"
            rules={[{ required: true, message: 'Please enter rule name' }]}
          >
            <Input placeholder="e.g., Email Masking" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Rule description" />
          </Form.Item>

          <Form.Item
            name="field_pattern"
            label="Field Pattern (Regex)"
            rules={[{ required: true, message: 'Please enter field pattern' }]}
          >
            <Input placeholder="e.g., ^email$|.*_email$|.*email.*" />
          </Form.Item>

          <Form.Item
            name="algorithm"
            label="Masking Algorithm"
            rules={[{ required: true, message: 'Please select algorithm' }]}
          >
            <Select placeholder="Select algorithm">
              {Object.entries(algorithmDescriptions).map(([algo, desc]) => (
                <Option key={algo} value={algo}>
                  <Tag color={algorithmColors[algo as MaskingAlgorithmType]}>
                    {algo.toUpperCase()}
                  </Tag>
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>{desc}</span>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="applicable_roles" label="Applicable Roles">
            <Select mode="tags" placeholder="Leave empty for all roles">
              <Option value="viewer">Viewer</Option>
              <Option value="annotator">Annotator</Option>
              <Option value="reviewer">Reviewer</Option>
              <Option value="manager">Manager</Option>
            </Select>
          </Form.Item>

          <Form.Item name="priority" label="Priority" initialValue={0}>
            <Input type="number" placeholder="Higher priority rules are applied first" />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="Active"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title="Preview Masking"
        open={previewModalOpen}
        onCancel={() => {
          setPreviewModalOpen(false);
          setPreviewResult(null);
        }}
        footer={[
          <Button key="close" onClick={() => setPreviewModalOpen(false)}>
            Close
          </Button>,
          <Button
            key="preview"
            type="primary"
            onClick={() => previewForm.submit()}
            loading={previewMutation.isPending}
          >
            Preview
          </Button>,
        ]}
        width={500}
      >
        <Form form={previewForm} layout="vertical" onFinish={handlePreview}>
          <Form.Item
            name="value"
            label="Test Value"
            rules={[{ required: true, message: 'Please enter a test value' }]}
          >
            <Input placeholder="e.g., john.doe@example.com" />
          </Form.Item>

          <Form.Item
            name="algorithm"
            label="Algorithm"
            rules={[{ required: true, message: 'Please select algorithm' }]}
          >
            <Select placeholder="Select algorithm">
              <Option value="replacement">Replacement</Option>
              <Option value="partial">Partial</Option>
              <Option value="encryption">Encryption</Option>
              <Option value="hash">Hash</Option>
              <Option value="nullify">Nullify</Option>
            </Select>
          </Form.Item>
        </Form>

        {previewResult && (
          <Card style={{ marginTop: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Original">
                <code>{previewResult.original_value}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Masked">
                <code style={{ color: '#52c41a' }}>{previewResult.masked_value}</code>
              </Descriptions.Item>
              <Descriptions.Item label="Algorithm">
                <Tag color={algorithmColors[previewResult.algorithm]}>
                  {previewResult.algorithm.toUpperCase()}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Modal>
    </div>
  );
};

export default MaskingConfigPage;
