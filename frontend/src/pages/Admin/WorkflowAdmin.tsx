import React, { useEffect, useState, useCallback } from 'react';
import {
  Card, Table, Button, Modal, Form, Input, Select, Tag, Space,
  message, Popconfirm, Typography, Tree, Divider, Spin, Switch,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  getWorkflows, createWorkflow, updateWorkflow, deleteWorkflow,
  getAvailableDataSources, getOpenClawStatus,
} from '@/services/aiAssistantApi';
import type { WorkflowItem, AIDataSource, SkillInfo, DataSourceAuth } from '@/types/aiAssistant';

const { Text } = Typography;

const ROLES = ['admin', 'business_expert', 'annotator', 'viewer'];
const OUTPUT_MODES = ['merge', 'compare'];

// ---------------------------------------------------------------------------
// Helper: DataSourceAuth[] → tree checked keys
// ---------------------------------------------------------------------------
function authToCheckedKeys(auth: DataSourceAuth[]): string[] {
  const keys: string[] = [];
  for (const item of auth) {
    if (item.tables.length === 1 && item.tables[0] === '*') {
      keys.push(`ds:${item.source_id}`);
    } else {
      for (const tbl of item.tables) {
        keys.push(`tbl:${item.source_id}:${tbl}`);
      }
    }
  }
  return keys;
}

// ---------------------------------------------------------------------------
// Helper: tree checked keys → DataSourceAuth[]
// ---------------------------------------------------------------------------
function checkedKeysToAuth(checkedKeys: string[]): DataSourceAuth[] {
  const sourceMap = new Map<string, string[]>();
  for (const key of checkedKeys) {
    if (key.startsWith('ds:')) {
      sourceMap.set(key.slice(3), ['*']);
    } else if (key.startsWith('tbl:')) {
      const parts = key.split(':');
      const sourceId = parts[1];
      const table = parts.slice(2).join(':');
      if (sourceMap.get(sourceId)?.[0] === '*') continue;
      const existing = sourceMap.get(sourceId) || [];
      if (!existing.includes(table)) existing.push(table);
      sourceMap.set(sourceId, existing);
    } else if (key.startsWith('fld:')) {
      // field-level: roll up to table level
      const parts = key.split(':');
      const sourceId = parts[1];
      const table = parts[2];
      if (sourceMap.get(sourceId)?.[0] === '*') continue;
      const existing = sourceMap.get(sourceId) || [];
      if (!existing.includes(table)) existing.push(table);
      sourceMap.set(sourceId, existing);
    }
  }
  return Array.from(sourceMap.entries()).map(([source_id, tables]) => ({ source_id, tables }));
}

// ---------------------------------------------------------------------------
// Helper: translate skill name — if already Chinese keep it, else use i18n
// ---------------------------------------------------------------------------
function isChineseText(text: string): boolean {
  return /[\u4e00-\u9fff]/.test(text);
}

const WorkflowAdmin: React.FC = () => {
  const { t } = useTranslation('workflow');
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowItem | null>(null);
  const [searchText, setSearchText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // Helper: translate skill name
  const translateSkillName = (name: string): string => {
    if (isChineseText(name)) return name;
    const key = `skillNames.${name}`;
    const translated = t(key);
    return translated === key ? name : translated;
  };

  // --- Real data from backend ---
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [dataSources, setDataSources] = useState<AIDataSource[]>([]);
  const [dsCheckedKeys, setDsCheckedKeys] = useState<string[]>([]);
  const [metaLoading, setMetaLoading] = useState(false);

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

  const fetchMeta = useCallback(async () => {
    setMetaLoading(true);
    try {
      const [clawStatus, dsList] = await Promise.all([
        getOpenClawStatus(),
        getAvailableDataSources(),
      ]);
      setSkills(clawStatus.skills || []);
      setDataSources(dsList);
    } catch {
      // non-blocking
    } finally {
      setMetaLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkflows();
    fetchMeta();
  }, [fetchWorkflows, fetchMeta]);

  // ---------------------------------------------------------------------------
  // Build data source tree nodes (multi-level: source → tables → fields)
  // ---------------------------------------------------------------------------
  const translateTableName = (name: string): string => {
    const key = `tableNames.${name}`;
    const translated = t(key);
    return translated === key ? name : translated;
  };

  const dsTreeData = dataSources
    .filter((ds) => ds.enabled)
    .map((ds) => ({
      title: `${ds.label} (${ds.id})`,
      key: `ds:${ds.id}`,
      children: (ds.tables || []).map((tbl) => {
        const tblObj = typeof tbl === 'string' ? { id: tbl, label: tbl, fields: [] as string[] } : tbl;
        return {
          title: tblObj.label || translateTableName(tblObj.id),
          key: `tbl:${ds.id}:${tblObj.id}`,
          children: (tblObj.fields || []).map((field: string) => ({
            title: field,
            key: `fld:${ds.id}:${tblObj.id}:${field}`,
          })),
        };
      }),
    }));

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const openCreateModal = () => {
    setEditingWorkflow(null);
    form.resetFields();
    setDsCheckedKeys([]);
    setModalOpen(true);
  };

  const openEditModal = (record: WorkflowItem) => {
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
    setDsCheckedKeys(authToCheckedKeys(record.data_source_auth || []));
    setModalOpen(true);
  };

  const handleToggleStatus = async (record: WorkflowItem) => {
    const newStatus = record.status === 'enabled' ? 'disabled' : 'enabled';
    try {
      await updateWorkflow(record.id, { status: newStatus });
      message.success(t('admin.updateSuccess'));
      fetchWorkflows();
    } catch {
      message.error(t('errors.saveFailed'));
    }
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

      const payload = {
        ...values,
        data_source_auth: checkedKeysToAuth(dsCheckedKeys),
      };

      if (editingWorkflow) {
        await updateWorkflow(editingWorkflow.id, payload);
        message.success(t('admin.updateSuccess'));
      } else {
        await createWorkflow(payload);
        message.success(t('admin.createSuccess'));
      }

      setModalOpen(false);
      form.resetFields();
      setDsCheckedKeys([]);
      setEditingWorkflow(null);
      fetchWorkflows();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error(t('errors.saveFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleModalCancel = () => {
    setModalOpen(false);
    form.resetFields();
    setDsCheckedKeys([]);
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
  // Helper: render data_source_auth summary
  // ---------------------------------------------------------------------------
  const renderDsAuth = (auth: DataSourceAuth[]) => {
    if (!auth?.length) return <Text type="secondary">-</Text>;
    return (
      <Space size={4} wrap>
        {auth.map((a) => {
          const ds = dataSources.find((d) => d.id === a.source_id);
          const label = ds?.label || a.source_id;
          const suffix = a.tables[0] === '*' ? '' : ` (${a.tables.length})`;
          return <Tag key={a.source_id}>{label}{suffix}</Tag>;
        })}
      </Space>
    );
  };

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
      render: (_: string, record: WorkflowItem) => (
        <Switch
          checked={record.status === 'enabled'}
          checkedChildren={t('admin.enabled')}
          unCheckedChildren={t('admin.disabled')}
          onChange={() => handleToggleStatus(record)}
        />
      ),
    },
    {
      title: t('admin.skills'),
      dataIndex: 'skill_ids',
      key: 'skill_ids',
      width: 200,
      render: (ids: string[]) => {
        if (!ids?.length) return <Text type="secondary">{t('admin.noSkills')}</Text>;
        return (
          <Space size={4} wrap>
            {ids.map((id) => {
              const sk = skills.find((s) => s.id === id);
              return <Tag key={id}>{sk ? translateSkillName(sk.name) : id.slice(0, 8)}</Tag>;
            })}
          </Space>
        );
      },
    },
    {
      title: t('admin.dataSources'),
      dataIndex: 'data_source_auth',
      key: 'data_source_auth',
      width: 220,
      render: renderDsAuth,
    },
    {
      title: t('admin.visibleRoles'),
      dataIndex: 'visible_roles',
      key: 'visible_roles',
      render: (roles: string[]) => (
        <Space size={4} wrap>
          {roles?.map((role) => <Tag key={role}>{t(`roles.${role}`)}</Tag>)}
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
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditModal(record)}>
            {t('admin.edit')}
          </Button>
          {record.is_preset ? (
            <Button type="link" size="small" disabled icon={<DeleteOutlined />} title={t('admin.presetDeleteDenied')}>
              {t('admin.delete')}
            </Button>
          ) : (
            <Popconfirm title={t('admin.deleteConfirm')} onConfirm={() => handleDelete(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>{t('admin.delete')}</Button>
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
    <Spin spinning={metaLoading && !workflows.length}>
      <Card
        title={t('admin.title')}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            {t('admin.create')}
          </Button>
        }
      >
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder={t('selector.searchPlaceholder')}
            prefix={<SearchOutlined />}
            allowClear
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 260 }}
          />
        </Space>

        <Table<WorkflowItem>
          rowKey="id"
          columns={columns}
          dataSource={filtered}
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create / Edit Modal */}
      <Modal
        title={editingWorkflow ? t('admin.edit') : t('admin.create')}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleModalCancel}
        confirmLoading={submitting}
        width={640}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
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

          <Divider />

          {/* Skills */}
          <Form.Item name="skill_ids" label={t('admin.skills')}>
            <Select
              mode="multiple"
              placeholder={t('admin.selectSkills')}
              options={skills.map((s) => ({ label: `${translateSkillName(s.name)} (${s.version})`, value: s.id }))}
            />
          </Form.Item>

          {/* Data Source Auth (Tree) */}
          <Form.Item label={t('admin.dataSources')}>
            <Tree
              checkable
              checkedKeys={dsCheckedKeys}
              onCheck={(keys) => setDsCheckedKeys(keys as string[])}
              treeData={dsTreeData}
              defaultExpandAll
            />
            {!dsTreeData.length && <Text type="secondary">{t('admin.selectDataSources')}</Text>}
          </Form.Item>

          {/* Output Modes */}
          <Form.Item name="output_modes" label={t('admin.outputModes')}>
            <Select
              mode="multiple"
              options={OUTPUT_MODES.map((m) => ({ label: t(`outputModeOptions.${m}`), value: m }))}
            />
          </Form.Item>

          {/* Visible Roles */}
          <Form.Item
            name="visible_roles"
            label={t('admin.visibleRoles')}
            rules={[{ required: true, message: t('admin.rolesRequired') }]}
          >
            <Select
              mode="multiple"
              placeholder={t('admin.selectRoles')}
              options={ROLES.map((r) => ({ label: t(`roles.${r}`), value: r }))}
            />
          </Form.Item>

          {/* Preset Prompt */}
          <Form.Item name="preset_prompt" label={t('admin.presetPrompt')}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Spin>
  );
};

export default WorkflowAdmin;
