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
import type { ColumnsType } from 'antd/es/table';
import { qualityApi, type QualityRule, type QualityRuleTemplate } from '@/services/qualityApi';

const { Option } = Select;
const { TextArea } = Input;

interface RuleConfigProps {
  projectId: string;
}

const RuleConfig: React.FC<RuleConfigProps> = ({ projectId }) => {
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
      message.error('加载规则失败');
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
      message.success('规则已删除');
      loadRules();
    } catch {
      message.error('删除失败');
    }
  };

  const handleToggle = async (rule: QualityRule) => {
    try {
      await qualityApi.updateRule(rule.id, { enabled: !rule.enabled });
      message.success(rule.enabled ? '规则已禁用' : '规则已启用');
      loadRules();
    } catch {
      message.error('操作失败');
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule) {
        await qualityApi.updateRule(editingRule.id, values);
        message.success('规则已更新');
      } else {
        await qualityApi.createRule({ ...values, project_id: projectId });
        message.success('规则已创建');
      }
      setModalVisible(false);
      loadRules();
    } catch {
      message.error('保存失败');
    }
  };

  const handleCreateFromTemplate = async (template: QualityRuleTemplate) => {
    try {
      await qualityApi.createRuleFromTemplate(template.id, projectId);
      message.success('从模板创建规则成功');
      setTemplateDrawerVisible(false);
      loadRules();
    } catch {
      message.error('创建失败');
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
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{name}</span>
          {record.rule_type === 'custom' && <Tag color="purple">自定义</Tag>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 70,
      render: (v: number) => `v${v}`,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record) => (
        <Switch checked={enabled} size="small" onChange={() => handleToggle(record)} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="复制">
            <Button
              type="link"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => {
                setEditingRule(null);
                form.setFieldsValue({ ...record, id: undefined, name: `${record.name} (副本)` });
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="版本历史">
            <Button type="link" size="small" icon={<HistoryOutlined />} />
          </Tooltip>
          <Popconfirm title="确定删除此规则？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="质量规则配置"
        extra={
          <Space>
            <Button icon={<CopyOutlined />} onClick={() => setTemplateDrawerVisible(true)}>
              从模板创建
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              添加规则
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
        title={editingRule ? '编辑规则' : '添加规则'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
            <Input placeholder="请输入规则名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="请输入规则描述" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="rule_type" label="规则类型" rules={[{ required: true }]}>
                <Select placeholder="选择类型">
                  <Option value="builtin">内置规则</Option>
                  <Option value="custom">自定义规则</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="severity" label="严重程度" rules={[{ required: true }]}>
                <Select placeholder="选择严重程度">
                  <Option value="critical">严重</Option>
                  <Option value="high">高</Option>
                  <Option value="medium">中</Option>
                  <Option value="low">低</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="priority" label="优先级">
                <InputNumber min={0} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.rule_type !== curr.rule_type}>
            {({ getFieldValue }) =>
              getFieldValue('rule_type') === 'custom' && (
                <Form.Item name="script" label="自定义脚本">
                  <TextArea rows={6} placeholder="输入 Python 脚本" style={{ fontFamily: 'monospace' }} />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* 模板抽屉 */}
      <Drawer
        title="规则模板"
        open={templateDrawerVisible}
        onClose={() => setTemplateDrawerVisible(false)}
        width={500}
      >
        <Alert message="选择模板快速创建规则" type="info" showIcon style={{ marginBottom: 16 }} />
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
                使用此模板
              </Button>,
            ]}
          >
            <Card.Meta
              title={
                <Space>
                  {template.name}
                  <Tag color={getSeverityColor(template.severity)}>{template.severity}</Tag>
                </Space>
              }
              description={template.description}
            />
          </Card>
        ))}
        {templates.length === 0 && (
          <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>暂无可用模板</div>
        )}
      </Drawer>
    </div>
  );
};

export default RuleConfig;
