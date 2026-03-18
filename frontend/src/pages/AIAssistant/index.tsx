import React, { useState, useRef, useEffect } from 'react';
import {
  Card, Input, Button, Space, Typography, Avatar, List, Tag, Spin, Empty,
  Divider, Row, Col, Statistic, Segmented, message, Checkbox,
} from 'antd';
import {
  SendOutlined, StopOutlined, RobotOutlined, UserOutlined,
  ThunderboltOutlined, LineChartOutlined, BulbOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { sendMessageStream, getOpenClawStatus, getAvailableSkills } from '@/services/aiAssistantApi';
import type { ChatMessage as ApiChatMessage, ChatMode, SkillInfo, OutputMode } from '@/types/aiAssistant';
import { useAuthStore } from '@/stores/authStore';
import ConfigPanel from './components/ConfigPanel';
import DataSourceConfigModal from './components/DataSourceConfigModal';
import PermissionTableModal from './components/PermissionTableModal';
import OutputModeModal from './components/OutputModeModal';
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

const AIAssistant: React.FC = () => {
  const { t } = useTranslation('aiAssistant');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Chat mode state
  const [chatMode, setChatMode] = useState<ChatMode>('direct');
  const [gatewayId, setGatewayId] = useState<string | null>(null);
  const [gatewayAvailable, setGatewayAvailable] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]);
  const [isCheckingGateway, setIsCheckingGateway] = useState(false);

  // Data source state
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [outputMode, setOutputMode] = useState<OutputMode>('merge');

  // Auth & modal state
  const user = useAuthStore((s) => s.user);
  const userRole = user?.role || 'viewer';
  const [dsConfigOpen, setDsConfigOpen] = useState(false);
  const [permTableOpen, setPermTableOpen] = useState(false);
  const [outputModeOpen, setOutputModeOpen] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  // Quick actions
  const quickActions = [
    { icon: <LineChartOutlined />, titleKey: 'salesForecast', descKey: 'salesForecastDesc',
      prompt: '请根据最新的数据集，设计一个工作流，可以分析每日的销售预测，并根据实际销售额，实时修正预测能力。' },
    { icon: <ThunderboltOutlined />, titleKey: 'dataQualityCheck', descKey: 'dataQualityCheckDesc',
      prompt: '帮我分析当前数据集的质量，找出可能存在的问题，并给出改进建议。' },
    { icon: <BulbOutlined />, titleKey: 'smartAnnotation', descKey: 'smartAnnotationDesc',
      prompt: '请帮我分析未标注的数据，并提供智能标注建议。' },
    { icon: <ClockCircleOutlined />, titleKey: 'taskTracking', descKey: 'taskTrackingDesc',
      prompt: '帮我分析当前所有任务的进度，找出可能延期的任务，并给出优化建议。' },
  ];

  const handleModeChange = async (value: string | number) => {
    const newMode = value as ChatMode;
    if (newMode === 'openclaw') {
      setIsCheckingGateway(true);
      try {
        const [status, availableSkills] = await Promise.all([
          getOpenClawStatus(),
          getAvailableSkills(),
        ]);
        if (!status.available) {
          message.warning(`${t('openClawUnavailable')}: ${status.error || ''}`);
          setIsCheckingGateway(false);
          return;
        }
        setChatMode('openclaw');
        setGatewayId(status.gateway_id);
        setGatewayAvailable(true);

        // Filter skills by role permissions
        const allowedSet = new Set(availableSkills.skill_ids);
        const filtered = status.skills.filter((s) => allowedSet.has(s.id));
        setSkills(filtered);

        message.success(t('switchedToOpenClaw'));
      } catch {
        message.error(t('cannotConnectOpenClaw'));
      } finally {
        setIsCheckingGateway(false);
      }
      return;
    }
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
      data_source_ids: selectedSourceIds.length > 0 ? selectedSourceIds : undefined,
      output_mode: selectedSourceIds.length > 0 ? outputMode : undefined,
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
        if (errorMsg.includes('503') || errorMsg.includes('不可用')) {
          message.error(t('openClawUnavailable'));
        } else {
          message.error(errorMsg || 'AI service unavailable');
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleOutputModeConfirm = (sourceIds: string[], mode: OutputMode) => {
    setSelectedSourceIds(sourceIds);
    setOutputMode(mode);
  };

  return (
    <div className="ai-assistant-container">
      <Row gutter={16}>
        {/* Left: Chat area */}
        <Col span={16}>
          <Card className="chat-card">
            <div className="chat-header">
              <Space>
                <Avatar size={40} icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <div>
                  <Title level={4} style={{ margin: 0 }}>{t('title')}</Title>
                  <Text type="secondary">
                    {chatMode === 'openclaw' ? t('modeOpenClaw') : t('modeDirect')}
                  </Text>
                </div>
              </Space>
              <Space>
                <Segmented
                  value={chatMode}
                  options={[
                    { label: t('modeDirect'), value: 'direct' },
                    { label: 'OpenClaw', value: 'openclaw' },
                  ]}
                  onChange={handleModeChange}
                  disabled={isCheckingGateway}
                />
                {isCheckingGateway && <Spin size="small" />}
                <Tag color={chatMode === 'openclaw' && gatewayAvailable ? 'success' : 'default'}>
                  {chatMode === 'openclaw' ? (gatewayAvailable ? t('gatewayOnline') : t('gatewayOffline')) : t('online')}
                </Tag>
              </Space>
            </div>

            <Divider />

            {/* Messages */}
            <div className="messages-container">
              {messages.length === 0 ? (
                <Empty
                  image={<RobotOutlined style={{ fontSize: 64, color: '#1890ff' }} />}
                  description={
                    <Space direction="vertical" size="large">
                      <Text>{t('greeting')}</Text>
                      <Space direction="vertical" align="start">
                        <Text>{t('capability1')}</Text>
                        <Text>{t('capability2')}</Text>
                        <Text>{t('capability3')}</Text>
                        <Text>{t('capability4')}</Text>
                      </Space>
                      <Text type="secondary">{t('selectQuickAction')}</Text>
                    </Space>
                  }
                />
              ) : (
                <List
                  dataSource={messages}
                  renderItem={(msg) => (
                    <div className={`message-item ${msg.role}`}>
                      <Avatar
                        icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                        style={{
                          backgroundColor: msg.role === 'user' ? '#52c41a' : '#1890ff',
                          flexShrink: 0,
                        }}
                      />
                      <div className="message-content">
                        <div className="message-header">
                          <Text strong>{msg.role === 'user' ? t('you') : t('assistant')}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {msg.timestamp.toLocaleTimeString()}
                          </Text>
                        </div>
                        <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                          {msg.content}
                        </Paragraph>
                      </div>
                    </div>
                  )}
                />
              )}
              {isLoading && messages.length > 0 && messages[messages.length - 1].content === '' && (
                <div className="message-item assistant">
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff', flexShrink: 0 }} />
                  <Spin tip={t('thinking')} />
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="input-area">
              <TextArea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={t('inputPlaceholder')}
                autoSize={{ minRows: 2, maxRows: 6 }}
                disabled={isLoading}
              />
              {isLoading ? (
                <Button type="default" danger icon={<StopOutlined />} onClick={handleStopGeneration} style={{ marginTop: 8 }}>
                  {t('stop')}
                </Button>
              ) : (
                <Button type="primary" icon={<SendOutlined />} onClick={handleSendMessage} disabled={!inputValue.trim()} style={{ marginTop: 8 }}>
                  {t('send')}
                </Button>
              )}
            </div>

            {/* Quick actions */}
            <div className="quick-actions-inline">
              <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>{t('quickActions')}</Text>
              <Row gutter={[8, 8]}>
                {quickActions.map((action, index) => (
                  <Col key={index} xs={12} sm={12} md={6}>
                    <div className="quick-action-compact" onClick={() => setInputValue(action.prompt)}>
                      <Space size={6}>
                        <span className="quick-action-icon">{action.icon}</span>
                        <Text style={{ fontSize: 13 }}>{t(action.titleKey)}</Text>
                      </Space>
                    </div>
                  </Col>
                ))}
              </Row>
            </div>
          </Card>
        </Col>

        {/* Right sidebar */}
        <Col span={8}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Skill panel (OpenClaw mode) */}
            {chatMode === 'openclaw' && (
              <Card title={t('skillPanel')} size="small">
                {skills.length === 0 ? (
                  <Text type="secondary">{t('noSkills')}</Text>
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

            {/* Stats */}
            <Card title={t('todayStats')}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title={t('chatCount')} value={Math.floor(messages.length / 2)} suffix={t('chatUnit')} />
                </Col>
                <Col span={12}>
                  <Statistic title={t('workflowCreated')} value={0} suffix={t('workflowUnit')} />
                </Col>
              </Row>
            </Card>

            {/* Tips */}
            <Card title={t('usageTips')} size="small">
              <Space direction="vertical" size="small">
                <Text>• {t('tip1')}</Text>
                <Text>• {t('tip2')}</Text>
                <Text>• {t('tip3')}</Text>
                <Text>• {t('tip4')}</Text>
              </Space>
            </Card>

            {/* Config Panel */}
            <ConfigPanel
              userRole={userRole}
              onOpenDataSourceConfig={() => setDsConfigOpen(true)}
              onOpenPermissionTable={() => setPermTableOpen(true)}
              onOpenOutputMode={() => setOutputModeOpen(true)}
            />
          </Space>
        </Col>
      </Row>

      {/* Config Modals */}
      <DataSourceConfigModal open={dsConfigOpen} onClose={() => setDsConfigOpen(false)} />
      <PermissionTableModal open={permTableOpen} onClose={() => setPermTableOpen(false)} />
      <OutputModeModal
        open={outputModeOpen}
        onClose={() => setOutputModeOpen(false)}
        onConfirm={handleOutputModeConfirm}
        initialSourceIds={selectedSourceIds}
        initialMode={outputMode}
      />
    </div>
  );
};

export default AIAssistant;
