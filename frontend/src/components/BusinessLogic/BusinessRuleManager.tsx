// 业务规则管理组件
import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Progress,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Typography,
  Tooltip,
  Popconfirm,
  message,
  Descriptions,
  List,
  Badge,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CopyOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface BusinessRuleManagerProps {
  projectId: string;
  rules: BusinessRule[];
  onRulesChange: (rules: BusinessRule[]) => void;
}

interface BusinessRule {
  id: string;
  name: string;
  description: string;
  pattern: string;
  rule_type: string;
  confidence: number;
  frequency: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const BusinessRuleManager: React.FC<BusinessRuleManagerProps> = ({
  projectId,
  rules,
  onRulesChange,
}) => {
  const [selectedRule, setSelectedRule] = useState<BusinessRule | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 规则类型选项
  const ruleTypeOptions = [
    { value: 'sentiment_rule', label: '情感规则' },
    { value: 'keyword_rule', label: '关键词规则' },
    { value: 'temporal_rule', label: '时间规则' },
    { value: 'behavioral_rule', label: '行为规则' },
  ];

  // 获取规则类型配置
  const getRuleTypeConfig = (type: string) => {
    const configs: Record<string, { color: string; text: string }> = {
      sentiment_rule: { color: 'blue', text: '情感规则' },
      keyword_rule: { color: 'green', text: '关键词规则' },
      temporal_rule: { color: 'orange', text: '时间规则' },
      behavioral_rule: { color: 'purple', text: '行为规则' },
    };
    return configs[type] || { color: 'default', text: type };
  };

  // 创建规则
  const handleCreateRule = async (values: any) => {
    setLoading(true);
    try {
      // 模拟创建规则API调用
      const newRule: BusinessRule = {
        id: `rule_${Date.now()}`,
        name: values.name,
        description: values.description,
        pattern: values.pattern,
        rule_type: values.rule_type,
        confidence: values.confidence || 0.8,
        frequency: 0,
        is_active: values.is_active !== false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      const updatedRules = [...rules, newRule];
      onRulesChange(updatedRules);
      
      message.success('规则创建成功');
      setCreateModalVisible(false);
      form.resetFields();
    } catch (error) {
      console.error('创建规则失败:', error);
      message.error('创建规则失败');
    } finally {
      setLoading(false);
    }
  };

  // 编辑规则
  const handleEditRule = async (values: any) => {
    if (!selectedRule) return;

    setLoading(true);
    try {
      const updatedRule: BusinessRule = {
        ...selectedRule,
        name: values.name,
        description: values.description,
        pattern: values.pattern,
        rule_type: values.rule_type,
        confidence: values.confidence,
        is_active: values.is_active,
        updated_at: new Date().toISOString(),
      };

      const updatedRules = rules.map(rule => 
        rule.id === selectedRule.id ? updatedRule : rule
      );
      onRulesChange(updatedRules);
      
      message.success('规则更新成功');
      setEditModalVisible(false);
      form.resetFields();
    } catch (error) {
      console.error('更新规则失败:', error);
      message.error('更新规则失败');
    } finally {
      setLoading(false);
    }
  };

  // 删除规则
  const handleDeleteRule = async (rule: BusinessRule) => {
    try {
      const updatedRules = rules.filter(r => r.id !== rule.id);
      onRulesChange(updatedRules);
      message.success('规则删除成功');
    } catch (error) {
      console.error('删除规则失败:', error);
      message.error('删除规则失败');
    }
  };

  // 切换规则状态
  const handleToggleRule = async (rule: BusinessRule) => {
    try {
      const updatedRule = { ...rule, is_active: !rule.is_active };
      const updatedRules = rules.map(r => r.id === rule.id ? updatedRule : r);
      onRulesChange(updatedRules);
      
      message.success(`规则已${updatedRule.is_active ? '激活' : '停用'}`);
    } catch (error) {
      console.error('切换规则状态失败:', error);
      message.error('切换规则状态失败');
    }
  };

  // 复制规则
  const handleCopyRule = (rule: BusinessRule) => {
    const copiedRule: BusinessRule = {
      ...rule,
      id: `rule_${Date.now()}`,
      name: `${rule.name} (副本)`,
      frequency: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const updatedRules = [...rules, copiedRule];
    onRulesChange(updatedRules);
    message.success('规则复制成功');
  };

  // 查看规则详情
  const viewRuleDetail = (rule: BusinessRule) => {
    setSelectedRule(rule);
    setDetailModalVisible(true);
  };

  // 编辑规则
  const editRule = (rule: BusinessRule) => {
    setSelectedRule(rule);
    form.setFieldsValue({
      name: rule.name,
      description: rule.description,
      pattern: rule.pattern,
      rule_type: rule.rule_type,
      confidence: rule.confidence,
      is_active: rule.is_active,
    });
    setEditModalVisible(true);
  };

  // 表格列定义
  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: BusinessRule) => (
        <Space>
          <Text strong>{text}</Text>
          {!record.is_active && <Badge status="default" text="已停用" />}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      render: (type: string) => {
        const config = getRuleTypeConfig(type);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
      filters: ruleTypeOptions.map(option => ({
        text: option.label,
        value: option.value,
      })),
      onFilter: (value: any, record: BusinessRule) => record.rule_type === value,
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => (
        <Space>
          <Progress
            percent={Math.round(confidence * 100)}
            size="small"
            status={confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'normal' : 'exception'}
            style={{ width: 80 }}
          />
          <Text>{(confidence * 100).toFixed(1)}%</Text>
        </Space>
      ),
      sorter: (a: BusinessRule, b: BusinessRule) => a.confidence - b.confidence,
    },
    {
      title: '频率',
      dataIndex: 'frequency',
      key: 'frequency',
      sorter: (a: BusinessRule, b: BusinessRule) => a.frequency - b.frequency,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Badge 
          status={isActive ? 'success' : 'default'} 
          text={isActive ? '激活' : '停用'} 
        />
      ),
      filters: [
        { text: '激活', value: true },
        { text: '停用', value: false },
      ],
      onFilter: (value: any, record: BusinessRule) => record.is_active === value,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
      sorter: (a: BusinessRule, b: BusinessRule) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: BusinessRule) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => viewRuleDetail(record)}
            />
          </Tooltip>
          <Tooltip title="编辑规则">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => editRule(record)}
            />
          </Tooltip>
          <Tooltip title="复制规则">
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={() => handleCopyRule(record)}
            />
          </Tooltip>
          <Tooltip title={record.is_active ? '停用规则' : '激活规则'}>
            <Button
              type="text"
              icon={record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleToggleRule(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个规则吗？"
            onConfirm={() => handleDeleteRule(record)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除规则">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            创建规则
          </Button>
          <Button icon={<SettingOutlined />}>
            批量操作
          </Button>
        </Space>
      </Card>

      {/* 规则列表 */}
      <Card title={`业务规则列表 (${rules.length})`}>
        <Table
          dataSource={rules}
          columns={columns}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 创建规则模态框 */}
      <Modal
        title="创建业务规则"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={loading}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateRule}
          initialValues={{
            confidence: 0.8,
            is_active: true,
          }}
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="请输入规则名称" />
          </Form.Item>

          <Form.Item
            name="rule_type"
            label="规则类型"
            rules={[{ required: true, message: '请选择规则类型' }]}
          >
            <Select placeholder="请选择规则类型">
              {ruleTypeOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="pattern"
            label="规则模式"
            rules={[{ required: true, message: '请输入规则模式' }]}
          >
            <TextArea
              rows={3}
              placeholder="请输入规则模式，例如：IF text CONTAINS ['excellent', 'great'] THEN sentiment = 'positive'"
            />
          </Form.Item>

          <Form.Item
            name="description"
            label="规则描述"
          >
            <TextArea
              rows={2}
              placeholder="请输入规则描述"
            />
          </Form.Item>

          <Form.Item
            name="confidence"
            label="初始置信度"
          >
            <InputNumber
              min={0.1}
              max={1.0}
              step={0.1}
              style={{ width: '100%' }}
              formatter={(value) => `${((value as number) * 100).toFixed(0)}%`}
              parser={(value) => (parseFloat(value?.replace('%', '') || '0') / 100)}
            />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="激活状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="激活" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑规则模态框 */}
      <Modal
        title="编辑业务规则"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={loading}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleEditRule}
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="请输入规则名称" />
          </Form.Item>

          <Form.Item
            name="rule_type"
            label="规则类型"
            rules={[{ required: true, message: '请选择规则类型' }]}
          >
            <Select placeholder="请选择规则类型">
              {ruleTypeOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="pattern"
            label="规则模式"
            rules={[{ required: true, message: '请输入规则模式' }]}
          >
            <TextArea
              rows={3}
              placeholder="请输入规则模式"
            />
          </Form.Item>

          <Form.Item
            name="description"
            label="规则描述"
          >
            <TextArea
              rows={2}
              placeholder="请输入规则描述"
            />
          </Form.Item>

          <Form.Item
            name="confidence"
            label="置信度"
          >
            <InputNumber
              min={0.1}
              max={1.0}
              step={0.1}
              style={{ width: '100%' }}
              formatter={(value) => `${((value as number) * 100).toFixed(0)}%`}
              parser={(value) => (parseFloat(value?.replace('%', '') || '0') / 100)}
            />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="激活状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="激活" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 规则详情模态框 */}
      <Modal
        title="规则详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {selectedRule && (
          <div>
            <Descriptions title="基本信息" bordered column={2}>
              <Descriptions.Item label="规则ID">
                {selectedRule.id}
              </Descriptions.Item>
              <Descriptions.Item label="规则名称">
                {selectedRule.name}
              </Descriptions.Item>
              <Descriptions.Item label="规则类型">
                <Tag color={getRuleTypeConfig(selectedRule.rule_type).color}>
                  {getRuleTypeConfig(selectedRule.rule_type).text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge 
                  status={selectedRule.is_active ? 'success' : 'default'} 
                  text={selectedRule.is_active ? '激活' : '停用'} 
                />
              </Descriptions.Item>
              <Descriptions.Item label="置信度" span={2}>
                <Progress
                  percent={Math.round(selectedRule.confidence * 100)}
                  status={selectedRule.confidence >= 0.8 ? 'success' : 'normal'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="频率">
                {selectedRule.frequency}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedRule.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间" span={2}>
                {new Date(selectedRule.updated_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Card title="规则模式" style={{ marginTop: 16 }}>
              <Paragraph>
                <Text code>{selectedRule.pattern}</Text>
              </Paragraph>
            </Card>

            {selectedRule.description && (
              <Card title="规则描述" style={{ marginTop: 16 }}>
                <Paragraph>{selectedRule.description}</Paragraph>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};