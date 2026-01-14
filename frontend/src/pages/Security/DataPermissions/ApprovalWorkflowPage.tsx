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
      message.success('Decision submitted successfully');
    },
    onError: () => {
      message.error('Failed to submit decision');
    },
  });

  // Delegate mutation
  const delegateMutation = useMutation({
    mutationFn: (data: DelegationRequest) => dataPermissionApi.delegateApproval(data),
    onSuccess: () => {
      setDelegateModalOpen(false);
      delegateForm.resetFields();
      message.success('Delegation created successfully');
    },
    onError: () => {
      message.error('Failed to create delegation');
    },
  });

  // Fetch approval history
  const fetchHistory = async (requestId: string) => {
    try {
      const history = await dataPermissionApi.getApprovalHistory(requestId);
      setApprovalHistory(history);
    } catch {
      message.error('Failed to fetch approval history');
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
      title: 'Resource',
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource}</div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.resource_type}</div>
        </div>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => <Tag>{action.toUpperCase()}</Tag>,
    },
    {
      title: 'Requester',
      dataIndex: 'requester_id',
      key: 'requester_id',
      width: 150,
      ellipsis: true,
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
      title: 'Level',
      dataIndex: 'current_level',
      key: 'current_level',
      width: 80,
      render: (level) => <Badge count={level} style={{ backgroundColor: '#1890ff' }} />,
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Expires',
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
      title: 'Actions',
      key: 'actions',
      width: 200,
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
          <Tooltip title="Approve">
            <Button
              type="link"
              size="small"
              icon={<CheckOutlined />}
              style={{ color: '#52c41a' }}
              onClick={() => handleDecision(record, 'approved')}
            />
          </Tooltip>
          <Tooltip title="Reject">
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
      title: 'Resource',
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource}</div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.resource_type}</div>
        </div>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => <Tag>{action.toUpperCase()}</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: ApprovalStatus) => (
        <Tag color={statusColors[status]}>{status.toUpperCase()}</Tag>
      ),
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
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Resolved',
      dataIndex: 'resolved_at',
      key: 'resolved_at',
      width: 150,
      render: (date) => (date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: 'Actions',
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
              title="Pending Approvals"
              value={pendingCount}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: pendingCount > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="My Requests"
              value={myApprovals?.length || 0}
              prefix={<HistoryOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="Approved Today"
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
              title="Rejected Today"
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
            Delegate Approvals
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
                  Pending Approvals
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
                  My Requests
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
        title="Approval Request Details"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            Close
          </Button>,
        ]}
        width={700}
      >
        {selectedRequest && (
          <>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="ID">{selectedRequest.id}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={statusColors[selectedRequest.status]}>
                  {selectedRequest.status.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Resource">{selectedRequest.resource}</Descriptions.Item>
              <Descriptions.Item label="Resource Type">
                {selectedRequest.resource_type}
              </Descriptions.Item>
              <Descriptions.Item label="Action">{selectedRequest.action}</Descriptions.Item>
              <Descriptions.Item label="Sensitivity">
                <Tag color={sensitivityColors[selectedRequest.sensitivity_level]}>
                  {selectedRequest.sensitivity_level}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Requester" span={2}>
                {selectedRequest.requester_id}
              </Descriptions.Item>
              <Descriptions.Item label="Reason" span={2}>
                {selectedRequest.reason}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {dayjs(selectedRequest.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Expires">
                {dayjs(selectedRequest.expires_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            {approvalHistory.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <h4>Approval History</h4>
                <Timeline
                  items={approvalHistory.map((action) => ({
                    color: action.decision === 'approved' ? 'green' : 'red',
                    children: (
                      <div>
                        <div>
                          <strong>Level {action.approval_level}</strong> -{' '}
                          <Tag color={action.decision === 'approved' ? 'success' : 'error'}>
                            {action.decision.toUpperCase()}
                          </Tag>
                        </div>
                        <div style={{ fontSize: 12, color: '#666' }}>
                          By: {action.approver_id}
                          {action.delegated_from && ` (delegated from ${action.delegated_from})`}
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
        title={`${decisionForm.getFieldValue('decision') === 'approved' ? 'Approve' : 'Reject'} Request`}
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
              message={`Resource: ${selectedRequest.resource}`}
              description={`Action: ${selectedRequest.action} | Sensitivity: ${selectedRequest.sensitivity_level}`}
              type="info"
              style={{ marginBottom: 16 }}
            />
          )}

          <Form.Item name="comments" label="Comments">
            <TextArea rows={4} placeholder="Add comments (optional)" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Delegate Modal */}
      <Modal
        title="Delegate Approvals"
        open={delegateModalOpen}
        onCancel={() => setDelegateModalOpen(false)}
        onOk={() => delegateForm.submit()}
        confirmLoading={delegateMutation.isPending}
      >
        <Form form={delegateForm} layout="vertical" onFinish={handleDelegateSubmit}>
          <Form.Item
            name="delegate_to"
            label="Delegate To"
            rules={[{ required: true, message: 'Please enter delegate user ID' }]}
          >
            <Input placeholder="User ID to delegate approvals to" />
          </Form.Item>

          <Form.Item
            name="start_date"
            label="Start Date"
            rules={[{ required: true, message: 'Please select start date' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="end_date"
            label="End Date"
            rules={[{ required: true, message: 'Please select end date' }]}
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApprovalWorkflowPage;
