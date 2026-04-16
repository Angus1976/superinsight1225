import React, {
  useState, useRef, useEffect, useMemo, useCallback,
} from 'react';
import {
  Card, Input, Button, Space, Typography, Avatar, List, Tag, Empty,
  Divider, Row, Col, message,
} from 'antd';
import {
  SendOutlined, StopOutlined, RobotOutlined, UserOutlined,
  ThunderboltOutlined, LineChartOutlined, BulbOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import {
  sendMessageStream,
  getWorkflows,
  getOpenClawStatus,
  getServiceStatus,
  type ServiceStatusResponse,
} from '@/services/aiAssistantApi';
import type {
  ChatMessage as ApiChatMessage,
  WorkflowItem,
  OpenClawStatus,
} from '@/types/aiAssistant';
import { useAuthStore } from '@/stores/authStore';
import WorkflowSelector from './components/WorkflowSelector';
import StatsPanel from './components/StatsPanel';
import ProcessingSteps from './components/ProcessingSteps';
import type { StatusStep } from './components/ProcessingSteps';
import './styles.css';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

/** 当前工作流所需技能是否均已在 OpenClaw 侧部署 */
function workflowSkillsDeployed(
  wf: WorkflowItem | null,
  oc: OpenClawStatus | null,
): boolean {
  if (!wf?.skill_ids?.length) return true;
  if (!oc?.skills?.length) return false;
  const deployed = new Set(
    oc.skills.filter((s) => s.status === 'deployed').map((s) => s.id),
  );
  return wf.skill_ids.every((id) => deployed.has(id));
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  type?: 'text' | 'workflow' | 'analysis';
  outputMode?: 'merge' | 'compare';
}

const AIAssistant: React.FC = () => {
  const { t } = useTranslation('aiAssistant');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Workflow state
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [workflowsLoading, setWorkflowsLoading] = useState(false);

  /** OpenClaw / 基础设施探测：用于页头区分「LLM 直连」与「技能/OpenClaw」状态 */
  const [ocStatus, setOcStatus] = useState<OpenClawStatus | null>(null);
  const [svcStatus, setSvcStatus] = useState<ServiceStatusResponse | null>(null);

  // Auth state
  const user = useAuthStore((s) => s.user);
  const userRole = user?.role || 'viewer';

  // Processing steps for progress indicator
  const [statusSteps, setStatusSteps] = useState<StatusStep[]>([]);

  // Stats refresh counter — increments after each completed message
  const [statsRefreshKey, setStatsRefreshKey] = useState(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  const refreshConnectionStatus = useCallback(async () => {
    try {
      const [oc, svc] = await Promise.allSettled([
        getOpenClawStatus(),
        getServiceStatus(),
      ]);
      if (oc.status === 'fulfilled') setOcStatus(oc.value);
      else setOcStatus(null);
      if (svc.status === 'fulfilled') setSvcStatus(svc.value);
      else setSvcStatus(null);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refreshConnectionStatus();
    const timer = window.setInterval(refreshConnectionStatus, 30_000);
    return () => window.clearInterval(timer);
  }, [refreshConnectionStatus]);

  const effectiveWorkflow = useMemo((): WorkflowItem | null => {
    if (!selectedWorkflowId) {
      return workflows.find((w) => w.is_preset && w.name === 'LLM 直连') ?? null;
    }
    return workflows.find((w) => w.id === selectedWorkflowId) ?? null;
  }, [workflows, selectedWorkflowId]);

  const isLlmDirectMode = useMemo(() => {
    const w = effectiveWorkflow;
    if (!w) return true;
    const name = (w.name || '').trim();
    if (name === 'LLM 直连' || name === 'LLM Direct') return true;
    return (w.skill_ids?.length ?? 0) === 0;
  }, [effectiveWorkflow]);

  const openClawChannelOk = useMemo(() => {
    if (!ocStatus || !svcStatus) return null;
    if (!ocStatus.available) return false;
    if (ocStatus.gateway_reachable === false) return false;
    if (!svcStatus.openclaw?.healthy) return false;
    if (!workflowSkillsDeployed(effectiveWorkflow, ocStatus)) return false;
    return true;
  }, [ocStatus, svcStatus, effectiveWorkflow]);

  /** OpenClaw 通道（openclaw 应用 / 网关固定）— 与直连通道相互独立 */
  const openClawLlmSubtitle = useMemo(() => {
    const llm = svcStatus?.openclaw?.llm;
    if (!llm?.model) return null;
    const sk = `openclawLlmSource.${llm.source}` as const;
    const srcLabel = t(sk, { defaultValue: llm.source });
    return t('openclawLlmLine', { model: llm.model, source: srcLabel });
  }, [svcStatus, t]);

  /** LLM 直连通道（ai_assistant 应用绑定）— get_llm_switcher 同源 */
  const directLlmSubtitle = useMemo(() => {
    const llm = svcStatus?.llm_direct?.llm;
    if (!llm?.model) return null;
    const sk = `directLlmSource.${llm.source}` as const;
    const srcLabel = t(sk, { defaultValue: llm.source });
    return t('directLlmLine', { model: llm.model, source: srcLabel });
  }, [svcStatus, t]);

  /**
   * 直连「在线」：后端可用，且若解析为 ollama 提供商则要求 Ollama 探活通过。
   * （云端直连不依赖 Ollama 侧车。）
   */
  const llmChannelOk = useMemo(() => {
    if (!svcStatus?.backend?.healthy) return false;
    const prov = (svcStatus.llm_direct?.llm?.provider || '').toLowerCase();
    if (prov === 'ollama') {
      return !!svcStatus.ollama?.healthy;
    }
    return true;
  }, [svcStatus]);

  const statusBadgeLoading = useMemo(() => {
    if (svcStatus === null) return true;
    if (!isLlmDirectMode && ocStatus === null) return true;
    return false;
  }, [svcStatus, ocStatus, isLlmDirectMode]);

  // Load workflows on mount
  useEffect(() => {
    const loadWorkflows = async () => {
      setWorkflowsLoading(true);
      try {
        const data = await getWorkflows();
        setWorkflows(data);
      } catch (err) {
        console.error('Failed to load workflows:', err);
      } finally {
        setWorkflowsLoading(false);
      }
    };
    loadWorkflows();
  }, []);

  // Quick actions
  const quickActions = [
    { icon: <LineChartOutlined />, titleKey: 'salesForecast', descKey: 'salesForecastDesc',
      promptKey: 'salesForecastPrompt' },
    { icon: <ThunderboltOutlined />, titleKey: 'dataQualityCheck', descKey: 'dataQualityCheckDesc',
      promptKey: 'dataQualityCheckPrompt' },
    { icon: <BulbOutlined />, titleKey: 'smartAnnotation', descKey: 'smartAnnotationDesc',
      promptKey: 'smartAnnotationPrompt' },
    { icon: <ClockCircleOutlined />, titleKey: 'taskTracking', descKey: 'taskTrackingDesc',
      promptKey: 'taskTrackingPrompt' },
  ];

  // Filter quick actions by preset workflow visibility
  const visibleQuickActions = quickActions.filter((action) => {
    const presetWorkflow = workflows.find(
      (w) => w.is_preset && w.preset_prompt === t(action.promptKey)
    );
    if (!presetWorkflow) return true; // show if no matching preset found
    return presetWorkflow.visible_roles.includes(userRole) || userRole === 'admin';
  });

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    const assistantMessageId = (Date.now() + 1).toString();
    const selectedWorkflow = selectedWorkflowId
      ? workflows.find(w => w.id === selectedWorkflowId)
      : null;
    const useCompare = selectedWorkflow?.output_modes?.includes('compare') ?? false;

    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      outputMode: useCompare ? 'compare' : 'merge',
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInputValue('');
    setIsLoading(true);

    const apiMessages: ApiChatMessage[] = [
      ...messages.map((m) => ({ role: m.role, content: m.content })),
      { role: 'user' as const, content: inputValue },
    ];

    // When no workflow is selected, fall back to the "LLM 直连" preset workflow
    // so all requests go through the permission chain.
    const effectiveWorkflowId = selectedWorkflowId
      ?? workflows.find(w => w.is_preset && w.name === 'LLM 直连')?.id
      ?? undefined;

    setStatusSteps([]);

    const { abort } = sendMessageStream({
      messages: apiMessages,
      workflow_id: effectiveWorkflowId,
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
      onStatus: (text, progress) => {
        setStatusSteps((prev) => [...prev, { text, progress, ts: Date.now() }]);
      },
      onDone: () => {
        setIsLoading(false);
        setStatusSteps([]);
        abortRef.current = null;
        setStatsRefreshKey((k) => k + 1);
        refreshConnectionStatus();
      },
      onError: (error) => {
        const errorMsg = error.message || '';
        if (errorMsg.includes('503') || errorMsg.includes('不可用')) {
          message.error(t('openClawUnavailable'));
        } else {
          message.error(errorMsg || t('aiServiceUnavailable'));
        }
        console.error('AI stream error:', error);
        setIsLoading(false);
        setStatusSteps([]);
        abortRef.current = null;
      },
    });

    abortRef.current = abort;
  };

  const handleStopGeneration = () => {
    abortRef.current?.();
    abortRef.current = null;
    setIsLoading(false);
    setStatusSteps([]);
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
        {/* Left: Chat area */}
        <Col span={16}>
          <Card className="chat-card">
            <div className="chat-header">
              <Space>
                <Avatar size={40} icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <div>
                  <Title level={4} style={{ margin: 0 }}>{t('title')}</Title>
                  <Text type="secondary">
                    {selectedWorkflowId
                      ? workflows.find(w => w.id === selectedWorkflowId)?.name || ''
                      : t('modeDirect')}
                  </Text>
                </div>
              </Space>
              <Space>
                {selectedWorkflowId && (
                  <Tag color="blue">
                    {workflows.find(w => w.id === selectedWorkflowId)?.name || ''}
                  </Tag>
                )}
                {statusBadgeLoading ? (
                  <Tag color="default">{t('statusChecking')}</Tag>
                ) : isLlmDirectMode ? (
                  <Space direction="vertical" size={0} align="end">
                    <Tag color={llmChannelOk ? 'success' : 'error'}>
                      {t('statusLlm')} · {llmChannelOk ? t('online') : t('offline')}
                    </Tag>
                    {directLlmSubtitle ? (
                      <Text type="secondary" style={{ fontSize: 11, maxWidth: 300, textAlign: 'right' }}>
                        {directLlmSubtitle}
                      </Text>
                    ) : null}
                    {(svcStatus?.llm_direct?.llm?.provider || '').toLowerCase() === 'ollama' ? (
                      <Text type="secondary" style={{ fontSize: 10, maxWidth: 300, textAlign: 'right' }}>
                        {t('ollamaProbeNote')}
                        {typeof svcStatus?.ollama?.healthy === 'boolean'
                          ? ` · Ollama ${svcStatus.ollama.healthy ? t('online') : t('offline')}`
                          : ''}
                      </Text>
                    ) : null}
                  </Space>
                ) : (
                  <Space direction="vertical" size={0} align="end">
                    <Tag color={openClawChannelOk ? 'success' : 'error'}>
                      {t('statusOpenClaw')} · {openClawChannelOk ? t('online') : t('offline')}
                    </Tag>
                    {openClawLlmSubtitle ? (
                      <Text type="secondary" style={{ fontSize: 11, maxWidth: 300, textAlign: 'right' }}>
                        {openClawLlmSubtitle}
                      </Text>
                    ) : null}
                    {directLlmSubtitle ? (
                      <Text type="secondary" style={{ fontSize: 10, maxWidth: 300, textAlign: 'right' }}>
                        {t('directFallbackNote', { line: directLlmSubtitle })}
                      </Text>
                    ) : null}
                  </Space>
                )}
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
                        {msg.outputMode === 'compare' && msg.role === 'assistant' && msg.content.includes('---COMPARE---') ? (
                          <Row gutter={16} className="compare-output">
                            {msg.content.split('---COMPARE---').map((part, idx) => (
                              <Col span={12} key={idx}>
                                <Card size="small" title={t(idx === 0 ? 'compareLeft' : 'compareRight')} className="compare-column">
                                  <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                                    {part.trim()}
                                  </Paragraph>
                                </Card>
                              </Col>
                            ))}
                          </Row>
                        ) : (
                          <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                            {msg.content}
                          </Paragraph>
                        )}
                      </div>
                    </div>
                  )}
                />
              )}
              {isLoading && messages.length > 0 && messages[messages.length - 1].content === '' && (
                <div className="message-item assistant">
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff', flexShrink: 0 }} />
                  <ProcessingSteps steps={statusSteps} visible={isLoading} />
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
                {visibleQuickActions.map((action, index) => (
                  <Col key={index} xs={12} sm={12} md={6}>
                    <div className="quick-action-compact" onClick={() => setInputValue(t(action.promptKey))}>
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
            {/* Workflow Selector */}
            <WorkflowSelector
              workflows={workflows}
              selectedId={selectedWorkflowId}
              onSelect={setSelectedWorkflowId}
              loading={workflowsLoading}
              userRole={userRole}
            />

            {/* Stats */}
            <StatsPanel userRole={userRole} refreshKey={statsRefreshKey} />

            {/* Tips */}
            <Card title={t('usageTips')} size="small">
              <Space direction="vertical" size="small">
                <Text>• {t('tip1')}</Text>
                <Text>• {t('tip2')}</Text>
                <Text>• {t('tip3')}</Text>
              </Space>
            </Card>

          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default AIAssistant;
