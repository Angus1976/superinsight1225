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
import { useTranslation } from 'react-i18next';
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

export function BillingRuleConfig({
  tenantId,
  currentUserId,
  isAdmin = false,
  onRuleCreated,
  onRuleApproved,
}: BillingRuleConfigProps) {
  const { t } = useTranslation(['billing', 'common']);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm<RuleFormValues>();

  const BILLING_MODE_OPTIONS: { value: BillingMode; label: string; description: string }[] = [
    { value: 'by_count', label: t('ruleConfig.modes.byCount'), description: t('ruleConfig.modeDescriptions.byCount') },
    { value: 'by_time', label: t('ruleConfig.modes.byTime'), description: t('ruleConfig.modeDescriptions.byTime') },
    { value: 'by_project', label: t('ruleConfig.modes.byProject'), description: t('ruleConfig.modeDescriptions.byProject') },
    { value: 'hybrid', label: t('ruleConfig.modes.hybrid'), description: t('ruleConfig.modeDescriptions.hybrid') },
  ];

  const getBillingModeTag = (mode: BillingMode) => {
    const modeColors: Record<BillingMode, string> = {
      by_count: 'blue',
      by_time: 'green',
      by_project: 'purple',
      hybrid: 'orange',
    };
    const modeLabels: Record<BillingMode, string> = {
      by_count: t('ruleConfig.modeLabels.byCount'),
      by_time: t('ruleConfig.modeLabels.byTime'),
      by_project: t('ruleConfig.modeLabels.byProject'),
      hybrid: t('ruleConfig.modeLabels.hybrid'),
    };
    return <Tag color={modeColors[mode]}>{modeLabels[mode]}</Tag>;
  };

  const getStatusBadge = (rule: BillingRuleVersion) => {
    if (rule.is_active) {
      return <Badge status="success" text={t('ruleConfig.ruleStatus.active')} />;
    }
    if (rule.approved_by) {
      return <Badge status="default" text={t('ruleConfig.ruleStatus.approved')} />;
    }
    return <Badge status="processing" text={t('ruleConfig.ruleStatus.pending')} />;
  };

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
      message.success(t('ruleConfig.createSuccess'));
      setIsModalOpen(false);
      form.resetFields();
      onRuleCreated?.(result.rule);
    } catch (err) {
      message.error(t('ruleConfig.createError'));
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
      message.success(t('ruleConfig.approveSuccess', { version }));
      onRuleApproved?.(result.rule);
    } catch (err) {
      message.error(t('ruleConfig.approveError'));
      console.error('Failed to approve billing rule:', err);
    }
  };

  const columns: ColumnsType<BillingRuleVersion> = [
    {
      title: t('ruleConfig.columns.version'),
      dataIndex: 'version',
      key: 'version',
      width: 80,
      render: (version: number) => <Tag>v{version}</Tag>,
    },
    {
      title: t('ruleConfig.columns.billingMode'),
      dataIndex: 'billing_mode',
      key: 'billing_mode',
      render: (mode: BillingMode) => getBillingModeTag(mode),
    },
    {
      title: t('ruleConfig.columns.ratePerAnnotation'),
      dataIndex: 'rate_per_annotation',
      key: 'rate_per_annotation',
      render: (rate: number) => `¥${rate.toFixed(2)}`,
    },
    {
      title: t('ruleConfig.columns.ratePerHour'),
      dataIndex: 'rate_per_hour',
      key: 'rate_per_hour',
      render: (rate: number) => `¥${rate.toFixed(2)}/h`,
    },
    {
      title: t('ruleConfig.columns.projectAnnualFee'),
      dataIndex: 'project_annual_fee',
      key: 'project_annual_fee',
      render: (fee: number) => `¥${fee.toLocaleString()}`,
    },
    {
      title: t('ruleConfig.columns.effectiveFrom'),
      dataIndex: 'effective_from',
      key: 'effective_from',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: t('ruleConfig.columns.status'),
      key: 'status',
      render: (_, record) => getStatusBadge(record),
    },
    {
      title: t('ruleConfig.columns.createdBy'),
      dataIndex: 'created_by',
      key: 'created_by',
      ellipsis: true,
    },
    {
      title: t('ruleConfig.columns.approvedBy'),
      dataIndex: 'approved_by',
      key: 'approved_by',
      render: (approver: string, record) => (
        <Space direction="vertical" size={0}>
          <Text>{approver || '-'}</Text>
          {record.approved_at && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {new Date(record.approved_at).toLocaleDateString()}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: t('ruleConfig.columns.action'),
      key: 'action',
      width: 100,
      render: (_, record) => {
        if (record.is_active) {
          return <Tag color="green">{t('ruleConfig.ruleStatus.currentVersion')}</Tag>;
        }
        if (!record.approved_by && isAdmin) {
          return (
            <Popconfirm
              title={t('ruleConfig.approveConfirmTitle')}
              description={t('ruleConfig.approveConfirmDesc')}
              onConfirm={() => handleApproveRule(record.version)}
              okText={t('common:confirm')}
              cancelText={t('common:cancel')}
            >
              <Button
                type="link"
                size="small"
                icon={<CheckOutlined />}
                loading={approveMutation.isPending}
              >
                {t('ruleConfig.actions.approve')}
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
          description={t('ruleConfig.loadError')}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => refetch()}>
            {t('common:retry')}
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
            <span>{t('ruleConfig.title')}</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<SyncOutlined />}
              onClick={() => refetch()}
              loading={isLoading}
            >
              {t('common:refresh')}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsModalOpen(true)}
            >
              {t('ruleConfig.createVersion')}
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip={t('common:status.loading')} />
          </div>
        ) : activeRule ? (
          <Row gutter={16}>
            <Col span={24}>
              <Descriptions bordered size="small" column={4}>
                <Descriptions.Item label={t('ruleConfig.labels.versionNumber')}>
                  <Tag color="blue">v{activeRule.version}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.columns.billingMode')}>
                  {getBillingModeTag(activeRule.billing_mode)}
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.labels.effectiveDate')}>
                  {new Date(activeRule.effective_from).toLocaleDateString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.columns.status')}>
                  <Badge status="success" text={t('ruleConfig.ruleStatus.inEffect')} />
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.columns.ratePerAnnotation')}>
                  <Text strong>¥{activeRule.rate_per_annotation.toFixed(2)}</Text>
                  <Text type="secondary"> {t('ruleConfig.form.perItem')}</Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.columns.ratePerHour')}>
                  <Text strong>¥{activeRule.rate_per_hour.toFixed(2)}</Text>
                  <Text type="secondary"> {t('ruleConfig.form.perHour')}</Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.columns.projectAnnualFee')}>
                  <Text strong>¥{activeRule.project_annual_fee.toLocaleString()}</Text>
                  <Text type="secondary"> {t('ruleConfig.form.perYear')}</Text>
                </Descriptions.Item>
                <Descriptions.Item label={t('ruleConfig.columns.approvedBy')}>
                  {activeRule.approved_by || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Col>
          </Row>
        ) : (
          <Alert
            message={t('ruleConfig.noActiveRule')}
            description={t('ruleConfig.noActiveRuleDesc')}
            type="info"
            showIcon
          />
        )}
      </Card>

      {/* Pending Rules Alert */}
      {pendingRules.length > 0 && (
        <Alert
          message={t('ruleConfig.pendingRulesAlert', { count: pendingRules.length })}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          action={
            isAdmin && (
              <Button size="small" type="primary" onClick={() => refetch()}>
                {t('ruleConfig.actions.view')}
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
            <span>{t('ruleConfig.ruleHistory')}</span>
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
            showTotal: (total) => t('workHours.report.messages.totalRecords', { total }),
          }}
          rowClassName={(record) => (record.is_active ? 'active-rule-row' : '')}
        />
      </Card>

      {/* Create Rule Modal */}
      <Modal
        title={
          <Space>
            <PlusOutlined />
            <span>{t('ruleConfig.createRuleVersion')}</span>
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
            message={t('ruleConfig.createAlert')}
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />

          <Form.Item
            label={
              <Space>
                <span>{t('ruleConfig.form.billingMode')}</span>
                <Tooltip title={t('ruleConfig.billingModeTooltip')}>
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
            name="billing_mode"
            rules={[{ required: true, message: t('ruleConfig.form.billingModeRequired') }]}
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
                label={t('ruleConfig.form.ratePerAnnotation')}
                name="rate_per_annotation"
                rules={[
                  { required: true, message: t('ruleConfig.form.ratePerAnnotationRequired') },
                  { type: 'number', min: 0, message: t('ruleConfig.form.ratePerAnnotationMin') },
                ]}
              >
                <InputNumber
                  min={0}
                  step={0.1}
                  precision={2}
                  style={{ width: '100%' }}
                  addonAfter={t('ruleConfig.form.perItem')}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label={t('ruleConfig.form.ratePerHour')}
                name="rate_per_hour"
                rules={[
                  { required: true, message: t('ruleConfig.form.ratePerHourRequired') },
                  { type: 'number', min: 0, message: t('ruleConfig.form.ratePerHourMin') },
                ]}
              >
                <InputNumber
                  min={0}
                  step={5}
                  precision={2}
                  style={{ width: '100%' }}
                  addonAfter={t('ruleConfig.form.perHour')}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label={t('ruleConfig.form.projectAnnualFee')}
                name="project_annual_fee"
                rules={[
                  { required: true, message: t('ruleConfig.form.projectAnnualFeeRequired') },
                  { type: 'number', min: 0, message: t('ruleConfig.form.projectAnnualFeeMin') },
                ]}
              >
                <InputNumber
                  min={0}
                  step={1000}
                  precision={0}
                  style={{ width: '100%' }}
                  addonAfter={t('ruleConfig.form.perYear')}
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
                {t('common:cancel')}
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={createMutation.isPending}
              >
                {t('ruleConfig.actions.createRule')}
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
