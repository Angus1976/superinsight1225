/**
 * Approval Workflow Page
 * 
 * Manages data access approval requests and workflows.
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
  Tabs,
  Badge,
  message,
  Descriptions,
  Timeline,
  Row,
  Col,
  Statistic,
  Tooltip,
  Alert,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  UserSwitchOutlined,
  PlusOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import {
  dataPermissionApi,
  ApprovalRequest,
  ApprovalAction,
  ApprovalStatus,
  SensitivityLevel,
  DelegationRequest,
} from '@/services/dataPermissionApi';

const { TextArea } = Input;
const { Option } = Select;

const statusColors: Record<ApprovalStatus, string> = {
  pending: 'processing',
  approved: 'success',
  rejected: 'error',
  expired: 'default',
  cancelled: 'warning',
};

const sensitivityColors: Record<SensitivityLevel, string> = {
  public: 'green',
  internal: 'blue',
  confidential: 'orange',
  top_secret: 'red',
};

const ApprovalWorkflowPage: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [activeTab, setActiveTab] = useState('pending');
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [delegateModalOpen, setDelegateModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [approvalHistory, setApprovalHistory] = useState<ApprovalAction[]>([]);

  const [decisionForm] = Form.useForm();
  const [delegateForm] = Form.useForm();
  const queryClient = useQueryClient();

  // Fetch pending approvals
  const { data: pendingApprovals, isLoading: pendingLoading } = useQuery({
    queryKey: ['pendingApprovals'],
    queryFn: () => dataPermissionApi.getPendingApprovals(),
  });

  // Fetch my approval requests
  const { data: myApprovals, isLoading: myApprovalsLoading } = useQuery({
    queryKey: ['myApprovals'],
    queryFn: () => dataPermissionApi.getMyApprovals(),
  });

  // Approve/Reject mutation
  const decisionMutation = useMutation({
    mutationFn: ({
      requestId,
      decision,
      comments,
    }: {
      requestId: string;
      decision: 'approved' | 'rejected';
      comments?: string;
    }) => dataPermissionApi.approveRequest(requestId, { decision, comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingApprovals'] });
      queryClient.invalidateQueries({ queryKey: ['myApprovals'] });
      setDecisionModalOpen(false);
      decisionForm.resetFields();
      message.success(t('dataPermissions.approval.decisionSubmitted'));
    },
    onError: () => {
      message.error(t('dataPermissions.approval.decisionFailed'));
    },
  });

  // Delegate mutation
  const delegateMutation = useMutation({
    mutationFn: (data: DelegationRequest) => dataPermissionApi.delegateApproval(data),
    onSuccess: () => {
      setDelegateModalOpen(false);
      delegateForm.resetFields();
      message.success(t('dataPermissions.approval.delegation.createSuccess'));
    },
    onError: () => {
      message.error(t('dataPermissions.approval.delegation.createFailed'));
    },
  });

  // Fetch approval history
  const fetchHistory = async (requestId: string) => {
    try {
      const history = await dataPermissionApi.getApprovalHistory(requestId);
      setApprovalHistory(history);
    } catch {
      message.error(t('common:loadFailed'));
    }
  };

  const handleViewDetail = async (request: ApprovalRequest) => {
    setSelectedRequest(request);
    await fetchHistory(request.id);
    setDetailModalOpen(true);
  };

  const handleDecision = (request: ApprovalRequest, decision: 'approved' | 'rejected') => {
    setSelectedRequest(request);
    decisionForm.setFieldsValue({ decision });
    setDecisionModalOpen(true);
  };

  const handleDecisionSubmit = (values: { decision: 'approved' | 'rejected'; comments?: string }) => {
    if (selectedRequest) {
      decisionMutation.mutate({
        requestId: selectedRequest.id,
        decision: values.decision,
        comments: values.comments,
      });
    }
  };

  const handleDelegateSubmit = (values: DelegationRequest) => {
    delegateMutation.mutate({
      ...values,
      start_date: dayjs(values.start_date).toISOString(),
      end_date: dayjs(values.end_date).toISOString(),
    });
  };

  const pendingColumns: ColumnsType<ApprovalRequest> = [
    {
      title: t('dataPermissions.approval.columns.resource'),
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource}</div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.resource_type}</div>
        </div>
      ),
    },
    {
      title: t('dataPermissions.approval.columns.action'),
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => <Tag>{action.toUpperCase()}</Tag>,
    },
    {
      title: t('dataPermissions.approval.columns.requester'),
      dataIndex: 'requester_id',
      key: 'requester_id',
      width: 150,
      ellipsis: true,
    },
    {
      title: t('dataPermissions.approval.columns.sensitivity'),
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      width: 120,
      render: (level: SensitivityLevel) => (
        <Tag color={sensitivityColors[level]}>{t(`sensitivity.${level}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.approval.columns.level'),
      dataIndex: 'current_level',
      key: 'current_level',
      width: 80,
      render: (level) => <Badge count={level} style={{ backgroundColor: '#1890ff' }} />,
    },
    {
      title: t('dataPermissions.approval.columns.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('dataPermissions.approval.columns.expires'),
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 150,
      render: (date) => {
        const isExpiringSoon = dayjs(date).diff(dayjs(), 'hour') < 24;
        return (
          <span style={{ color: isExpiringSoon ? '#ff4d4f' : undefined }}>
            {dayjs(date).format('YYYY-MM-DD HH:mm')}
          </span>
        );
      },
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 200,
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
          <Tooltip title={t('dataPermissions.approval.approve')}>
            <Button
              type="link"
              size="small"
              icon={<CheckOutlined />}
              style={{ color: '#52c41a' }}
              onClick={() => handleDecision(record, 'approved')}
            />
          </Tooltip>
          <Tooltip title={t('dataPermissions.approval.reject')}>
            <Button
              type="link"
              size="small"
              icon={<CloseOutlined />}
              danger
              onClick={() => handleDecision(record, 'rejected')}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const myRequestColumns: ColumnsType<ApprovalRequest> = [
    {
      title: t('dataPermissions.approval.columns.resource'),
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource}</div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.resource_type}</div>
        </div>
      ),
    },
    {
      title: t('dataPermissions.approval.columns.action'),
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => <Tag>{action.toUpperCase()}</Tag>,
    },
    {
      title: t('dataPermissions.approval.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: ApprovalStatus) => (
        <Tag color={statusColors[status]}>{t(`dataPermissions.approval.status.${status}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.approval.columns.sensitivity'),
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      width: 120,
      render: (level: SensitivityLevel) => (
        <Tag color={sensitivityColors[level]}>{t(`sensitivity.${level}`)}</Tag>
      ),
    },
    {
      title: t('dataPermissions.approval.columns.created'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: t('dataPermissions.approval.columns.resolved'),
      dataIndex: 'resolved_at',
      key: 'resolved_at',
      width: 150,
      render: (date) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        />
      ),
    },
  ];

  const pendingCount = pendingApprovals?.length || 0;

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.approval.stats.pending')}
              value={pendingCount}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: pendingCount > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.approval.stats.myRequests')}
              value={myApprovals?.length || 0}
              prefix={<HistoryOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.approval.stats.approvedToday')}
              value={
                myApprovals?.filter(
                  (r) =>
                    r.status === 'approved' &&
                    dayjs(r.resolved_at).isSame(dayjs(), 'day')
                ).length || 0
              }
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('dataPermissions.approval.stats.rejectedToday')}
              value={
                myApprovals?.filter(
                  (r) =>
                    r.status === 'rejected' &&
                    dayjs(r.resolved_at).isSame(dayjs(), 'day')
                ).length || 0
              }
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card
        extra={
          <Button icon={<UserSwitchOutlined />} onClick={() => setDelegateModalOpen(true)}>
            {t('dataPermissions.approval.delegateApprovals')}
          </Button>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'pending',
              label: (
                <span>
                  <ClockCircleOutlined />
                  {t('dataPermissions.approval.pendingApprovals')}
                  {pendingCount > 0 && (
                    <Badge count={pendingCount} style={{ marginLeft: 8 }} />
                  )}
                </span>
              ),
              children: (
                <Table
                  columns={pendingColumns}
                  dataSource={pendingApprovals || []}
                  rowKey="id"
                  loading={pendingLoading}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 1100 }}
                />
              ),
            },
            {
              key: 'my-requests',
              label: (
                <span>
                  <HistoryOutlined />
                  {t('dataPermissions.approval.myRequests')}
                </span>
              ),
              children: (
                <Table
                  columns={myRequestColumns}
                  dataSource={myApprovals || []}
                  rowKey="id"
                  loading={myApprovalsLoading}
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 900 }}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title={t('dataPermissions.approval.requestDetails')}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {t('common:close')}
          </Button>,
        ]}
        width={700}
      >
        {selectedRequest && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="ID">{selectedRequest.id}</Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.status')}>
                <Tag color={statusColors[selectedRequest.status]}>
                  {t(`dataPermissions.approval.status.${selectedRequest.status}`)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.resource')}>{selectedRequest.resource}</Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.permissionConfig.form.resourceType')}>
                {selectedRequest.resource_type}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.action')}>{selectedRequest.action}</Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.sensitivity')}>
                <Tag color={sensitivityColors[selectedRequest.sensitivity_level]}>
                  {t(`sensitivity.${selectedRequest.sensitivity_level}`)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.requester')} span={2}>
                {selectedRequest.requester_id}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.permissionConfig.test.reason')} span={2}>
                {selectedRequest.reason}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.created')}>
                {dayjs(selectedRequest.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label={t('dataPermissions.approval.columns.expires')}>
                {dayjs(selectedRequest.expires_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {approvalHistory.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h4>{t('dataPermissions.approval.approvalHistory')}</h4>
                <Timeline
                  items={approvalHistory.map((action) => ({
                    color: action.decision === 'approved' ? 'green' : 'red',
                    children: (
                      <div>
                        <div>
                          <strong>{t('dataPermissions.approval.columns.level')} {action.approval_level}</strong> -{' '}
                          <Tag color={action.decision === 'approved' ? 'success' : 'error'}>
                            {t(`dataPermissions.approval.status.${action.decision}`)}
                          </Tag>
                        </div>
                        <div style={{ fontSize: 12, color: '#666' }}>
                          {t('audit.user')}: {action.approver_id}
                          {action.delegated_from && ` (${t('dataPermissions.approval.delegateApprovals')} ${action.delegated_from})`}
                        </div>
                        {action.comments && (
                          <div style={{ fontSize: 12, marginTop: 4 }}>{action.comments}</div>
                        )}
                        <div style={{ fontSize: 12, color: '#999' }}>
                          {dayjs(action.action_at).format('YYYY-MM-DD HH:mm:ss')}
                        </div>
                      </div>
                    ),
                  }))}
                />
              </div>
            )}
          </>
        )}
      </Modal>

      {/* Decision Modal */}
      <Modal
        title={`${decisionForm.getFieldValue('decision') === 'approved' ? t('dataPermissions.approval.approve') : t('dataPermissions.approval.reject')} ${t('dataPermissions.approval.requestDetails')}`}
        open={decisionModalOpen}
        onCancel={() => setDecisionModalOpen(false)}
        onOk={() => decisionForm.submit()}
        confirmLoading={decisionMutation.isPending}
      >
        <Form form={decisionForm} layout="vertical" onFinish={handleDecisionSubmit}>
          <Form.Item name="decision" hidden>
            <Input />
          </Form.Item>

          {selectedRequest && (
            <Alert
              message={`${t('dataPermissions.approval.columns.resource')}: ${selectedRequest.resource}`}
              description={`${t('dataPermissions.approval.columns.action')}: ${selectedRequest.action} | ${t('dataPermissions.approval.columns.sensitivity')}: ${t(`sensitivity.${selectedRequest.sensitivity_level}`)}`}
              type="info"
              style={{ marginBottom: 16 }}
            />
          )}

          <Form.Item name="comments" label={t('dataPermissions.approval.comments')}>
            <TextArea rows={4} placeholder={t('dataPermissions.approval.commentsPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Delegate Modal */}
      <Modal
        title={t('dataPermissions.approval.delegation.title')}
        open={delegateModalOpen}
        onCancel={() => setDelegateModalOpen(false)}
        onOk={() => delegateForm.submit()}
        confirmLoading={delegateMutation.isPending}
      >
        <Form form={delegateForm} layout="vertical" onFinish={handleDelegateSubmit}>
          <Form.Item
            name="delegate_to"
            label={t('dataPermissions.approval.delegation.delegateTo')}
            rules={[{ required: true, message: t('dataPermissions.approval.delegation.delegateTo') }]}
          >
            <Input placeholder={t('dataPermissions.approval.delegation.delegateToPlaceholder')} />
          </Form.Item>

          <Form.Item
            name="start_date"
            label={t('dataPermissions.approval.delegation.startDate')}
            rules={[{ required: true, message: t('dataPermissions.approval.delegation.startDate') }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="end_date"
            label={t('dataPermissions.approval.delegation.endDate')}
            rules={[{ required: true, message: t('dataPermissions.approval.delegation.endDate') }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApprovalWorkflowPage;
