// Excel Export and Reports Manager Component
import { useState, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Select,
  DatePicker,
  Form,
  Input,
  Checkbox,
  Space,
  Table,
  Tag,
  Progress,
  Modal,
  Steps,
  Alert,
  Typography,
  Divider,
  Tooltip,
  message,
  Upload,
  List,
  Popconfirm,
} from 'antd';
import {
  FileExcelOutlined,
  DownloadOutlined,
  SettingOutlined,
  ScheduleOutlined,
  ShareAltOutlined,
  DeleteOutlined,
  EyeOutlined,
  CloudUploadOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import { useExportBilling } from '@/hooks/useBilling';

const { RangePicker } = DatePicker;
const { TextArea } = Input;
const { Step } = Steps;
const { Text, Title } = Typography;
const { Option } = Select;

interface ExcelExportManagerProps {
  tenantId: string;
}

interface ExportTemplate {
  id: string;
  name: string;
  description: string;
  fields: string[];
  filters: Record<string, unknown>;
  format: 'xlsx' | 'csv' | 'pdf';
  createdAt: string;
  createdBy: string;
  isDefault: boolean;
}

interface ScheduledExport {
  id: string;
  templateId: string;
  templateName: string;
  schedule: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  nextRun: string;
  recipients: string[];
  status: 'active' | 'paused' | 'error';
  lastRun?: string;
  lastStatus?: 'success' | 'failed';
}

interface ExportHistory {
  id: string;
  templateName: string;
  exportType: 'manual' | 'scheduled';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
  fileSize?: number;
  downloadUrl?: string;
  error?: string;
}

interface ShareSettings {
  recipients: string[];
  permissions: 'view' | 'download' | 'edit';
  expiresAt?: string;
  password?: string;
}

const AVAILABLE_FIELDS = [
  { value: 'id', label: 'billId' },
  { value: 'period_start', label: 'periodStart' },
  { value: 'period_end', label: 'periodEnd' },
  { value: 'total_amount', label: 'totalAmount' },
  { value: 'status', label: 'status' },
  { value: 'due_date', label: 'dueDate' },
  { value: 'paid_at', label: 'paidAt' },
  { value: 'items', label: 'items' },
  { value: 'created_at', label: 'createdAt' },
];

const SCHEDULE_OPTIONS = [
  { value: 'daily', label: 'daily' },
  { value: 'weekly', label: 'weekly' },
  { value: 'monthly', label: 'monthly' },
  { value: 'quarterly', label: 'quarterly' },
];

export const ExcelExportManager: React.FC<ExcelExportManagerProps> = ({ tenantId }) => {
  const { t } = useTranslation('billing');
  const [activeTab, setActiveTab] = useState<'export' | 'templates' | 'scheduled' | 'history'>('export');
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [templateModalVisible, setTemplateModalVisible] = useState(false);
  const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedTemplate, setSelectedTemplate] = useState<ExportTemplate | null>(null);
  const [selectedExport, setSelectedExport] = useState<ExportHistory | null>(null);

  const [form] = Form.useForm();
  const [templateForm] = Form.useForm();
  const [scheduleForm] = Form.useForm();
  const [shareForm] = Form.useForm();

  const exportMutation = useExportBilling();

  // Mock data for demo
  const templates = useMemo((): ExportTemplate[] => [
    {
      id: '1',
      name: 'Standard Billing Report',
      description: 'Complete billing information with all line items',
      fields: ['id', 'period_start', 'period_end', 'total_amount', 'status', 'items'],
      filters: {},
      format: 'xlsx',
      createdAt: '2025-01-01T00:00:00Z',
      createdBy: 'admin',
      isDefault: true,
    },
    {
      id: '2',
      name: 'Financial Summary',
      description: 'Summary report for financial analysis',
      fields: ['period_start', 'period_end', 'total_amount', 'status', 'paid_at'],
      filters: { status: 'paid' },
      format: 'xlsx',
      createdAt: '2025-01-02T00:00:00Z',
      createdBy: 'finance_user',
      isDefault: false,
    },
    {
      id: '3',
      name: 'Pending Payments',
      description: 'Outstanding invoices requiring attention',
      fields: ['id', 'total_amount', 'due_date', 'status'],
      filters: { status: ['pending', 'overdue'] },
      format: 'csv',
      createdAt: '2025-01-03T00:00:00Z',
      createdBy: 'accounts_user',
      isDefault: false,
    },
  ], []);

  const scheduledExports = useMemo((): ScheduledExport[] => [
    {
      id: '1',
      templateId: '1',
      templateName: 'Standard Billing Report',
      schedule: 'monthly',
      nextRun: '2025-02-01T09:00:00Z',
      recipients: ['finance@company.com', 'admin@company.com'],
      status: 'active',
      lastRun: '2025-01-01T09:00:00Z',
      lastStatus: 'success',
    },
    {
      id: '2',
      templateId: '3',
      templateName: 'Pending Payments',
      schedule: 'weekly',
      nextRun: '2025-01-15T10:00:00Z',
      recipients: ['accounts@company.com'],
      status: 'active',
      lastRun: '2025-01-08T10:00:00Z',
      lastStatus: 'success',
    },
  ], []);

  const exportHistory = useMemo((): ExportHistory[] => [
    {
      id: '1',
      templateName: 'Standard Billing Report',
      exportType: 'manual',
      status: 'completed',
      createdAt: '2025-01-08T14:30:00Z',
      completedAt: '2025-01-08T14:32:00Z',
      fileSize: 2048576, // 2MB
      downloadUrl: '/downloads/billing-report-20250108.xlsx',
    },
    {
      id: '2',
      templateName: 'Financial Summary',
      exportType: 'scheduled',
      status: 'completed',
      createdAt: '2025-01-08T09:00:00Z',
      completedAt: '2025-01-08T09:01:30Z',
      fileSize: 1024000, // 1MB
      downloadUrl: '/downloads/financial-summary-20250108.xlsx',
    },
    {
      id: '3',
      templateName: 'Pending Payments',
      exportType: 'manual',
      status: 'failed',
      createdAt: '2025-01-08T11:15:00Z',
      error: 'Database connection timeout',
    },
    {
      id: '4',
      templateName: 'Custom Export',
      exportType: 'manual',
      status: 'processing',
      createdAt: '2025-01-08T15:45:00Z',
    },
  ], []);

  // Handle export execution
  const handleExport = async (values: Record<string, unknown>) => {
    try {
      setCurrentStep(1);
      
      // Simulate export process
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      await exportMutation.mutateAsync({
        tenantId,
        params: {
          start_date: values.dateRange?.[0]?.format('YYYY-MM-DD'),
          end_date: values.dateRange?.[1]?.format('YYYY-MM-DD'),
          status: values.status,
        },
      });

      setCurrentStep(2);
      message.success(t('excelExport.messages.exportSuccess'));
      setExportModalVisible(false);
      setCurrentStep(0);
    } catch {
      message.error(t('excelExport.messages.exportFailed'));
      setCurrentStep(0);
    }
  };

  // Handle template creation
  const handleCreateTemplate = async (values: Record<string, unknown>) => {
    try {
      console.log('Creating template:', values);
      message.success(t('excelExport.messages.templateCreated'));
      setTemplateModalVisible(false);
      templateForm.resetFields();
    } catch {
      message.error(t('excelExport.messages.templateFailed'));
    }
  };

  // Handle schedule creation
  const handleCreateSchedule = async (values: Record<string, unknown>) => {
    try {
      console.log('Creating schedule:', values);
      message.success(t('excelExport.messages.scheduleCreated'));
      setScheduleModalVisible(false);
      scheduleForm.resetFields();
    } catch {
      message.error(t('excelExport.messages.scheduleFailed'));
    }
  };

  // Handle file sharing
  const handleShare = async (values: Record<string, unknown>) => {
    try {
      console.log('Sharing export:', values);
      message.success(t('excelExport.messages.shareSuccess'));
      setShareModalVisible(false);
      shareForm.resetFields();
    } catch {
      message.error(t('excelExport.messages.shareFailed'));
    }
  };

  // Table columns for templates
  const templateColumns: ColumnsType<ExportTemplate> = [
    {
      title: t('excelExport.columns.templateName'),
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          <Text strong>{name}</Text>
          {record.isDefault && <Tag color="blue">Default</Tag>}
        </Space>
      ),
    },
    {
      title: t('excelExport.columns.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('excelExport.columns.format'),
      dataIndex: 'format',
      key: 'format',
      render: (format: string) => (
        <Tag color="green">{format.toUpperCase()}</Tag>
      ),
    },
    {
      title: t('excelExport.columns.fields'),
      dataIndex: 'fields',
      key: 'fields',
      render: (fields: string[]) => `${fields.length} ${t('excelExport.fields')}`,
    },
    {
      title: t('excelExport.columns.created'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => dayjs(date).format('MMM DD, YYYY'),
    },
    {
      title: t('excelExport.columns.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => setSelectedTemplate(record)}
          >
            {t('excelExport.columns.view')}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FileExcelOutlined />}
            onClick={() => {
              form.setFieldsValue({
                template: record.id,
                fields: record.fields,
                format: record.format,
              });
              setExportModalVisible(true);
            }}
          >
            {t('excelExport.columns.export')}
          </Button>
        </Space>
      ),
    },
  ];

  // Table columns for scheduled exports
  const scheduleColumns: ColumnsType<ScheduledExport> = [
    {
      title: t('excelExport.template'),
      dataIndex: 'templateName',
      key: 'templateName',
    },
    {
      title: t('excelExport.columns.schedule'),
      dataIndex: 'schedule',
      key: 'schedule',
      render: (schedule: string) => (
        <Tag color="blue">{t(`excelExport.scheduleOptions.${schedule}`)}</Tag>
      ),
    },
    {
      title: t('excelExport.columns.nextRun'),
      dataIndex: 'nextRun',
      key: 'nextRun',
      render: (date: string) => dayjs(date).format('MMM DD, YYYY HH:mm'),
    },
    {
      title: t('excelExport.columns.recipients'),
      dataIndex: 'recipients',
      key: 'recipients',
      render: (recipients: string[]) => `${recipients.length} ${t('excelExport.recipients')}`,
    },
    {
      title: t('excelExport.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : status === 'paused' ? 'orange' : 'red'}>
          {t(`excelExport.status.${status}`)}
        </Tag>
      ),
    },
    {
      title: t('excelExport.columns.lastRun'),
      key: 'lastRun',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.lastRun && (
            <Text>{dayjs(record.lastRun).format('MMM DD, HH:mm')}</Text>
          )}
          {record.lastStatus && (
            <Tag color={record.lastStatus === 'success' ? 'green' : 'red'} size="small">
              {t(`excelExport.status.${record.lastStatus}`)}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('excelExport.columns.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small">
            {t('excelExport.edit')}
          </Button>
          <Button type="link" size="small">
            {t('excelExport.columns.pause')}
          </Button>
          <Popconfirm title={t('excelExport.messages.deleteConfirm')} onConfirm={() => {}}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Table columns for export history
  const historyColumns: ColumnsType<ExportHistory> = [
    {
      title: t('excelExport.template'),
      dataIndex: 'templateName',
      key: 'templateName',
    },
    {
      title: t('excelExport.columns.type'),
      dataIndex: 'exportType',
      key: 'exportType',
      render: (type: string) => (
        <Tag color={type === 'manual' ? 'blue' : 'green'}>{t(`excelExport.status.${type}`)}</Tag>
      ),
    },
    {
      title: t('excelExport.columns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors = {
          pending: 'default',
          processing: 'processing',
          completed: 'success',
          failed: 'error',
        };
        const icons = {
          pending: <ClockCircleOutlined />,
          processing: <ClockCircleOutlined />,
          completed: <CheckCircleOutlined />,
          failed: <ExclamationCircleOutlined />,
        };
        return (
          <Tag color={colors[status as keyof typeof colors]} icon={icons[status as keyof typeof icons]}>
            {t(`excelExport.status.${status}`)}
          </Tag>
        );
      },
    },
    {
      title: t('excelExport.columns.created'),
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => dayjs(date).format('MMM DD, HH:mm'),
    },
    {
      title: t('excelExport.columns.size'),
      dataIndex: 'fileSize',
      key: 'fileSize',
      render: (size?: number) => {
        if (!size) return '-';
        return size > 1024 * 1024 
          ? `${(size / (1024 * 1024)).toFixed(1)} MB`
          : `${(size / 1024).toFixed(0)} KB`;
      },
    },
    {
      title: t('excelExport.columns.actions'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          {record.status === 'completed' && record.downloadUrl && (
            <Button
              type="link"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => {
                message.success(t('excelExport.messages.downloadStarted'));
              }}
            >
              {t('excelExport.download')}
            </Button>
          )}
          {record.status === 'completed' && (
            <Button
              type="link"
              size="small"
              icon={<ShareAltOutlined />}
              onClick={() => {
                setSelectedExport(record);
                setShareModalVisible(true);
              }}
            >
              {t('excelExport.columns.share')}
            </Button>
          )}
          {record.status === 'failed' && record.error && (
            <Tooltip title={record.error}>
              <Button type="link" size="small" danger>
                {t('excelExport.columns.viewError')}
              </Button>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="excel-export-manager">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={18}>
          <Title level={3}>{t('excelExport.title')}</Title>
        </Col>
        <Col span={6} style={{ textAlign: 'right' }}>
          <Space>
            <Button
              type="primary"
              icon={<FileExcelOutlined />}
              onClick={() => setExportModalVisible(true)}
            >
              {t('excelExport.quickExport')}
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setTemplateModalVisible(true)}
            >
              {t('excelExport.newTemplate')}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Navigation Tabs */}
      <Card>
        <Space size="large" style={{ marginBottom: 16 }}>
          <Button
            type={activeTab === 'export' ? 'primary' : 'default'}
            onClick={() => setActiveTab('export')}
          >
            {t('excelExport.quickExport')}
          </Button>
          <Button
            type={activeTab === 'templates' ? 'primary' : 'default'}
            onClick={() => setActiveTab('templates')}
          >
            {t('excelExport.templates')} ({templates.length})
          </Button>
          <Button
            type={activeTab === 'scheduled' ? 'primary' : 'default'}
            onClick={() => setActiveTab('scheduled')}
          >
            {t('excelExport.scheduled')} ({scheduledExports.length})
          </Button>
          <Button
            type={activeTab === 'history' ? 'primary' : 'default'}
            onClick={() => setActiveTab('history')}
          >
            {t('excelExport.history')} ({exportHistory.length})
          </Button>
        </Space>

        <Divider />

        {/* Quick Export Tab */}
        {activeTab === 'export' && (
          <Row gutter={16}>
            <Col span={12}>
              <Card title={t('excelExport.quickExport')} size="small">
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={handleExport}
                >
                  <Form.Item
                    name="template"
                    label={t('excelExport.template')}
                    rules={[{ required: true }]}
                  >
                    <Select placeholder={t('excelExport.selectTemplate')}>
                      {templates.map(template => (
                        <Option key={template.id} value={template.id}>
                          {template.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item
                    name="dateRange"
                    label={t('excelExport.dateRange')}
                    rules={[{ required: true }]}
                  >
                    <RangePicker style={{ width: '100%' }} />
                  </Form.Item>

                  <Form.Item name="status" label={t('excelExport.statusFilter')}>
                    <Select mode="multiple" placeholder={t('excelExport.allStatuses')}>
                      <Option value="pending">{t('status.pending')}</Option>
                      <Option value="paid">{t('status.paid')}</Option>
                      <Option value="overdue">{t('status.overdue')}</Option>
                      <Option value="cancelled">{t('status.cancelled')}</Option>
                    </Select>
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={exportMutation.isPending}
                      block
                    >
                      {t('excelExport.exportNow')}
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>
            <Col span={12}>
              <Card title={t('excelExport.recentExports')} size="small">
                <List
                  dataSource={exportHistory.slice(0, 5)}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        item.status === 'completed' && (
                          <Button type="link" size="small" icon={<DownloadOutlined />}>
                            {t('excelExport.download')}
                          </Button>
                        ),
                      ].filter(Boolean)}
                    >
                      <List.Item.Meta
                        title={item.templateName}
                        description={
                          <Space>
                            <Tag color={item.status === 'completed' ? 'green' : 'orange'}>
                              {t(`excelExport.status.${item.status}`)}
                            </Tag>
                            <Text type="secondary">
                              {dayjs(item.createdAt).fromNow()}
                            </Text>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* Templates Tab */}
        {activeTab === 'templates' && (
          <div>
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<SettingOutlined />}
                onClick={() => setTemplateModalVisible(true)}
              >
                {t('excelExport.createTemplate')}
              </Button>
            </div>
            <Table
              columns={templateColumns}
              dataSource={templates}
              rowKey="id"
              pagination={false}
            />
          </div>
        )}

        {/* Scheduled Exports Tab */}
        {activeTab === 'scheduled' && (
          <div>
            <div style={{ marginBottom: 16, textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<ScheduleOutlined />}
                onClick={() => setScheduleModalVisible(true)}
              >
                {t('excelExport.scheduleExport')}
              </Button>
            </div>
            <Table
              columns={scheduleColumns}
              dataSource={scheduledExports}
              rowKey="id"
              pagination={false}
            />
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <Table
            columns={historyColumns}
            dataSource={exportHistory}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      {/* Export Modal */}
      <Modal
        title={t('excelExport.exportBillingData')}
        open={exportModalVisible}
        onCancel={() => {
          setExportModalVisible(false);
          setCurrentStep(0);
        }}
        footer={null}
        width={600}
      >
        <Steps current={currentStep} style={{ marginBottom: 24 }}>
          <Step title={t('excelExport.configure')} />
          <Step title={t('excelExport.processing')} />
          <Step title={t('excelExport.complete')} />
        </Steps>

        {currentStep === 0 && (
          <Form form={form} layout="vertical" onFinish={handleExport}>
            <Form.Item name="template" label={t('excelExport.template')} rules={[{ required: true }]}>
              <Select placeholder={t('excelExport.selectTemplate')}>
                {templates.map(template => (
                  <Option key={template.id} value={template.id}>
                    {template.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item name="dateRange" label={t('excelExport.dateRange')} rules={[{ required: true }]}>
              <RangePicker style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="fields" label={t('excelExport.fieldsToExport')}>
              <Checkbox.Group options={AVAILABLE_FIELDS.map(f => ({ ...f, label: t(`excelExport.fieldLabels.${f.label}`) }))} />
            </Form.Item>

            <Form.Item name="format" label={t('excelExport.format')} initialValue="xlsx">
              <Select>
                <Option value="xlsx">Excel (.xlsx)</Option>
                <Option value="csv">CSV (.csv)</Option>
                <Option value="pdf">PDF (.pdf)</Option>
              </Select>
            </Form.Item>

            <Form.Item>
              <Space>
                <Button onClick={() => setExportModalVisible(false)}>
                  {t('excelExport.cancel')}
                </Button>
                <Button type="primary" htmlType="submit">
                  {t('excelExport.startExport')}
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}

        {currentStep === 1 && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Progress type="circle" percent={75} />
            <p style={{ marginTop: 16 }}>{t('excelExport.processingExport')}</p>
          </div>
        )}

        {currentStep === 2 && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            <p style={{ marginTop: 16 }}>{t('excelExport.exportCompleted')}</p>
            <Button type="primary" icon={<DownloadOutlined />}>
              {t('excelExport.downloadFile')}
            </Button>
          </div>
        )}
      </Modal>

      {/* Template Creation Modal */}
      <Modal
        title={t('excelExport.createExportTemplate')}
        open={templateModalVisible}
        onCancel={() => setTemplateModalVisible(false)}
        onOk={() => templateForm.submit()}
        width={600}
      >
        <Form form={templateForm} layout="vertical" onFinish={handleCreateTemplate}>
          <Form.Item name="name" label={t('excelExport.templateName')} rules={[{ required: true }]}>
            <Input placeholder={t('excelExport.enterTemplateName')} />
          </Form.Item>

          <Form.Item name="description" label={t('excelExport.description')}>
            <TextArea rows={3} placeholder={t('excelExport.describeTemplate')} />
          </Form.Item>

          <Form.Item name="fields" label={t('excelExport.fields')} rules={[{ required: true }]}>
            <Checkbox.Group options={AVAILABLE_FIELDS.map(f => ({ ...f, label: t(`excelExport.fieldLabels.${f.label}`) }))} />
          </Form.Item>

          <Form.Item name="format" label={t('excelExport.defaultFormat')} initialValue="xlsx">
            <Select>
              <Option value="xlsx">Excel (.xlsx)</Option>
              <Option value="csv">CSV (.csv)</Option>
              <Option value="pdf">PDF (.pdf)</Option>
            </Select>
          </Form.Item>

          <Form.Item name="isDefault" valuePropName="checked">
            <Checkbox>{t('excelExport.setAsDefault')}</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      {/* Schedule Export Modal */}
      <Modal
        title={t('excelExport.scheduleExport')}
        open={scheduleModalVisible}
        onCancel={() => setScheduleModalVisible(false)}
        onOk={() => scheduleForm.submit()}
        width={600}
      >
        <Form form={scheduleForm} layout="vertical" onFinish={handleCreateSchedule}>
          <Form.Item name="templateId" label={t('excelExport.template')} rules={[{ required: true }]}>
            <Select placeholder={t('excelExport.selectTemplate')}>
              {templates.map(template => (
                <Option key={template.id} value={template.id}>
                  {template.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="schedule" label={t('excelExport.schedule')} rules={[{ required: true }]}>
            <Select placeholder={t('excelExport.selectFrequency')} options={SCHEDULE_OPTIONS.map(o => ({ ...o, label: t(`excelExport.scheduleOptions.${o.label}`) }))} />
          </Form.Item>

          <Form.Item name="recipients" label={t('excelExport.recipients')} rules={[{ required: true }]}>
            <Select mode="tags" placeholder={t('excelExport.enterEmailAddresses')} />
          </Form.Item>

          <Form.Item name="startDate" label={t('excelExport.startDate')} rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Share Modal */}
      <Modal
        title={t('excelExport.shareExport')}
        open={shareModalVisible}
        onCancel={() => setShareModalVisible(false)}
        onOk={() => shareForm.submit()}
      >
        <Form form={shareForm} layout="vertical" onFinish={handleShare}>
          <Form.Item name="recipients" label={t('excelExport.recipients')} rules={[{ required: true }]}>
            <Select mode="tags" placeholder={t('excelExport.enterEmailAddresses')} />
          </Form.Item>

          <Form.Item name="permissions" label={t('excelExport.permissions')} initialValue="download">
            <Select>
              <Option value="view">{t('excelExport.viewOnly')}</Option>
              <Option value="download">{t('excelExport.download')}</Option>
              <Option value="edit">{t('excelExport.edit')}</Option>
            </Select>
          </Form.Item>

          <Form.Item name="expiresAt" label={t('excelExport.expiresAt')}>
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="password" label={t('excelExport.passwordProtection')}>
            <Input.Password placeholder={t('excelExport.optionalPassword')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ExcelExportManager;