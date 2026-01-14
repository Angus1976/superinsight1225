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
import { workflowApi, type ImprovementTask, type ImprovementHistory, type QualityIssue } from '@/services/workflowApi';

const { TextArea } = Input;

const ImprovementTaskDetail: React.FC = () => {
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
      message.error('加载任务详情失败');
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
      message.success('改进已提交');
      setEditMode(false);
      loadTask();
      loadHistory();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('JSON 格式错误');
      } else {
        message.error('提交失败');
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
      message.success(approved ? '已批准' : '已拒绝');
      setReviewModalVisible(false);
      loadTask();
      loadHistory();
    } catch {
      message.error('审核失败');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待处理' },
      in_progress: { color: 'processing', text: '进行中' },
      submitted: { color: 'warning', text: '待审核' },
      approved: { color: 'success', text: '已通过' },
      rejected: { color: 'error', text: '已拒绝' },
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
    if (priority >= 3) return { color: 'red', text: '高优先级' };
    if (priority >= 2) return { color: 'orange', text: '中优先级' };
    return { color: 'blue', text: '低优先级' };
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!task) {
    return <Alert message="任务不存在" type="error" />;
  }

  const statusConfig = getStatusConfig(task.status);
  const priorityConfig = getPriorityText(task.priority);
  const canEdit = task.status === 'pending' || task.status === 'in_progress' || task.status === 'rejected';
  const canReview = task.status === 'submitted';

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回列表
      </Button>

      <Row gutter={16}>
        <Col span={16}>
          {/* 基本信息 */}
          <Card
            title="任务详情"
            extra={
              <Space>
                <Tag color={statusConfig.color}>{statusConfig.text}</Tag>
                <Tag color={priorityConfig.color}>{priorityConfig.text}</Tag>
              </Space>
            }
          >
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
              <Descriptions.Item label="标注ID">{task.annotation_id}</Descriptions.Item>
              <Descriptions.Item label="负责人">
                <Space>
                  <Avatar size="small" icon={<UserOutlined />} />
                  {task.assignee_name || '未分配'}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="审核人">
                {task.reviewer_name ? (
                  <Space>
                    <Avatar size="small" icon={<UserOutlined />} />
                    {task.reviewer_name}
                  </Space>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{new Date(task.created_at).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="提交时间">{task.submitted_at ? new Date(task.submitted_at).toLocaleString() : '-'}</Descriptions.Item>
              <Descriptions.Item label="审核时间" span={2}>
                {task.reviewed_at ? new Date(task.reviewed_at).toLocaleString() : '-'}
              </Descriptions.Item>
              {task.review_comments && (
                <Descriptions.Item label="审核意见" span={2}>
                  {task.review_comments}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          {/* 问题列表 */}
          <Card title="质量问题" style={{ marginTop: 16 }}>
            <List
              dataSource={task.issues}
              renderItem={(issue: QualityIssue) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<ExclamationCircleOutlined style={{ fontSize: 20, color: getSeverityColor(issue.severity) }} />}
                    title={
                      <Space>
                        <span>{issue.rule_name}</span>
                        <Tag color={getSeverityColor(issue.severity)}>{issue.severity}</Tag>
                      </Space>
                    }
                    description={
                      <>
                        <div>{issue.message}</div>
                        {issue.field && <Tag style={{ marginTop: 4 }}>字段: {issue.field}</Tag>}
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>

          {/* 改进数据 */}
          <Card
            title="改进数据"
            style={{ marginTop: 16 }}
            extra={
              canEdit && (
                <Button icon={<EditOutlined />} onClick={() => setEditMode(!editMode)}>
                  {editMode ? '取消编辑' : '编辑'}
                </Button>
              )
            }
          >
            {editMode ? (
              <Form form={form} layout="vertical">
                <Form.Item name="improved_data" label="改进后的数据 (JSON 格式)" rules={[{ required: true, message: '请输入改进数据' }]}>
                  <TextArea rows={10} style={{ fontFamily: 'monospace' }} placeholder='{"field": "value"}' />
                </Form.Item>
                <Form.Item>
                  <Space>
                    <Button type="primary" icon={<SendOutlined />} onClick={handleSubmitImprovement} loading={submitting}>
                      提交改进
                    </Button>
                    <Button onClick={() => setEditMode(false)}>取消</Button>
                  </Space>
                </Form.Item>
              </Form>
            ) : (
              <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4, overflow: 'auto' }}>
                {task.improved_data ? JSON.stringify(task.improved_data, null, 2) : '暂无改进数据'}
              </pre>
            )}
          </Card>

          {/* 审核操作 */}
          {canReview && (
            <Card style={{ marginTop: 16 }}>
              <Alert message="此任务待审核，请审核改进内容" type="info" showIcon style={{ marginBottom: 16 }} />
              <Space>
                <Button
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  onClick={() => {
                    reviewForm.resetFields();
                    setReviewModalVisible(true);
                  }}
                >
                  批准
                </Button>
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={() => {
                    reviewForm.resetFields();
                    setReviewModalVisible(true);
                  }}
                >
                  拒绝
                </Button>
              </Space>
            </Card>
          )}
        </Col>

        <Col span={8}>
          {/* 操作历史 */}
          <Card title="操作历史">
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
            {history.length === 0 && <div style={{ color: '#999', textAlign: 'center' }}>暂无操作记录</div>}
          </Card>
        </Col>
      </Row>

      {/* 审核弹窗 */}
      <Modal
        title="审核改进"
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setReviewModalVisible(false)}>取消</Button>
            <Button danger onClick={() => handleReview(false)} loading={submitting}>
              拒绝
            </Button>
            <Button type="primary" onClick={() => handleReview(true)} loading={submitting}>
              批准
            </Button>
          </Space>
        }
      >
        <Form form={reviewForm} layout="vertical">
          <Form.Item name="comments" label="审核意见">
            <TextArea rows={4} placeholder="请输入审核意见（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ImprovementTaskDetail;
