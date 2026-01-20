/**
 * Data Classification Page
 * 
 * Manage data classification and sensitivity levels.
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
  Row,
  Col,
  Statistic,
  Progress,
  message,
  Descriptions,
  Tooltip,
  Alert,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  SyncOutlined,
  FileSearchOutlined,
  RobotOutlined,
  EditOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  dataPermissionApi,
  DataClassification,
  ClassificationRule,
  SensitivityLevel,
  ClassificationMethod,
  ClassificationUpdate,
} from '@/services/dataPermissionApi';

const { Option } = Select;

const sensitivityColors: Record<SensitivityLevel, string> = {
  public: 'green',
  internal: 'blue',
  confidential: 'orange',
  top_secret: 'red',
};

const methodColors: Record<ClassificationMethod, string> = {
  manual: 'default',
  rule_based: 'blue',
  ai_based: 'purple',
};

const DataClassificationPage: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [classifyModalOpen, setClassifyModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedClassification, setSelectedClassification] = useState<DataClassification | null>(null);
  const [filters, setFilters] = useState<{
    sensitivity_level?: SensitivityLevel;
    limit: number;
    offset: number;
  }>({ limit: 20, offset: 0 });

  const [ruleForm] = Form.useForm();
  const [classifyForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch classifications
  const { data: classificationsData, isLoading } = useQuery({
    queryKey: ['classifications', filters],
    queryFn: () => dataPermissionApi.listClassifications(filters),
  });

  // Fetch classification rules
  const { data: rules } = useQuery({
    queryKey: ['classificationRules'],
    queryFn: () => dataPermissionApi.listClassificationRules(),
  });

  // Fetch report
  const { data: report } = useQuery({
    queryKey: ['classificationReport'],
    queryFn: () => dataPermissionApi.getClassificationReport(),
  });

  // Auto-classify mutation
  const classifyMutation = useMutation({
    mutationFn: ({ datasetId, useAI }: { datasetId: string; useAI: boolean }) =>
      dataPermissionApi.autoClassify(datasetId, useAI),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['classifications'] });
      queryClient.invalidateQueries({ queryKey: ['classificationReport'] });
      setClassifyModalOpen(false);
      classifyForm.resetFields();
      message.success(
        t('dataPermissions.classification.classificationComplete', { classified: result.classified_count, total: result.total_fields })
      );
    },
    onError: () => {
      message.error(t('dataPermissions.classification.classificationFailed'));
    },
  });

  // Create rule mutation
  const createRuleMutation = useMutation({
    mutationFn: (rule: ClassificationRule) =>
      dataPermissionApi.createClassificationRule(rule),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['classificationRules'] });
      setRuleModalOpen(false);
      ruleForm.resetFields();
      message.success(t('dataPermissions.classification.ruleCreated'));
    },
    onError: () => {
      message.error(t('dataPermissions.classification.ruleCreateFailed'));
    },
  });

  // Batch update mutation
  const batchUpdateMutation = useMutation({
    mutationFn: (updates: ClassificationUpdate[]) =>
      dataPermissionApi.batchUpdateClassification(updates),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['classifications'] });
      queryClient.invalidateQueries({ queryKey: ['classificationReport'] });
      setEditModalOpen(false);
      editForm.resetFields();
      message.success(t('dataPermissions.classification.updateSuccess', { count: result.updated_count }));
    },
    onError: () => {
      message.error(t('dataPermissions.classification.updateFailed'));
    },
  });

  const handleEdit = (classification: DataClassification) => {
    setSelectedClassification(classification);
    editForm.setFieldsValue({
      category: classification.category,
      sensitivity_level: classification.sensitivity_level,
    });
    setEditModalOpen(true);
  };

  const handleEditSubmit = (values: { category: string; sensitivity_level: SensitivityLevel }) => {
    if (selectedClassification) {
      batchUpdateMutation.mutate([
        {
          dataset_id: selectedClassification.dataset_id,
          field_name: selectedClassification.field_name,
          category: values.category,
          sensitivity_level: values.sensitivity_level,
        },
      ]);
    }
  };

  const columns: ColumnsType<DataClassification> = [
    {
      title: t('dataPermissions.classification.columns.dataset'),
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      ellipsis: true,
    },
    {
      title: t('dataPermissions.classification.columns.field'),
      dataIndex: 'field_name',
      key: 'field_name',
      render: (name) => name || <Tag>{t('dataPermissions.classification.allFields')}</Tag>,
    },
    {
      title: t('dataPermissions.classification.columns.category'),
      dataIndex: 'category',
      key: 'category',
      render: (category) => <Tag>{category}</Tag>,
    },
    {
      title: t('dataPermissions.classification.columns.sensitivity'),
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      width: 120,
      render: (level: SensitivityLevel) => (
        <Tag color={sensitivityColors[level]}>{t(`sensitivity.${level}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.classification.columns.method'),
      dataIndex: 'classified_by',
      key: 'classified_by',
      width: 120,
      render: (method: ClassificationMethod) => (
        <Tag color={methodColors[method]}>
          {method === 'ai_based' && <RobotOutlined style={{ marginRight: 4 }} />}
          {t(`dataPermissions.classification.methods.${method === 'rule_based' ? 'ruleBased' : method === 'ai_based' ? 'aiBased' : 'manual'}`)}
        </Tag>
      ),
    },
    {
      title: t('dataPermissions.classification.columns.confidence'),
      dataIndex: 'confidence_score',
      key: 'confidence_score',
      width: 120,
      render: (score) =>
        score !== null && score !== undefined ? (
          <Progress percent={Math.round(score * 100)} size="small" />
        ) : (
          '-'
        ),
    },
    {
      title: t('dataPermissions.classification.columns.verified'),
      dataIndex: 'manually_verified',
      key: 'manually_verified',
      width: 80,
      render: (verified) => (
        <Tag color={verified ? 'success' : 'default'}>{verified ? t('common:yes') : t('common:no')}</Tag>
      ),
    },
    {
      title: t('dataPermissions.classification.columns.updated'),
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Tooltip title={t('common:edit')}>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
        </Tooltip>
      ),
    },
  ];

  const ruleColumns: ColumnsType<ClassificationRule> = [
    {
      title: t('dataPermissions.classification.ruleName'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('dataPermissions.classification.regexPattern'),
      dataIndex: 'pattern',
      key: 'pattern',
      render: (pattern) => <code>{pattern}</code>,
    },
    {
      title: t('dataPermissions.classification.category'),
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: t('dataPermissions.classification.columns.sensitivity'),
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: SensitivityLevel) => (
        <Tag color={sensitivityColors[level]}>{t(`sensitivity.${level}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.classification.priority'),
      dataIndex: 'priority',
      key: 'priority',
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.classification.stats.totalFields')}
              value={report?.total_fields || 0}
              prefix={<FileSearchOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.classification.stats.classified')}
              value={
                (report?.total_fields || 0) - (report?.unclassified_count || 0)
              }
              suffix={`/ ${report?.total_fields || 0}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.classification.stats.confidentialPlus')}
              value={
                (report?.by_sensitivity?.confidential || 0) +
                (report?.by_sensitivity?.top_secret || 0)
              }
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.classification.stats.unclassified')}
              value={report?.unclassified_count || 0}
              valueStyle={{
                color: (report?.unclassified_count || 0) > 0 ? '#ff4d4f' : '#52c41a',
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        title={t('dataPermissions.classification.title')}
        extra={
          <Space>
            <Button icon={<BarChartOutlined />} onClick={() => setReportModalOpen(true)}>
              {t('dataPermissions.classification.viewReport')}
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => setRuleModalOpen(true)}>
              {t('dataPermissions.classification.addRule')}
            </Button>
            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={() => setClassifyModalOpen(true)}
            >
              {t('dataPermissions.classification.autoClassify')}
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder={t('dataPermissions.classification.columns.sensitivity')}
              style={{ width: 150 }}
              allowClear
              onChange={(value) =>
                setFilters((prev) => ({ ...prev, sensitivity_level: value, offset: 0 }))
              }
            >
              <Option value="public">{t('sensitivity.public')}</Option>
              <Option value="internal">{t('sensitivity.internal')}</Option>
              <Option value="confidential">{t('sensitivity.confidential')}</Option>
              <Option value="top_secret">{t('sensitivity.topSecret')}</Option>
            </Select>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={classificationsData?.classifications || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor(filters.offset / filters.limit) + 1,
            pageSize: filters.limit,
            total: classificationsData?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => t('common.totalLogs', { total }),
            onChange: (page, pageSize) => {
              setFilters((prev) => ({
                ...prev,
                offset: (page - 1) * pageSize,
                limit: pageSize,
              }));
            },
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* Classification Rules */}
      <Card title={t('dataPermissions.classification.classificationRules')} style={{ marginTop: 24 }}>
        <Table
          columns={ruleColumns}
          dataSource={rules || []}
          rowKey="name"
          size="small"
          pagination={false}
        />
      </Card>

      {/* Auto Classify Modal */}
      <Modal
        title={t('dataPermissions.classification.autoClassifyDataset')}
        open={classifyModalOpen}
        onCancel={() => setClassifyModalOpen(false)}
        onOk={() => classifyForm.submit()}
        confirmLoading={classifyMutation.isPending}
      >
        <Form
          form={classifyForm}
          layout="vertical"
          onFinish={(values) =>
            classifyMutation.mutate({
              datasetId: values.dataset_id,
              useAI: values.use_ai,
            })
          }
        >
          <Form.Item
            name="dataset_id"
            label={t('dataPermissions.classification.datasetId')}
            rules={[{ required: true, message: t('dataPermissions.classification.datasetId') }]}
          >
            <Input placeholder={t('dataPermissions.classification.datasetId')} />
          </Form.Item>

          <Form.Item
            name="use_ai"
            label={t('dataPermissions.classification.classificationMethod')}
            initialValue={false}
          >
            <Select>
              <Option value={false}>{t('dataPermissions.classification.ruleBasedClassification')}</Option>
              <Option value={true}>
                <RobotOutlined /> {t('dataPermissions.classification.aiBasedClassification')}
              </Option>
            </Select>
          </Form.Item>

          <Alert
            message={t('dataPermissions.classification.aiBasedClassification')}
            description={t('dataPermissions.classification.aiClassificationInfo')}
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* Add Rule Modal */}
      <Modal
        title={t('dataPermissions.classification.addRuleTitle')}
        open={ruleModalOpen}
        onCancel={() => setRuleModalOpen(false)}
        onOk={() => ruleForm.submit()}
        confirmLoading={createRuleMutation.isPending}
      >
        <Form form={ruleForm} layout="vertical" onFinish={createRuleMutation.mutate}>
          <Form.Item
            name="name"
            label={t('dataPermissions.classification.ruleName')}
            rules={[{ required: true, message: t('dataPermissions.classification.ruleName') }]}
          >
            <Input placeholder="e.g., Email Pattern" />
          </Form.Item>

          <Form.Item
            name="pattern"
            label={t('dataPermissions.classification.regexPattern')}
            rules={[{ required: true, message: t('dataPermissions.classification.regexPattern') }]}
          >
            <Input placeholder="e.g., ^email$|.*_email$" />
          </Form.Item>

          <Form.Item
            name="category"
            label={t('dataPermissions.classification.category')}
            rules={[{ required: true, message: t('dataPermissions.classification.category') }]}
          >
            <Input placeholder="e.g., PII, Financial, Health" />
          </Form.Item>

          <Form.Item
            name="sensitivity_level"
            label={t('dataPermissions.classification.columns.sensitivity')}
            rules={[{ required: true, message: t('dataPermissions.classification.columns.sensitivity') }]}
          >
            <Select placeholder={t('dataPermissions.classification.columns.sensitivity')}>
              <Option value="public">{t('sensitivity.public')}</Option>
              <Option value="internal">{t('sensitivity.internal')}</Option>
              <Option value="confidential">{t('sensitivity.confidential')}</Option>
              <Option value="top_secret">{t('sensitivity.topSecret')}</Option>
            </Select>
          </Form.Item>

          <Form.Item name="priority" label={t('dataPermissions.classification.priority')} initialValue={0}>
            <Input type="number" placeholder={t('dataPermissions.masking.form.priorityHint')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Classification Modal */}
      <Modal
        title={t('dataPermissions.classification.editClassification')}
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={() => editForm.submit()}
        confirmLoading={batchUpdateMutation.isPending}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEditSubmit}>
          <Form.Item
            name="category"
            label={t('dataPermissions.classification.category')}
            rules={[{ required: true, message: t('dataPermissions.classification.category') }]}
          >
            <Input placeholder={t('dataPermissions.classification.category')} />
          </Form.Item>

          <Form.Item
            name="sensitivity_level"
            label={t('dataPermissions.classification.columns.sensitivity')}
            rules={[{ required: true, message: t('dataPermissions.classification.columns.sensitivity') }]}
          >
            <Select placeholder={t('dataPermissions.classification.columns.sensitivity')}>
              <Option value="public">{t('sensitivity.public')}</Option>
              <Option value="internal">{t('sensitivity.internal')}</Option>
              <Option value="confidential">{t('sensitivity.confidential')}</Option>
              <Option value="top_secret">{t('sensitivity.topSecret')}</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Report Modal */}
      <Modal
        title={t('dataPermissions.classification.report.title')}
        open={reportModalOpen}
        onCancel={() => setReportModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setReportModalOpen(false)}>
            {t('common:close')}
          </Button>,
        ]}
        width={600}
      >
        {report && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label={t('dataPermissions.classification.report.totalDatasets')}>
                {report.total_datasets}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.classification.report.totalFields')}>
                {report.total_fields}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.classification.report.unclassified')}>
                {report.unclassified_count}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.classification.report.generatedAt')}>
                {dayjs(report.generated_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            </Descriptions>

            <Divider>{t('dataPermissions.classification.report.bySensitivity')}</Divider>
            <Row gutter={16}>
              {Object.entries(report.by_sensitivity || {}).map(([level, count]) => (
                <Col span={6} key={level}>
                  <Statistic
                    title={t(`sensitivity.${level}`)}
                    value={count}
                    valueStyle={{ color: sensitivityColors[level as SensitivityLevel] }}
                  />
                </Col>
              ))}
            </Row>

            <Divider>{t('dataPermissions.classification.report.byMethod')}</Divider>
            <Row gutter={16}>
              {Object.entries(report.by_method || {}).map(([method, count]) => (
                <Col span={8} key={method}>
                  <Statistic
                    title={t(`dataPermissions.classification.methods.${method === 'rule_based' ? 'ruleBased' : method === 'ai_based' ? 'aiBased' : 'manual'}`)}
                    value={count}
                  />
                </Col>
              ))}
            </Row>
          </>
        )}
      </Modal>
    </div>
  );
};

export default DataClassificationPage;
