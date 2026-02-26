import React, { useState, useEffect, useCallback } from 'react';
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
  PlusOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  DashboardOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';

const { Title, Paragraph, Text } = Typography;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface ServiceStatus {
  healthy: boolean;
  label: string;
  url: string;
}

interface Skill {
  id: string;
  name: string;
  description: string;
  version: string;
  category: string;
  status: 'active' | 'inactive';
  deployed_at: string;
}

interface OllamaStatus {
  healthy: boolean;
  models: string[];
  provider: string;
  model: string;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
const GATEWAY_URL = 'http://localhost:3000';
const AGENT_URL = 'http://localhost:8081';

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const AIIntegration: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [isSkillModalVisible, setIsSkillModalVisible] = useState(false);
  const [skillForm] = Form.useForm();

  // State
  const [gatewayStatus, setGatewayStatus] = useState<ServiceStatus>({ healthy: false, label: '检测中…', url: GATEWAY_URL });
  const [agentStatus, setAgentStatus] = useState<ServiceStatus>({ healthy: false, label: '检测中…', url: AGENT_URL });
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [catalog, setCatalog] = useState<Skill[]>([]);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  const refreshAll = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.allSettled([refreshServices(), refreshSkills(), refreshLLM()]);
    } finally {
      setLoading(false);
    }
  }, []);

  async function refreshServices() {
    // Gateway
    try {
      await fetchJSON(`${GATEWAY_URL}/health`);
      setGatewayStatus({ healthy: true, label: '运行中', url: GATEWAY_URL });
    } catch {
      setGatewayStatus({ healthy: false, label: '离线', url: GATEWAY_URL });
    }
    // Agent
    try {
      await fetchJSON(`${AGENT_URL}/health`);
      setAgentStatus({ healthy: true, label: '运行中', url: AGENT_URL });
    } catch {
      setAgentStatus({ healthy: false, label: '离线', url: AGENT_URL });
    }
  }

  async function refreshSkills() {
    try {
      const data = await fetchJSON<{ skills: Skill[] }>(`${AGENT_URL}/api/skills`);
      setSkills(data.skills || []);
    } catch { /* ignore */ }
    try {
      const data = await fetchJSON<{ catalog: Skill[] }>(`${AGENT_URL}/api/skills/catalog`);
      setCatalog(data.catalog || []);
    } catch { /* ignore */ }
  }

  async function refreshLLM() {
    try {
      const data = await fetchJSON<OllamaStatus>(`${AGENT_URL}/api/llm/status`);
      setOllamaStatus(data);
    } catch {
      setOllamaStatus(null);
    }
  }

  useEffect(() => { refreshAll(); }, [refreshAll]);

  // ---------------------------------------------------------------------------
  // Skill actions
  // ---------------------------------------------------------------------------
  const handleDeploySkill = async (values: { skill_id: string }) => {
    try {
      await fetchJSON(`${AGENT_URL}/api/skills/deploy`, {
        method: 'POST',
        body: JSON.stringify({ skill_id: values.skill_id }),
      });
      message.success('技能部署成功');
      setIsSkillModalVisible(false);
      skillForm.resetFields();
      await refreshSkills();
    } catch {
      message.error('技能部署失败');
    }
  };

  const handleUndeploySkill = async (skillId: string) => {
    try {
      await fetchJSON(`${AGENT_URL}/api/skills/undeploy`, {
        method: 'POST',
        body: JSON.stringify({ skill_id: skillId }),
      });
      message.success('技能已卸载');
      await refreshSkills();
    } catch {
      message.error('卸载失败');
    }
  };

  const handleExecuteSkill = async (skillId: string) => {
    message.loading({ content: '执行中…', key: 'exec' });
    try {
      const result = await fetchJSON<{ success: boolean; result: unknown }>(`${AGENT_URL}/api/skills/execute`, {
        method: 'POST',
        body: JSON.stringify({ skill_name: skillId, parameters: { query: '测试查询', text: '这是一段测试文本' } }),
      });
      message.success({ content: '执行完成', key: 'exec' });
      Modal.info({ title: '执行结果', width: 600, content: <pre style={{ maxHeight: 400, overflow: 'auto' }}>{JSON.stringify(result.result, null, 2)}</pre> });
    } catch {
      message.error({ content: '执行失败', key: 'exec' });
    }
  };

  // ---------------------------------------------------------------------------
  // Table columns
  // ---------------------------------------------------------------------------
  const skillColumns: ColumnsType<Skill> = [
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
      render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s === 'active' ? '活跃' : '未激活'}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: Skill) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleExecuteSkill(record.id)}>测试</Button>
          <Button type="link" size="small" danger onClick={() => handleUndeploySkill(record.id)}>卸载</Button>
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
                        <Card><Statistic title="活跃技能" value={skills.filter(s => s.status === 'active').length} prefix={<ThunderboltOutlined />} valueStyle={{ color: '#1890ff' }} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title="可用技能" value={catalog.length} prefix={<ApiOutlined />} valueStyle={{ color: '#3f8600' }} /></Card>
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
                    <Card title="快速操作">
                      <Space wrap>
                        <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => setIsSkillModalVisible(true)}>部署技能</Button>
                        <Button icon={<ReloadOutlined />} onClick={refreshAll}>刷新状态</Button>
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
                      <Text strong>已部署技能 ({skills.length})</Text>
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsSkillModalVisible(true)}>部署技能</Button>
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
            ]} />
          </Card>
        </Space>
      </Spin>

      {/* Deploy Skill Modal */}
      <Modal title="部署技能" open={isSkillModalVisible} onCancel={() => setIsSkillModalVisible(false)} footer={null} width={600}>
        <Form form={skillForm} layout="vertical" onFinish={handleDeploySkill}>
          <Form.Item label="选择技能" name="skill_id" rules={[{ required: true, message: '请选择技能' }]}>
            <Select placeholder="选择要部署的技能">
              {catalog.map(s => (
                <Select.Option key={s.id} value={s.id}>
                  {s.name} - {s.description}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">部署</Button>
              <Button onClick={() => setIsSkillModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AIIntegration;
