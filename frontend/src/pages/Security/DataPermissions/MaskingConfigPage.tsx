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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['security', 'common']);
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
      message.success(t('dataPermissions.masking.createSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.masking.createFailed'));
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
      message.success(t('dataPermissions.masking.updateSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.masking.updateFailed'));
    },
  });

  // Delete rule mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => dataPermissionApi.deleteMaskingRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maskingRules'] });
      message.success(t('dataPermissions.masking.deleteSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.masking.deleteFailed'));
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
      message.error(t('dataPermissions.masking.previewFailed'));
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
      title: t('dataPermissions.masking.columns.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('dataPermissions.masking.columns.fieldPattern'),
      dataIndex: 'field_pattern',
      key: 'field_pattern',
      render: (pattern) => <code>{pattern}</code>,
    },
    {
      title: t('dataPermissions.masking.columns.algorithm'),
      dataIndex: 'algorithm',
      key: 'algorithm',
      width: 120,
      render: (algo: MaskingAlgorithmType) => (
        <Tooltip title={t(`dataPermissions.masking.algorithmDescriptions.${algo}`)}>
          <Tag color={algorithmColors[algo]}>{t(`dataPermissions.masking.algorithms.${algo}`)}</Tag>
        </Tooltip>
      ),
    },
    {
      title: t('dataPermissions.masking.columns.applicableRoles'),
      dataIndex: 'applicable_roles',
      key: 'applicable_roles',
      render: (roles: string[] | undefined) =>
        roles?.length ? roles.map((r) => <Tag key={r}>{r}</Tag>) : <Tag>{t('dataPermissions.masking.allRoles')}</Tag>,
    },
    {
      title: t('dataPermissions.masking.columns.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
    },
    {
      title: t('dataPermissions.masking.columns.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active) => (
        <Tag color={active ? 'success' : 'default'}>{active ? t('dataPermissions.masking.active') : t('dataPermissions.masking.inactive')}</Tag>
      ),
    },
    {
      title: t('dataPermissions.masking.columns.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('common:edit')}>
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('dataPermissions.masking.deleteConfirm')}
            onConfirm={() => record.id && deleteMutation.mutate(record.id)}
            okText={t('common:yes')}
            cancelText={t('common:no')}
          >
            <Tooltip title={t('common:delete')}>
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
              title={t('dataPermissions.masking.stats.totalRules')}
              value={rules?.length || 0}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.masking.stats.activeRules')}
              value={activeRules}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.masking.stats.encryptionRules')}
              value={rules?.filter((r) => r.algorithm === 'encryption').length || 0}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.masking.stats.hashRules')}
              value={rules?.filter((r) => r.algorithm === 'hash').length || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        title={t('dataPermissions.masking.title')}
        extra={
          <Space>
            <Button icon={<ExperimentOutlined />} onClick={() => setPreviewModalOpen(true)}>
              {t('dataPermissions.masking.previewMasking')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('dataPermissions.masking.addRule')}
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
      <Card title={t('dataPermissions.masking.algorithmReference')} style={{ marginTop: 24 }}>
        <Row gutter={16}>
          {Object.entries(algorithmDescriptions).map(([algo, desc]) => (
            <Col xs={24} sm={12} md={8} key={algo}>
              <Card size="small" style={{ marginBottom: 16 }}>
                <Tag color={algorithmColors[algo as MaskingAlgorithmType]}>
                  {t(`dataPermissions.masking.algorithms.${algo}`)}
                </Tag>
                <p style={{ marginTop: 8, marginBottom: 0, fontSize: 12 }}>{t(`dataPermissions.masking.algorithmDescriptions.${algo}`)}</p>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Rule Modal */}
      <Modal
        title={editingRule ? t('dataPermissions.masking.editRule') : t('dataPermissions.masking.addRule')}
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
            label={t('dataPermissions.masking.form.ruleName')}
            rules={[{ required: true, message: t('dataPermissions.masking.form.ruleName') }]}
          >
            <Input placeholder={t('dataPermissions.masking.form.ruleNamePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('dataPermissions.masking.form.description')}>
            <TextArea rows={2} placeholder={t('dataPermissions.masking.form.descriptionPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="field_pattern"
            label={t('dataPermissions.masking.form.fieldPattern')}
            rules={[{ required: true, message: t('dataPermissions.masking.form.fieldPattern') }]}
          >
            <Input placeholder={t('dataPermissions.masking.form.fieldPatternPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="algorithm"
            label={t('dataPermissions.masking.form.algorithm')}
            rules={[{ required: true, message: t('dataPermissions.masking.form.selectAlgorithm') }]}
          >
            <Select placeholder={t('dataPermissions.masking.form.selectAlgorithm')}>
              {Object.entries(algorithmDescriptions).map(([algo, desc]) => (
                <Option key={algo} value={algo}>
                  <Tag color={algorithmColors[algo as MaskingAlgorithmType]}>
                    {t(`dataPermissions.masking.algorithms.${algo}`)}
                  </Tag>
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>{t(`dataPermissions.masking.algorithmDescriptions.${algo}`)}</span>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="applicable_roles" label={t('dataPermissions.masking.form.applicableRoles')}>
            <Select mode="tags" placeholder={t('dataPermissions.masking.form.applicableRolesPlaceholder')}>
              <Option value="viewer">Viewer</Option>
              <Option value="annotator">Annotator</Option>
              <Option value="reviewer">Reviewer</Option>
              <Option value="manager">Manager</Option>
            </Select>
          </Form.Item>

          <Form.Item name="priority" label={t('dataPermissions.masking.form.priority')} initialValue={0}>
            <Input type="number" placeholder={t('dataPermissions.masking.form.priorityHint')} />
          </Form.Item>

          <Form.Item
            name="is_active"
            label={t('dataPermissions.masking.form.active')}
            valuePropName="checked"
            initialValue={true}
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Preview Modal */}
      <Modal
        title={t('dataPermissions.masking.preview.title')}
        open={previewModalOpen}
        onCancel={() => {
          setPreviewModalOpen(false);
          setPreviewResult(null);
        }}
        footer={[
          <Button key="close" onClick={() => setPreviewModalOpen(false)}>
            {t('common:close')}
          </Button>,
          <Button
            key="preview"
            type="primary"
            onClick={() => previewForm.submit()}
            loading={previewMutation.isPending}
          >
            {t('common:preview')}
          </Button>,
        ]}
        width={500}
      >
        <Form form={previewForm} layout="vertical" onFinish={handlePreview}>
          <Form.Item
            name="value"
            label={t('dataPermissions.masking.preview.testValue')}
            rules={[{ required: true, message: t('dataPermissions.masking.preview.testValue') }]}
          >
            <Input placeholder={t('dataPermissions.masking.preview.testValuePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="algorithm"
            label={t('dataPermissions.masking.preview.algorithm')}
            rules={[{ required: true, message: t('dataPermissions.masking.preview.selectAlgorithm') }]}
          >
            <Select placeholder={t('dataPermissions.masking.preview.selectAlgorithm')}>
              <Option value="replacement">{t('dataPermissions.masking.algorithms.replacement')}</Option>
              <Option value="partial">{t('dataPermissions.masking.algorithms.partial')}</Option>
              <Option value="encryption">{t('dataPermissions.masking.algorithms.encryption')}</Option>
              <Option value="hash">{t('dataPermissions.masking.algorithms.hash')}</Option>
              <Option value="nullify">{t('dataPermissions.masking.algorithms.nullify')}</Option>
            </Select>
          </Form.Item>
        </Form>

        {previewResult && (
          <Card style={{ marginTop: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label={t('dataPermissions.masking.preview.original')}>
                <code>{previewResult.original_value}</code>
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.masking.preview.masked')}>
                <code style={{ color: '#52c41a' }}>{previewResult.masked_value}</code>
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.masking.preview.algorithm')}>
                <Tag color={algorithmColors[previewResult.algorithm]}>
                  {t(`dataPermissions.masking.algorithms.${previewResult.algorithm}`)}
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
