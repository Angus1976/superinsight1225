import React, { useState } from 'react';
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
  Badge
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
  DashboardOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

interface Gateway {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'inactive' | 'deploying';
  tenant_id: string;
  api_key: string;
  created_at: string;
  last_active_at: string;
}

interface Skill {
  id: string;
  name: string;
  gateway_id: string;
  status: 'active' | 'inactive';
  version: string;
  deployed_at: string;
}

const AIIntegration: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [isGatewayModalVisible, setIsGatewayModalVisible] = useState(false);
  const [isSkillModalVisible, setIsSkillModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [skillForm] = Form.useForm();

  // Mock data
  const [gateways, setGateways] = useState<Gateway[]>([
    {
      id: '1',
      name: 'OpenClaw Gateway 1',
      type: 'openclaw',
      status: 'active',
      tenant_id: 'default-tenant',
      api_key: 'dev-test-api-key-12345',
      created_at: '2024-01-15T10:00:00Z',
      last_active_at: '2024-01-15T15:30:00Z'
    }
  ]);

  const [skills, setSkills] = useState<Skill[]>([
    {
      id: '1',
      name: 'SuperInsight Data Query',
      gateway_id: '1',
      status: 'active',
      version: '1.0.0',
      deployed_at: '2024-01-15T10:30:00Z'
    }
  ]);

  const handleRegisterGateway = async () => {
    try {
      // TODO: Call API to register gateway
      message.success('网关注册成功');
      setIsGatewayModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('网关注册失败');
    }
  };

  const handleDeploySkill = async () => {
    try {
      // TODO: Call API to deploy skill
      message.success('技能部署成功');
      setIsSkillModalVisible(false);
      skillForm.resetFields();
    } catch (error) {
      message.error('技能部署失败');
    }
  };

  const gatewayColumns: ColumnsType<Gateway> = [
    {
      title: '网关名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => <Tag color="blue">{type.toUpperCase()}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const config: Record<string, { color: 'success' | 'processing' | 'error' | 'default' | 'warning', icon: React.ReactNode, text: string }> = {
          active: { color: 'success', icon: <CheckCircleOutlined />, text: '运行中' },
          inactive: { color: 'default', icon: <CloseCircleOutlined />, text: '已停止' },
          deploying: { color: 'processing', icon: <SyncOutlined spin />, text: '部署中' }
        };
        const { color, icon, text } = config[status as keyof typeof config];
        return <Badge status={color} text={<Space>{icon}{text}</Space>} />;
      }
    },
    {
      title: '租户ID',
      dataIndex: 'tenant_id',
      key: 'tenant_id',
    },
    {
      title: '最后活跃',
      dataIndex: 'last_active_at',
      key: 'last_active_at',
      render: (date) => new Date(date).toLocaleString('zh-CN')
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small">配置</Button>
          <Button type="link" size="small">健康检查</Button>
          <Button type="link" size="small" danger>停用</Button>
        </Space>
      ),
    },
  ];

  const skillColumns: ColumnsType<Skill> = [
    {
      title: '技能名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version) => <Tag>{version}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status === 'active' ? '活跃' : '未激活'}
        </Tag>
      )
    },
    {
      title: '部署时间',
      dataIndex: 'deployed_at',
      key: 'deployed_at',
      render: (date) => new Date(date).toLocaleString('zh-CN')
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space>
          <Button type="link" size="small">热重载</Button>
          <Button type="link" size="small">查看日志</Button>
          <Button type="link" size="small" danger>卸载</Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <Card>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Title level={2}>
              <RocketOutlined /> AI 应用集成
            </Title>
            <Paragraph>
              管理 OpenClaw 等 AI 助手与 SuperInsight 平台的集成，
              通过对话界面访问治理后的高质量数据。
            </Paragraph>
          </Space>
        </Card>

        {/* Tabs */}
        <Card>
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            {/* Overview Tab */}
            <TabPane 
              tab={<span><DashboardOutlined />概览</span>} 
              key="overview"
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                {/* Statistics */}
                <Row gutter={16}>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="活跃网关" 
                        value={gateways.filter(g => g.status === 'active').length}
                        prefix={<ApiOutlined />}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="部署技能" 
                        value={skills.filter(s => s.status === 'active').length}
                        prefix={<ThunderboltOutlined />}
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="今日请求" 
                        value={1234}
                        suffix="次"
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic 
                        title="平均响应时间" 
                        value={156}
                        suffix="ms"
                      />
                    </Card>
                  </Col>
                </Row>

                {/* Service Status */}
                <Card title="OpenClaw 服务状态">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Descriptions column={2} bordered>
                      <Descriptions.Item label="Gateway 状态">
                        <Badge status="success" text="运行中" />
                      </Descriptions.Item>
                      <Descriptions.Item label="Gateway 地址">
                        <a href="http://localhost:3000/health" target="_blank" rel="noopener noreferrer">
                          http://localhost:3000
                        </a>
                      </Descriptions.Item>
                      <Descriptions.Item label="Agent 状态">
                        <Badge status="success" text="运行中" />
                      </Descriptions.Item>
                      <Descriptions.Item label="Agent 地址">
                        <a href="http://localhost:8081/health" target="_blank" rel="noopener noreferrer">
                          http://localhost:8081
                        </a>
                      </Descriptions.Item>
                    </Descriptions>
                  </Space>
                </Card>

                {/* Quick Actions */}
                <Card title="快速操作">
                  <Space wrap>
                    <Button 
                      type="primary" 
                      icon={<PlusOutlined />}
                      onClick={() => setIsGatewayModalVisible(true)}
                    >
                      注册新网关
                    </Button>
                    <Button 
                      icon={<ThunderboltOutlined />}
                      onClick={() => setIsSkillModalVisible(true)}
                    >
                      部署技能
                    </Button>
                    <Button icon={<SettingOutlined />}>
                      <a href="/admin/config/llm">配置 LLM</a>
                    </Button>
                    <Button icon={<DashboardOutlined />}>
                      查看监控
                    </Button>
                  </Space>
                </Card>
              </Space>
            </TabPane>

            {/* Gateways Tab */}
            <TabPane 
              tab={<span><ApiOutlined />网关管理</span>} 
              key="gateways"
            >
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text strong>已注册网关列表</Text>
                  <Button 
                    type="primary" 
                    icon={<PlusOutlined />}
                    onClick={() => setIsGatewayModalVisible(true)}
                  >
                    注册网关
                  </Button>
                </div>
                <Table 
                  columns={gatewayColumns} 
                  dataSource={gateways}
                  rowKey="id"
                />
              </Space>
            </TabPane>

            {/* Skills Tab */}
            <TabPane 
              tab={<span><ThunderboltOutlined />技能管理</span>} 
              key="skills"
            >
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text strong>已部署技能列表</Text>
                  <Button 
                    type="primary" 
                    icon={<PlusOutlined />}
                    onClick={() => setIsSkillModalVisible(true)}
                  >
                    部署技能
                  </Button>
                </div>
                <Table 
                  columns={skillColumns} 
                  dataSource={skills}
                  rowKey="id"
                />
              </Space>
            </TabPane>

            {/* Configuration Tab */}
            <TabPane 
              tab={<span><SettingOutlined />配置</span>} 
              key="config"
            >
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Alert
                  message="配置说明"
                  description="在这里配置 OpenClaw 的全局设置，包括 LLM 提供商、语言偏好、速率限制等。"
                  type="info"
                  showIcon
                />

                <Card title="LLM 配置">
                  <Form layout="vertical">
                    <Form.Item label="LLM 提供商">
                      <Select defaultValue="ollama">
                        <Select.Option value="ollama">Ollama (本地)</Select.Option>
                        <Select.Option value="openai">OpenAI</Select.Option>
                        <Select.Option value="qwen">通义千问</Select.Option>
                        <Select.Option value="zhipu">智谱 AI</Select.Option>
                      </Select>
                    </Form.Item>
                    <Form.Item label="模型">
                      <Input defaultValue="llama2" />
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
                    <Form.Item label="启用多语言支持">
                      <Switch defaultChecked />
                    </Form.Item>
                    <Button type="primary">保存设置</Button>
                  </Form>
                </Card>

                <Card title="速率限制">
                  <Form layout="vertical">
                    <Form.Item label="每分钟请求数">
                      <Input type="number" defaultValue="60" />
                    </Form.Item>
                    <Form.Item label="每日配额">
                      <Input type="number" defaultValue="10000" />
                    </Form.Item>
                    <Button type="primary">保存限制</Button>
                  </Form>
                </Card>
              </Space>
            </TabPane>
          </Tabs>
        </Card>
      </Space>

      {/* Register Gateway Modal */}
      <Modal
        title="注册新网关"
        open={isGatewayModalVisible}
        onCancel={() => setIsGatewayModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleRegisterGateway}
        >
          <Form.Item
            label="网关名称"
            name="name"
            rules={[{ required: true, message: '请输入网关名称' }]}
          >
            <Input placeholder="例如: OpenClaw Gateway 1" />
          </Form.Item>

          <Form.Item
            label="网关类型"
            name="type"
            rules={[{ required: true, message: '请选择网关类型' }]}
          >
            <Select>
              <Select.Option value="openclaw">OpenClaw</Select.Option>
              <Select.Option value="langchain">LangChain</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="租户ID"
            name="tenant_id"
            rules={[{ required: true, message: '请输入租户ID' }]}
          >
            <Input placeholder="default-tenant" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
          >
            <Input.TextArea rows={3} placeholder="网关描述信息" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                注册
              </Button>
              <Button onClick={() => setIsGatewayModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Deploy Skill Modal */}
      <Modal
        title="部署技能"
        open={isSkillModalVisible}
        onCancel={() => setIsSkillModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={skillForm}
          layout="vertical"
          onFinish={handleDeploySkill}
        >
          <Form.Item
            label="技能名称"
            name="name"
            rules={[{ required: true, message: '请输入技能名称' }]}
          >
            <Input placeholder="例如: SuperInsight Data Query" />
          </Form.Item>

          <Form.Item
            label="目标网关"
            name="gateway_id"
            rules={[{ required: true, message: '请选择目标网关' }]}
          >
            <Select>
              {gateways.map(g => (
                <Select.Option key={g.id} value={g.id}>{g.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="技能版本"
            name="version"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="1.0.0" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
          >
            <Input.TextArea rows={3} placeholder="技能描述信息" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                部署
              </Button>
              <Button onClick={() => setIsSkillModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AIIntegration;
