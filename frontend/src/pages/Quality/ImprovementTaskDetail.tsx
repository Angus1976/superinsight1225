/**
 * Improvement Task Detail Component - 改进任务详情组件
 * 实现改进任务的详情查看、编辑和审核功能
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Descriptions,
  Timeline,
  Form,
  Input,
  message,
  Spin,
  Row,
  Col,
  Alert,
  Modal,
  Divider,
  Avatar,
  List,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  SendOutlined,
  UserOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { workflowApi, type ImprovementTask, type ImprovementHistory, type QualityIssue } from '@/services/workflowApi';

const { TextArea } = Input;

const ImprovementTaskDetail: React.FC = () => {
  const { t } = useTranslation(['quality', 'common']);
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<ImprovementTask | null>(null);
  const [history, setHistory] = useState<ImprovementHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [reviewForm] = Form.useForm();

  useEffect(() => {
    if (taskId) {
      loadTask();
      loadHistory();
    }
  }, [taskId]);

  const loadTask = async () => {
    setLoading(true);
    try {
      const data = await workflowApi.getTask(taskId!);
      setTask(data);
      if (data.improved_data) {
        form.setFieldsValue({ improved_data: JSON.stringify(data.improved_data, null, 2) });
      }
    } catch {
      message.error(t('improvementTask.loadDetailError'));
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await workflowApi.getTaskHistory(taskId!);
      setHistory(data);
    } catch {
      // History is optional
    }
  };

  const handleSubmitImprovement = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const improvedData = JSON.parse(values.improved_data);
      await workflowApi.submitImprovement(taskId!, { improved_data: improvedData });
      message.success(t('improvementTaskDetail.improvementSubmitted'));
      setEditMode(false);
      loadTask();
      loadHistory();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error(t('improvementTaskDetail.jsonFormatError'));
      } else {
        message.error(t('improvementTaskDetail.submitFailed'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleReview = async (approved: boolean) => {
    try {
      const values = await reviewForm.validateFields();
      setSubmitting(true);
      await workflowApi.reviewImprovement(taskId!, {
        approved,
        comments: values.comments,
      });
      message.success(approved ? t('improvementTaskDetail.approved') : t('improvementTaskDetail.rejected'));
      setReviewModalVisible(false);
      loadTask();
      loadHistory();
    } catch {
      message.error(t('improvementTaskDetail.reviewFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: t('improvementTask.status.pending') },
      in_progress: { color: 'processing', text: t('improvementTask.status.inProgress') },
      submitted: { color: 'warning', text: t('improvementTask.status.submitted') },
      approved: { color: 'success', text: t('improvementTask.status.approved') },
      rejected: { color: 'error', text: t('improvementTask.status.rejected') },
    };
    return configs[status] || { color: 'default', text: status };
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'red',
      high: 'orange',
      medium: 'gold',
      low: 'blue',
    };
    return colors[severity] || 'default';
  };

  const getPriorityText = (priority: number) => {
    if (priority >= 3) return { color: 'red', text: t('improvementTask.priority.high') };
    if (priority >= 2) return { color: 'orange', text: t('improvementTask.priority.medium') };
    return { color: 'blue', text: t('improvementTask.priority.low') };
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!task) {
    return <Alert message={t('improvementTaskDetail.taskNotExist')} type="error" />;
  }

  const statusConfig = getStatusConfig(task.status);
  const priorityConfig = getPriorityText(task.priority);
  const canEdit = task.status === 'pending' || task.status === 'in_progress' || task.status === 'rejected';
  const canReview = task.status === 'submitted';

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        {t('improvementTaskDetail.backToList')}
      </Button>

      <Row gutter={16}>
        <Col span={16}>
          {/* 基本信息 */}
          <Card
            title={t('improvementTaskDetail.taskDetail')}
            extra={
              <Space>
                <Tag color={statusConfig.color}>{statusConfig.text}</Tag>
                <Tag color={priorityConfig.color}>{priorityConfig.text}</Tag>
              </Space>
            }
          >
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label={t('improvementTaskDetail.taskId')}>{task.id}</Descriptions.Item>
              <Descriptions.Item label={t('improvementTaskDetail.annotationId')}>{task.annotation_id}</Descriptions.Item>
              <Descriptions.Item label={t('improvementTaskDetail.assignee')}>
                <Space>
                  <Avatar size="small" icon={<UserOutlined />} />
                  {task.assignee_name || t('improvementTask.unassigned')}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label={t('improvementTaskDetail.reviewer')}>
                {task.reviewer_name ? (
                  <Space>
                    <Avatar size="small" icon={<UserOutlined />} />
                    {task.reviewer_name}
                  </Space>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label={t('improvementTaskDetail.createdAt')}>{new Date(task.created_at).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label={t('improvementTaskDetail.submittedAt')}>{task.submitted_at ? new Date(task.submitted_at).toLocaleString() : '-'}</Descriptions.Item>
              <Descriptions.Item label={t('improvementTaskDetail.reviewedAt')} span={2}>
                {task.reviewed_at ? new Date(task.reviewed_at).toLocaleString() : '-'}
              </Descriptions.Item>
              {task.review_comments && (
                <Descriptions.Item label={t('improvementTaskDetail.reviewComments')} span={2}>
                  {task.review_comments}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          {/* 问题列表 */}
          <Card title={t('improvementTaskDetail.qualityIssues')} style={{ marginTop: 16 }}>
            <List
              dataSource={task.issues}
              renderItem={(issue: QualityIssue) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<ExclamationCircleOutlined style={{ fontSize: 20, color: getSeverityColor(issue.severity) }} />}
                    title={
                      <Space>
                        <span>{issue.rule_name}</span>
                        <Tag color={getSeverityColor(issue.severity)}>{t(`rules.severities.${issue.severity}`)}</Tag>
                      </Space>
                    }
                    description={
                      <>
                        <div>{issue.message}</div>
                        {issue.field && <Tag style={{ marginTop: 4 }}>{t('improvementTaskDetail.field')}: {issue.field}</Tag>}
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>

          {/* 改进数据 */}
          <Card
            title={t('improvementTaskDetail.improvedData')}
            style={{ marginTop: 16 }}
            extra={
              canEdit && (
                <Button icon={<EditOutlined />} onClick={() => setEditMode(!editMode)}>
                  {editMode ? t('improvementTaskDetail.cancelEdit') : t('improvementTaskDetail.edit')}
                </Button>
              )
            }
          >
            {editMode ? (
              <Form form={form} layout="vertical">
                <Form.Item name="improved_data" label={t('improvementTaskDetail.improvedDataLabel')} rules={[{ required: true, message: t('improvementTaskDetail.inputImprovedData') }]}>
                  <TextArea rows={10} style={{ fontFamily: 'monospace' }} placeholder={t('improvementTaskDetail.improvedDataPlaceholder')} />
                </Form.Item>
                <Form.Item>
                  <Space>
                    <Button type="primary" icon={<SendOutlined />} onClick={handleSubmitImprovement} loading={submitting}>
                      {t('improvementTaskDetail.submitImprovement')}
                    </Button>
                    <Button onClick={() => setEditMode(false)}>{t('improvementTaskDetail.cancel')}</Button>
                  </Space>
                </Form.Item>
              </Form>
            ) : (
              <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto' }}>
                {task.improved_data ? JSON.stringify(task.improved_data, null, 2) : t('improvementTaskDetail.noImprovedData')}
              </pre>
            )}
          </Card>

          {/* 审核操作 */}
          {canReview && (
            <Card style={{ marginTop: 16 }}>
              <Alert message={t('improvementTaskDetail.pendingReview')} type="info" showIcon style={{ marginBottom: 16 }} />
              <Space>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => {
                    reviewForm.resetFields();
                    setReviewModalVisible(true);
                  }}
                >
                  {t('improvementTaskDetail.approve')}
                </Button>
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => {
                    reviewForm.resetFields();
                    setReviewModalVisible(true);
                  }}
                >
                  {t('improvementTaskDetail.reject')}
                </Button>
              </Space>
            </Card>
          )}
        </Col>

        <Col span={8}>
          {/* 操作历史 */}
          <Card title={t('improvementTaskDetail.operationHistory')}>
            <Timeline
              items={history.map((h) => ({
                color: h.action === 'approved' ? 'green' : h.action === 'rejected' ? 'red' : 'blue',
                children: (
                  <div>
                    <div style={{ fontWeight: 500 }}>{h.action}</div>
                    <div style={{ color: '#999', fontSize: 12 }}>
                      {h.actor_name} · {new Date(h.created_at).toLocaleString()}
                    </div>
                  </div>
                ),
              }))}
            />
            {history.length === 0 && <div style={{ color: '#999', textAlign: 'center' }}>{t('improvementTaskDetail.noHistory')}</div>}
          </Card>
        </Col>
      </Row>

      {/* 审核弹窗 */}
      <Modal
        title={t('improvementTaskDetail.reviewImprovement')}
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setReviewModalVisible(false)}>{t('improvementTaskDetail.cancel')}</Button>
            <Button danger onClick={() => handleReview(false)} loading={submitting}>
              {t('improvementTaskDetail.reject')}
            </Button>
            <Button type="primary" onClick={() => handleReview(true)} loading={submitting}>
              {t('improvementTaskDetail.approve')}
            </Button>
          </Space>
        }
      >
        <Form form={reviewForm} layout="vertical">
          <Form.Item name="comments" label={t('improvementTaskDetail.reviewCommentsLabel')}>
            <TextArea rows={4} placeholder={t('improvementTaskDetail.reviewCommentsPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ImprovementTaskDetail;
