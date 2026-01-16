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
  Upload,
  Progress,
  Timeline,
  Descriptions,
  Avatar,
  Tooltip,
  message,
  Typography,
  Divider,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  EyeOutlined,
  SendOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  FileTextOutlined,
  PaperClipOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import type { UploadProps } from 'antd';

const { TextArea } = Input;
const { Text } = Typography;

export interface WorkOrder {
  id: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'inProgress' | 'completed' | 'cancelled';
  assigneeId?: string;
  assigneeName?: string;
  assigneeAvatar?: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  dueDate?: string;
  progress: number;
  issueIds: string[];
  comments: WorkOrderComment[];
  attachments: WorkOrderAttachment[];
  tags?: string[];
}

export interface WorkOrderComment {
  id: string;
  content: string;
  authorId: string;
  authorName: string;
  authorAvatar?: string;
  createdAt: string;
}

export interface WorkOrderAttachment {
  id: string;
  name: string;
  url: string;
  size: number;
  type: string;
  uploadedBy: string;
  uploadedAt: string;
}

interface WorkOrderManagerProps {
  workOrders: WorkOrder[];
  onCreateWorkOrder: (workOrder: Omit<WorkOrder, 'id' | 'createdAt' | 'updatedAt' | 'progress' | 'comments' | 'attachments'>) => Promise<void>;
  onUpdateWorkOrder: (id: string, workOrder: Partial<WorkOrder>) => Promise<void>;
  onDispatchWorkOrder: (id: string, assigneeId: string) => Promise<void>;
  onAddComment: (workOrderId: string, comment: string) => Promise<void>;
  onUploadAttachment: (workOrderId: string, file: File) => Promise<void>;
  users: Array<{ id: string; name: string; avatar?: string }>;
  loading?: boolean;
}

const WorkOrderManager: React.FC<WorkOrderManagerProps> = ({
  workOrders,
  onCreateWorkOrder,
  onUpdateWorkOrder,
  onDispatchWorkOrder,
  onAddComment,
  onUploadAttachment,
  users,
  loading = false,
}) => {
  const { t } = useTranslation(['quality', 'common']);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [dispatchModalOpen, setDispatchModalOpen] = useState(false);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<WorkOrder | null>(null);
  const [createForm] = Form.useForm();
  const [commentForm] = Form.useForm();
  const [dispatchForm] = Form.useForm();

  const handleCreateWorkOrder = async (values: Record<string, unknown>) => {
    try {
      const workOrderData = {
        title: values.title as string,
        description: values.description as string,
        priority: values.priority as WorkOrder['priority'],
        status: 'pending' as const,
        createdBy: 'current-user', // Should be from auth context
        dueDate: values.dueDate ? (values.dueDate as any).toISOString() : undefined,
        issueIds: values.issueIds as string[] || [],
        tags: values.tags as string[] || [],
      };

      await onCreateWorkOrder(workOrderData);
      message.success(t('messages.workOrderCreated'));
      setCreateModalOpen(false);
      createForm.resetFields();
    } catch (error) {
      message.error(t('operationFailed'));
    }
  };

  const handleDispatchWorkOrder = async (values: Record<string, unknown>) => {
    if (!selectedWorkOrder) return;

    try {
      await onDispatchWorkOrder(selectedWorkOrder.id, values.assigneeId as string);
      message.success(t('messages.workOrderDispatched'));
      setDispatchModalOpen(false);
      dispatchForm.resetFields();
    } catch (error) {
      message.error(t('operationFailed'));
    }
  };

  const handleAddComment = async (values: Record<string, unknown>) => {
    if (!selectedWorkOrder) return;

    try {
      await onAddComment(selectedWorkOrder.id, values.comment as string);
      message.success(t('success'));
      commentForm.resetFields();
    } catch (error) {
      message.error(t('operationFailed'));
    }
  };

  const handleViewDetail = (workOrder: WorkOrder) => {
    setSelectedWorkOrder(workOrder);
    setDetailModalOpen(true);
  };

  const handleDispatch = (workOrder: WorkOrder) => {
    setSelectedWorkOrder(workOrder);
    setDispatchModalOpen(true);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    beforeUpload: (file) => {
      if (selectedWorkOrder) {
        onUploadAttachment(selectedWorkOrder.id, file);
      }
      return false; // Prevent default upload
    },
  };

  const priorityColors = {
    low: 'green',
    medium: 'blue',
    high: 'orange',
    urgent: 'red',
  };

  const statusColors = {
    pending: 'default',
    inProgress: 'processing',
    completed: 'success',
    cancelled: 'error',
  } as const;

  const columns: ColumnsType<WorkOrder> = [
    {
      title: t('workOrders.title'),
      dataIndex: 'title',
      key: 'title',
      render: (title, record) => (
        <div>
          <Text strong>{title}</Text>
          <div style={{ fontSize: '12px', color: '#666' }}>
            #{record.id}
          </div>
        </div>
      ),
    },
    {
      title: t('workOrders.priority'),
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: keyof typeof priorityColors) => (
        <Tag color={priorityColors[priority]}>
          {t(`quality.workOrders.priorities.${priority}`)}
        </Tag>
      ),
    },
    {
      title: t('workOrders.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>
          {t(`quality.workOrders.statuses.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('workOrders.assignee'),
      dataIndex: 'assigneeName',
      key: 'assignee',
      width: 150,
      render: (name, record) => (
        name ? (
          <Space>
            <Avatar size="small" src={record.assigneeAvatar} icon={<UserOutlined />} />
            <Text>{name}</Text>
          </Space>
        ) : (
          <Text type="secondary">{t('unassigned')}</Text>
        )
      ),
    },
    {
      title: t('workOrders.progress'),
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress) => (
        <Progress
          percent={progress}
          size="small"
          status={progress === 100 ? 'success' : 'active'}
        />
      ),
    },
    {
      title: t('workOrders.dueDate'),
      dataIndex: 'dueDate',
      key: 'dueDate',
      width: 120,
      render: (date) => (
        date ? new Date(date).toLocaleDateString() : '-'
      ),
    },
    {
      title: t('actions'),
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('view')}>
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          {record.status === 'pending' && (
            <Tooltip title={t('workOrders.dispatch')}>
              <Button
                type="text"
                size="small"
                icon={<SendOutlined />}
                onClick={() => handleDispatch(record)}
              />
            </Tooltip>
          )}
          <Tooltip title={t('edit')}>
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Calculate statistics
  const stats = {
    total: workOrders.length,
    pending: workOrders.filter(w => w.status === 'pending').length,
    inProgress: workOrders.filter(w => w.status === 'inProgress').length,
    completed: workOrders.filter(w => w.status === 'completed').length,
  };

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('total')}
              value={stats.total}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('workOrders.statuses.pending')}
              value={stats.pending}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('workOrders.statuses.inProgress')}
              value={stats.inProgress}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('workOrders.statuses.completed')}
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Work Orders Table */}
      <Card
        title={t('workOrders.title')}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            {t('workOrders.create')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={workOrders}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} ${t('of')} ${total} ${t('items')}`,
          }}
        />
      </Card>

      {/* Create Work Order Modal */}
      <Modal
        title={t('workOrders.create')}
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        onOk={() => createForm.submit()}
        width={600}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateWorkOrder}
        >
          <Form.Item
            name="title"
            label={t('workOrders.title')}
            rules={[{ required: true, message: t('required') }]}
          >
            <Input placeholder={t('workOrders.title')} />
          </Form.Item>

          <Form.Item
            name="description"
            label={t('rules.description')}
            rules={[{ required: true, message: t('required') }]}
          >
            <TextArea rows={4} placeholder={t('rules.description')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label={t('workOrders.priority')}
                rules={[{ required: true, message: t('required') }]}
                initialValue="medium"
              >
                <Select>
                  <Select.Option value="low">{t('workOrders.priorities.low')}</Select.Option>
                  <Select.Option value="medium">{t('workOrders.priorities.medium')}</Select.Option>
                  <Select.Option value="high">{t('workOrders.priorities.high')}</Select.Option>
                  <Select.Option value="urgent">{t('workOrders.priorities.urgent')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dueDate"
                label={t('workOrders.dueDate')}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="issueIds"
            label={t('issues.title')}
          >
            <Select
              mode="multiple"
              placeholder={t('selectIssues')}
              style={{ width: '100%' }}
            >
              {/* Mock issue options */}
              <Select.Option value="issue1">Issue #1 - Label consistency</Select.Option>
              <Select.Option value="issue2">Issue #2 - Text validation</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="tags"
            label={t('tags')}
          >
            <Select
              mode="tags"
              placeholder={t('enterTags')}
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Dispatch Work Order Modal */}
      <Modal
        title={t('workOrders.dispatch')}
        open={dispatchModalOpen}
        onCancel={() => {
          setDispatchModalOpen(false);
          dispatchForm.resetFields();
        }}
        onOk={() => dispatchForm.submit()}
      >
        <Form
          form={dispatchForm}
          layout="vertical"
          onFinish={handleDispatchWorkOrder}
        >
          <Form.Item
            name="assigneeId"
            label={t('workOrders.assignee')}
            rules={[{ required: true, message: t('required') }]}
          >
            <Select placeholder={t('selectUser')}>
              {users.map(user => (
                <Select.Option key={user.id} value={user.id}>
                  <Space>
                    <Avatar size="small" src={user.avatar} icon={<UserOutlined />} />
                    {user.name}
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Work Order Detail Modal */}
      <Modal
        title={`${t('workOrders.title')} - ${selectedWorkOrder?.title}`}
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedWorkOrder(null);
        }}
        footer={null}
        width={1000}
      >
        {selectedWorkOrder && (
          <div>
            <Descriptions bordered column={2}>
              <Descriptions.Item label={t('workOrders.title')}>
                {selectedWorkOrder.title}
              </Descriptions.Item>
              <Descriptions.Item label={t('workOrders.priority')}>
                <Tag color={priorityColors[selectedWorkOrder.priority]}>
                  {t(`quality.workOrders.priorities.${selectedWorkOrder.priority}`)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('workOrders.status')}>
                <Tag color={statusColors[selectedWorkOrder.status]}>
                  {t(`quality.workOrders.statuses.${selectedWorkOrder.status}`)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('workOrders.progress')}>
                <Progress percent={selectedWorkOrder.progress} size="small" />
              </Descriptions.Item>
              <Descriptions.Item label={t('workOrders.assignee')}>
                {selectedWorkOrder.assigneeName ? (
                  <Space>
                    <Avatar size="small" src={selectedWorkOrder.assigneeAvatar} icon={<UserOutlined />} />
                    {selectedWorkOrder.assigneeName}
                  </Space>
                ) : (
                  <Text type="secondary">{t('unassigned')}</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label={t('workOrders.dueDate')}>
                {selectedWorkOrder.dueDate ? new Date(selectedWorkOrder.dueDate).toLocaleString() : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('rules.description')} span={2}>
                {selectedWorkOrder.description}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            {/* Comments Section */}
            <div style={{ marginBottom: 24 }}>
              <h4>{t('workOrders.comments')}</h4>
              <Timeline
                items={selectedWorkOrder.comments.map(comment => ({
                  children: (
                    <div>
                      <Space>
                        <Avatar size="small" src={comment.authorAvatar} icon={<UserOutlined />} />
                        <Text strong>{comment.authorName}</Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {new Date(comment.createdAt).toLocaleString()}
                        </Text>
                      </Space>
                      <div style={{ marginTop: 8 }}>
                        <Text>{comment.content}</Text>
                      </div>
                    </div>
                  ),
                }))}
              />
              
              <Form
                form={commentForm}
                onFinish={handleAddComment}
                style={{ marginTop: 16 }}
              >
                <Form.Item name="comment">
                  <TextArea
                    rows={3}
                    placeholder={t('workOrders.comments')}
                  />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit">
                    {t('addComment')}
                  </Button>
                </Form.Item>
              </Form>
            </div>

            {/* Attachments Section */}
            <div>
              <h4>{t('workOrders.attachments')}</h4>
              <Upload {...uploadProps}>
                <Button icon={<UploadOutlined />}>
                  {t('upload')}
                </Button>
              </Upload>
              
              {selectedWorkOrder.attachments.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  {selectedWorkOrder.attachments.map(attachment => (
                    <div key={attachment.id} style={{ marginBottom: 8 }}>
                      <Space>
                        <PaperClipOutlined />
                        <a href={attachment.url} target="_blank" rel="noopener noreferrer">
                          {attachment.name}
                        </a>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          ({(attachment.size / 1024).toFixed(1)} KB)
                        </Text>
                      </Space>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default WorkOrderManager;