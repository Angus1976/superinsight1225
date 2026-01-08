// Quality management page
import { useState } from 'react';
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
  Switch,
  Row,
  Col,
  Statistic,
  Tabs,
  Badge,
  Tooltip,
  message,
  Drawer,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  BugOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  HistoryOutlined,
  SendOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import RuleTemplateManager, { type RuleTemplate } from '@/components/Quality/RuleTemplateManager';
import RuleConfigForm from '@/components/Quality/RuleConfigForm';
import RuleVersionManager, { type RuleVersion } from '@/components/Quality/RuleVersionManager';
import WorkOrderManager, { type WorkOrder } from '@/components/Quality/WorkOrderManager';
import QualityReportsAnalysis, { 
  type QualityAssessment, 
  type QualityTrend, 
  type IssueDistribution, 
  type ActionPlan 
} from '@/components/Quality/QualityReportsAnalysis';

interface QualityRule {
  id: string;
  name: string;
  type: 'format' | 'content' | 'consistency' | 'custom';
  description: string;
  enabled: boolean;
  severity: 'warning' | 'error';
  violations_count: number;
  last_run?: string;
}

interface QualityIssue {
  id: string;
  rule_id: string;
  rule_name: string;
  task_id: string;
  task_name: string;
  severity: 'warning' | 'error';
  description: string;
  status: 'open' | 'fixed' | 'ignored';
  created_at: string;
  assigned_to?: string;
}

// Mock data
const mockRules: QualityRule[] = [
  {
    id: '1',
    name: 'Label Consistency Check',
    type: 'consistency',
    description: 'Ensure labels are consistent across similar samples',
    enabled: true,
    severity: 'error',
    violations_count: 12,
    last_run: '2025-01-20T10:00:00Z',
  },
  {
    id: '2',
    name: 'Text Length Validation',
    type: 'format',
    description: 'Check if annotation text meets minimum length requirements',
    enabled: true,
    severity: 'warning',
    violations_count: 45,
    last_run: '2025-01-20T10:00:00Z',
  },
  {
    id: '3',
    name: 'Empty Label Detection',
    type: 'content',
    description: 'Detect annotations with empty or missing labels',
    enabled: true,
    severity: 'error',
    violations_count: 3,
    last_run: '2025-01-20T10:00:00Z',
  },
  {
    id: '4',
    name: 'Duplicate Detection',
    type: 'consistency',
    description: 'Find duplicate or near-duplicate annotations',
    enabled: false,
    severity: 'warning',
    violations_count: 0,
  },
];

const mockIssues: QualityIssue[] = [
  {
    id: '1',
    rule_id: '1',
    rule_name: 'Label Consistency Check',
    task_id: 'task1',
    task_name: 'Customer Review Classification',
    severity: 'error',
    description: 'Inconsistent labeling for similar review content',
    status: 'open',
    created_at: '2025-01-20T08:30:00Z',
    assigned_to: 'John Doe',
  },
  {
    id: '2',
    rule_id: '2',
    rule_name: 'Text Length Validation',
    task_id: 'task1',
    task_name: 'Customer Review Classification',
    severity: 'warning',
    description: 'Annotation text is below minimum length (5 chars)',
    status: 'fixed',
    created_at: '2025-01-19T14:20:00Z',
  },
  {
    id: '3',
    rule_id: '3',
    rule_name: 'Empty Label Detection',
    task_id: 'task2',
    task_name: 'Product Entity Recognition',
    severity: 'error',
    description: 'Empty label found in annotation #1234',
    status: 'open',
    created_at: '2025-01-20T09:15:00Z',
  },
];

const typeColors: Record<string, string> = {
  format: 'blue',
  content: 'green',
  consistency: 'orange',
  custom: 'purple',
};

const severityColors = {
  warning: 'warning',
  error: 'error',
} as const;

const statusColors = {
  open: 'error',
  fixed: 'success',
  ignored: 'default',
} as const;

const QualityPage: React.FC = () => {
  const { t } = useTranslation();
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false);
  const [versionDrawerOpen, setVersionDrawerOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<QualityRule | null>(null);
  const [ruleForm] = Form.useForm();

  // Mock templates data
  const mockTemplates: RuleTemplate[] = [
    {
      id: 'template1',
      name: 'Label Consistency Template',
      type: 'consistency',
      description: 'Template for checking label consistency across similar samples',
      severity: 'error',
      config: { similarityThreshold: 0.9, checkDuplicates: true },
      isBuiltIn: true,
      usageCount: 15,
    },
    {
      id: 'template2',
      name: 'Text Length Template',
      type: 'format',
      description: 'Template for validating text length requirements',
      severity: 'warning',
      config: { minLength: 5, maxLength: 1000 },
      isBuiltIn: true,
      usageCount: 8,
    },
  ];

  // Mock versions data
  const mockVersions: RuleVersion[] = [
    {
      id: 'v1',
      ruleId: '1',
      version: '1.2.0',
      name: 'Label Consistency Check',
      description: 'Updated similarity threshold',
      config: { similarityThreshold: 0.9, checkDuplicates: true },
      createdBy: 'John Doe',
      createdAt: '2025-01-20T10:00:00Z',
      isActive: true,
      changeLog: 'Improved accuracy by adjusting similarity threshold',
      tags: ['stable', 'production'],
    },
    {
      id: 'v2',
      ruleId: '1',
      version: '1.1.0',
      name: 'Label Consistency Check',
      description: 'Initial version',
      config: { similarityThreshold: 0.8, checkDuplicates: false },
      createdBy: 'Jane Smith',
      createdAt: '2025-01-15T10:00:00Z',
      isActive: false,
      changeLog: 'Initial implementation',
      tags: ['legacy'],
    },
  ];

  // Mock work orders data
  const mockWorkOrders: WorkOrder[] = [
    {
      id: 'wo1',
      title: 'Fix Label Consistency Issues',
      description: 'Address inconsistent labeling found in customer review dataset',
      priority: 'high',
      status: 'inProgress',
      assigneeId: 'user1',
      assigneeName: 'John Doe',
      assigneeAvatar: undefined,
      createdBy: 'admin',
      createdAt: '2025-01-20T09:00:00Z',
      updatedAt: '2025-01-20T10:00:00Z',
      dueDate: '2025-01-25T18:00:00Z',
      progress: 65,
      issueIds: ['issue1', 'issue2'],
      comments: [
        {
          id: 'c1',
          content: 'Started working on the consistency issues',
          authorId: 'user1',
          authorName: 'John Doe',
          createdAt: '2025-01-20T10:00:00Z',
        },
      ],
      attachments: [],
      tags: ['urgent', 'quality'],
    },
    {
      id: 'wo2',
      title: 'Review Text Length Validation',
      description: 'Review and update text length validation rules',
      priority: 'medium',
      status: 'pending',
      createdBy: 'admin',
      createdAt: '2025-01-19T14:00:00Z',
      updatedAt: '2025-01-19T14:00:00Z',
      dueDate: '2025-01-30T18:00:00Z',
      progress: 0,
      issueIds: ['issue3'],
      comments: [],
      attachments: [],
      tags: ['validation'],
    },
  ];

  // Mock users data
  const mockUsers = [
    { id: 'user1', name: 'John Doe' },
    { id: 'user2', name: 'Jane Smith' },
    { id: 'user3', name: 'Bob Wilson' },
  ];

  // Mock assessment data
  const mockAssessments: QualityAssessment[] = [
    {
      id: 'a1',
      userId: 'user1',
      userName: 'John Doe',
      period: '2025-01',
      qualityScore: 95,
      tasksCompleted: 45,
      issuesFound: 8,
      issuesFixed: 7,
      averageResolutionTime: 2.5,
      trend: 'up',
      rank: 1,
      department: 'Annotation',
      achievements: ['Quality Champion', 'Fast Resolver'],
      improvements: ['Consistency training'],
    },
    {
      id: 'a2',
      userId: 'user2',
      userName: 'Jane Smith',
      period: '2025-01',
      qualityScore: 88,
      tasksCompleted: 38,
      issuesFound: 12,
      issuesFixed: 10,
      averageResolutionTime: 3.2,
      trend: 'stable',
      rank: 2,
      department: 'Review',
      achievements: ['Reliable Performer'],
      improvements: ['Speed optimization'],
    },
  ];

  // Mock trend data
  const mockTrends: QualityTrend[] = [
    { date: '2025-01-14', qualityScore: 85, issuesFound: 15, issuesFixed: 12, efficiency: 80 },
    { date: '2025-01-15', qualityScore: 87, issuesFound: 12, issuesFixed: 11, efficiency: 82 },
    { date: '2025-01-16', qualityScore: 89, issuesFound: 10, issuesFixed: 9, efficiency: 85 },
    { date: '2025-01-17', qualityScore: 91, issuesFound: 8, issuesFixed: 8, efficiency: 88 },
    { date: '2025-01-18', qualityScore: 93, issuesFound: 6, issuesFixed: 6, efficiency: 90 },
    { date: '2025-01-19', qualityScore: 92, issuesFound: 7, issuesFixed: 6, efficiency: 89 },
    { date: '2025-01-20', qualityScore: 94, issuesFound: 5, issuesFixed: 5, efficiency: 92 },
  ];

  // Mock issue distribution data
  const mockIssueDistribution: IssueDistribution[] = [
    { category: 'Label Consistency', count: 25, percentage: 45, color: '#ff4d4f' },
    { category: 'Text Format', count: 15, percentage: 27, color: '#faad14' },
    { category: 'Missing Data', count: 10, percentage: 18, color: '#1890ff' },
    { category: 'Other', count: 6, percentage: 10, color: '#52c41a' },
  ];

  // Mock action plans data
  const mockActionPlans: ActionPlan[] = [
    {
      id: 'ap1',
      title: 'Improve Label Consistency Training',
      description: 'Develop comprehensive training materials for label consistency',
      priority: 'high',
      assignee: 'Training Team',
      dueDate: '2025-02-15',
      status: 'inProgress',
      progress: 60,
    },
    {
      id: 'ap2',
      title: 'Automate Format Validation',
      description: 'Implement automated checks for text format issues',
      priority: 'medium',
      assignee: 'Dev Team',
      dueDate: '2025-02-28',
      status: 'pending',
      progress: 0,
    },
  ];

  const handleCreateRule = async (_values: Record<string, unknown>) => {
    message.success(t('quality.messages.ruleCreated'));
    setRuleModalOpen(false);
    ruleForm.resetFields();
  };

  const handleToggleRule = (_id: string, enabled: boolean) => {
    message.success(enabled ? t('quality.messages.ruleEnabled') : t('quality.messages.ruleDisabled'));
  };

  const handleRunAllRules = () => {
    message.info(t('quality.messages.ruleRunning'));
  };

  const handleEditRule = (rule: QualityRule) => {
    setSelectedRule(rule);
    setConfigDrawerOpen(true);
  };

  const handleViewVersions = (rule: QualityRule) => {
    setSelectedRule(rule);
    setVersionDrawerOpen(true);
  };

  const handleSaveRuleConfig = async (ruleData: Partial<QualityRule>) => {
    // Implementation for saving rule configuration
    console.log('Saving rule config:', ruleData);
    message.success(t('quality.messages.ruleUpdated'));
    setConfigDrawerOpen(false);
  };

  const handleTestRule = async (ruleData: Partial<QualityRule>) => {
    // Implementation for testing rule
    console.log('Testing rule:', ruleData);
    return { success: true, message: t('quality.messages.testPassed') };
  };

  const handleCreateFromTemplate = (template: RuleTemplate) => {
    // Implementation for creating rule from template
    console.log('Creating rule from template:', template);
    message.success(t('quality.messages.ruleCreated'));
  };

  const handleCreateTemplate = async (template: Omit<RuleTemplate, 'id' | 'usageCount'>) => {
    // Implementation for creating template
    console.log('Creating template:', template);
  };

  const handleUpdateTemplate = async (id: string, template: Partial<RuleTemplate>) => {
    // Implementation for updating template
    console.log('Updating template:', id, template);
  };

  const handleDeleteTemplate = async (id: string) => {
    // Implementation for deleting template
    console.log('Deleting template:', id);
  };

  const handleRollbackVersion = async (versionId: string) => {
    // Implementation for rolling back to version
    console.log('Rolling back to version:', versionId);
  };

  const handleDeleteVersion = async (versionId: string) => {
    // Implementation for deleting version
    console.log('Deleting version:', versionId);
  };

  const handleViewVersion = (version: RuleVersion) => {
    // Implementation for viewing version details
    console.log('Viewing version:', version);
  };

  // Work order handlers
  const handleCreateWorkOrder = async (workOrder: Omit<WorkOrder, 'id' | 'createdAt' | 'updatedAt' | 'progress' | 'comments' | 'attachments'>) => {
    // Implementation for creating work order
    console.log('Creating work order:', workOrder);
  };

  const handleUpdateWorkOrder = async (id: string, workOrder: Partial<WorkOrder>) => {
    // Implementation for updating work order
    console.log('Updating work order:', id, workOrder);
  };

  const handleDispatchWorkOrder = async (id: string, assigneeId: string) => {
    // Implementation for dispatching work order
    console.log('Dispatching work order:', id, 'to:', assigneeId);
  };

  const handleAddComment = async (workOrderId: string, comment: string) => {
    // Implementation for adding comment
    console.log('Adding comment to work order:', workOrderId, comment);
  };

  const handleUploadAttachment = async (workOrderId: string, file: File) => {
    // Implementation for uploading attachment
    console.log('Uploading attachment to work order:', workOrderId, file.name);
  };

  // Reports handlers
  const handleExportReport = async (type: string, period: string) => {
    // Implementation for exporting report
    console.log('Exporting report:', type, period);
  };

  const handleScheduleReport = async (config: Record<string, unknown>) => {
    // Implementation for scheduling report
    console.log('Scheduling report:', config);
  };

  const ruleColumns: ColumnsType<QualityRule> = [
    {
      title: 'Rule Name',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          {record.enabled ? (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          ) : (
            <CloseCircleOutlined style={{ color: '#999' }} />
          )}
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type) => <Tag color={typeColors[type]}>{type.toUpperCase()}</Tag>,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: keyof typeof severityColors) => (
        <Badge status={severityColors[severity]} text={severity.toUpperCase()} />
      ),
    },
    {
      title: 'Violations',
      dataIndex: 'violations_count',
      key: 'violations_count',
      width: 100,
      render: (count) => (
        <Tag color={count > 0 ? 'red' : 'green'}>{count}</Tag>
      ),
    },
    {
      title: 'Enabled',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 100,
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          size="small"
          onChange={(checked) => handleToggleRule(record.id, checked)}
        />
      ),
    },
    {
      title: 'Last Run',
      dataIndex: 'last_run',
      key: 'last_run',
      width: 150,
      render: (date) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Tooltip title={t('quality.rules.run')}>
            <Button type="link" size="small" icon={<PlayCircleOutlined />} />
          </Tooltip>
          <Tooltip title={t('quality.rules.config')}>
            <Button 
              type="link" 
              size="small" 
              icon={<SettingOutlined />}
              onClick={() => handleEditRule(record)}
            />
          </Tooltip>
          <Tooltip title={t('quality.rules.version')}>
            <Button 
              type="link" 
              size="small" 
              icon={<HistoryOutlined />}
              onClick={() => handleViewVersions(record)}
            />
          </Tooltip>
          <Tooltip title={t('quality.rules.edit')}>
            <Button type="link" size="small" icon={<EditOutlined />} />
          </Tooltip>
          <Tooltip title={t('quality.rules.delete')}>
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const issueColumns: ColumnsType<QualityIssue> = [
    {
      title: 'Issue',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Rule',
      dataIndex: 'rule_name',
      key: 'rule_name',
      width: 200,
    },
    {
      title: 'Task',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
      render: (name) => <a>{name}</a>,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: keyof typeof severityColors) => (
        <Badge status={severityColors[severity]} text={severity.toUpperCase()} />
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: keyof typeof statusColors) => (
        <Tag color={statusColors[status]}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => new Date(date).toLocaleString(),
    },
  ];

  // Calculate stats
  const totalViolations = mockRules.reduce((sum, r) => sum + r.violations_count, 0);
  const openIssues = mockIssues.filter((i) => i.status === 'open').length;
  void mockIssues.filter((i) => i.severity === 'error' && i.status === 'open').length; // Error count for future use

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>{t('quality.title')}</h2>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('quality.stats.activeRules')}
              value={mockRules.filter((r) => r.enabled).length}
              suffix={`/ ${mockRules.length}`}
              prefix={<SafetyCertificateOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('quality.stats.totalViolations')}
              value={totalViolations}
              prefix={<WarningOutlined />}
              valueStyle={{ color: totalViolations > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('quality.stats.openIssues')}
              value={openIssues}
              prefix={<BugOutlined />}
              valueStyle={{ color: openIssues > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title={t('quality.stats.qualityScore')}
              value={92}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Card>
        <Tabs
          defaultActiveKey="rules"
          items={[
            {
              key: 'rules',
              label: (
                <span>
                  <SafetyCertificateOutlined />
                  {t('quality.rules.title')}
                </span>
              ),
              children: (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <Space>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setRuleModalOpen(true)}
                      >
                        {t('quality.rules.create')}
                      </Button>
                      <Button
                        icon={<PlayCircleOutlined />}
                        onClick={handleRunAllRules}
                      >
                        {t('quality.rules.runAll')}
                      </Button>
                    </Space>
                  </div>
                  <Table
                    columns={ruleColumns}
                    dataSource={mockRules}
                    rowKey="id"
                    pagination={false}
                    expandable={{
                      expandedRowRender: (record) => (
                        <p style={{ margin: 0, color: '#666' }}>
                          {record.description}
                        </p>
                      ),
                    }}
                  />
                </>
              ),
            },
            {
              key: 'templates',
              label: (
                <span>
                  <SettingOutlined />
                  {t('quality.rules.template')}
                </span>
              ),
              children: (
                <RuleTemplateManager
                  templates={mockTemplates}
                  onCreateFromTemplate={handleCreateFromTemplate}
                  onCreateTemplate={handleCreateTemplate}
                  onUpdateTemplate={handleUpdateTemplate}
                  onDeleteTemplate={handleDeleteTemplate}
                />
              ),
            },
            {
              key: 'issues',
              label: (
                <span>
                  <BugOutlined />
                  {t('quality.issues.title')}
                  {openIssues > 0 && (
                    <Badge
                      count={openIssues}
                      size="small"
                      style={{ marginLeft: 8 }}
                    />
                  )}
                </span>
              ),
              children: (
                <Table
                  columns={issueColumns}
                  dataSource={mockIssues}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                />
              ),
            },
            {
              key: 'workOrders',
              label: (
                <span>
                  <SendOutlined />
                  {t('quality.workOrders.title')}
                </span>
              ),
              children: (
                <WorkOrderManager
                  workOrders={mockWorkOrders}
                  onCreateWorkOrder={handleCreateWorkOrder}
                  onUpdateWorkOrder={handleUpdateWorkOrder}
                  onDispatchWorkOrder={handleDispatchWorkOrder}
                  onAddComment={handleAddComment}
                  onUploadAttachment={handleUploadAttachment}
                  users={mockUsers}
                />
              ),
            },
            {
              key: 'reports',
              label: (
                <span>
                  <BarChartOutlined />
                  {t('quality.reports.title')}
                </span>
              ),
              children: (
                <QualityReportsAnalysis
                  assessments={mockAssessments}
                  trends={mockTrends}
                  issueDistribution={mockIssueDistribution}
                  actionPlans={mockActionPlans}
                  onExportReport={handleExportReport}
                  onScheduleReport={handleScheduleReport}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* Create Rule Modal */}
      <Modal
        title={t('quality.rules.create')}
        open={ruleModalOpen}
        onCancel={() => setRuleModalOpen(false)}
        onOk={() => ruleForm.submit()}
        width={600}
      >
        <Form form={ruleForm} layout="vertical" onFinish={handleCreateRule}>
          <Form.Item
            name="name"
            label={t('quality.rules.name')}
            rules={[{ required: true, message: t('common.required') }]}
          >
            <Input placeholder={t('quality.rules.name')} />
          </Form.Item>
          <Form.Item
            name="type"
            label={t('quality.rules.type')}
            rules={[{ required: true }]}
          >
            <Select placeholder={t('quality.rules.type')}>
              <Select.Option value="format">{t('quality.rules.types.format')}</Select.Option>
              <Select.Option value="content">{t('quality.rules.types.content')}</Select.Option>
              <Select.Option value="consistency">{t('quality.rules.types.consistency')}</Select.Option>
              <Select.Option value="custom">{t('quality.rules.types.custom')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="severity"
            label={t('quality.rules.severity')}
            rules={[{ required: true }]}
            initialValue="warning"
          >
            <Select>
              <Select.Option value="warning">{t('quality.rules.severities.warning')}</Select.Option>
              <Select.Option value="error">{t('quality.rules.severities.error')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label={t('quality.rules.description')}>
            <Input.TextArea rows={3} placeholder={t('quality.rules.description')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Rule Configuration Drawer */}
      <Drawer
        title={`${t('quality.rules.config')} - ${selectedRule?.name}`}
        open={configDrawerOpen}
        onClose={() => setConfigDrawerOpen(false)}
        width={800}
        destroyOnClose
      >
        {selectedRule && (
          <RuleConfigForm
            rule={selectedRule}
            onSave={handleSaveRuleConfig}
            onTest={handleTestRule}
          />
        )}
      </Drawer>

      {/* Version Management Drawer */}
      <Drawer
        title={`${t('quality.rules.version')} - ${selectedRule?.name}`}
        open={versionDrawerOpen}
        onClose={() => setVersionDrawerOpen(false)}
        width={1000}
        destroyOnClose
      >
        {selectedRule && (
          <RuleVersionManager
            ruleId={selectedRule.id}
            versions={mockVersions}
            onRollback={handleRollbackVersion}
            onDeleteVersion={handleDeleteVersion}
            onViewVersion={handleViewVersion}
          />
        )}
      </Drawer>
    </div>
  );
};

export default QualityPage;
