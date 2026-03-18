import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, Tag, Space,
  message, Popconfirm, Typography,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  getWorkflows, createWorkflow, updateWorkflow, deleteWorkflow,
} from '@/services/aiAssistantApi';
import type { WorkflowItem } from '@/types/aiAssistant';

const { Text } = Typography;

const ROLES = ['admin', 'business_expert', 'annotator', 'viewer'];
const OUTPUT_MODES = ['merge', 'compare'];

const WorkflowAdmin: React.FC = () => {
  const { t } = useTranslation('workflow');
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowItem | null>(null);
  const [searchText, setSearchText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  const fetchWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getWorkflows();
      setWorkflows(data);
    } catch {
      message.error(t('errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const handleCreate = () => {
    setEditingWorkflow(null);
    form.resetFields();
    setModalOpen(true);
  };

  const handleEdit = (record: WorkflowItem) => {
    setEditingWorkflow(record);
    form.setFieldsValue({
      name: record.name,
      name_en: record.name_en,
      description: record.description,
      description_en: record.description_en,
      skill_ids: record.skill_ids,
      output_modes: record.output_modes,
      visible_roles: record.visible_roles,
      preset_prompt: record.preset_prompt,
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteWorkflow(id);
      message.success(t('admin.deleteSuccess'));
      fetchWorkflows();
    } catch {
      message.error(t('errors.saveFailed'));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      if (editingWorkflow) {
        await updateWorkflow(editingWorkflow.id, values);
        message.success(t('admin.updateSuccess'));
      } else {
        await createWorkflow(values);
        message.success(t('admin.createSuccess'));
      }

      setModalOpen(false);
      form.resetFields();
      setEditingWorkflow(null);
      fetchWorkflows();
    } catch (err: unknown) {
      // Form validation errors are handled by antd; only show API errors
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error(t('errors.saveFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleModalCancel = () => {
    setModalOpen(false);
    form.resetFields();
    setEditingWorkflow(null);
  };

  // ---------------------------------------------------------------------------
  // Filtered data
  // ---------------------------------------------------------------------------
  const filtered = searchText
    ? workflows.filter((w) =>
        w.name.toLowerCase().includes(searchText.toLowerCase()) ||
        (w.name_en ?? '').toLowerCase().includes(searchText.toLowerCase()),
      )
    : workflows;

  // ---------------------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------------------
  const columns: ColumnsType<WorkflowItem> = [
    {
      title: t('admin.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: WorkflowItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          {record.is_preset && <Tag color="blue">{t('admin.isPreset')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('admin.status'),
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'enabled' ? 'green' : 'default'}>
          {status === 'enabled' ? t('admin.enabled') : t('admin.disabled')}
        </Tag>
      ),
    },
    {
      title: t('admin.skills'),
      dataIndex: 'skill_ids',
      key: 'skill_ids',
      width: 120,
      render: (ids: string[]) => (
        <Text>{ids?.length ? t('selector.skillCount', { count: ids.length }) : t('admin.noSkills')}</Text>
      ),
    },
    {
      title: t('admin.visibleRoles'),
      dataIndex: 'visible_roles',
      key: 'visible_roles',
      render: (roles: string[]) => (
        <Space size={4} wrap>
          {roles?.map((role) => (
            <Tag key={role}>{t(`roles.${role}`)}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('admin.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v: string) => (v ? new Date(v).toLocaleString() : '-'),
    },
    {
      title: '',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: WorkflowItem) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('admin.edit')}
          </Button>
          {record.is_preset ? (
            <Button type="link" size="small" disabled icon={<DeleteOutlined />}
              title={t('admin.presetDeleteDenied')}
            >
              {t('admin.delete')}
            </Button>
          ) : (
            <Popconfirm
              title={t('admin.deleteConfirm')}
              onConfirm={() => handleDelete(record.id)}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                {t('admin.delete')}
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <Card
      title={t('admin.title')}
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          {t('admin.create')}
        </Button>
      }
    >
      <Input
        prefix={<SearchOutlined />}
        placeholder={t('selector.searchPlaceholder')}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        allowClear
        style={{ marginBottom: 16, maxWidth: 300 }}
      />

      <Table
        columns={columns}
        dataSource={filtered}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editingWorkflow ? t('admin.edit') : t('admin.create')}
        open={modalOpen}
        onCancel={handleModalCancel}
        onOk={handleSubmit}
        confirmLoading={submitting}
        destroyOnClose
        width={640}
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="name"
            label={t('admin.name')}
            rules={[{ required: true, message: t('admin.nameRequired') }]}
          >
            <Input />
          </Form.Item>

          <Form.Item name="name_en" label={t('admin.nameEn')}>
            <Input />
          </Form.Item>

          <Form.Item name="description" label={t('admin.description')}>
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="description_en" label={t('admin.descriptionEn')}>
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="skill_ids" label={t('admin.skills')}>
            <Select
              mode="tags"
              placeholder={t('admin.selectSkills')}
              allowClear
            />
          </Form.Item>

          <Form.Item name="output_modes" label={t('admin.outputModes')}>
            <Select
              mode="multiple"
              placeholder={t('admin.outputModes')}
              allowClear
              options={OUTPUT_MODES.map((m) => ({ label: m, value: m }))}
            />
          </Form.Item>

          <Form.Item
            name="visible_roles"
            label={t('admin.visibleRoles')}
            rules={[{ required: true, message: t('admin.rolesRequired'), type: 'array', min: 1 }]}
          >
            <Select
              mode="multiple"
              placeholder={t('admin.selectRoles')}
              allowClear
              options={ROLES.map((r) => ({ label: t(`roles.${r}`), value: r }))}
            />
          </Form.Item>

          <Form.Item name="preset_prompt" label={t('admin.presetPrompt')}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default WorkflowAdmin;
