import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Typography,
  Space,
  Tabs,
  Button,
  Table,
  Tag,
  Modal,
  Select,
  Switch,
  message,
  Statistic,
  Row,
  Col,
  Alert,
  Descriptions,
  Badge,
  Spin,
} from 'antd';
import {
  RocketOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  SyncOutlined,
  DashboardOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listSkills, syncSkills, executeSkill, toggleSkillStatus, seedClawHubSkills } from '@/services/skillAdminApi';
import { getDataSourceConfig, updateDataSourceConfig, getAccessLogs, getServiceStatus } from '@/services/aiAssistantApi';
import type { AccessLogItem, ServiceStatusResponse } from '@/services/aiAssistantApi';
import type { SkillDetail } from '@/types/aiAssistant';
import type { AIDataSource } from '@/types/aiAssistant';

const { Title, Paragraph, Text } = Typography;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const AIIntegration: React.FC = () => {
  const { t } = useTranslation('aiAssistant');
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);

  // State
  const [serviceStatus, setServiceStatus] = useState<ServiceStatusResponse | null>(null);
  const [skills, setSkills] = useState<SkillDetail[]>([]);
  const [dsConfig, setDsConfig] = useState<AIDataSource[]>([]);

  // Access log state
  const [logModalOpen, setLogModalOpen] = useState(false);
  const [logItems, setLogItems] = useState<AccessLogItem[]>([]);
  const [logTotal, setLogTotal] = useState(0);
  const [logPage, setLogPage] = useState(1);
  const [logFilter, setLogFilter] = useState<string | undefined>(undefined);
  const [logLoading, setLogLoading] = useState(false);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  const refreshAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.allSettled([refreshServiceStatus(), refreshSkills(), refreshDsConfig()]);
    } finally {
      setLoading(false);
    }
  }, []);

  async function refreshServiceStatus() {
    try {
      const data = await getServiceStatus();
      setServiceStatus(data);
    } catch {
      setServiceStatus(null);
    }
  }

  async function refreshSkills() {
    try {
      const data = await listSkills();
      setSkills(data.skills);
    } catch { /* ignore */ }
  }

  async function refreshDsConfig() {
    try {
      const data = await getDataSourceConfig();
      setDsConfig(data);
    } catch { /* ignore */ }
  }

  const handleSaveDsConfig = async () => {
    try {
      const items = dsConfig.map(s => ({
        id: s.id,
        enabled: s.enabled,
        access_mode: s.access_mode,
      }));
      const updated = await updateDataSourceConfig(items);
      setDsConfig(updated);
      message.success(t('configSaved'));
    } catch {
      message.error(t('configSaveFailed'));
    }
  };

  useEffect(() => { refreshAll(); }, [refreshAll]);

  // ---------------------------------------------------------------------------
  // Skill actions
  // ---------------------------------------------------------------------------
  const handleSync = async () => {
    setLoading(true);
    try {
      const result = await syncSkills();
      message.success(`${t('syncComplete')}: ${t('syncAdded')} ${result.added}, ${t('syncUpdated')} ${result.updated}, ${t('syncRemoved')} ${result.removed}`);
      setSkills(result.skills);
    } catch {
      message.error(t('syncFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleSeedClawHub = async () => {
    setLoading(true);
    try {
      const result = await seedClawHubSkills();
      message.success(`${t('seedComplete')}: ${t('syncAdded')} ${result.added}, ${t('seedSkipped')} ${result.skipped}`);
      await refreshSkills();
    } catch {
      message.error(t('seedFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteSkill = async (skillId: string) => {
    message.loading({ content: t('skillTable.executing'), key: 'exec' });
    try {
      const result = await executeSkill(skillId, { query: '测试查询', text: '这是一段测试文本' });
      if (result.success) {
        message.success({ content: `${t('skillTable.executeDone')} (${result.execution_time_ms}ms)`, key: 'exec' });
        Modal.info({ title: t('skillTable.executeResult'), width: 600, content: <pre style={{ maxHeight: 400, overflow: 'auto' }}>{JSON.stringify(result.result, null, 2)}</pre> });
      } else {
        message.error({ content: result.error || t('skillTable.executeFailed'), key: 'exec' });
      }
    } catch {
      message.error({ content: t('skillTable.executeFailed'), key: 'exec' });
    }
  };

  const handleToggleStatus = async (skill: SkillDetail) => {
    const newStatus = skill.status === 'deployed' ? 'pending' : 'deployed';
    try {
      await toggleSkillStatus(skill.id, newStatus);
      message.success(t('skillTable.statusUpdated'));
      await refreshSkills();
    } catch {
      message.error(t('skillTable.statusUpdateFailed'));
    }
  };

  // Access log helpers
  const fetchAccessLogs = async (page = 1, eventType?: string) => {
    setLogLoading(true);
    try {
      const data = await getAccessLogs({ page, page_size: 20, event_type: eventType });
      setLogItems(data.items);
      setLogTotal(data.total);
      setLogPage(data.page);
    } catch {
      message.error(t('accessLog.loadFailed'));
    } finally {
      setLogLoading(false);
    }
  };

  const handleOpenLogs = () => {
    setLogModalOpen(true);
    setLogFilter(undefined);
    fetchAccessLogs(1);
  };

  // Derived values from service status
  const ollamaHealthy = serviceStatus?.ollama?.healthy ?? false;
  const ollamaModels = serviceStatus?.ollama?.models ?? [];

  // ---------------------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------------------
  const skillColumns: ColumnsType<SkillDetail> = [
    { title: t('skillTable.name'), dataIndex: 'name', key: 'name', render: (name: string) => t(`skillName.${name}` as never, name) },
    { title: t('skillTable.description'), dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: t('skillTable.category'), dataIndex: 'category', key: 'category',
      render: (cat: string) => {
        const colors: Record<string, string> = { 'data-annotation': 'blue', 'data-structuring': 'purple', 'data-analysis': 'orange', 'data-processing': 'green' };
        return <Tag color={colors[cat] || 'default'}>{cat}</Tag>;
      },
    },
    { title: t('skillTable.version'), dataIndex: 'version', key: 'version', render: (v: string) => <Tag>{v}</Tag> },
    {
      title: t('skillTable.status'), dataIndex: 'status', key: 'status',
      render: (s: string) => {
        const map: Record<string, { color: string; label: string }> = {
          deployed: { color: 'green', label: t('skillTable.deployed') },
          pending: { color: 'orange', label: t('skillTable.pending') },
          removed: { color: 'red', label: t('skillTable.removed') },
        };
        const info = map[s] || { color: 'default', label: s };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: t('skillTable.deployedAt'), dataIndex: 'deployed_at', key: 'deployed_at',
      render: (v: string) => v ? new Date(v).toLocaleString() : '-',
    },
    {
      title: t('skillTable.actions'), key: 'action',
      render: (_: unknown, record: SkillDetail) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleExecuteSkill(record.id)}>{t('skillTable.test')}</Button>
          <Switch
            size="small"
            checked={record.status === 'deployed'}
            onChange={() => handleToggleStatus(record)}
            checkedChildren={t('skillTable.enabled')}
            unCheckedChildren={t('skillTable.disabled')}
          />
        </Space>
      ),
    },
  ];

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div style={{ padding: '24px' }}>
      <Spin spinning={loading}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Header */}
          <Card>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2} style={{ margin: 0 }}>
                  <RocketOutlined /> {t('header.title')}
                </Title>
                <Button icon={<ReloadOutlined />} onClick={refreshAll}>{t('header.refresh')}</Button>
              </div>
              <Paragraph>{t('header.description')}</Paragraph>
            </Space>
          </Card>

          {/* Tabs */}
          <Card>
            <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
              {
                key: 'overview',
                label: <span><DashboardOutlined /> {t('tabs.overview')}</span>,
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    {/* Statistics */}
                    <Row gutter={16}>
                      <Col span={6}>
                        <Card><Statistic title={t('overview.activeSkills')} value={skills.filter(s => s.status === 'deployed').length} prefix={<ThunderboltOutlined />} valueStyle={{ color: '#1890ff' }} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title={t('overview.availableSkills')} value={skills.length} prefix={<ApiOutlined />} valueStyle={{ color: '#3f8600' }} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title={t('overview.llmModels')} value={ollamaModels.length} suffix={t('overview.llmModelsUnit')} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title={t('overview.llmStatus')} value={ollamaHealthy ? t('serviceStatus.running') : t('serviceStatus.offline')} valueStyle={{ color: ollamaHealthy ? '#3f8600' : '#cf1322' }} /></Card>
                      </Col>
                    </Row>

                    {/* Service Status */}
                    <Card title={t('serviceStatus.title')}>
                      <Descriptions column={2} bordered>
                        <Descriptions.Item label={t('serviceStatus.backend')}>
                          <Badge status={serviceStatus?.backend?.healthy ? 'success' : 'error'} text={serviceStatus?.backend?.healthy ? t('serviceStatus.running') : t('serviceStatus.offline')} />
                        </Descriptions.Item>
                        <Descriptions.Item label={t('serviceStatus.backendUrl')}>
                          /api/v1
                        </Descriptions.Item>
                        <Descriptions.Item label={t('serviceStatus.ollama')}>
                          <Badge status={ollamaHealthy ? 'success' : 'error'} text={ollamaHealthy ? t('serviceStatus.running') : t('serviceStatus.offline')} />
                        </Descriptions.Item>
                        <Descriptions.Item label={t('serviceStatus.ollamaModels')}>
                          {ollamaModels.length ? ollamaModels.join(', ') : t('serviceStatus.noModels')}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('serviceStatus.openclaw')}>
                          <Badge status={serviceStatus?.openclaw?.healthy ? 'success' : 'error'} text={serviceStatus?.openclaw?.healthy ? t('serviceStatus.running') : t('serviceStatus.offline')} />
                        </Descriptions.Item>
                        <Descriptions.Item label={t('serviceStatus.openclawSkills')}>
                          {serviceStatus?.openclaw?.skills_count ?? 0}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>

                    {/* Quick Actions */}
                    <Card title={t('quickActions')}>
                      <Space wrap>
                        <Button type="primary" icon={<SyncOutlined />} onClick={handleSync}>{t('syncSkills')}</Button>
                        <Button icon={<DatabaseOutlined />} onClick={handleSeedClawHub}>{t('seedClawHub')}</Button>
                        <Button icon={<ReloadOutlined />} onClick={refreshAll}>{t('refreshStatus')}</Button>
                      </Space>
                    </Card>
                  </Space>
                ),
              },
              {
                key: 'skills',
                label: <span><ThunderboltOutlined /> {t('tabs.skills')}</span>,
                children: (
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text strong>{t('deployedSkills')} ({skills.length})</Text>
                      <Space>
                        <Button icon={<FileSearchOutlined />} onClick={handleOpenLogs}>{t('accessLog.viewLogs')}</Button>
                        <Button icon={<DatabaseOutlined />} onClick={handleSeedClawHub}>{t('seedClawHub')}</Button>
                        <Button type="primary" icon={<SyncOutlined />} onClick={handleSync}>{t('syncSkills')}</Button>
                      </Space>
                    </div>
                    <Table columns={skillColumns} dataSource={skills} rowKey="id" pagination={false} />
                  </Space>
                ),
              },
              {
                key: 'config',
                label: <span><SettingOutlined /> {t('tabs.config')}</span>,
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert message={t('config.llmAlert')} type="info" showIcon />
                    <Card title="LLM">
                      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <Paragraph>{t('config.llmConfigDesc')}</Paragraph>
                        <Button type="primary" icon={<LinkOutlined />} onClick={() => navigate('/admin/llm-config')}>
                          {t('config.goToLLMConfig')}
                        </Button>
                      </Space>
                    </Card>
                  </Space>
                ),
              },
              {
                key: 'datasources',
                label: <span><DatabaseOutlined /> {t('dataSourceConfig')}</span>,
                children: (
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Alert message={t('dataSourceConfigDesc')} type="info" showIcon />
                    <Table<AIDataSource>
                      dataSource={dsConfig}
                      rowKey="id"
                      pagination={false}
                      columns={[
                        {
                          title: t('dataSource'),
                          dataIndex: 'id',
                          key: 'name',
                          render: (_: unknown, record: AIDataSource) => (
                            <Space direction="vertical" size={0}>
                              <Text strong>{t(`source.${record.id}` as never, record.label)}</Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>{record.description}</Text>
                            </Space>
                          ),
                        },
                        {
                          title: t('categoryLabel'),
                          dataIndex: 'category',
                          key: 'category',
                          width: 120,
                          render: (cat: string) => (
                            <Tag>{t(`category.${cat}` as never, cat)}</Tag>
                          ),
                        },
                        {
                          title: t('sourceEnabled'),
                          dataIndex: 'enabled',
                          key: 'enabled',
                          width: 100,
                          render: (enabled: boolean, record: AIDataSource) => (
                            <Switch
                              checked={enabled}
                              checkedChildren={t('sourceEnabled')}
                              unCheckedChildren={t('sourceDisabled')}
                              onChange={(checked) => {
                                setDsConfig(prev => prev.map(s => s.id === record.id ? { ...s, enabled: checked } : s));
                              }}
                            />
                          ),
                        },
                        {
                          title: t('outputMode'),
                          dataIndex: 'access_mode',
                          key: 'access_mode',
                          width: 140,
                          render: (mode: string, record: AIDataSource) => (
                            <Select
                              value={mode}
                              style={{ width: 120 }}
                              onChange={(val) => {
                                setDsConfig(prev => prev.map(s => s.id === record.id ? { ...s, access_mode: val } : s));
                              }}
                            >
                              <Select.Option value="read">{t('accessRead')}</Select.Option>
                              <Select.Option value="read_write">{t('accessReadWrite')}</Select.Option>
                            </Select>
                          ),
                        },
                      ]}
                    />
                    <Button type="primary" onClick={handleSaveDsConfig}>{t('saveConfig')}</Button>
                  </Space>
                ),
              },
            ]} />
          </Card>
        </Space>
      </Spin>

      {/* Access Log Modal */}
      <Modal
        title={t('accessLog.title')}
        open={logModalOpen}
        onCancel={() => setLogModalOpen(false)}
        footer={null}
        width={900}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Select
            allowClear
            placeholder={t('accessLog.allEvents')}
            style={{ width: 200 }}
            value={logFilter}
            onChange={(val) => { setLogFilter(val); fetchAccessLogs(1, val); }}
          >
            <Select.Option value="skill_invoke">{t('accessLog.skillInvoke')}</Select.Option>
            <Select.Option value="skill_denied">{t('accessLog.skillDenied')}</Select.Option>
            <Select.Option value="data_access">{t('accessLog.dataAccess')}</Select.Option>
            <Select.Option value="permission_change">{t('accessLog.permissionChange')}</Select.Option>
          </Select>
          <Table<AccessLogItem>
            loading={logLoading}
            dataSource={logItems}
            rowKey="id"
            size="small"
            pagination={{
              current: logPage,
              total: logTotal,
              pageSize: 20,
              onChange: (p) => fetchAccessLogs(p, logFilter),
              showTotal: (total) => `${total}`,
              showSizeChanger: false,
            }}
            columns={[
              {
                title: t('accessLog.time'),
                dataIndex: 'created_at',
                key: 'created_at',
                width: 170,
                render: (v: string) => v ? new Date(v).toLocaleString() : '-',
              },
              {
                title: t('accessLog.eventType'),
                dataIndex: 'event_type',
                key: 'event_type',
                width: 120,
                render: (v: string) => {
                  const colorMap: Record<string, string> = {
                    skill_invoke: 'blue',
                    skill_denied: 'red',
                    data_access: 'green',
                    permission_change: 'orange',
                  };
                  const labelKey = v.replace('_', '') as string;
                  const labelMap: Record<string, string> = {
                    skillinvoke: t('accessLog.skillInvoke'),
                    skilldenied: t('accessLog.skillDenied'),
                    dataaccess: t('accessLog.dataAccess'),
                    permissionchange: t('accessLog.permissionChange'),
                  };
                  return <Tag color={colorMap[v] || 'default'}>{labelMap[labelKey] || v}</Tag>;
                },
              },
              {
                title: t('accessLog.userId'),
                dataIndex: 'user_id',
                key: 'user_id',
                width: 100,
                ellipsis: true,
              },
              {
                title: t('accessLog.userRole'),
                dataIndex: 'user_role',
                key: 'user_role',
                width: 80,
              },
              {
                title: t('accessLog.resource'),
                dataIndex: 'resource_name',
                key: 'resource_name',
                width: 120,
              },
              {
                title: t('accessLog.success'),
                dataIndex: 'success',
                key: 'success',
                width: 70,
                render: (v: boolean) => (
                  <Tag color={v ? 'green' : 'red'}>
                    {v ? t('accessLog.successLabel') : t('accessLog.failedLabel')}
                  </Tag>
                ),
              },
              {
                title: t('accessLog.details'),
                dataIndex: 'details',
                key: 'details',
                ellipsis: true,
                render: (v: Record<string, unknown>) => (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {JSON.stringify(v)}
                  </Text>
                ),
              },
            ]}
            locale={{ emptyText: t('accessLog.noLogs') }}
          />
        </Space>
      </Modal>
    </div>
  );
};

export default AIIntegration;
