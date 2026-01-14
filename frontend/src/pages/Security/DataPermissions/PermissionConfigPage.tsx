/**
 * Data Permission Configuration Page
 * 
 * Manages data-level permissions (dataset/record/field level).
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
  DatePicker,
  Switch,
  message,
  Tooltip,
  Row,
  Col,
  Statistic,
  Descriptions,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  dataPermissionApi,
  DataPermission,
  GrantPermissionRequest,
  PermissionCheckRequest,
  PermissionResult,
  ResourceLevel,
  DataPermissionAction,
} from '@/services/dataPermissionApi';

const { Option } = Select;

const resourceLevelColors: Record<ResourceLevel, string> = {
  dataset: 'blue',
  record: 'cyan',
  field: 'purple',
};

const actionColors: Record<DataPermissionAction, string> = {
  read: 'green',
  write: 'orange',
  delete: 'red',
  export: 'gold',
  annotate: 'cyan',
  review: 'purple',
};

const PermissionConfigPage: React.FC = () => {
  const [grantModalOpen, setGrantModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedPermission, setSelectedPermission] = useState<DataPermission | null>(null);
  const [testResult, setTestResult] = useState<PermissionResult | null>(null);
  const [filters, setFilters] = useState<{
    resource_type?: string;
    limit: number;
    offset: number;
  }>({ limit: 20, offset: 0 });

  const [grantForm] = Form.useForm();
  const [testForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch permissions
  const { data: permissionsData, isLoading } = useQuery({
    queryKey: ['dataPermissions', filters],
    queryFn: () => dataPermissionApi.listPermissions(filters),
  });

  // Grant permission mutation
  const grantMutation = useMutation({
    mutationFn: (data: GrantPermissionRequest) => dataPermissionApi.grantPermission(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataPermissions'] });
      setGrantModalOpen(false);
      grantForm.resetFields();
      message.success('Permission granted successfully');
    },
    onError: () => {
      message.error('Failed to grant permission');
    },
  });

  // Revoke permission mutation
  const revokeMutation = useMutation({
    mutationFn: (permission: DataPermission) =>
      dataPermissionApi.revokePermission({
        user_id: permission.user_id,
        role_id: permission.role_id,
        resource_type: permission.resource_type,
        resource_id: permission.resource_id,
        action: permission.action,
        field_name: permission.field_name,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataPermissions'] });
      message.success('Permission revoked successfully');
    },
    onError: () => {
      message.error('Failed to revoke permission');
    },
  });

  // Test permission mutation
  const testMutation = useMutation({
    mutationFn: (data: PermissionCheckRequest) => dataPermissionApi.testPermission(data),
    onSuccess: (result) => {
      setTestResult(result);
    },
    onError: () => {
      message.error('Permission test failed');
    },
  });

  const handleGrantSubmit = (values: GrantPermissionRequest) => {
    const data: GrantPermissionRequest = {
      ...values,
      expires_at: values.expires_at ? dayjs(values.expires_at).toISOString() : undefined,
    };
    grantMutation.mutate(data);
  };

  const handleTestSubmit = (values: PermissionCheckRequest) => {
    testMutation.mutate(values);
  };

  const handleViewDetail = (permission: DataPermission) => {
    setSelectedPermission(permission);
    setDetailModalOpen(true);
  };

  const columns: ColumnsType<DataPermission> = [
    {
      title: 'Resource Level',
      dataIndex: 'resource_level',
      key: 'resource_level',
      width: 120,
      render: (level: ResourceLevel) => (
        <Tag color={resourceLevelColors[level]}>{level.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Resource',
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource_type}/{record.resource_id}</div>
          {record.field_name && (
            <div style={{ fontSize: 12, color: '#666' }}>Field: {record.field_name}</div>
          )}
        </div>
      ),
    },
    {
      title: 'User/Role',
      key: 'target',
      render: (_, record) => (
        <div>
          {record.user_id && <Tag color="blue">User: {record.user_id.slice(0, 8)}...</Tag>}
          {record.role_id && <Tag color="green">Role: {record.role_id.slice(0, 8)}...</Tag>}
        </div>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: DataPermissionAction) => (
        <Tag color={actionColors[action]}>{action.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color={record.is_active ? 'success' : 'default'}>
            {record.is_active ? 'Active' : 'Inactive'}
          </Tag>
          {record.is_temporary && <Tag color="warning">Temporary</Tag>}
        </Space>
      ),
    },
    {
      title: 'Expires',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 150,
      render: (date) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : 'Never'),
    },
    {
      title: 'Granted',
      dataIndex: 'granted_at',
      key: 'granted_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Revoke this permission?"
            onConfirm={() => revokeMutation.mutate(record)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Revoke">
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Total Permissions"
              value={permissionsData?.total || 0}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Active"
              value={permissionsData?.permissions?.filter((p) => p.is_active).length || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Temporary"
              value={permissionsData?.permissions?.filter((p) => p.is_temporary).length || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Expiring Soon"
              value={
                permissionsData?.permissions?.filter(
                  (p) => p.expires_at && dayjs(p.expires_at).diff(dayjs(), 'day') <= 7
                ).length || 0
              }
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Table */}
      <Card
        title="Data Permissions"
        extra={
          <Space>
            <Button icon={<ExperimentOutlined />} onClick={() => setTestModalOpen(true)}>
              Test Permission
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setGrantModalOpen(true)}>
              Grant Permission
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder="Resource Type"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => setFilters((prev) => ({ ...prev, resource_type: value }))}
            >
              <Option value="dataset">Dataset</Option>
              <Option value="project">Project</Option>
              <Option value="task">Task</Option>
            </Select>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={permissionsData?.permissions || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: Math.floor(filters.offset / filters.limit) + 1,
            pageSize: filters.limit,
            total: permissionsData?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} permissions`,
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

      {/* Grant Permission Modal */}
      <Modal
        title="Grant Permission"
        open={grantModalOpen}
        onCancel={() => setGrantModalOpen(false)}
        onOk={() => grantForm.submit()}
        confirmLoading={grantMutation.isPending}
        width={600}
      >
        <Form form={grantForm} layout="vertical" onFinish={handleGrantSubmit}>
          <Form.Item
            name="resource_level"
            label="Resource Level"
            rules={[{ required: true, message: 'Please select resource level' }]}
          >
            <Select placeholder="Select level">
              <Option value="dataset">Dataset</Option>
              <Option value="record">Record</Option>
              <Option value="field">Field</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="resource_type"
            label="Resource Type"
            rules={[{ required: true, message: 'Please enter resource type' }]}
          >
            <Input placeholder="e.g., dataset, project, task" />
          </Form.Item>

          <Form.Item
            name="resource_id"
            label="Resource ID"
            rules={[{ required: true, message: 'Please enter resource ID' }]}
          >
            <Input placeholder="Resource identifier" />
          </Form.Item>

          <Form.Item name="field_name" label="Field Name (for field-level)">
            <Input placeholder="Field name (optional)" />
          </Form.Item>

          <Form.Item name="user_id" label="User ID">
            <Input placeholder="User UUID (leave empty for role-based)" />
          </Form.Item>

          <Form.Item name="role_id" label="Role ID">
            <Input placeholder="Role UUID (leave empty for user-based)" />
          </Form.Item>

          <Form.Item
            name="action"
            label="Action"
            rules={[{ required: true, message: 'Please select action' }]}
          >
            <Select placeholder="Select action">
              <Option value="read">Read</Option>
              <Option value="write">Write</Option>
              <Option value="delete">Delete</Option>
              <Option value="export">Export</Option>
              <Option value="annotate">Annotate</Option>
              <Option value="review">Review</Option>
            </Select>
          </Form.Item>

          <Form.Item name="expires_at" label="Expires At">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="is_temporary" label="Temporary Permission" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="tags" label="Tags">
            <Select mode="tags" placeholder="Add tags" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Test Permission Modal */}
      <Modal
        title="Test Permission"
        open={testModalOpen}
        onCancel={() => {
          setTestModalOpen(false);
          setTestResult(null);
        }}
        footer={[
          <Button key="close" onClick={() => setTestModalOpen(false)}>
            Close
          </Button>,
          <Button
            key="test"
            type="primary"
            onClick={() => testForm.submit()}
            loading={testMutation.isPending}
          >
            Test
          </Button>,
        ]}
        width={600}
      >
        <Form form={testForm} layout="vertical" onFinish={handleTestSubmit}>
          <Form.Item
            name="user_id"
            label="User ID"
            rules={[{ required: true, message: 'Please enter user ID' }]}
          >
            <Input placeholder="User UUID to test" />
          </Form.Item>

          <Form.Item
            name="resource_type"
            label="Resource Type"
            rules={[{ required: true, message: 'Please enter resource type' }]}
          >
            <Input placeholder="e.g., dataset, project" />
          </Form.Item>

          <Form.Item
            name="resource_id"
            label="Resource ID"
            rules={[{ required: true, message: 'Please enter resource ID' }]}
          >
            <Input placeholder="Resource identifier" />
          </Form.Item>

          <Form.Item
            name="action"
            label="Action"
            rules={[{ required: true, message: 'Please select action' }]}
          >
            <Select placeholder="Select action">
              <Option value="read">Read</Option>
              <Option value="write">Write</Option>
              <Option value="delete">Delete</Option>
              <Option value="export">Export</Option>
            </Select>
          </Form.Item>

          <Form.Item name="field_name" label="Field Name (optional)">
            <Input placeholder="For field-level check" />
          </Form.Item>
        </Form>

        {testResult && (
          <Card style={{ marginTop: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Result">
                {testResult.allowed ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    ALLOWED
                  </Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    DENIED
                  </Tag>
                )}
              </Descriptions.Item>
              {testResult.reason && (
                <Descriptions.Item label="Reason">{testResult.reason}</Descriptions.Item>
              )}
              {testResult.requires_approval && (
                <Descriptions.Item label="Requires Approval">
                  <Tag color="warning">Yes</Tag>
                </Descriptions.Item>
              )}
              {testResult.masked_fields.length > 0 && (
                <Descriptions.Item label="Masked Fields">
                  {testResult.masked_fields.map((f) => (
                    <Tag key={f}>{f}</Tag>
                  ))}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        )}
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="Permission Details"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={600}
      >
        {selectedPermission && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{selectedPermission.id}</Descriptions.Item>
            <Descriptions.Item label="Resource Level">
              <Tag color={resourceLevelColors[selectedPermission.resource_level]}>
                {selectedPermission.resource_level}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Resource Type">
              {selectedPermission.resource_type}
            </Descriptions.Item>
            <Descriptions.Item label="Resource ID">{selectedPermission.resource_id}</Descriptions.Item>
            {selectedPermission.field_name && (
              <Descriptions.Item label="Field Name">{selectedPermission.field_name}</Descriptions.Item>
            )}
            <Descriptions.Item label="User ID">{selectedPermission.user_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="Role ID">{selectedPermission.role_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="Action">
              <Tag color={actionColors[selectedPermission.action]}>{selectedPermission.action}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={selectedPermission.is_active ? 'success' : 'default'}>
                {selectedPermission.is_active ? 'Active' : 'Inactive'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Temporary">
              {selectedPermission.is_temporary ? 'Yes' : 'No'}
            </Descriptions.Item>
            <Descriptions.Item label="Tags">
              {selectedPermission.tags?.map((t) => <Tag key={t}>{t}</Tag>) || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Granted By">{selectedPermission.granted_by}</Descriptions.Item>
            <Descriptions.Item label="Granted At">
              {dayjs(selectedPermission.granted_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="Expires At">
              {selectedPermission.expires_at
                ? dayjs(selectedPermission.expires_at).format('YYYY-MM-DD HH:mm:ss')
                : 'Never'}
            </Descriptions.Item>
            {selectedPermission.conditions && (
              <Descriptions.Item label="Conditions">
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedPermission.conditions, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default PermissionConfigPage;
