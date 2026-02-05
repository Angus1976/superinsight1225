/**
 * PendingApprovalsDashboard Component (待审批仪表板)
 * 
 * Dashboard showing pending approvals for the current expert with:
 * - List of pending approvals sorted by deadline
 * - Filter by ontology area
 * - Quick approve/reject actions
 * - Urgency indicators
 * 
 * Requirements: 4.1, 13.2
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Input,
  Empty,
  Badge,
  Tooltip,
  Modal,
  Form,
  message,
  Typography,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import {
  ontologyApprovalApi,
  type PendingApproval,
} from '../../services/ontologyExpertApi';

const { Text } = Typography;
const { TextArea } = Input;

interface PendingApprovalsDashboardProps {
  expertId: string;
  onViewRequest?: (changeRequestId: string) => void;
}

const ONTOLOGY_AREAS = [
  '金融',
  '医疗',
  '制造',
  '政务',
  '法律',
  '教育',
];

const PendingApprovalsDashboard: React.FC<PendingApprovalsDashboardProps> = ({
  expertId,
  onViewRequest,
}) => {
  const { t } = useTranslation('ontology');
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterArea, setFilterArea] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');
  
  // Modal states
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [changesModalVisible, setChangesModalVisible] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<PendingApproval | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectForm] = Form.useForm();
  const [changesForm] = Form.useForm();

  const loadApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const data = await ontologyApprovalApi.getPendingApprovals(expertId);
      setApprovals(data);
    } catch (error) {
      console.error('Failed to load pending approvals:', error);
      message.error(t('approval.loadError'));
    } finally {
      setLoading(false);
    }
  }, [expertId, t]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  // Calculate urgency based on deadline
  const getUrgencyInfo = (deadline: string) => {
    const deadlineDate = new Date(deadline);
    const now = new Date();
    const hoursRemaining = (deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60);

    if (hoursRemaining < 0) {
      return { status: 'error' as const, text: t('approval.overdue'), color: 'red' };
    } else if (hoursRemaining < 4) {
      return { status: 'warning' as const, text: t('approval.urgent'), color: 'orange' };
    } else if (hoursRemaining < 24) {
      return { status: 'processing' as const, text: t('approval.dueSoon'), color: 'gold' };
    }
    return { 
      status: 'default' as const, 
      text: t('approval.dueIn', { hours: Math.round(hoursRemaining) }), 
      color: 'blue' 
    };
  };

  const handleQuickApprove = async (approval: PendingApproval) => {
    setActionLoading(true);
    try {
      await ontologyApprovalApi.approveChangeRequest(
        approval.change_request_id,
        expertId
      );
      message.success(t('approval.approveSuccess'));
      loadApprovals();
    } catch (error) {
      console.error('Failed to approve:', error);
      message.error(t('approval.approveFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedApproval) return;
    
    try {
      const values = await rejectForm.validateFields();
      setActionLoading(true);
      
      await ontologyApprovalApi.rejectChangeRequest(
        selectedApproval.change_request_id,
        expertId,
        values.reason
      );
      
      message.success(t('approval.rejectSuccess'));
      setRejectModalVisible(false);
      rejectForm.resetFields();
      loadApprovals();
    } catch (error) {
      console.error('Failed to reject:', error);
      message.error(t('approval.rejectFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestChanges = async () => {
    if (!selectedApproval) return;
    
    try {
      const values = await changesForm.validateFields();
      setActionLoading(true);
      
      await ontologyApprovalApi.requestChanges(
        selectedApproval.change_request_id,
        expertId,
        values.feedback
      );
      
      message.success(t('approval.requestChangesSuccess'));
      setChangesModalVisible(false);
      changesForm.resetFields();
      loadApprovals();
    } catch (error) {
      console.error('Failed to request changes:', error);
      message.error(t('approval.requestChangesFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const openRejectModal = (approval: PendingApproval) => {
    setSelectedApproval(approval);
    setRejectModalVisible(true);
  };

  const openChangesModal = (approval: PendingApproval) => {
    setSelectedApproval(approval);
    setChangesModalVisible(true);
  };

  // Filter approvals
  const filteredApprovals = approvals.filter((approval) => {
    if (filterArea && approval.ontology_area !== filterArea) return false;
    if (searchText) {
      const search = searchText.toLowerCase();
      return (
        approval.requester_name.toLowerCase().includes(search) ||
        approval.target_element.toLowerCase().includes(search)
      );
    }
    return true;
  });

  // Statistics
  const overdueCount = approvals.filter((a) => {
    const deadline = new Date(a.deadline);
    return deadline < new Date();
  }).length;

  const urgentCount = approvals.filter((a) => {
    const deadline = new Date(a.deadline);
    const hoursRemaining = (deadline.getTime() - new Date().getTime()) / (1000 * 60 * 60);
    return hoursRemaining >= 0 && hoursRemaining < 4;
  }).length;

  const columns: ColumnsType<PendingApproval> = [
    {
      title: t('approval.deadline'),
      dataIndex: 'deadline',
      key: 'deadline',
      width: 150,
      sorter: (a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime(),
      defaultSortOrder: 'ascend',
      render: (deadline: string) => {
        const urgency = getUrgencyInfo(deadline);
        return (
          <Space>
            <Badge status={urgency.status} />
            <Tag color={urgency.color} icon={<ClockCircleOutlined />}>
              {urgency.text}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: t('approval.requester'),
      dataIndex: 'requester_name',
      key: 'requester_name',
      width: 120,
    },
    {
      title: t('approval.changeType'),
      dataIndex: 'change_type',
      key: 'change_type',
      width: 100,
      render: (type: string) => {
        const colors: Record<string, string> = {
          ADD: 'green',
          MODIFY: 'blue',
          DELETE: 'red',
        };
        return <Tag color={colors[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: t('approval.targetElement'),
      dataIndex: 'target_element',
      key: 'target_element',
      ellipsis: true,
    },
    {
      title: t('approval.ontologyArea'),
      dataIndex: 'ontology_area',
      key: 'ontology_area',
      width: 100,
      render: (area: string) => <Tag>{area}</Tag>,
    },
    {
      title: t('approval.currentLevel'),
      key: 'level',
      width: 100,
      render: (_, record) => (
        <Text type="secondary">
          {t('approval.levelNumber', { number: record.current_level })}
        </Text>
      ),
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={t('approval.quickApprove')}>
            <Button
              type="primary"
              size="small"
              icon={<CheckOutlined />}
              onClick={() => handleQuickApprove(record)}
              loading={actionLoading}
            />
          </Tooltip>
          <Tooltip title={t('approval.quickReject')}>
            <Button
              danger
              size="small"
              icon={<CloseOutlined />}
              onClick={() => openRejectModal(record)}
            />
          </Tooltip>
          <Tooltip title={t('approval.requestChanges')}>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => openChangesModal(record)}
            />
          </Tooltip>
          <Tooltip title={t('approval.viewRequest')}>
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onViewRequest?.(record.change_request_id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title={t('approval.pendingApprovals')}
              value={approvals.length}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title={t('approval.urgent')}
              value={urgentCount}
              valueStyle={{ color: '#faad14' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title={t('approval.overdue')}
              value={overdueCount}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder={t('approval.searchPlaceholder')}
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          <Select
            placeholder={t('approval.filterByArea')}
            value={filterArea}
            onChange={setFilterArea}
            style={{ width: 150 }}
            allowClear
          >
            {ONTOLOGY_AREAS.map((area) => (
              <Select.Option key={area} value={area}>
                {area}
              </Select.Option>
            ))}
          </Select>
          <Button onClick={loadApprovals} loading={loading}>
            {t('common.refresh')}
          </Button>
        </Space>
      </Card>

      {/* Table */}
      <Card title={t('approval.pendingApprovals')}>
        <Table
          columns={columns}
          dataSource={filteredApprovals}
          rowKey="change_request_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1000 }}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={t('approval.noPendingApprovals')}
              />
            ),
          }}
        />
      </Card>

      {/* Reject Modal */}
      <Modal
        title={t('approval.reject')}
        open={rejectModalVisible}
        onOk={handleReject}
        onCancel={() => {
          setRejectModalVisible(false);
          rejectForm.resetFields();
        }}
        confirmLoading={actionLoading}
        okText={t('approval.reject')}
        okButtonProps={{ danger: true }}
      >
        <Form form={rejectForm} layout="vertical">
          <Form.Item
            name="reason"
            label={t('approval.rejectReason')}
            rules={[{ required: true, message: t('approval.rejectReasonRequired') }]}
          >
            <TextArea
              rows={4}
              placeholder={t('approval.rejectReasonPlaceholder')}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Request Changes Modal */}
      <Modal
        title={t('approval.requestChanges')}
        open={changesModalVisible}
        onOk={handleRequestChanges}
        onCancel={() => {
          setChangesModalVisible(false);
          changesForm.resetFields();
        }}
        confirmLoading={actionLoading}
        okText={t('approval.requestChanges')}
      >
        <Form form={changesForm} layout="vertical">
          <Form.Item
            name="feedback"
            label={t('approval.changesFeedback')}
            rules={[{ required: true, message: t('approval.changesFeedbackRequired') }]}
          >
            <TextArea
              rows={4}
              placeholder={t('approval.changesFeedbackPlaceholder')}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PendingApprovalsDashboard;
