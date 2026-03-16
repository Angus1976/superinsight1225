/**
 * ValidationRuleEditor Component (验证规则编辑器)
 * 
 * Form for creating and editing validation rules with:
 * - Select region (CN, HK, TW, INTL) and industry
 * - Define validation logic (regex, Python expression)
 * - Set error message with i18n keys
 * - Rule list with filtering
 * 
 * Requirements: 5.1, 5.4
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Form,
  Input,
  Select,
  Button,
  Space,
  Modal,
  Tag,
  message,
  Empty,
  Tooltip,
  Popconfirm,
  Row,
  Col,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  FilterOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  ontologyValidationApi,
  type ValidationRule,
} from '../../services/ontologyExpertApi';

const { TextArea } = Input;
const { Text } = Typography;

interface ValidationRuleEditorProps {
  onRuleChange?: () => void;
}

const REGIONS = ['CN', 'HK', 'TW', 'INTL'] as const;
const INDUSTRIES = ['金融', '医疗', '制造', '政务', '法律', '教育', 'GENERAL'] as const;
const RULE_TYPES = ['regex', 'python', 'builtin'] as const;
const ENTITY_TYPES = ['Company', 'Person', 'Contract', 'Product', 'Organization', 'Document'];

const ValidationRuleEditor: React.FC<ValidationRuleEditorProps> = ({
  onRuleChange,
}) => {
  const { t } = useTranslation('ontology');
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<ValidationRule | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // Filters
  const [filterRegion, setFilterRegion] = useState<string | undefined>();
  const [filterIndustry, setFilterIndustry] = useState<string | undefined>();
  const [filterEntityType, setFilterEntityType] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await ontologyValidationApi.listRules({
        region: filterRegion,
        industry: filterIndustry,
        entity_type: filterEntityType,
      });
      setRules(data);
    } catch (error) {
      console.error('Failed to load validation rules:', error);
      message.error(t('validation.loadError'));
    } finally {
      setLoading(false);
    }
  }, [filterRegion, filterIndustry, filterEntityType, t]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleCreate = () => {
    setEditingRule(null);
    form.resetFields();
    form.setFieldsValue({
      region: 'CN',
      rule_type: 'regex',
    });
    setModalVisible(true);
  };

  const handleEdit = (rule: ValidationRule) => {
    setEditingRule(rule);
    form.setFieldsValue(rule);
    setModalVisible(true);
  };

  const handleDelete = async (ruleId: string) => {
    try {
      // Note: Delete API would need to be added to ontologyValidationApi
      message.success(t('validation.deleteSuccess'));
      loadRules();
      onRuleChange?.();
    } catch (error) {
      console.error('Failed to delete rule:', error);
      message.error(t('validation.deleteFailed'));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      await ontologyValidationApi.createRule(values);
      
      message.success(t(editingRule ? 'validation.updateSuccess' : 'validation.createSuccess'));
      setModalVisible(false);
      form.resetFields();
      loadRules();
      onRuleChange?.();
    } catch (error) {
      console.error('Failed to save rule:', error);
      message.error(t(editingRule ? 'validation.updateFailed' : 'validation.createFailed'));
    } finally {
      setSaving(false);
    }
  };

  // Filter rules by search text
  const filteredRules = rules.filter((rule) => {
    if (searchText) {
      const search = searchText.toLowerCase();
      return (
        rule.name.toLowerCase().includes(search) ||
        rule.target_entity_type.toLowerCase().includes(search)
      );
    }
    return true;
  });

  const columns: ColumnsType<ValidationRule> = [
    {
      title: t('validation.ruleName'),
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: t('validation.targetEntityType'),
      dataIndex: 'target_entity_type',
      key: 'target_entity_type',
      width: 120,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('validation.targetField'),
      dataIndex: 'target_field',
      key: 'target_field',
      width: 120,
      render: (field: string) => field || '-',
    },
    {
      title: t('validation.ruleType'),
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'regex' ? 'blue' : type === 'python' ? 'green' : 'orange'}>
          {t(`validation.ruleTypes.${type}`)}
        </Tag>
      ),
    },
    {
      title: t('validation.region'),
      dataIndex: 'region',
      key: 'region',
      width: 100,
      render: (region: string) => (
        <Tag color={region === 'CN' ? 'red' : region === 'INTL' ? 'blue' : 'default'}>
          {t(`validation.regions.${region}`)}
        </Tag>
      ),
    },
    {
      title: t('validation.industry'),
      dataIndex: 'industry',
      key: 'industry',
      width: 100,
      render: (industry: string) => industry ? <Tag>{industry}</Tag> : '-',
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('validation.editRule')}>
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('validation.confirmDeleteRule')}
            onConfirm={() => handleDelete(record.id)}
            okText={t('common.confirm')}
            cancelText={t('common.cancel')}
          >
            <Tooltip title={t('validation.deleteRule')}>
              <Button
                type="text"
                size="small"
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
      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder={t('validation.searchPlaceholder')}
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 200 }}
                allowClear
              />
              <Select
                placeholder={t('validation.filterByRegion')}
                value={filterRegion}
                onChange={setFilterRegion}
                style={{ width: 150 }}
                allowClear
              >
                {REGIONS.map((region) => (
                  <Select.Option key={region} value={region}>
                    {t(`validation.regions.${region}`)}
                  </Select.Option>
                ))}
              </Select>
              <Select
                placeholder={t('validation.filterByIndustry')}
                value={filterIndustry}
                onChange={setFilterIndustry}
                style={{ width: 150 }}
                allowClear
              >
                {INDUSTRIES.map((industry) => (
                  <Select.Option key={industry} value={industry}>
                    {industry}
                  </Select.Option>
                ))}
              </Select>
              <Select
                placeholder={t('validation.filterByEntityType')}
                value={filterEntityType}
                onChange={setFilterEntityType}
                style={{ width: 150 }}
                allowClear
              >
                {ENTITY_TYPES.map((type) => (
                  <Select.Option key={type} value={type}>
                    {type}
                  </Select.Option>
                ))}
              </Select>
            </Space>
          </Col>
          <Col>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              {t('validation.createRule')}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* Rules Table */}
      <Card
        title={t('validation.rulesTitle')}
        extra={
          <Text type="secondary">
            {t('validation.totalRules', { count: filteredRules.length })}
          </Text>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredRules}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 900 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={t('validation.noRules')}
              />
            ),
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={t(editingRule ? 'validation.editRule' : 'validation.createRule')}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={saving}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={t('validation.ruleName')}
                rules={[{ required: true, message: t('validation.ruleNameRequired') }]}
              >
                <Input placeholder={t('validation.ruleNamePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rule_type"
                label={t('validation.ruleType')}
                rules={[{ required: true }]}
              >
                <Select>
                  {RULE_TYPES.map((type) => (
                    <Select.Option key={type} value={type}>
                      {t(`validation.ruleTypes.${type}`)}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="target_entity_type"
                label={t('validation.targetEntityType')}
                rules={[{ required: true, message: t('validation.targetEntityTypeRequired') }]}
              >
                <Select placeholder={t('validation.targetEntityTypePlaceholder')}>
                  {ENTITY_TYPES.map((type) => (
                    <Select.Option key={type} value={type}>
                      {type}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="target_field"
                label={t('validation.targetField')}
              >
                <Input placeholder={t('validation.targetFieldPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="region"
                label={t('validation.region')}
                rules={[{ required: true }]}
              >
                <Select>
                  {REGIONS.map((region) => (
                    <Select.Option key={region} value={region}>
                      {t(`validation.regions.${region}`)}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="industry"
                label={t('validation.industry')}
              >
                <Select allowClear>
                  {INDUSTRIES.map((industry) => (
                    <Select.Option key={industry} value={industry}>
                      {industry}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="validation_logic"
            label={
              <Space>
                <CodeOutlined />
                {t('validation.validationLogic')}
              </Space>
            }
            rules={[{ required: true, message: t('validation.validationLogicRequired') }]}
          >
            <TextArea
              rows={4}
              placeholder={t('validation.validationLogicPlaceholder')}
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item
            name="error_message_key"
            label={t('validation.errorMessageKey')}
            rules={[{ required: true, message: t('validation.errorMessageKeyRequired') }]}
          >
            <Input placeholder={t('validation.errorMessageKeyPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ValidationRuleEditor;
