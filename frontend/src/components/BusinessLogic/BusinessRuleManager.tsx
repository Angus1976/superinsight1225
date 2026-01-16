// 业务规则管理组件
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['businessLogic', 'common']);
  const [selectedRule, setSelectedRule] = useState<BusinessRule | null>(null);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 规则类型选项
  const ruleTypeOptions = [
    { value: 'sentiment_rule', label: t('rules.types.sentimentRule') },
    { value: 'keyword_rule', label: t('rules.types.keywordRule') },
    { value: 'temporal_rule', label: t('rules.types.temporalRule') },
    { value: 'behavioral_rule', label: t('rules.types.behavioralRule') },
  ];

  // 规则类型映射
  const ruleTypeKeyMap: Record<string, string> = {
    sentiment_rule: 'sentimentRule',
    keyword_rule: 'keywordRule',
    temporal_rule: 'temporalRule',
    behavioral_rule: 'behavioralRule',
  };

  // 获取规则类型配置
  const getRuleTypeConfig = (type: string) => {
    const configs: Record<string, { color: string }> = {
      sentiment_rule: { color: 'blue' },
      keyword_rule: { color: 'green' },
      temporal_rule: { color: 'orange' },
      behavioral_rule: { color: 'purple' },
    };
    const config = configs[type] || { color: 'default' };
    const typeKey = ruleTypeKeyMap[type] || type;
    return { ...config, text: t(`rules.types.${typeKey}`, type) };
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
      
      message.success(t('rules.messages.createSuccess'));
      setCreateModalVisible(false);
      form.resetFields();
    } catch (error) {
      console.error('创建规则失败:', error);
      message.error(t('rules.messages.createError'));
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
      
      message.success(t('rules.messages.updateSuccess'));
      setEditModalVisible(false);
      form.resetFields();
    } catch (error) {
      console.error('更新规则失败:', error);
      message.error(t('rules.messages.updateError'));
    } finally {
      setLoading(false);
    }
  };

  // 删除规则
  const handleDeleteRule = async (rule: BusinessRule) => {
    try {
      const updatedRules = rules.filter(r => r.id !== rule.id);
      onRulesChange(updatedRules);
      message.success(t('rules.messages.deleteSuccess'));
    } catch (error) {
      console.error('删除规则失败:', error);
      message.error(t('rules.messages.deleteError'));
    }
  };

  // 切换规则状态
  const handleToggleRule = async (rule: BusinessRule) => {
    try {
      const updatedRule = { ...rule, is_active: !rule.is_active };
      const updatedRules = rules.map(r => r.id === rule.id ? updatedRule : r);
      onRulesChange(updatedRules);
      
      message.success(t('rules.messages.toggleSuccess', { status: updatedRule.is_active ? t('rules.status.active') : t('rules.status.inactive') }));
    } catch (error) {
      console.error('切换规则状态失败:', error);
      message.error(t('rules.messages.toggleError'));
    }
  };

  // 复制规则
  const handleCopyRule = (rule: BusinessRule) => {
    const copiedRule: BusinessRule = {
      ...rule,
      id: `rule_${Date.now()}`,
      name: `${rule.name} (${t('rules.copy')})`,
      frequency: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const updatedRules = [...rules, copiedRule];
    onRulesChange(updatedRules);
    message.success(t('rules.messages.copySuccess'));
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
      title: t('rules.columns.ruleName'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: BusinessRule) => (
        <Space>
          <Text strong>{text}</Text>
          {!record.is_active && <Badge status="default" text={t('rules.status.disabled')} />}
        </Space>
      ),
    },
    {
      title: t('rules.columns.type'),
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
      title: t('rules.columns.confidence'),
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
      title: t('rules.columns.frequency'),
      dataIndex: 'frequency',
      key: 'frequency',
      sorter: (a: BusinessRule, b: BusinessRule) => a.frequency - b.frequency,
    },
    {
      title: t('rules.columns.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Badge 
          status={isActive ? 'success' : 'default'} 
          text={isActive ? t('rules.status.active') : t('rules.status.inactive')} 
        />
      ),
      filters: [
        { text: t('rules.status.active'), value: true },
        { text: t('rules.status.inactive'), value: false },
      ],
      onFilter: (value: any, record: BusinessRule) => record.is_active === value,
    },
    {
      title: t('rules.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
      sorter: (a: BusinessRule, b: BusinessRule) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: t('rules.columns.actions'),
      key: 'actions',
      render: (_, record: BusinessRule) => (
        <Space>
          <Tooltip title={t('rules.actions.viewDetail')}>
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => viewRuleDetail(record)}
            />
          </Tooltip>
          <Tooltip title={t('rules.actions.editRule')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => editRule(record)}
            />
          </Tooltip>
          <Tooltip title={t('rules.actions.copyRule')}>
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={() => handleCopyRule(record)}
            />
          </Tooltip>
          <Tooltip title={record.is_active ? t('rules.actions.deactivateRule') : t('rules.actions.activateRule')}>
            <Button
              type="text"
              icon={record.is_active ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleToggleRule(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('rules.messages.deleteConfirm')}
            onConfirm={() => handleDeleteRule(record)}
            okText={t('common:confirm')}
            cancelText={t('common:cancel')}
          >
            <Tooltip title={t('rules.actions.deleteRule')}>
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
            {t('rules.createRule')}
          </Button>
          <Button icon={<SettingOutlined />}>
            {t('rules.batchOperation')}
          </Button>
        </Space>
      </Card>

      {/* 规则列表 */}
      <Card title={`${t('rules.listTitle')} (${rules.length})`}>
        <Table
          dataSource={rules}
          columns={columns}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => t('rules.pagination.total', { start: range[0], end: range[1], total }),
          }}
        />
      </Card>

      {/* 创建规则模态框 */}
      <Modal
        title={t('rules.createBusinessRule')}
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
            label={t('rules.form.ruleName')}
            rules={[{ required: true, message: t('rules.form.ruleNameRequired') }]}
          >
            <Input placeholder={t('rules.form.ruleNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="rule_type"
            label={t('rules.form.ruleType')}
            rules={[{ required: true, message: t('rules.form.ruleTypeRequired') }]}
          >
            <Select placeholder={t('rules.form.ruleTypePlaceholder')}>
              {ruleTypeOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="pattern"
            label={t('rules.form.rulePattern')}
            rules={[{ required: true, message: t('rules.form.rulePatternRequired') }]}
          >
            <TextArea
              rows={3}
              placeholder={t('rules.form.rulePatternPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('rules.form.ruleDescription')}
          >
            <TextArea
              rows={2}
              placeholder={t('rules.form.ruleDescriptionPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="confidence"
            label={t('rules.form.initialConfidence')}
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
            label={t('rules.form.activeStatus')}
            valuePropName="checked"
          >
            <Switch checkedChildren={t('rules.status.active')} unCheckedChildren={t('rules.status.inactive')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑规则模态框 */}
      <Modal
        title={t('rules.editRule')}
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
            label={t('rules.form.ruleName')}
            rules={[{ required: true, message: t('rules.form.ruleNameRequired') }]}
          >
            <Input placeholder={t('rules.form.ruleNamePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="rule_type"
            label={t('rules.form.ruleType')}
            rules={[{ required: true, message: t('rules.form.ruleTypeRequired') }]}
          >
            <Select placeholder={t('rules.form.ruleTypePlaceholder')}>
              {ruleTypeOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="pattern"
            label={t('rules.form.rulePattern')}
            rules={[{ required: true, message: t('rules.form.rulePatternRequired') }]}
          >
            <TextArea
              rows={3}
              placeholder={t('rules.form.rulePatternPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('rules.form.ruleDescription')}
          >
            <TextArea
              rows={2}
              placeholder={t('rules.form.ruleDescriptionPlaceholder')}
            />
          </Form.Item>

          <Form.Item
            name="confidence"
            label={t('rules.columns.confidence')}
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
            label={t('rules.form.activeStatus')}
            valuePropName="checked"
          >
            <Switch checkedChildren={t('rules.status.active')} unCheckedChildren={t('rules.status.inactive')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 规则详情模态框 */}
      <Modal
        title={t('rules.ruleDetail')}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            {t('common:common.close')}
          </Button>,
        ]}
      >
        {selectedRule && (
          <div>
            <Descriptions title={t('rules.detail.basicInfo')} bordered column={2}>
              <Descriptions.Item label={t('rules.detail.ruleId')}>
                {selectedRule.id}
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.form.ruleName')}>
                {selectedRule.name}
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.form.ruleType')}>
                <Tag color={getRuleTypeConfig(selectedRule.rule_type).color}>
                  {getRuleTypeConfig(selectedRule.rule_type).text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.columns.status')}>
                <Badge 
                  status={selectedRule.is_active ? 'success' : 'default'} 
                  text={selectedRule.is_active ? t('rules.status.active') : t('rules.status.inactive')} 
                />
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.columns.confidence')} span={2}>
                <Progress
                  percent={Math.round(selectedRule.confidence * 100)}
                  status={selectedRule.confidence >= 0.8 ? 'success' : 'normal'}
                />
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.columns.frequency')}>
                {selectedRule.frequency}
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.columns.createdAt')}>
                {new Date(selectedRule.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.columns.updatedAt')} span={2}>
                {new Date(selectedRule.updated_at).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            <Card title={t('rules.detail.rulePattern')} style={{ marginTop: 16 }}>
              <Paragraph>
                <Text code>{selectedRule.pattern}</Text>
              </Paragraph>
            </Card>

            {selectedRule.description && (
              <Card title={t('rules.detail.ruleDescription')} style={{ marginTop: 16 }}>
                <Paragraph>{selectedRule.description}</Paragraph>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};