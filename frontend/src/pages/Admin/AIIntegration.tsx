import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Typography,
  Space,
  Tabs,
  Button,
  Table,
  Tag,
  Modal,
  Form,
  Input,
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
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { listSkills, syncSkills, executeSkill, toggleSkillStatus, seedClawHubSkills } from '@/services/skillAdminApi';
import { getDataSourceConfig, updateDataSourceConfig, getAccessLogs } from '@/services/aiAssistantApi';
import type { AccessLogItem } from '@/services/aiAssistantApi';
import type { SkillDetail } from '@/types/aiAssistant';
import type { AIDataSource } from '@/types/aiAssistant';

const { Title, Paragraph, Text } = Typography;

// ---------------------------------------------------------------------------
// Types (service health only — skill types come from @/types/aiAssistant)
// ---------------------------------------------------------------------------
interface ServiceStatus {
  healthy: boolean;
  label: string;
  url: string;
}

interface OllamaStatus {
  healthy: boolean;
  models: string[];
  provider: string;
  model: string;
}

// Service URLs for health checks only
const GATEWAY_URL = 'http://localhost:3000';
const AGENT_URL = 'http://localhost:8081';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const AIIntegration: React.FC = () => {
  const { t } = useTranslation('aiAssistant');
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);

  // State
  const [gatewayStatus, setGatewayStatus] = useState<ServiceStatus>({ healthy: false, label: '检测中…', url: GATEWAY_URL });
  const [agentStatus, setAgentStatus] = useState<ServiceStatus>({ healthy: false, label: '检测中…', url: AGENT_URL });
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
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
      await Promise.allSettled([refreshServices(), refreshSkills(), refreshLLM(), refreshDsConfig()]);
    } finally {
      setLoading(false);
    }
  }, []);

  async function refreshServices() {
    // Gateway
    try {
      const resp = await fetch(`${GATEWAY_URL}/health`);
      if (!resp.ok) throw new Error();
      setGatewayStatus({ healthy: true, label: '运行中', url: GATEWAY_URL });
    } catch {
      setGatewayStatus({ healthy: false, label: '离线', url: GATEWAY_URL });
    }
    // Agent
    try {
      const resp = await fetch(`${AGENT_URL}/health`);
      if (!resp.ok) throw new Error();
      setAgentStatus({ healthy: true, label: '运行中', url: AGENT_URL });
    } catch {
      setAgentStatus({ healthy: false, label: '离线', url: AGENT_URL });
    }
  }

  async function refreshSkills() {
    try {
      const data = await listSkills();
      setSkills(data.skills);
    } catch { /* ignore */ }
  }

  async function refreshLLM() {
    try {
      const resp = await fetch(`${AGENT_URL}/api/llm/status`);
      if (!resp.ok) throw new Error();
      const data: OllamaStatus = await resp.json();
      setOllamaStatus(data);
    } catch {
      setOllamaStatus(null);
    }
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
    message.loading({ content: '执行中…', key: 'exec' });
    try {
      const result = await executeSkill(skillId, { query: '测试查询', text: '这是一段测试文本' });
      if (result.success) {
        message.success({ content: `执行完成 (${result.execution_time_ms}ms)`, key: 'exec' });
        Modal.info({ title: '执行结果', width: 600, content: <pre style={{ maxHeight: 400, overflow: 'auto' }}>{JSON.stringify(result.result, null, 2)}</pre> });
      } else {
        message.error({ content: result.error || '执行失败', key: 'exec' });
      }
    } catch {
      message.error({ content: '执行失败', key: 'exec' });
    }
  };

  const handleToggleStatus = async (skill: SkillDetail) => {
    const newStatus = skill.status === 'deployed' ? 'pending' : 'deployed';
    try {
      await toggleSkillStatus(skill.id, newStatus);
      message.success(`技能状态已更新为 ${newStatus === 'deployed' ? '已部署' : '待部署'}`);
      await refreshSkills();
    } catch {
      message.error('状态更新失败');
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

  // ---------------------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------------------
  const skillColumns: ColumnsType<SkillDetail> = [
    { title: '技能名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '分类', dataIndex: 'category', key: 'category',
      render: (cat: string) => {
        const colors: Record<string, string> = { 'data-annotation': 'blue', 'data-structuring': 'purple', 'data-analysis': 'orange', 'data-processing': 'green' };
        return <Tag color={colors[cat] || 'default'}>{cat}</Tag>;
      },
    },
    { title: '版本', dataIndex: 'version', key: 'version', render: (v: string) => <Tag>{v}</Tag> },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => {
        const map: Record<string, { color: string; label: string }> = {
          deployed: { color: 'green', label: '已部署' },
          pending: { color: 'orange', label: '待部署' },
          removed: { color: 'red', label: '已移除' },
        };
        const info = map[s] || { color: 'default', label: s };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: '部署时间', dataIndex: 'deployed_at', key: 'deployed_at',
      render: (v: string) => v ? new Date(v).toLocaleString() : '-',
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: SkillDetail) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleExecuteSkill(record.id)}>测试</Button>
          <Switch
            size="small"
            checked={record.status === 'deployed'}
            onChange={() => handleToggleStatus(record)}
            checkedChildren="启用"
            unCheckedChildren="禁用"
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
                  <RocketOutlined /> AI 应用集成
                </Title>
                <Button icon={<ReloadOutlined />} onClick={refreshAll}>刷新</Button>
              </div>
              <Paragraph>
                管理 OpenClaw AI 助手与 SuperInsight 平台的集成，通过对话界面访问治理后的高质量数据。
              </Paragraph>
            </Space>
          </Card>

          {/* Tabs */}
          <Card>
            <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
              {
                key: 'overview',
                label: <span><DashboardOutlined /> 概览</span>,
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    {/* Statistics */}
                    <Row gutter={16}>
                      <Col span={6}>
                        <Card><Statistic title="活跃技能" value={skills.filter(s => s.status === 'deployed').length} prefix={<ThunderboltOutlined />} valueStyle={{ color: '#1890ff' }} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title="可用技能" value={skills.length} prefix={<ApiOutlined />} valueStyle={{ color: '#3f8600' }} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title="LLM 模型" value={ollamaStatus?.models?.length ?? 0} suffix="个" /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title="LLM 状态" value={ollamaStatus?.healthy ? '在线' : '离线'} valueStyle={{ color: ollamaStatus?.healthy ? '#3f8600' : '#cf1322' }} /></Card>
                      </Col>
                    </Row>

                    {/* Service Status */}
                    <Card title="服务状态">
                      <Descriptions column={2} bordered>
                        <Descriptions.Item label="Gateway">
                          <Badge status={gatewayStatus.healthy ? 'success' : 'error'} text={gatewayStatus.label} />
                        </Descriptions.Item>
                        <Descriptions.Item label="Gateway 地址">
                          <a href={`${gatewayStatus.url}/health`} target="_blank" rel="noopener noreferrer">{gatewayStatus.url}</a>
                        </Descriptions.Item>
                        <Descriptions.Item label="Agent">
                          <Badge status={agentStatus.healthy ? 'success' : 'error'} text={agentStatus.label} />
                        </Descriptions.Item>
                        <Descriptions.Item label="Agent 地址">
                          <a href={`${agentStatus.url}/health`} target="_blank" rel="noopener noreferrer">{agentStatus.url}</a>
                        </Descriptions.Item>
                        <Descriptions.Item label="Ollama LLM">
                          <Badge status={ollamaStatus?.healthy ? 'success' : 'error'} text={ollamaStatus?.healthy ? '运行中' : '离线'} />
                        </Descriptions.Item>
                        <Descriptions.Item label="当前模型">
                          {ollamaStatus?.models?.length ? ollamaStatus.models.join(', ') : '无模型'}
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
                label: <span><ThunderboltOutlined /> 技能管理</span>,
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
                label: <span><SettingOutlined /> 配置</span>,
                children: (
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert message="LLM 配置" description={`当前使用 ${ollamaStatus?.provider || 'ollama'} 提供商，模型: ${ollamaStatus?.model || '未知'}`} type="info" showIcon />
                    <Card title="LLM 配置">
                      <Form layout="vertical">
                        <Form.Item label="LLM 提供商">
                          <Select defaultValue="ollama">
                            <Select.Option value="ollama">Ollama (本地)</Select.Option>
                            <Select.Option value="openai">OpenAI</Select.Option>
                            <Select.Option value="qwen">通义千问</Select.Option>
                          </Select>
                        </Form.Item>
                        <Form.Item label="模型">
                          <Input defaultValue={ollamaStatus?.model || 'qwen2.5:1.5b'} />
                        </Form.Item>
                        <Form.Item label="API 端点">
                          <Input defaultValue="http://ollama:11434" />
                        </Form.Item>
                        <Button type="primary">保存配置</Button>
                      </Form>
                    </Card>
                    <Card title="语言设置">
                      <Form layout="vertical">
                        <Form.Item label="默认语言">
                          <Select defaultValue="zh-CN">
                            <Select.Option value="zh-CN">简体中文</Select.Option>
                            <Select.Option value="en-US">English</Select.Option>
                          </Select>
                        </Form.Item>
                        <Form.Item label="启用多语言支持"><Switch defaultChecked /></Form.Item>
                        <Button type="primary">保存设置</Button>
                      </Form>
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
