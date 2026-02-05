/**
 * ChangeRequestReviewPanel Component (变更请求审核面板)
 * 
 * Panel for reviewing change requests with:
 * - Change request details display
 * - Impact analysis report
 * - Before/after comparison
 * - Approve/Reject/Request Changes actions
 * - Comment box for feedback
 * 
 * Requirements: 4.2, 4.3, 4.4, 10.4
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Alert,
  Divider,
  Form,
  Input,
  Modal,
  message,
  Typography,
  Spin,
  Row,
  Col,
  Statistic,
  List,
  Collapse,
  Progress,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  BranchesOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  ontologyApprovalApi,
  ontologyImpactApi,
  type ChangeRequest,
  type ImpactReport,
} from '../../services/ontologyExpertApi';
import ChangeComparisonView from './ChangeComparisonView';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

interface ChangeRequestReviewPanelProps {
  changeRequest: ChangeRequest;
  expertId: string;
  onActionComplete?: () => void;
}

const ChangeRequestReviewPanel: React.FC<ChangeRequestReviewPanelProps> = ({
  changeRequest,
  expertId,
  onActionComplete,
}) => {
  const { t } = useTranslation('ontology');
  const [impactReport, setImpactReport] = useState<ImpactReport | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  
  // Modal states
  const [approveModalVisible, setApproveModalVisible] = useState(false);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [changesModalVisible, setChangesModalVisible] = useState(false);
  
  const [approveForm] = Form.useForm();
  const [rejectForm] = Form.useForm();
  const [changesForm] = Form.useForm();

  // Load impact report
  useEffect(() => {
    const loadImpactReport = async () => {
      if (changeRequest.impact_analysis) {
        setImpactReport(changeRequest.impact_analysis);
        return;
      }
      
      setLoadingImpact(true);
      try {
        const report = await ontologyImpactApi.getImpactReport(changeRequest.id);
        setImpactReport(report);
      } catch (error) {
        console.error('Failed to load impact report:', error);
        // Impact report may not exist for all requests
      } finally {
        setLoadingImpact(false);
      }
    };
    
    loadImpactReport();
  }, [changeRequest]);

  const handleApprove = async () => {
    try {
      const values = await approveForm.validateFields();
      setActionLoading(true);
      
      await ontologyApprovalApi.approveChangeRequest(
        changeRequest.id,
        expertId,
        values.reason
      );
      
      message.success(t('approval.approveSuccess'));
      setApproveModalVisible(false);
      approveForm.resetFields();
      onActionComplete?.();
    } catch (error) {
      console.error('Failed to approve:', error);
      message.error(t('approval.approveFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    try {
      const values = await rejectForm.validateFields();
      setActionLoading(true);
      
      await ontologyApprovalApi.rejectChangeRequest(
        changeRequest.id,
        expertId,
        values.reason
      );
      
      message.success(t('approval.rejectSuccess'));
      setRejectModalVisible(false);
      rejectForm.resetFields();
      onActionComplete?.();
    } catch (error) {
      console.error('Failed to reject:', error);
      message.error(t('approval.rejectFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestChanges = async () => {
    try {
      const values = await changesForm.validateFields();
      setActionLoading(true);
      
      await ontologyApprovalApi.requestChanges(
        changeRequest.id,
        expertId,
        values.feedback
      );
      
      message.success(t('approval.requestChangesSuccess'));
      setChangesModalVisible(false);
      changesForm.resetFields();
      onActionComplete?.();
    } catch (error) {
      console.error('Failed to request changes:', error);
      message.error(t('approval.requestChangesFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      submitted: 'blue',
      in_review: 'processing',
      approved: 'success',
      rejected: 'error',
      changes_requested: 'warning',
    };
    return colors[status] || 'default';
  };

  const getChangeTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      ADD: 'green',
      MODIFY: 'blue',
      DELETE: 'red',
    };
    return colors[type] || 'default';
  };

  const getComplexityColor = (complexity: string) => {
    const colors: Record<string, string> = {
      LOW: 'green',
      MEDIUM: 'orange',
      HIGH: 'red',
    };
    return colors[complexity] || 'default';
  };

  const renderImpactAnalysis = () => {
    if (loadingImpact) {
      return <Spin tip={t('common.loading')} />;
    }

    if (!impactReport) {
      return (
        <Alert
          message={t('approval.noImpactAnalysis')}
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />
      );
    }

    return (
      <div>
        {/* High Impact Warning */}
        {impactReport.requires_high_impact_approval && (
          <Alert
            message={t('approval.highImpactWarning')}
            description={t('approval.highImpactWarningDesc')}
            type="warning"
            showIcon
            icon={<ExclamationCircleOutlined />}
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Impact Statistics */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={t('approval.affectedEntities')}
                value={impactReport.affected_entity_count}
                prefix={<BranchesOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={t('approval.affectedRelations')}
                value={impactReport.affected_relation_count}
                prefix={<BranchesOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={t('approval.estimatedHours')}
                value={impactReport.estimated_migration_hours}
                suffix="h"
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Text type="secondary">{t('approval.migrationComplexity')}</Text>
                <div style={{ marginTop: 8 }}>
                  <Tag color={getComplexityColor(impactReport.migration_complexity)}>
                    {t(`approval.complexity${impactReport.migration_complexity.charAt(0) + impactReport.migration_complexity.slice(1).toLowerCase()}`)}
                  </Tag>
                </div>
              </div>
            </Card>
          </Col>
        </Row>

        {/* Affected Projects */}
        {impactReport.affected_projects.length > 0 && (
          <Card size="small" title={t('approval.affectedProjects')} style={{ marginBottom: 16 }}>
            <Space wrap>
              {impactReport.affected_projects.map((project) => (
                <Tag key={project} icon={<FileTextOutlined />}>
                  {project}
                </Tag>
              ))}
            </Space>
          </Card>
        )}

        {/* Breaking Changes */}
        <Card size="small" title={t('approval.breakingChanges')} style={{ marginBottom: 16 }}>
          {impactReport.breaking_changes.length > 0 ? (
            <List
              size="small"
              dataSource={impactReport.breaking_changes}
              renderItem={(change) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<WarningOutlined style={{ color: '#ff4d4f' }} />}
                    title={`${change.element_type}: ${change.element_id}`}
                    description={
                      <Space direction="vertical" size={0}>
                        <Text type="secondary">{change.reason}</Text>
                        <Text type="secondary">
                          {t('approval.affectedEntities')}: {change.affected_count}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          ) : (
            <Text type="secondary">{t('approval.noBreakingChanges')}</Text>
          )}
        </Card>

        {/* Recommendations */}
        <Card size="small" title={t('approval.recommendations')}>
          {impactReport.recommendations.length > 0 ? (
            <List
              size="small"
              dataSource={impactReport.recommendations}
              renderItem={(rec) => (
                <List.Item>
                  <Space>
                    <ThunderboltOutlined style={{ color: '#1890ff' }} />
                    <Text>{rec}</Text>
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Text type="secondary">{t('approval.noRecommendations')}</Text>
          )}
        </Card>
      </div>
    );
  };

  return (
    <div>
      {/* Change Request Details */}
      <Card title={t('approval.reviewTitle')} style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label={t('comparison.changeType')}>
            <Tag color={getChangeTypeColor(changeRequest.change_type)}>
              {t(`comparison.changeType${changeRequest.change_type.charAt(0) + changeRequest.change_type.slice(1).toLowerCase()}`)}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('comparison.status')}>
            <Tag color={getStatusColor(changeRequest.status)}>
              {t(`comparison.status${changeRequest.status.charAt(0).toUpperCase() + changeRequest.status.slice(1).replace(/_/g, '')}`)}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('comparison.targetElement')}>
            {changeRequest.target_element}
          </Descriptions.Item>
          <Descriptions.Item label={t('comparison.createdAt')}>
            {new Date(changeRequest.created_at).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label={t('comparison.description')} span={2}>
            {changeRequest.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Collapsible Sections */}
      <Collapse defaultActiveKey={['impact', 'comparison']} style={{ marginBottom: 16 }}>
        <Panel header={t('approval.impactAnalysis')} key="impact">
          {renderImpactAnalysis()}
        </Panel>
        <Panel header={t('comparison.title')} key="comparison">
          <ChangeComparisonView changeRequest={changeRequest} />
        </Panel>
      </Collapse>

      {/* Action Buttons */}
      <Card>
        <Space size="large">
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={() => setApproveModalVisible(true)}
            size="large"
          >
            {t('approval.approve')}
          </Button>
          <Button
            danger
            icon={<CloseOutlined />}
            onClick={() => setRejectModalVisible(true)}
            size="large"
          >
            {t('approval.reject')}
          </Button>
          <Button
            icon={<EditOutlined />}
            onClick={() => setChangesModalVisible(true)}
            size="large"
          >
            {t('approval.requestChanges')}
          </Button>
        </Space>
      </Card>

      {/* Approve Modal */}
      <Modal
        title={t('approval.approve')}
        open={approveModalVisible}
        onOk={handleApprove}
        onCancel={() => {
          setApproveModalVisible(false);
          approveForm.resetFields();
        }}
        confirmLoading={actionLoading}
        okText={t('approval.approve')}
      >
        <Form form={approveForm} layout="vertical">
          <Form.Item
            name="reason"
            label={t('approval.approveReason')}
          >
            <TextArea
              rows={4}
              placeholder={t('approval.approveReasonPlaceholder')}
            />
          </Form.Item>
        </Form>
      </Modal>

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

export default ChangeRequestReviewPanel;
