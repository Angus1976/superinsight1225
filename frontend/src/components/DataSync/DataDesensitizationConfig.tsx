import React, { useState, useEffect } from 'react';
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
  Tabs,
  Alert,
  Tooltip,
  Typography,
  Row,
  Col,
  Statistic,
  Timeline,
  Badge,
  Drawer,
  Tree,
  Divider,
  Progress,
  List,
  Avatar,
  Descriptions,
  Radio,
  Slider,
  Checkbox,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SecurityScanOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  SafetyOutlined,
  AuditOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface DesensitizationRule {
  id: string;
  name: string;
  description: string;
  fieldPattern: string;
  dataType: 'email' | 'phone' | 'idcard' | 'bankcard' | 'name' | 'address' | 'custom';
  method: 'mask' | 'hash' | 'encrypt' | 'replace' | 'remove';
  maskPattern?: string;
  replaceValue?: string;
  enabled: boolean;
  priority: number;
  appliedTables: string[];
  appliedFields: string[];
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
}

interface FieldPermission {
  id: string;
  tableName: string;
  fieldName: string;
  dataType: string;
  sensitivityLevel: 'public' | 'internal' | 'confidential' | 'secret';
  permissions: {
    roleId: string;
    roleName: string;
    canRead: boolean;
    canWrite: boolean;
    canExport: boolean;
    conditions?: string;
  }[];
  desensitizationRuleId?: string;
  auditEnabled: boolean;
  createdAt: Date;
  updatedAt: Date;
}

interface AuditLog {
  id: string;
  userId: string;
  userName: string;
  action: 'read' | 'write' | 'export' | 'delete';
  tableName: string;
  fieldName: string;
  recordId?: string;
  originalValue?: string;
  newValue?: string;
  ipAddress: string;
  userAgent: string;
  timestamp: Date;
  riskLevel: 'low' | 'medium' | 'high';
}

interface ComplianceReport {
  id: string;
  reportType: 'gdpr' | 'ccpa' | 'pipl' | 'custom';
  generatedAt: Date;
  period: {
    start: Date;
    end: Date;
  };
  summary: {
    totalRecords: number;
    sensitiveRecords: number;
    accessCount: number;
    violationCount: number;
    complianceScore: number;
  };
  violations: {
    type: string;
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    count: number;
  }[];
  recommendations: string[];
}

const DataDesensitizationConfig: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'security', 'common']);
  const [activeTab, setActiveTab] = useState('rules');
  const [rules, setRules] = useState<DesensitizationRule[]>([]);
  const [permissions, setPermissions] = useState<FieldPermission[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [complianceReports, setComplianceReports] = useState<ComplianceReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<DesensitizationRule | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<FieldPermission | null>(null);
  const [form] = Form.useForm();

  // Mock data for demonstration
  useEffect(() => {
    const mockRules: DesensitizationRule[] = [
      {
        id: '1',
        name: 'Email Masking',
        description: 'Mask email addresses for privacy protection',
        fieldPattern: '*email*',
        dataType: 'email',
        method: 'mask',
        maskPattern: '***@***.***',
        enabled: true,
        priority: 1,
        appliedTables: ['users', 'customers'],
        appliedFields: ['email', 'contact_email'],
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
        createdBy: 'admin',
      },
      {
        id: '2',
        name: 'Phone Number Encryption',
        description: 'Encrypt phone numbers using AES-256',
        fieldPattern: '*phone*',
        dataType: 'phone',
        method: 'encrypt',
        enabled: true,
        priority: 2,
        appliedTables: ['users', 'contacts'],
        appliedFields: ['phone', 'mobile', 'telephone'],
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 1),
        createdBy: 'security_admin',
      },
      {
        id: '3',
        name: 'ID Card Hashing',
        description: 'Hash ID card numbers for compliance',
        fieldPattern: '*id_card*',
        dataType: 'idcard',
        method: 'hash',
        enabled: false,
        priority: 3,
        appliedTables: ['users'],
        appliedFields: ['id_card', 'identity_number'],
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
        updatedAt: new Date(Date.now() - 1000 * 60 * 30),
        createdBy: 'compliance_officer',
      },
    ];
    setRules(mockRules);

    const mockPermissions: FieldPermission[] = [
      {
        id: '1',
        tableName: 'users',
        fieldName: 'email',
        dataType: 'varchar',
        sensitivityLevel: 'confidential',
        permissions: [
          {
            roleId: '1',
            roleName: 'Admin',
            canRead: true,
            canWrite: true,
            canExport: true,
          },
          {
            roleId: '2',
            roleName: 'Manager',
            canRead: true,
            canWrite: false,
            canExport: false,
          },
          {
            roleId: '3',
            roleName: 'Analyst',
            canRead: false,
            canWrite: false,
            canExport: false,
          },
        ],
        desensitizationRuleId: '1',
        auditEnabled: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 3),
      },
      {
        id: '2',
        tableName: 'users',
        fieldName: 'phone',
        dataType: 'varchar',
        sensitivityLevel: 'secret',
        permissions: [
          {
            roleId: '1',
            roleName: 'Admin',
            canRead: true,
            canWrite: true,
            canExport: false,
          },
          {
            roleId: '2',
            roleName: 'Manager',
            canRead: false,
            canWrite: false,
            canExport: false,
          },
        ],
        desensitizationRuleId: '2',
        auditEnabled: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 8),
        updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 1),
      },
    ];
    setPermissions(mockPermissions);

    const mockAuditLogs: AuditLog[] = [
      {
        id: '1',
        userId: 'user1',
        userName: 'John Doe',
        action: 'read',
        tableName: 'users',
        fieldName: 'email',
        recordId: '12345',
        ipAddress: '192.168.1.100',
        userAgent: 'Mozilla/5.0...',
        timestamp: new Date(Date.now() - 1000 * 60 * 30),
        riskLevel: 'low',
      },
      {
        id: '2',
        userId: 'user2',
        userName: 'Jane Smith',
        action: 'export',
        tableName: 'users',
        fieldName: 'phone',
        ipAddress: '192.168.1.101',
        userAgent: 'Mozilla/5.0...',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
        riskLevel: 'high',
      },
    ];
    setAuditLogs(mockAuditLogs);

    const mockReports: ComplianceReport[] = [
      {
        id: '1',
        reportType: 'gdpr',
        generatedAt: new Date(),
        period: {
          start: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30),
          end: new Date(),
        },
        summary: {
          totalRecords: 100000,
          sensitiveRecords: 25000,
          accessCount: 5420,
          violationCount: 3,
          complianceScore: 95,
        },
        violations: [
          {
            type: 'Unauthorized Access',
            description: 'Access to sensitive data without proper authorization',
            severity: 'high',
            count: 2,
          },
          {
            type: 'Data Export Violation',
            description: 'Export of sensitive data without approval',
            severity: 'medium',
            count: 1,
          },
        ],
        recommendations: [
          'Implement stricter access controls for sensitive fields',
          'Enable mandatory approval workflow for data exports',
          'Increase audit log retention period',
        ],
      },
    ];
    setComplianceReports(mockReports);
  }, []);

  const getSensitivityColor = (level: string) => {
    switch (level) {
      case 'public':
        return 'green';
      case 'internal':
        return 'blue';
      case 'confidential':
        return 'orange';
      case 'secret':
        return 'red';
      default:
        return 'default';
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'green';
      case 'medium':
        return 'orange';
      case 'high':
        return 'red';
      default:
        return 'default';
    }
  };

  const getMethodIcon = (method: string) => {
    switch (method) {
      case 'mask':
        return <EyeInvisibleOutlined />;
      case 'hash':
        return <SecurityScanOutlined />;
      case 'encrypt':
        return <LockOutlined />;
      case 'replace':
        return <EditOutlined />;
      case 'remove':
        return <DeleteOutlined />;
      default:
        return <SafetyOutlined />;
    }
  };

  const handleCreateOrUpdateRule = async (values: any) => {
    setLoading(true);
    try {
      if (editingRule) {
        setRules(prev =>
          prev.map(rule =>
            rule.id === editingRule.id
              ? { ...rule, ...values, updatedAt: new Date() }
              : rule
          )
        );
      } else {
        const newRule: DesensitizationRule = {
          id: Date.now().toString(),
          ...values,
          appliedTables: values.appliedTables || [],
          appliedFields: values.appliedFields || [],
          createdAt: new Date(),
          updatedAt: new Date(),
          createdBy: 'current_user',
        };
        setRules(prev => [...prev, newRule]);
      }
      setModalVisible(false);
      setEditingRule(null);
      form.resetFields();
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = (rule: DesensitizationRule) => {
    Modal.confirm({
      title: t('security:desensitization.deleteConfirm'),
      content: t('security:desensitization.deleteWarning', { name: rule.name }),
      onOk: () => {
        setRules(prev => prev.filter(r => r.id !== rule.id));
      },
    });
  };

  const rulesColumns: ColumnsType<DesensitizationRule> = [
    {
      title: t('security:desensitization.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          {getMethodIcon(record.method)}
          <div>
            <Text strong>{text}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.description}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: t('security:desensitization.dataType'),
      dataIndex: 'dataType',
      key: 'dataType',
      render: (type) => (
        <Tag color="blue">{t(`security:dataTypes.${type}`)}</Tag>
      ),
    },
    {
      title: t('security:desensitization.method'),
      dataIndex: 'method',
      key: 'method',
      render: (method) => (
        <Tag color="purple">{t(`security:methods.${method}`)}</Tag>
      ),
    },
    {
      title: t('security:desensitization.fieldPattern'),
      dataIndex: 'fieldPattern',
      key: 'fieldPattern',
      render: (pattern) => <Text code>{pattern}</Text>,
    },
    {
      title: t('security:desensitization.priority'),
      dataIndex: 'priority',
      key: 'priority',
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: t('security:desensitization.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled) => (
        <Badge
          status={enabled ? 'success' : 'default'}
          text={enabled ? t('common:enabled') : t('common:disabled')}
        />
      ),
    },
    {
      title: t('security:desensitization.appliedTables'),
      dataIndex: 'appliedTables',
      key: 'appliedTables',
      render: (tables) => (
        <Space wrap>
          {tables.slice(0, 2).map((table: string) => (
            <Tag key={table} size="small">{table}</Tag>
          ))}
          {tables.length > 2 && (
            <Tag size="small">+{tables.length - 2}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingRule(record);
                form.setFieldsValue(record);
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('common:delete')}>
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteRule(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const permissionsColumns: ColumnsType<FieldPermission> = [
    {
      title: t('security:permissions.table'),
      dataIndex: 'tableName',
      key: 'tableName',
    },
    {
      title: t('security:permissions.field'),
      dataIndex: 'fieldName',
      key: 'fieldName',
      render: (text, record) => (
        <Space>
          <Text strong>{text}</Text>
          <Tag color={getSensitivityColor(record.sensitivityLevel)}>
            {t(`security:sensitivity.${record.sensitivityLevel}`)}
          </Tag>
        </Space>
      ),
    },
    {
      title: t('security:permissions.dataType'),
      dataIndex: 'dataType',
      key: 'dataType',
    },
    {
      title: t('security:permissions.roles'),
      key: 'roles',
      render: (_, record) => (
        <Space wrap>
          {record.permissions.map(perm => (
            <Tag
              key={perm.roleId}
              color={perm.canRead || perm.canWrite || perm.canExport ? 'green' : 'red'}
            >
              {perm.roleName}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('security:permissions.audit'),
      dataIndex: 'auditEnabled',
      key: 'auditEnabled',
      render: (enabled) => (
        <Badge
          status={enabled ? 'success' : 'default'}
          text={enabled ? t('common:enabled') : t('common:disabled')}
        />
      ),
    },
    {
      title: t('common:actions.label'),
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title={t('security:permissions.viewDetails')}>
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setSelectedPermission(record);
                setDrawerVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title={t('common:edit')}>
            <Button
              type="text"
              icon={<EditOutlined />}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const auditColumns: ColumnsType<AuditLog> = [
    {
      title: t('security:audit.timestamp'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => dayjs(a.timestamp).unix() - dayjs(b.timestamp).unix(),
    },
    {
      title: t('security:audit.user'),
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          <div>
            <Text>{record.userName}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.userId}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: t('security:audit.action'),
      dataIndex: 'action',
      key: 'action',
      render: (action) => (
        <Tag color="blue">{t(`security:actions.${action}`)}</Tag>
      ),
    },
    {
      title: t('security:audit.resource'),
      key: 'resource',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text>{record.tableName}.{record.fieldName}</Text>
          {record.recordId && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              Record: {record.recordId}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: t('security:audit.riskLevel'),
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      render: (level) => (
        <Tag color={getRiskLevelColor(level)}>
          {t(`security:risk.${level}`)}
        </Tag>
      ),
    },
    {
      title: t('security:audit.ipAddress'),
      dataIndex: 'ipAddress',
      key: 'ipAddress',
    },
  ];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('security:stats.totalRules')}
              value={rules.length}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('security:stats.activeRules')}
              value={rules.filter(rule => rule.enabled).length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('security:stats.protectedFields')}
              value={permissions.length}
              prefix={<LockOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('security:stats.auditLogs')}
              value={auditLogs.length}
              prefix={<AuditOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab={t('security:tabs.rules')} key="rules">
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingRule(null);
                  form.resetFields();
                  setModalVisible(true);
                }}
              >
                {t('security:desensitization.createRule')}
              </Button>
            </div>
            <Table
              columns={rulesColumns}
              dataSource={rules}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => t('common:pagination.total', { total }),
              }}
            />
          </TabPane>

          <TabPane tab={t('security:tabs.permissions')} key="permissions">
            <Table
              columns={permissionsColumns}
              dataSource={permissions}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => t('common:pagination.total', { total }),
              }}
            />
          </TabPane>

          <TabPane tab={t('security:tabs.audit')} key="audit">
            <Table
              columns={auditColumns}
              dataSource={auditLogs}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => t('common:pagination.total', { total }),
              }}
            />
          </TabPane>

          <TabPane tab={t('security:tabs.compliance')} key="compliance">
            <Space direction="vertical" style={{ width: '100%' }}>
              {complianceReports.map(report => (
                <Card key={report.id} size="small">
                  <Row gutter={16}>
                    <Col span={18}>
                      <Descriptions title={t(`security:compliance.${report.reportType}`)} column={3}>
                        <Descriptions.Item label={t('security:compliance.period')}>
                          {dayjs(report.period.start).format('YYYY-MM-DD')} - {dayjs(report.period.end).format('YYYY-MM-DD')}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('security:compliance.totalRecords')}>
                          {report.summary.totalRecords.toLocaleString()}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('security:compliance.sensitiveRecords')}>
                          {report.summary.sensitiveRecords.toLocaleString()}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('security:compliance.accessCount')}>
                          {report.summary.accessCount.toLocaleString()}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('security:compliance.violations')}>
                          <Text type={report.summary.violationCount > 0 ? 'danger' : 'success'}>
                            {report.summary.violationCount}
                          </Text>
                        </Descriptions.Item>
                        <Descriptions.Item label={t('security:compliance.score')}>
                          <Progress
                            percent={report.summary.complianceScore}
                            size="small"
                            status={report.summary.complianceScore >= 90 ? 'success' : 'exception'}
                          />
                        </Descriptions.Item>
                      </Descriptions>
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={t('security:compliance.score')}
                        value={report.summary.complianceScore}
                        suffix="%"
                        valueStyle={{
                          color: report.summary.complianceScore >= 90 ? '#3f8600' : '#cf1322'
                        }}
                      />
                    </Col>
                  </Row>

                  {report.violations.length > 0 && (
                    <>
                      <Divider />
                      <Title level={5}>{t('security:compliance.violations')}</Title>
                      <List
                        size="small"
                        dataSource={report.violations}
                        renderItem={violation => (
                          <List.Item>
                            <List.Item.Meta
                              avatar={<Avatar icon={<WarningOutlined />} style={{ backgroundColor: getRiskLevelColor(violation.severity) }} />}
                              title={violation.type}
                              description={violation.description}
                            />
                            <Tag color={getRiskLevelColor(violation.severity)}>
                              {violation.count} {t('security:compliance.occurrences')}
                            </Tag>
                          </List.Item>
                        )}
                      />
                    </>
                  )}

                  {report.recommendations.length > 0 && (
                    <>
                      <Divider />
                      <Title level={5}>{t('security:compliance.recommendations')}</Title>
                      <List
                        size="small"
                        dataSource={report.recommendations}
                        renderItem={recommendation => (
                          <List.Item>
                            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                            {recommendation}
                          </List.Item>
                        )}
                      />
                    </>
                  )}
                </Card>
              ))}
            </Space>
          </TabPane>
        </Tabs>
      </Card>

      {/* Create/Edit Rule Modal */}
      <Modal
        title={editingRule ? t('security:desensitization.editRule') : t('security:desensitization.createRule')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingRule(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={loading}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateOrUpdateRule}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={t('security:desensitization.name')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder={t('security:desensitization.namePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dataType"
                label={t('security:desensitization.dataType')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Select placeholder={t('security:desensitization.dataTypePlaceholder')}>
                  <Select.Option value="email">{t('security:dataTypes.email')}</Select.Option>
                  <Select.Option value="phone">{t('security:dataTypes.phone')}</Select.Option>
                  <Select.Option value="idcard">{t('security:dataTypes.idcard')}</Select.Option>
                  <Select.Option value="bankcard">{t('security:dataTypes.bankcard')}</Select.Option>
                  <Select.Option value="name">{t('security:dataTypes.name')}</Select.Option>
                  <Select.Option value="address">{t('security:dataTypes.address')}</Select.Option>
                  <Select.Option value="custom">{t('security:dataTypes.custom')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label={t('security:desensitization.description')}
          >
            <TextArea rows={3} placeholder={t('security:desensitization.descriptionPlaceholder')} />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="fieldPattern"
                label={t('security:desensitization.fieldPattern')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Input placeholder="*email*" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="method"
                label={t('security:desensitization.method')}
                rules={[{ required: true, message: t('common:validation.required') }]}
              >
                <Select placeholder={t('security:desensitization.methodPlaceholder')}>
                  <Select.Option value="mask">{t('security:methods.mask')}</Select.Option>
                  <Select.Option value="hash">{t('security:methods.hash')}</Select.Option>
                  <Select.Option value="encrypt">{t('security:methods.encrypt')}</Select.Option>
                  <Select.Option value="replace">{t('security:methods.replace')}</Select.Option>
                  <Select.Option value="remove">{t('security:methods.remove')}</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="maskPattern"
            label={t('security:desensitization.maskPattern')}
          >
            <Input placeholder="***@***.***" />
          </Form.Item>

          <Form.Item
            name="replaceValue"
            label={t('security:desensitization.replaceValue')}
          >
            <Input placeholder="[REDACTED]" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label={t('security:desensitization.priority')}
                initialValue={1}
              >
                <Slider min={1} max={10} marks={{ 1: '1', 5: '5', 10: '10' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="enabled"
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>{t('security:desensitization.enabled')}</Checkbox>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="appliedTables"
            label={t('security:desensitization.appliedTables')}
          >
            <Select mode="tags" placeholder={t('security:desensitization.appliedTablesPlaceholder')}>
              <Select.Option value="users">users</Select.Option>
              <Select.Option value="customers">customers</Select.Option>
              <Select.Option value="orders">orders</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="appliedFields"
            label={t('security:desensitization.appliedFields')}
          >
            <Select mode="tags" placeholder={t('security:desensitization.appliedFieldsPlaceholder')}>
              <Select.Option value="email">email</Select.Option>
              <Select.Option value="phone">phone</Select.Option>
              <Select.Option value="mobile">mobile</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Permission Details Drawer */}
      <Drawer
        title={t('security:permissions.details')}
        placement="right"
        size="large"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
      >
        {selectedPermission && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Card size="small" title={t('security:permissions.basicInfo')}>
              <Descriptions column={1}>
                <Descriptions.Item label={t('security:permissions.table')}>
                  {selectedPermission.tableName}
                </Descriptions.Item>
                <Descriptions.Item label={t('security:permissions.field')}>
                  {selectedPermission.fieldName}
                </Descriptions.Item>
                <Descriptions.Item label={t('security:permissions.dataType')}>
                  {selectedPermission.dataType}
                </Descriptions.Item>
                <Descriptions.Item label={t('security:permissions.sensitivity')}>
                  <Tag color={getSensitivityColor(selectedPermission.sensitivityLevel)}>
                    {t(`security:sensitivity.${selectedPermission.sensitivityLevel}`)}
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title={t('security:permissions.rolePermissions')}>
              <Table
                size="small"
                columns={[
                  {
                    title: t('security:permissions.role'),
                    dataIndex: 'roleName',
                    key: 'roleName',
                  },
                  {
                    title: t('security:permissions.read'),
                    dataIndex: 'canRead',
                    key: 'canRead',
                    render: (canRead) => (
                      <Badge
                        status={canRead ? 'success' : 'error'}
                        text={canRead ? t('common:allowed') : t('common:denied')}
                      />
                    ),
                  },
                  {
                    title: t('security:permissions.write'),
                    dataIndex: 'canWrite',
                    key: 'canWrite',
                    render: (canWrite) => (
                      <Badge
                        status={canWrite ? 'success' : 'error'}
                        text={canWrite ? t('common:allowed') : t('common:denied')}
                      />
                    ),
                  },
                  {
                    title: t('security:permissions.export'),
                    dataIndex: 'canExport',
                    key: 'canExport',
                    render: (canExport) => (
                      <Badge
                        status={canExport ? 'success' : 'error'}
                        text={canExport ? t('common:allowed') : t('common:denied')}
                      />
                    ),
                  },
                ]}
                dataSource={selectedPermission.permissions}
                rowKey="roleId"
                pagination={false}
              />
            </Card>
          </Space>
        )}
      </Drawer>
    </div>
  );
};

export default DataDesensitizationConfig;