import React, { useState, useRef, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Space,
  Typography,
  Avatar,
  List,
  Tag,
  Spin,
  Empty,
  Divider,
  Row,
  Col,
  Statistic,
  Segmented,
  message,
  Checkbox,
} from 'antd';
import {
  SendOutlined,
  StopOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  BulbOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { sendMessageStream, getOpenClawStatus } from '@/services/aiAssistantApi';
import type { ChatMessage as ApiChatMessage, ChatMode, SkillInfo } from '@/types/aiAssistant';
import './styles.css';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  type?: 'text' | 'workflow' | 'analysis';
}

interface QuickAction {
  icon: React.ReactNode;
  title: string;
  description: string;
  prompt: string;
}

const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const [chatMode, setChatMode] = useState<ChatMode>('direct');
  const [gatewayId, setGatewayId] = useState<string | null>(null);
  const [gatewayAvailable, setGatewayAvailable] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]);
  const [isCheckingGateway, setIsCheckingGateway] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 快捷操作
  const quickActions: QuickAction[] = [
    {
      icon: <LineChartOutlined />,
      title: '销售预测分析',
      description: '基于历史数据预测未来销售趋势',
      prompt: '请根据最新的数据集，设计一个工作流，可以分析每日的销售预测，并根据实际销售额，实时修正预测能力。',
    },
    {
      icon: <ThunderboltOutlined />,
      title: '数据质量检查',
      description: '自动检查数据集的质量问题',
      prompt: '帮我分析当前数据集的质量，找出可能存在的问题，并给出改进建议。',
    },
    {
      icon: <BulbOutlined />,
      title: '智能标注建议',
      description: '基于 AI 提供标注建议',
      prompt: '请帮我分析未标注的数据，并提供智能标注建议。',
    },
    {
      icon: <ClockCircleOutlined />,
      title: '任务进度追踪',
      description: '查看和分析任务完成情况',
      prompt: '帮我分析当前所有任务的进度，找出可能延期的任务，并给出优化建议。',
    },
  ];

  const handleModeChange = async (value: string | number) => {
    const newMode = value as ChatMode;
    console.log('[AIAssistant] Mode change requested:', newMode);
    
    if (newMode === 'openclaw') {
      setIsCheckingGateway(true);
      try {
        console.log('[AIAssistant] Fetching OpenClaw status...');
        const status = await getOpenClawStatus();
        console.log('[AIAssistant] OpenClaw status received:', status);
        
        if (!status.available) {
          console.warn('[AIAssistant] OpenClaw not available:', status.error);
          message.warning(`OpenClaw 网关不可用: ${status.error || '请检查网关状态'}`);
          // Don't change mode - keep it as 'direct'
          setIsCheckingGateway(false);
          return;
        }
        
        console.log('[AIAssistant] Setting OpenClaw mode with gateway:', status.gateway_id);
        setChatMode('openclaw');
        setGatewayId(status.gateway_id);
        setGatewayAvailable(true);
        setSkills(status.skills);
        message.success('已切换到 OpenClaw 模式');
      } catch (error) {
        console.error('[AIAssistant] Failed to get OpenClaw status:', error);
        message.error('无法连接 OpenClaw 服务');
        // Don't change mode - keep it as 'direct'
      } finally {
        setIsCheckingGateway(false);
      }
      return;
    }
    
    console.log('[AIAssistant] Switching to direct mode');
    setChatMode('direct');
    setGatewayId(null);
    setGatewayAvailable(false);
    setSkills([]);
    setSelectedSkillIds([]);
  };

  const handleSkillToggle = (skillId: string) => {
    setSelectedSkillIds((prev) =>
      prev.includes(skillId) ? prev.filter((id) => id !== skillId) : [...prev, skillId]
    );
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInputValue('');
    setIsLoading(true);

    const apiMessages: ApiChatMessage[] = [
      ...messages.map((m) => ({ role: m.role, content: m.content })),
      { role: 'user' as const, content: inputValue },
    ];

    const { abort } = sendMessageStream({
      messages: apiMessages,
      mode: chatMode,
      gateway_id: chatMode === 'openclaw' ? gatewayId ?? undefined : undefined,
      skill_ids: chatMode === 'openclaw' ? selectedSkillIds : undefined,
    }, {
      onChunk: (chunk) => {
        if (!chunk.content) return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId
              ? { ...m, content: m.content + chunk.content }
              : m,
          ),
        );
      },
      onDone: () => {
        setIsLoading(false);
        abortRef.current = null;
      },
      onError: (error) => {
        const errorMsg = error.message || '';

        if (errorMsg.includes('503') || errorMsg.includes('网关') || errorMsg.includes('不可用')) {
          message.error('OpenClaw 网关不可用，建议切换到 LLM 直连模式');
        } else if (errorMsg.includes('504') || errorMsg.includes('超时') || errorMsg.includes('timeout')) {
          message.warning('请求超时，请稍后重试或切换到 LLM 直连模式');
        } else if (errorMsg.includes('404') || errorMsg.includes('not found')) {
          message.warning('网关信息已过期，正在刷新...');
          getOpenClawStatus()
            .then((status) => {
              if (status.available) {
                setGatewayId(status.gateway_id);
                setSkills(status.skills);
              } else {
                setChatMode('direct');
                setGatewayId(null);
                setGatewayAvailable(false);
                setSkills([]);
                setSelectedSkillIds([]);
                message.info('已自动切换到 LLM 直连模式');
              }
            })
            .catch(() => {
              // Silently fail — user already saw the warning
            });
        } else {
          message.error('AI 服务暂时不可用，请稍后重试');
        }

        console.error('AI stream error:', error);
        setIsLoading(false);
        abortRef.current = null;
      },
    });

    abortRef.current = abort;
  };

  const handleStopGeneration = () => {
    abortRef.current?.();
    abortRef.current = null;
    setIsLoading(false);
  };

  const handleQuickAction = (prompt: string) => {
    setInputValue(prompt);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="ai-assistant-container">
      <Row gutter={16}>
        {/* 左侧：对话区域 */}
        <Col span={16}>
          <Card className="chat-card">
            <div className="chat-header">
              <Space>
                <Avatar size={40} icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <div>
                  <Title level={4} style={{ margin: 0 }}>AI 智能助手</Title>
                  <Text type="secondary">
                    {chatMode === 'openclaw' ? 'OpenClaw 技能增强' : 'LLM 直连'}
                  </Text>
                </div>
              </Space>
              <Space>
                <Segmented
                  value={chatMode}
                  options={[
                    { label: 'LLM 直连', value: 'direct' },
                    { label: 'OpenClaw', value: 'openclaw' },
                  ]}
                  onChange={handleModeChange}
                  disabled={isCheckingGateway}
                />
                {isCheckingGateway && <Spin size="small" />}
                <Tag color={chatMode === 'openclaw' && gatewayAvailable ? 'success' : 'default'}>
                  {chatMode === 'openclaw' ? (gatewayAvailable ? '网关在线' : '网关离线') : '在线'}
                </Tag>
              </Space>
            </div>

            <Divider />

            <div className="messages-container">
              {messages.length === 0 ? (
                <Empty
                  image={<RobotOutlined style={{ fontSize: 64, color: '#1890ff' }} />}
                  description={
                    <Space direction="vertical" size="large">
                      <Text>您好！我是 AI 智能助手，可以帮您：</Text>
                      <Space direction="vertical" align="start">
                        <Text>• 📊 分析数据和生成报告</Text>
                        <Text>• 🔄 设计和优化工作流</Text>
                        <Text>• 💡 提供智能建议</Text>
                        <Text>• 📈 预测和趋势分析</Text>
                      </Space>
                      <Text type="secondary">请选择下方的快捷操作或直接输入您的问题</Text>
                    </Space>
                  }
                />
              ) : (
                <List
                  dataSource={messages}
                  renderItem={(msg) => (
                    <div className={`message-item ${msg.role}`}>
                      <Space align="start" size={12}>
                        <Avatar
                          icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                          style={{
                            backgroundColor: msg.role === 'user' ? '#52c41a' : '#1890ff',
                          }}
                        />
                        <div className="message-content">
                          <div className="message-header">
                            <Text strong>{msg.role === 'user' ? '您' : 'AI 助手'}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {msg.timestamp.toLocaleTimeString()}
                            </Text>
                          </div>
                          <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                            {msg.content}
                          </Paragraph>
                          {msg.type === 'workflow' && (
                            <Space style={{ marginTop: 12 }}>
                              <Button type="primary" size="small">
                                创建工作流
                              </Button>
                              <Button size="small">查看详情</Button>
                            </Space>
                          )}
                        </div>
                      </Space>
                    </div>
                  )}
                />
              )}
              {isLoading && messages.length > 0 && messages[messages.length - 1].content === '' && (
                <div className="message-item assistant">
                  <Space align="start" size={12}>
                    <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                    <Spin tip="AI 正在思考..." />
                  </Space>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <TextArea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题... (Shift+Enter 换行，Enter 发送)"
                autoSize={{ minRows: 2, maxRows: 6 }}
                disabled={isLoading}
              />
              {isLoading ? (
                <Button
                  type="default"
                  danger
                  icon={<StopOutlined />}
                  onClick={handleStopGeneration}
                  style={{ marginTop: 8 }}
                >
                  停止
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim()}
                  style={{ marginTop: 8 }}
                >
                  发送
                </Button>
              )}
            </div>
          </Card>
        </Col>

        {/* 右侧：快捷操作和统计 */}
        <Col span={8}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* 技能面板 */}
            {chatMode === 'openclaw' && (
              <Card title="🛠 技能面板" size="small">
                {skills.length === 0 ? (
                  <Text type="secondary">暂无可用技能</Text>
                ) : (
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {skills.map((skill) => (
                      <Card key={skill.id} size="small" style={{ marginBottom: 4 }}>
                        <Checkbox
                          checked={selectedSkillIds.includes(skill.id)}
                          onChange={() => handleSkillToggle(skill.id)}
                        >
                          <Text strong>{skill.name}</Text>
                          <Tag color="blue" style={{ marginLeft: 8 }}>{skill.version}</Tag>
                          <Tag color={skill.status === 'deployed' ? 'green' : 'default'}>{skill.status}</Tag>
                        </Checkbox>
                        {skill.description && (
                          <div style={{ marginLeft: 24, marginTop: 4 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>{skill.description}</Text>
                          </div>
                        )}
                      </Card>
                    ))}
                  </Space>
                )}
              </Card>
            )}

            {/* 统计卡片 */}
            <Card title="今日统计">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="对话次数" value={messages.length / 2} suffix="次" />
                </Col>
                <Col span={12}>
                  <Statistic title="工作流创建" value={0} suffix="个" />
                </Col>
              </Row>
            </Card>

            {/* 快捷操作 */}
            <Card title="快捷操作">
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {quickActions.map((action, index) => (
                  <Card
                    key={index}
                    size="small"
                    hoverable
                    onClick={() => handleQuickAction(action.prompt)}
                    className="quick-action-card"
                  >
                    <Space>
                      <Avatar icon={action.icon} style={{ backgroundColor: '#1890ff' }} />
                      <div>
                        <Text strong>{action.title}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {action.description}
                        </Text>
                      </div>
                    </Space>
                  </Card>
                ))}
              </Space>
            </Card>

            {/* 使用提示 */}
            <Card title="💡 使用提示" size="small">
              <Space direction="vertical" size="small">
                <Text>• 使用自然语言描述您的需求</Text>
                <Text>• 可以要求 AI 设计工作流</Text>
                <Text>• 支持数据分析和预测</Text>
                <Text>• 可以实时修正和优化</Text>
              </Space>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default AIAssistant;
