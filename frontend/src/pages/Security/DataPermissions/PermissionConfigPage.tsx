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
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['security', 'common']);
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
      message.success(t('dataPermissions.permissionConfig.grantSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.permissionConfig.grantFailed'));
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
      message.success(t('dataPermissions.permissionConfig.revokeSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.permissionConfig.revokeFailed'));
    },
  });

  // Test permission mutation
  const testMutation = useMutation({
    mutationFn: (data: PermissionCheckRequest) => dataPermissionApi.testPermission(data),
    onSuccess: (result) => {
      setTestResult(result);
    },
    onError: () => {
      message.error(t('dataPermissions.permissionConfig.test.testFailed'));
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
      title: t('dataPermissions.permissionConfig.columns.resourceLevel'),
      dataIndex: 'resource_level',
      key: 'resource_level',
      width: 120,
      render: (level: ResourceLevel) => (
        <Tag color={resourceLevelColors[level]}>{t(`dataPermissions.permissionConfig.resourceLevels.${level}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.permissionConfig.columns.resource'),
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource_type}/{record.resource_id}</div>
          {record.field_name && (
            <div style={{ fontSize: 12, color: '#666' }}>{t('dataPermissions.permissionConfig.form.fieldName')}: {record.field_name}</div>
          )}
        </div>
      ),
    },
    {
      title: t('dataPermissions.permissionConfig.columns.userRole'),
      key: 'target',
      render: (_, record) => (
        <div>
          {record.user_id && <Tag color="blue">{t('audit.user')}: {record.user_id.slice(0, 8)}...</Tag>}
          {record.role_id && <Tag color="green">{t('permissions.role')}: {record.role_id.slice(0, 8)}...</Tag>}
        </div>
      ),
    },
    {
      title: t('dataPermissions.permissionConfig.columns.action'),
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action: DataPermissionAction) => (
        <Tag color={actionColors[action]}>{t(`dataPermissions.permissionConfig.actions.${action}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.permissionConfig.columns.status'),
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Tag color={record.is_active ? 'success' : 'default'}>
            {record.is_active ? t('dataPermissions.masking.active') : t('dataPermissions.masking.inactive')}
          </Tag>
          {record.is_temporary && <Tag color="warning">{t('dataPermissions.permissionConfig.stats.temporary')}</Tag>}
        </Space>
      ),
    },
    {
      title: t('dataPermissions.permissionConfig.columns.expires'),
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 150,
      render: (date) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : t('dataPermissions.permissionConfig.never')),
    },
    {
      title: t('dataPermissions.permissionConfig.columns.granted'),
      dataIndex: 'granted_at',
      key: 'granted_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('dataPermissions.approval.viewDetails')}>
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Popconfirm
            title={t('dataPermissions.permissionConfig.revokePermission')}
            onConfirm={() => revokeMutation.mutate(record)}
            okText={t('common:yes')}
            cancelText={t('common:no')}
          >
            <Tooltip title={t('common:revoke')}>
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
              title={t('dataPermissions.permissionConfig.stats.totalPermissions')}
              value={permissionsData?.total || 0}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.permissionConfig.stats.active')}
              value={permissionsData?.permissions?.filter((p) => p.is_active).length || 0}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.permissionConfig.stats.temporary')}
              value={permissionsData?.permissions?.filter((p) => p.is_temporary).length || 0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.permissionConfig.stats.expiringSoon')}
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
        title={t('dataPermissions.permissionConfig.title')}
        extra={
          <Space>
            <Button icon={<ExperimentOutlined />} onClick={() => setTestModalOpen(true)}>
              {t('dataPermissions.permissionConfig.testPermission')}
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setGrantModalOpen(true)}>
              {t('dataPermissions.permissionConfig.grantPermission')}
            </Button>
          </Space>
        }
      >
        {/* Filters */}
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder={t('dataPermissions.permissionConfig.form.resourceType')}
              style={{ width: 150 }}
              allowClear
              onChange={(value) => setFilters((prev) => ({ ...prev, resource_type: value }))}
            >
              <Option value="dataset">{t('dataPermissions.permissionConfig.resourceLevels.dataset')}</Option>
              <Option value="project">{t('rbac.resources.projects')}</Option>
              <Option value="task">{t('rbac.resources.tasks')}</Option>
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
            showTotal: (total) => t('common.totalPermissions', { total }),
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
        title={t('dataPermissions.permissionConfig.grantPermission')}
        open={grantModalOpen}
        onCancel={() => setGrantModalOpen(false)}
        onOk={() => grantForm.submit()}
        confirmLoading={grantMutation.isPending}
        width={600}
      >
        <Form form={grantForm} layout="vertical" onFinish={handleGrantSubmit}>
          <Form.Item
            name="resource_level"
            label={t('dataPermissions.permissionConfig.form.resourceLevel')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.form.resourceLevel') }]}
          >
            <Select placeholder={t('dataPermissions.permissionConfig.form.resourceLevel')}>
              <Option value="dataset">{t('dataPermissions.permissionConfig.resourceLevels.dataset')}</Option>
              <Option value="record">{t('dataPermissions.permissionConfig.resourceLevels.record')}</Option>
              <Option value="field">{t('dataPermissions.permissionConfig.resourceLevels.field')}</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="resource_type"
            label={t('dataPermissions.permissionConfig.form.resourceType')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.form.resourceType') }]}
          >
            <Input placeholder={t('dataPermissions.permissionConfig.form.resourceTypePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="resource_id"
            label={t('dataPermissions.permissionConfig.form.resourceId')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.form.resourceId') }]}
          >
            <Input placeholder={t('dataPermissions.permissionConfig.form.resourceIdPlaceholder')} />
          </Form.Item>

          <Form.Item name="field_name" label={t('dataPermissions.permissionConfig.form.fieldName')}>
            <Input placeholder={t('dataPermissions.permissionConfig.form.fieldNamePlaceholder')} />
          </Form.Item>

          <Form.Item name="user_id" label={t('dataPermissions.permissionConfig.form.userId')}>
            <Input placeholder={t('dataPermissions.permissionConfig.form.userIdPlaceholder')} />
          </Form.Item>

          <Form.Item name="role_id" label={t('dataPermissions.permissionConfig.form.roleId')}>
            <Input placeholder={t('dataPermissions.permissionConfig.form.roleIdPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="action"
            label={t('dataPermissions.permissionConfig.form.action')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.form.selectAction') }]}
          >
            <Select placeholder={t('dataPermissions.permissionConfig.form.selectAction')}>
              <Option value="read">{t('dataPermissions.permissionConfig.actions.read')}</Option>
              <Option value="write">{t('dataPermissions.permissionConfig.actions.write')}</Option>
              <Option value="delete">{t('dataPermissions.permissionConfig.actions.delete')}</Option>
              <Option value="export">{t('dataPermissions.permissionConfig.actions.export')}</Option>
              <Option value="annotate">{t('dataPermissions.permissionConfig.actions.annotate')}</Option>
              <Option value="review">{t('dataPermissions.permissionConfig.actions.review')}</Option>
            </Select>
          </Form.Item>

          <Form.Item name="expires_at" label={t('dataPermissions.permissionConfig.form.expiresAt')}>
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="is_temporary" label={t('dataPermissions.permissionConfig.form.isTemporary')} valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="tags" label={t('dataPermissions.permissionConfig.form.tags')}>
            <Select mode="tags" placeholder={t('dataPermissions.permissionConfig.form.addTags')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Test Permission Modal */}
      <Modal
        title={t('dataPermissions.permissionConfig.test.title')}
        open={testModalOpen}
        onCancel={() => {
          setTestModalOpen(false);
          setTestResult(null);
        }}
        footer={[
          <Button key="close" onClick={() => setTestModalOpen(false)}>
            {t('common:close')}
          </Button>,
          <Button
            key="test"
            type="primary"
            onClick={() => testForm.submit()}
            loading={testMutation.isPending}
          >
            {t('common:test')}
          </Button>,
        ]}
        width={600}
      >
        <Form form={testForm} layout="vertical" onFinish={handleTestSubmit}>
          <Form.Item
            name="user_id"
            label={t('dataPermissions.permissionConfig.test.userId')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.test.userId') }]}
          >
            <Input placeholder={t('dataPermissions.permissionConfig.test.userIdPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="resource_type"
            label={t('dataPermissions.permissionConfig.test.resourceType')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.test.resourceType') }]}
          >
            <Input placeholder={t('dataPermissions.permissionConfig.form.resourceTypePlaceholder')} />
          </Form.Item>

          <Form.Item
            name="resource_id"
            label={t('dataPermissions.permissionConfig.test.resourceId')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.test.resourceId') }]}
          >
            <Input placeholder={t('dataPermissions.permissionConfig.form.resourceIdPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="action"
            label={t('dataPermissions.permissionConfig.test.action')}
            rules={[{ required: true, message: t('dataPermissions.permissionConfig.form.selectAction') }]}
          >
            <Select placeholder={t('dataPermissions.permissionConfig.form.selectAction')}>
              <Option value="read">{t('dataPermissions.permissionConfig.actions.read')}</Option>
              <Option value="write">{t('dataPermissions.permissionConfig.actions.write')}</Option>
              <Option value="delete">{t('dataPermissions.permissionConfig.actions.delete')}</Option>
              <Option value="export">{t('dataPermissions.permissionConfig.actions.export')}</Option>
            </Select>
          </Form.Item>

          <Form.Item name="field_name" label={t('dataPermissions.permissionConfig.test.fieldName')}>
            <Input placeholder={t('dataPermissions.permissionConfig.test.fieldNamePlaceholder')} />
          </Form.Item>
        </Form>

        {testResult && (
          <Card style={{ marginTop: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label={t('dataPermissions.permissionConfig.test.result')}>
                {testResult.allowed ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    {t('dataPermissions.permissionConfig.test.allowed')}
                  </Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">
                    {t('dataPermissions.permissionConfig.test.denied')}
                  </Tag>
                )}
              </Descriptions.Item>
              {testResult.reason && (
                <Descriptions.Item label={t('dataPermissions.permissionConfig.test.reason')}>{testResult.reason}</Descriptions.Item>
              )}
              {testResult.requires_approval && (
                <Descriptions.Item label={t('dataPermissions.permissionConfig.test.requiresApproval')}>
                  <Tag color="warning">{t('common:yes')}</Tag>
                </Descriptions.Item>
              )}
              {testResult.masked_fields.length > 0 && (
                <Descriptions.Item label={t('dataPermissions.permissionConfig.test.maskedFields')}>
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
        title={t('dataPermissions.permissionConfig.details.title')}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {t('common:close')}
          </Button>,
        ]}
        width={600}
      >
        {selectedPermission && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.id')}>{selectedPermission.id}</Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.resourceLevel')}>
              <Tag color={resourceLevelColors[selectedPermission.resource_level]}>
                {t(`dataPermissions.permissionConfig.resourceLevels.${selectedPermission.resource_level}`)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.resourceType')}>
              {selectedPermission.resource_type}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.resourceId')}>{selectedPermission.resource_id}</Descriptions.Item>
            {selectedPermission.field_name && (
              <Descriptions.Item label={t('dataPermissions.permissionConfig.details.fieldName')}>{selectedPermission.field_name}</Descriptions.Item>
            )}
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.userId')}>{selectedPermission.user_id || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.roleId')}>{selectedPermission.role_id || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.action')}>
              <Tag color={actionColors[selectedPermission.action]}>{t(`dataPermissions.permissionConfig.actions.${selectedPermission.action}`)}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.status')}>
              <Tag color={selectedPermission.is_active ? 'success' : 'default'}>
                {selectedPermission.is_active ? t('dataPermissions.masking.active') : t('dataPermissions.masking.inactive')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.temporary')}>
              {selectedPermission.is_temporary ? t('common:yes') : t('common:no')}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.tags')}>
              {selectedPermission.tags?.map((tag) => <Tag key={tag}>{tag}</Tag>) || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.grantedBy')}>{selectedPermission.granted_by}</Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.grantedAt')}>
              {dayjs(selectedPermission.granted_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label={t('dataPermissions.permissionConfig.details.expiresAt')}>
              {selectedPermission.expires_at
                ? dayjs(selectedPermission.expires_at).format('YYYY-MM-DD HH:mm:ss')
                : t('dataPermissions.permissionConfig.never')}
            </Descriptions.Item>
            {selectedPermission.conditions && (
              <Descriptions.Item label={t('dataPermissions.permissionConfig.details.conditions')}>
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
