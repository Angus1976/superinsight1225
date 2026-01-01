// Billing rule configuration component with version management
import { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Modal,
  Form,
  InputNumber,
  Select,
  Descriptions,
  Badge,
  message,
  Spin,
  Empty,
  Row,
  Col,
  Typography,
  Tooltip,
  Popconfirm,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  CheckOutlined,
  HistoryOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useRuleHistory, useCreateRuleVersion, useApproveRuleVersion } from '@/hooks/useBilling';
import type { BillingRuleVersion, BillingMode, BillingRuleVersionRequest } from '@/types/billing';

const { Text } = Typography;

interface BillingRuleConfigProps {
  tenantId: string;
  currentUserId: string;
  isAdmin?: boolean;
  onRuleCreated?: (rule: BillingRuleVersion) => void;
  onRuleApproved?: (rule: BillingRuleVersion) => void;
}

interface RuleFormValues {
  billing_mode: BillingMode;
  rate_per_annotation: number;
  rate_per_hour: number;
  project_annual_fee: number;
}

const BILLING_MODE_OPTIONS: { value: BillingMode; label: string; description: string }[] = [
  { value: 'by_count', label: '按条数计费', description: '根据标注数量计费' },
  { value: 'by_time', label: '按工时计费', description: '根据工作时间计费' },
  { value: 'by_project', label: '按项目计费', description: '按项目年费计费' },
  { value: 'hybrid', label: '混合计费', description: '综合多种计费方式' },
];

const getBillingModeTag = (mode: BillingMode) => {
  const modeColors: Record<BillingMode, string> = {
    by_count: 'blue',
    by_time: 'green',
    by_project: 'purple',
    hybrid: 'orange',
  };
  const modeLabels: Record<BillingMode, string> = {
    by_count: '按条数',
    by_time: '按工时',
    by_project: '按项目',
    hybrid: '混合',
  };
  return <Tag color={modeColors[mode]}>{modeLabels[mode]}</Tag>;
};

const getStatusBadge = (rule: BillingRuleVersion) => {
  if (rule.is_active) {
    return <Badge status="success" text="当前生效" />;
  }
  if (rule.approved_by) {
    return <Badge status="default" text="已审批" />;
  }
  return <Badge status="processing" text="待审批" />;
};

export function BillingRuleConfig({
  tenantId,
  currentUserId,
  isAdmin = false,
  onRuleCreated,
  onRuleApproved,
}: BillingRuleConfigProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm<RuleFormValues>();

  const { data, isLoading, error, refetch } = useRuleHistory(tenantId);
  const createMutation = useCreateRuleVersion();
  const approveMutation = useApproveRuleVersion();

  const activeRule = useMemo(() => {
    if (!data?.versions) return null;
    return data.versions.find((v) => v.is_active) || null;
  }, [data]);

  const pendingRules = useMemo(() => {
    if (!data?.versions) return [];
    return data.versions.filter((v) => !v.approved_by && !v.is_active);
  }, [data]);

  const handleCreateRule = async (values: RuleFormValues) => {
    try {
      const request: BillingRuleVersionRequest = {
        tenant_id: tenantId,
        billing_mode: values.billing_mode,
        rate_per_annotation: values.rate_per_annotation,
        rate_per_hour: values.rate_per_hour,
        project_annual_fee: values.project_annual_fee,
        created_by: currentUserId,
      };

      const result = await createMutation.mutateAsync(request);
      message.success('计费规则创建成功，等待审批');
      setIsModalOpen(false);
      form.resetFields();
      onRuleCreated?.(result.rule);
    } catch (err) {
      message.error('创建计费规则失败');
      console.error('Failed to create billing rule:', err);
    }
  };

  const handleApproveRule = async (version: number) => {
    try {
      const result = await approveMutation.mutateAsync({
        tenantId,
        version,
        approvedBy: currentUserId,
      });
      message.success(`规则版本 ${version} 已审批并生效`);
      onRuleApproved?.(result.rule);
    } catch (err) {
      message.error('审批计费规则失败');
      console.error('Failed to approve billing rule:', err);
    }
  };

  const columns: ColumnsType<BillingRuleVersion> = [
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
      render: (version: number) => <Tag>v{version}</Tag>,
    },
    {
      title: '计费模式',
      dataIndex: 'billing_mode',
      key: 'billing_mode',
      render: (mode: BillingMode) => getBillingModeTag(mode),
    },
    {
      title: '单条费率',
      dataIndex: 'rate_per_annotation',
      key: 'rate_per_annotation',
      render: (rate: number) => `¥${rate.toFixed(2)}`,
    },
    {
      title: '时薪',
      dataIndex: 'rate_per_hour',
      key: 'rate_per_hour',
      render: (rate: number) => `¥${rate.toFixed(2)}/h`,
    },
    {
      title: '项目年费',
      dataIndex: 'project_annual_fee',
      key: 'project_annual_fee',
      render: (fee: number) => `¥${fee.toLocaleString()}`,
    },
    {
      title: '生效日期',
      dataIndex: 'effective_from',
      key: 'effective_from',
      render: (date: string) => new Date(date).toLocaleDateString('zh-CN'),
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => getStatusBadge(record),
    },
    {
      title: '创建者',
      dataIndex: 'created_by',
      key: 'created_by',
      ellipsis: true,
    },
    {
      title: '审批者',
      dataIndex: 'approved_by',
      key: 'approved_by',
      render: (approver: string, record) => (
        <Space direction="vertical" size={0}>
          <Text>{approver || '-'}</Text>
          {record.approved_at && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(record.approved_at).toLocaleDateString('zh-CN')}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => {
        if (record.is_active) {
          return <Tag color="green">当前版本</Tag>;
        }
        if (!record.approved_by && isAdmin) {
          return (
            <Popconfirm
              title="审批确认"
              description="确定要审批并启用此计费规则吗？"
              onConfirm={() => handleApproveRule(record.version)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                loading={approveMutation.isPending}
              >
                审批
              </Button>
            </Popconfirm>
          );
        }
        return null;
      },
    },
  ];

  if (error) {
    return (
      <Card>
        <Empty
          description="加载计费规则失败"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => refetch()}>
            重试
          </Button>
        </Empty>
      </Card>
    );
  }

  return (
    <div className="billing-rule-config">
      {/* Active Rule Card */}
      <Card
        title={
          <Space>
            <SettingOutlined />
            <span>当前计费规则</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<SyncOutlined />}
              onClick={() => refetch()}
              loading={isLoading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsModalOpen(true)}
            >
              创建新版本
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="加载中..." />
          </div>
        ) : activeRule ? (
          <Row gutter={16}>
            <Col span={24}>
              <Descriptions bordered size="small" column={4}>
                <Descriptions.Item label="版本号">
                  <Tag color="blue">v{activeRule.version}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="计费模式">
                  {getBillingModeTag(activeRule.billing_mode)}
                </Descriptions.Item>
                <Descriptions.Item label="生效日期">
                  {new Date(activeRule.effective_from).toLocaleDateString('zh-CN')}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Badge status="success" text="生效中" />
                </Descriptions.Item>
                <Descriptions.Item label="单条费率">
                  <Text strong>¥{activeRule.rate_per_annotation.toFixed(2)}</Text>
                  <Text type="secondary"> / 条</Text>
                </Descriptions.Item>
                <Descriptions.Item label="时薪">
                  <Text strong>¥{activeRule.rate_per_hour.toFixed(2)}</Text>
                  <Text type="secondary"> / 小时</Text>
                </Descriptions.Item>
                <Descriptions.Item label="项目年费">
                  <Text strong>¥{activeRule.project_annual_fee.toLocaleString()}</Text>
                  <Text type="secondary"> / 年</Text>
                </Descriptions.Item>
                <Descriptions.Item label="审批者">
                  {activeRule.approved_by || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Col>
          </Row>
        ) : (
          <Alert
            message="暂无生效的计费规则"
            description="请创建并审批计费规则以开始使用计费功能"
            type="info"
            showIcon
          />
        )}
      </Card>

      {/* Pending Rules Alert */}
      {pendingRules.length > 0 && (
        <Alert
          message={`有 ${pendingRules.length} 条待审批的计费规则`}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            isAdmin && (
              <Button size="small" type="primary" onClick={() => refetch()}>
                查看
              </Button>
            )
          }
        />
      )}

      {/* Rule History Table */}
      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>规则版本历史</span>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={data?.versions || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          rowClassName={(record) => (record.is_active ? 'active-rule-row' : '')}
        />
      </Card>

      {/* Create Rule Modal */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            <span>创建计费规则版本</span>
          </Space>
        }
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateRule}
          initialValues={{
            billing_mode: 'by_count',
            rate_per_annotation: activeRule?.rate_per_annotation || 0.5,
            rate_per_hour: activeRule?.rate_per_hour || 50,
            project_annual_fee: activeRule?.project_annual_fee || 10000,
          }}
        >
          <Alert
            message="创建新版本后需要管理员审批才能生效"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />

          <Form.Item
            label={
              <Space>
                <span>计费模式</span>
                <Tooltip title="选择适合您业务的计费方式">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
            name="billing_mode"
            rules={[{ required: true, message: '请选择计费模式' }]}
          >
            <Select
              options={BILLING_MODE_OPTIONS.map((opt) => ({
                value: opt.value,
                label: (
                  <Space>
                    <span>{opt.label}</span>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {opt.description}
                    </Text>
                  </Space>
                ),
              }))}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="单条费率 (¥)"
                name="rate_per_annotation"
                rules={[
                  { required: true, message: '请输入单条费率' },
                  { type: 'number', min: 0, message: '费率不能为负数' },
                ]}
              >
                <InputNumber
                  min={0}
                  step={0.1}
                  precision={2}
                  style={{ width: '100%' }}
                  addonAfter="/ 条"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="时薪 (¥)"
                name="rate_per_hour"
                rules={[
                  { required: true, message: '请输入时薪' },
                  { type: 'number', min: 0, message: '时薪不能为负数' },
                ]}
              >
                <InputNumber
                  min={0}
                  step={5}
                  precision={2}
                  style={{ width: '100%' }}
                  addonAfter="/ 小时"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="项目年费 (¥)"
                name="project_annual_fee"
                rules={[
                  { required: true, message: '请输入项目年费' },
                  { type: 'number', min: 0, message: '年费不能为负数' },
                ]}
              >
                <InputNumber
                  min={0}
                  step={1000}
                  precision={0}
                  style={{ width: '100%' }}
                  addonAfter="/ 年"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button
                onClick={() => {
                  setIsModalOpen(false);
                  form.resetFields();
                }}
              >
                取消
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending}
              >
                创建规则
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <style>{`
        .active-rule-row {
          background-color: #f6ffed;
        }
        .active-rule-row:hover > td {
          background-color: #d9f7be !important;
        }
      `}</style>
    </div>
  );
}

export default BillingRuleConfig;
