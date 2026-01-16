/**
 * Rule Configuration Component - 规则配置组件
 * 实现质量规则的 CRUD 操作和配置界面
 */

import React, { useState, useEffect } from 'react';
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
  InputNumber,
  message,
  Tooltip,
  Popconfirm,
  Drawer,
  Tabs,
  Alert,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CopyOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import { qualityApi, type QualityRule, type QualityRuleTemplate } from '@/services/qualityApi';

const { Option } = Select;
const { TextArea } = Input;

interface RuleConfigProps {
  projectId: string;
}

const RuleConfig: React.FC<RuleConfigProps> = ({ projectId }) => {
  const { t } = useTranslation(['quality', 'common']);
  const [rules, setRules] = useState<QualityRule[]>([]);
  const [templates, setTemplates] = useState<QualityRuleTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [templateDrawerVisible, setTemplateDrawerVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<QualityRule | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRules();
    loadTemplates();
  }, [projectId]);

  const loadRules = async () => {
    setLoading(true);
    try {
      const data = await qualityApi.listRules(projectId);
      setRules(data);
    } catch (error) {
      message.error(t('messages.loadRulesFailed'));
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await qualityApi.listTemplates();
      setTemplates(data);
    } catch {
      // Templates are optional
    }
  };

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({ project_id: projectId, enabled: true, priority: 50 });
    setModalVisible(true);
  };

  const handleEdit = (rule: QualityRule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setModalVisible(true);
  };

  const handleDelete = async (ruleId: string) => {
    try {
      await qualityApi.deleteRule(ruleId);
      message.success(t('messages.ruleDeleted'));
      loadRules();
    } catch {
      message.error(t('messages.ruleDeleteFailed'));
    }
  };

  const handleToggle = async (rule: QualityRule) => {
    try {
      await qualityApi.updateRule(rule.id, { enabled: !rule.enabled });
      message.success(rule.enabled ? t('messages.ruleDisabled') : t('messages.ruleEnabled'));
      loadRules();
    } catch {
      message.error(t('messages.ruleStatusUpdateFailed'));
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule) {
        await qualityApi.updateRule(editingRule.id, values);
        message.success(t('messages.ruleUpdated'));
      } else {
        await qualityApi.createRule({ ...values, project_id: projectId });
        message.success(t('messages.ruleCreated'));
      }
      setModalVisible(false);
      loadRules();
    } catch {
      message.error(editingRule ? t('messages.ruleUpdateFailed') : t('messages.ruleCreateFailed'));
    }
  };

  const handleCreateFromTemplate = async (template: QualityRuleTemplate) => {
    try {
      await qualityApi.createRuleFromTemplate(template.id, projectId);
      message.success(t('messages.templateCreateSuccess'));
      setTemplateDrawerVisible(false);
      loadRules();
    } catch {
      message.error(t('messages.createFailed'));
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'red',
      high: 'orange',
      medium: 'gold',
      low: 'blue',
    };
    return colors[severity] || 'default';
  };

  const columns: ColumnsType<QualityRule> = [
    {
      title: t('rules.name'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{name}</span>
          {record.rule_type === 'custom' && <Tag color="purple">{t('rules.types.custom')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('rules.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('rules.severity'),
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{t(`rules.severities.${severity}`)}</Tag>
      ),
    },
    {
      title: t('rules.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: t('rules.version'),
      dataIndex: 'version',
      key: 'version',
      width: 70,
      render: (v: number) => `v${v}`,
    },
    {
      title: t('common:status'),
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record) => (
        <Switch checked={enabled} size="small" onChange={() => handleToggle(record)} />
      ),
    },
    {
      title: t('common:actions'),
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('common:edit')}>
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title={t('rules.copy')}>
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => {
                setEditingRule(null);
                form.setFieldsValue({ ...record, id: undefined, name: t('rules.copyName', { name: record.name }) });
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('rules.versionHistory')}>
            <Button type="link" size="small" icon={<HistoryOutlined />} />
          </Tooltip>
          <Popconfirm title={t('rules.confirmDelete')} onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={t('rules.config')}
        extra={
          <Space>
            <Button icon={<CopyOutlined />} onClick={() => setTemplateDrawerVisible(true)}>
              {t('rules.createFromTemplate')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('rules.addRule')}
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={rules}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 规则编辑弹窗 */}
      <Modal
        title={editingRule ? t('rules.editRule') : t('rules.addRule')}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('rules.name')} rules={[{ required: true, message: t('rules.inputRuleName') }]}>
            <Input placeholder={t('rules.inputRuleName')} />
          </Form.Item>
          <Form.Item name="description" label={t('rules.description')}>
            <TextArea rows={2} placeholder={t('rules.inputRuleDesc')} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="rule_type" label={t('rules.type')} rules={[{ required: true }]}>
                <Select placeholder={t('rules.selectRuleType')}>
                  <Option value="builtin">{t('rules.types.builtin')}</Option>
                  <Option value="custom">{t('rules.types.custom')}</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="severity" label={t('rules.severity')} rules={[{ required: true }]}>
                <Select placeholder={t('rules.selectPriority')}>
                  <Option value="critical">{t('rules.severities.critical')}</Option>
                  <Option value="high">{t('rules.severities.high')}</Option>
                  <Option value="medium">{t('rules.severities.medium')}</Option>
                  <Option value="low">{t('rules.severities.low')}</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="priority" label={t('rules.priority')}>
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.rule_type !== curr.rule_type}>
            {({ getFieldValue }) =>
              getFieldValue('rule_type') === 'custom' && (
                <Form.Item name="script" label={t('rules.customScript')}>
                  <TextArea rows={6} placeholder={t('rules.inputPythonScript')} style={{ fontFamily: 'monospace' }} />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item name="enabled" label={t('rules.enabledStatus')} valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 模板抽屉 */}
      <Drawer
        title={t('rules.templates.title')}
        open={templateDrawerVisible}
        onClose={() => setTemplateDrawerVisible(false)}
        width={500}
      >
        <Alert message={t('rules.templates.selectHint')} type="info" showIcon style={{ marginBottom: 16 }} />
        {templates.map((template) => (
          <Card
            key={template.id}
            size="small"
            style={{ marginBottom: 12 }}
            actions={[
              <Button
                key="use"
                type="link"
                icon={<PlayCircleOutlined />}
                onClick={() => handleCreateFromTemplate(template)}
              >
                {t('rules.templates.useTemplate')}
              </Button>,
            ]}
          >
            <Card.Meta
              title={
                <Space>
                  {template.name}
                  <Tag color={getSeverityColor(template.severity)}>{t(`rules.severities.${template.severity}`)}</Tag>
                </Space>
              }
              description={template.description}
            />
          </Card>
        ))}
        {templates.length === 0 && (
          <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>{t('rules.templates.noTemplates')}</div>
        )}
      </Drawer>
    </div>
  );
};

export default RuleConfig;
