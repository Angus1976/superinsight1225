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
        `Classification completed: ${result.classified_count}/${result.total_fields} fields classified`
      );
    },
    onError: () => {
      message.error('Classification failed');
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
      message.success('Rule created successfully');
    },
    onError: () => {
      message.error('Failed to create rule');
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
      message.success(`Updated ${result.updated_count} classifications`);
    },
    onError: () => {
      message.error('Update failed');
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
      title: 'Dataset',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      ellipsis: true,
    },
    {
      title: 'Field',
      dataIndex: 'field_name',
      key: 'field_name',
      render: (name) => name || <Tag>All Fields</Tag>,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category) => <Tag>{category}</Tag>,
    },
    {
      title: 'Sensitivity',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      width: 120,
      render: (level: SensitivityLevel) => (
        <Tag color={sensitivityColors[level]}>{level.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Method',
      dataIndex: 'classified_by',
      key: 'classified_by',
      width: 120,
      render: (method: ClassificationMethod) => (
        <Tag color={methodColors[method]}>
          {method === 'ai_based' && <RobotOutlined style={{ marginRight: 4 }} />}
          {method.replace('_', ' ').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Confidence',
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
      title: 'Verified',
      dataIndex: 'manually_verified',
      key: 'manually_verified',
      width: 80,
      render: (verified) => (
        <Tag color={verified ? 'success' : 'default'}>{verified ? 'Yes' : 'No'}</Tag>
      ),
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Tooltip title="Edit">
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
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Pattern',
      dataIndex: 'pattern',
      key: 'pattern',
      render: (pattern) => <code>{pattern}</code>,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
    },
    {
      title: 'Sensitivity',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: SensitivityLevel) => (
        <Tag color={sensitivityColors[level]}>{level}</Tag>
      ),
    },
    {
      title: 'Priority',
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
              title="Total Fields"
              value={report?.total_fields || 0}
              prefix={<FileSearchOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Classified"
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
              title="Confidential+"
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
              title="Unclassified"
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
        title="Data Classifications"
        extra={
          <Space>
            <Button icon={<BarChartOutlined />} onClick={() => setReportModalOpen(true)}>
              View Report
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => setRuleModalOpen(true)}>
              Add Rule
            </Button>
            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={() => setClassifyModalOpen(true)}
            >
              Auto Classify
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder="Sensitivity Level"
              style={{ width: 150 }}
              allowClear
              onChange={(value) =>
                setFilters((prev) => ({ ...prev, sensitivity_level: value, offset: 0 }))
              }
            >
              <Option value="public">Public</Option>
              <Option value="internal">Internal</Option>
              <Option value="confidential">Confidential</Option>
              <Option value="top_secret">Top Secret</Option>
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
            showTotal: (total) => `Total ${total} classifications`,
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
      <Card title="Classification Rules" style={{ marginTop: 24 }}>
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
        title="Auto Classify Dataset"
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
            label="Dataset ID"
            rules={[{ required: true, message: 'Please enter dataset ID' }]}
          >
            <Input placeholder="Dataset identifier" />
          </Form.Item>

          <Form.Item
            name="use_ai"
            label="Classification Method"
            initialValue={false}
          >
            <Select>
              <Option value={false}>Rule-based Classification</Option>
              <Option value={true}>
                <RobotOutlined /> AI-based Classification
              </Option>
            </Select>
          </Form.Item>

          <Alert
            message="AI Classification"
            description="AI-based classification uses machine learning to detect sensitive data patterns. It may take longer but provides higher accuracy for complex data."
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* Add Rule Modal */}
      <Modal
        title="Add Classification Rule"
        open={ruleModalOpen}
        onCancel={() => setRuleModalOpen(false)}
        onOk={() => ruleForm.submit()}
        confirmLoading={createRuleMutation.isPending}
      >
        <Form form={ruleForm} layout="vertical" onFinish={createRuleMutation.mutate}>
          <Form.Item
            name="name"
            label="Rule Name"
            rules={[{ required: true, message: 'Please enter rule name' }]}
          >
            <Input placeholder="e.g., Email Pattern" />
          </Form.Item>

          <Form.Item
            name="pattern"
            label="Regex Pattern"
            rules={[{ required: true, message: 'Please enter pattern' }]}
          >
            <Input placeholder="e.g., ^email$|.*_email$" />
          </Form.Item>

          <Form.Item
            name="category"
            label="Category"
            rules={[{ required: true, message: 'Please enter category' }]}
          >
            <Input placeholder="e.g., PII, Financial, Health" />
          </Form.Item>

          <Form.Item
            name="sensitivity_level"
            label="Sensitivity Level"
            rules={[{ required: true, message: 'Please select sensitivity' }]}
          >
            <Select placeholder="Select sensitivity">
              <Option value="public">Public</Option>
              <Option value="internal">Internal</Option>
              <Option value="confidential">Confidential</Option>
              <Option value="top_secret">Top Secret</Option>
            </Select>
          </Form.Item>

          <Form.Item name="priority" label="Priority" initialValue={0}>
            <Input type="number" placeholder="Higher priority rules are applied first" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Classification Modal */}
      <Modal
        title="Edit Classification"
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={() => editForm.submit()}
        confirmLoading={batchUpdateMutation.isPending}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEditSubmit}>
          <Form.Item
            name="category"
            label="Category"
            rules={[{ required: true, message: 'Please enter category' }]}
          >
            <Input placeholder="Category" />
          </Form.Item>

          <Form.Item
            name="sensitivity_level"
            label="Sensitivity Level"
            rules={[{ required: true, message: 'Please select sensitivity' }]}
          >
            <Select placeholder="Select sensitivity">
              <Option value="public">Public</Option>
              <Option value="internal">Internal</Option>
              <Option value="confidential">Confidential</Option>
              <Option value="top_secret">Top Secret</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Report Modal */}
      <Modal
        title="Classification Report"
        open={reportModalOpen}
        onCancel={() => setReportModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setReportModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={600}
      >
        {report && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="Total Datasets">
                {report.total_datasets}
              </Descriptions.Item>
              <Descriptions.Item label="Total Fields">
                {report.total_fields}
              </Descriptions.Item>
              <Descriptions.Item label="Unclassified">
                {report.unclassified_count}
              </Descriptions.Item>
              <Descriptions.Item label="Generated At">
                {dayjs(report.generated_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            </Descriptions>

            <Divider>By Sensitivity Level</Divider>
            <Row gutter={16}>
              {Object.entries(report.by_sensitivity || {}).map(([level, count]) => (
                <Col span={6} key={level}>
                  <Statistic
                    title={level.toUpperCase()}
                    value={count}
                    valueStyle={{ color: sensitivityColors[level as SensitivityLevel] }}
                  />
                </Col>
              ))}
            </Row>

            <Divider>By Classification Method</Divider>
            <Row gutter={16}>
              {Object.entries(report.by_method || {}).map(([method, count]) => (
                <Col span={8} key={method}>
                  <Statistic
                    title={method.replace('_', ' ').toUpperCase()}
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
