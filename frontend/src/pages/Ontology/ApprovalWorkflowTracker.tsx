/**
 * ApprovalWorkflowTracker Component (审批流程追踪器)
 * 
 * Visual progress indicator for approval chain with:
 * - Show completed and pending levels
 * - Display approver names and timestamps
 * - Show escalations and rejections
 * - Timeline view of approval history
 * 
 * Requirements: 4.5, 13.3
 */

import React from 'react';
import {
  Card,
  Steps,
  Tag,
  Space,
  Typography,
  Timeline,
  Avatar,
  Tooltip,
  Empty,
  Badge,
  Divider,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  UserOutlined,
  SyncOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ApprovalChain, ChangeRequestStatus } from '../../services/ontologyExpertApi';

const { Text, Title } = Typography;

interface ApprovalRecord {
  level_number: number;
  approver_id: string;
  approver_name: string;
  action: 'approve' | 'reject' | 'request_changes';
  reason?: string;
  timestamp: string;
}

interface ApprovalWorkflowTrackerProps {
  chain: ApprovalChain;
  currentLevel: number;
  status: ChangeRequestStatus;
  approvalHistory?: ApprovalRecord[];
  escalated?: boolean;
}

const ApprovalWorkflowTracker: React.FC<ApprovalWorkflowTrackerProps> = ({
  chain,
  currentLevel,
  status,
  approvalHistory = [],
  escalated = false,
}) => {
  const { t } = useTranslation('ontology');

  const getStepStatus = (levelNumber: number): 'finish' | 'process' | 'wait' | 'error' => {
    if (status === 'rejected') {
      // Find which level rejected
      const rejectionRecord = approvalHistory.find(
        (r) => r.action === 'reject' && r.level_number === levelNumber
      );
      if (rejectionRecord) return 'error';
      if (levelNumber < currentLevel) return 'finish';
      return 'wait';
    }
    
    if (status === 'approved') {
      return 'finish';
    }
    
    if (levelNumber < currentLevel) {
      return 'finish';
    } else if (levelNumber === currentLevel) {
      return 'process';
    }
    return 'wait';
  };

  const getStepIcon = (levelNumber: number) => {
    const stepStatus = getStepStatus(levelNumber);
    
    switch (stepStatus) {
      case 'finish':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'process':
        return escalated ? (
          <ExclamationCircleOutlined style={{ color: '#faad14' }} />
        ) : (
          <SyncOutlined spin style={{ color: '#1890ff' }} />
        );
      case 'error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getLevelDescription = (level: typeof chain.levels[0], levelNumber: number) => {
    const levelRecords = approvalHistory.filter((r) => r.level_number === levelNumber);
    const stepStatus = getStepStatus(levelNumber);
    
    return (
      <Space direction="vertical" size={4}>
        <Space wrap>
          {level.approvers.map((approverId, idx) => {
            const record = levelRecords.find((r) => r.approver_id === approverId);
            return (
              <Tooltip
                key={approverId}
                title={
                  record
                    ? `${record.approver_name} - ${record.action} (${new Date(record.timestamp).toLocaleString()})`
                    : approverId
                }
              >
                <Badge
                  status={
                    record?.action === 'approve'
                      ? 'success'
                      : record?.action === 'reject'
                      ? 'error'
                      : record?.action === 'request_changes'
                      ? 'warning'
                      : 'default'
                  }
                >
                  <Avatar size="small" icon={<UserOutlined />} />
                </Badge>
              </Tooltip>
            );
          })}
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>
          <ClockCircleOutlined /> {level.deadline_hours}h
          {level.min_approvals && ` | ${t('approval.minApprovals')}: ${level.min_approvals}`}
        </Text>
        {stepStatus === 'process' && escalated && (
          <Tag color="warning" icon={<ExclamationCircleOutlined />}>
            {t('approval.escalated')}
          </Tag>
        )}
      </Space>
    );
  };

  const getOverallStatusTag = () => {
    switch (status) {
      case 'approved':
        return (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            {t('approval.workflowCompleted')}
          </Tag>
        );
      case 'rejected':
        return (
          <Tag color="error" icon={<CloseCircleOutlined />}>
            {t('approval.workflowRejected')}
          </Tag>
        );
      case 'in_review':
        return (
          <Tag color="processing" icon={<SyncOutlined spin />}>
            {t('approval.workflowInProgress')}
          </Tag>
        );
      default:
        return (
          <Tag color="default" icon={<ClockCircleOutlined />}>
            {t('approval.workflowPending')}
          </Tag>
        );
    }
  };

  const renderTimeline = () => {
    if (approvalHistory.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('approval.noApprovalHistory')}
        />
      );
    }

    return (
      <Timeline mode="left">
        {approvalHistory.map((record, index) => {
          let color: string;
          let icon: React.ReactNode;
          
          switch (record.action) {
            case 'approve':
              color = 'green';
              icon = <CheckCircleOutlined />;
              break;
            case 'reject':
              color = 'red';
              icon = <CloseCircleOutlined />;
              break;
            case 'request_changes':
              color = 'orange';
              icon = <ExclamationCircleOutlined />;
              break;
            default:
              color = 'gray';
              icon = <MinusCircleOutlined />;
          }

          return (
            <Timeline.Item key={index} color={color} dot={icon}>
              <Space direction="vertical" size={0}>
                <Space>
                  <Text strong>{record.approver_name}</Text>
                  <Tag color={color}>
                    {t(`approval.levelNumber`, { number: record.level_number })}
                  </Tag>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(record.timestamp).toLocaleString()}
                </Text>
                {record.reason && (
                  <Text style={{ fontSize: 12 }}>{record.reason}</Text>
                )}
              </Space>
            </Timeline.Item>
          );
        })}
      </Timeline>
    );
  };

  return (
    <Card>
      {/* Header with overall status */}
      <Space style={{ marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          {t('approval.workflowProgress')}
        </Title>
        {getOverallStatusTag()}
        {escalated && (
          <Tooltip title={t('approval.escalatedDesc')}>
            <Tag color="warning" icon={<ExclamationCircleOutlined />}>
              {t('approval.escalated')}
            </Tag>
          </Tooltip>
        )}
      </Space>

      {/* Approval Chain Info */}
      <Space style={{ marginBottom: 16 }}>
        <Text type="secondary">{chain.name}</Text>
        <Tag>{chain.ontology_area}</Tag>
        <Tag color={chain.approval_type === 'PARALLEL' ? 'blue' : 'green'}>
          {t(`approval.approvalType${chain.approval_type.charAt(0) + chain.approval_type.slice(1).toLowerCase()}`)}
        </Tag>
      </Space>

      {/* Steps Progress */}
      <Steps
        current={currentLevel - 1}
        status={status === 'rejected' ? 'error' : undefined}
        style={{ marginBottom: 24 }}
      >
        {chain.levels.map((level, index) => (
          <Steps.Step
            key={level.level_number}
            title={t('approval.levelNumber', { number: level.level_number })}
            description={getLevelDescription(level, level.level_number)}
            icon={getStepIcon(level.level_number)}
          />
        ))}
      </Steps>

      <Divider />

      {/* Timeline History */}
      <Title level={5}>{t('approval.noApprovalHistory').replace('暂无', '')}</Title>
      {renderTimeline()}
    </Card>
  );
};

export default ApprovalWorkflowTracker;
