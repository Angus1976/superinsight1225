/**
 * AI Annotation Collaboration Component
 *
 * Real-time collaboration interface for AI-assisted annotation:
 * - WebSocket connection for live updates
 * - AI suggestion display with accept/reject
 * - Conflict detection and resolution
 * - Real-time progress tracking
 * - User presence indicators
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Space,
  Button,
  Tag,
  Badge,
  Avatar,
  List,
  Tooltip,
  Alert,
  Progress,
  Drawer,
  Modal,
  Form,
  Input,
  Select,
  Radio,
  Divider,
  Spin,
  Empty,
  message,
} from 'antd';
import {
  RobotOutlined,
  UserOutlined,
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  HistoryOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

// Types
export interface AISuggestion {
  id: string;
  documentId: string;
  text: string;
  annotations: AnnotationItem[];
  confidence: number;
  latencyMs: number;
  timestamp: string;
  status: 'pending' | 'accepted' | 'rejected' | 'modified';
}

export interface AnnotationItem {
  label: string;
  start: number;
  end: number;
  text: string;
  confidence: number;
}

export interface AnnotationConflict {
  id: string;
  documentId: string;
  conflictType: 'overlap' | 'label_mismatch' | 'boundary';
  annotations: AnnotationItem[];
  users: UserInfo[];
  createdAt: string;
  status: 'pending' | 'resolved';
}

export interface UserInfo {
  id: string;
  name: string;
  avatar?: string;
  role: 'annotator' | 'reviewer' | 'admin';
}

export interface CollaborationUser {
  id: string;
  name: string;
  avatar?: string;
  status: 'online' | 'idle' | 'annotating';
  currentDocument?: string;
  lastActivity: string;
}

export interface ProgressMetrics {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  pendingTasks: number;
  completionRate: number;
  avgTimePerTaskMinutes: number;
  activeAnnotators: number;
  activeReviewers: number;
}

interface AnnotationCollaborationProps {
  projectId: string;
  documentId?: string;
  onSuggestionAccept?: (suggestion: AISuggestion) => void;
  onSuggestionReject?: (suggestion: AISuggestion, reason?: string) => void;
  onConflictResolve?: (conflict: AnnotationConflict, resolution: string) => void;
}


const AnnotationCollaboration: React.FC<AnnotationCollaborationProps> = ({
  projectId,
  documentId,
  onSuggestionAccept,
  onSuggestionReject,
  onConflictResolve,
}) => {
  const { t } = useTranslation(['ai_annotation', 'common']);
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [conflicts, setConflicts] = useState<AnnotationConflict[]>([]);
  const [onlineUsers, setOnlineUsers] = useState<CollaborationUser[]>([]);
  const [progress, setProgress] = useState<ProgressMetrics | null>(null);
  const [selectedConflict, setSelectedConflict] = useState<AnnotationConflict | null>(null);
  const [conflictDrawerOpen, setConflictDrawerOpen] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState<AISuggestion | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnecting(true);
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/annotation/ws`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setConnected(true);
        setConnecting(false);
        // Authenticate and join project
        wsRef.current?.send(JSON.stringify({
          type: 'authenticate',
          projectId,
          documentId,
        }));
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onclose = () => {
        setConnected(false);
        setConnecting(false);
        // Attempt reconnection after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnecting(false);
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnecting(false);
    }
  }, [projectId, documentId]);

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'suggestion':
        setSuggestions(prev => [data.payload, ...prev].slice(0, 50));
        break;
      case 'suggestion_batch':
        setSuggestions(prev => [...data.payload, ...prev].slice(0, 50));
        break;
      case 'conflict':
        setConflicts(prev => [data.payload, ...prev]);
        break;
      case 'user_joined':
        setOnlineUsers(prev => [...prev.filter(u => u.id !== data.payload.id), data.payload]);
        break;
      case 'user_left':
        setOnlineUsers(prev => prev.filter(u => u.id !== data.payload.id));
        break;
      case 'progress_update':
        setProgress(data.payload);
        break;
      case 'annotation_update':
        // Handle annotation updates from other users
        break;
      case 'quality_alert':
        message.warning(data.payload.message);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  useEffect(() => {
    connectWebSocket();
    loadInitialData();

    return () => {
      wsRef.current?.close();
    };
  }, [connectWebSocket]);

  const loadInitialData = async () => {
    try {
      // Load progress metrics
      const progressRes = await fetch(`/api/v1/annotation/progress/${projectId}`);
      if (progressRes.ok) {
        const progressData = await progressRes.json();
        setProgress(progressData);
      }

      // Load conflicts
      const conflictsRes = await fetch(`/api/v1/annotation/conflicts/${projectId}`);
      if (conflictsRes.ok) {
        const conflictsData = await conflictsRes.json();
        setConflicts(conflictsData);
      }
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  const handleAcceptSuggestion = async (suggestion: AISuggestion) => {
    try {
      await fetch('/api/v1/annotation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suggestion_id: suggestion.id,
          accepted: true,
        }),
      });

      setSuggestions(prev =>
        prev.map(s => s.id === suggestion.id ? { ...s, status: 'accepted' } : s)
      );
      onSuggestionAccept?.(suggestion);
      message.success(t('ai_annotation:collaboration.suggestion_accepted'));
    } catch (error) {
      message.error(t('ai_annotation:collaboration.accept_failed'));
    }
  };

  const handleRejectSuggestion = async () => {
    if (!selectedSuggestion) return;

    try {
      await fetch('/api/v1/annotation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suggestion_id: selectedSuggestion.id,
          accepted: false,
          reason: rejectReason,
        }),
      });

      setSuggestions(prev =>
        prev.map(s => s.id === selectedSuggestion.id ? { ...s, status: 'rejected' } : s)
      );
      onSuggestionReject?.(selectedSuggestion, rejectReason);
      setRejectModalOpen(false);
      setSelectedSuggestion(null);
      setRejectReason('');
      message.success(t('ai_annotation:collaboration.suggestion_rejected'));
    } catch (error) {
      message.error(t('ai_annotation:collaboration.reject_failed'));
    }
  };

  const handleResolveConflict = async (resolution: string, resolvedAnnotation?: AnnotationItem) => {
    if (!selectedConflict) return;

    try {
      await fetch('/api/v1/annotation/conflicts/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conflict_id: selectedConflict.id,
          resolution,
          resolved_annotation: resolvedAnnotation,
        }),
      });

      setConflicts(prev =>
        prev.map(c => c.id === selectedConflict.id ? { ...c, status: 'resolved' } : c)
      );
      onConflictResolve?.(selectedConflict, resolution);
      setConflictDrawerOpen(false);
      setSelectedConflict(null);
      message.success(t('ai_annotation:collaboration.conflict_resolved'));
    } catch (error) {
      message.error(t('ai_annotation:collaboration.resolve_failed'));
    }
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return '#52c41a';
    if (confidence >= 0.7) return '#1890ff';
    if (confidence >= 0.5) return '#faad14';
    return '#ff4d4f';
  };

  const getUserStatusColor = (status: string): string => {
    switch (status) {
      case 'online': return '#52c41a';
      case 'annotating': return '#1890ff';
      case 'idle': return '#faad14';
      default: return '#999';
    }
  };

  const pendingConflicts = conflicts.filter(c => c.status === 'pending');
  const pendingSuggestions = suggestions.filter(s => s.status === 'pending');

  return (
    <div className="annotation-collaboration">
      {/* Connection Status */}
      <Alert
        message={
          connected
            ? t('ai_annotation:collaboration.connected')
            : connecting
            ? t('ai_annotation:collaboration.connecting')
            : t('ai_annotation:collaboration.disconnected')
        }
        type={connected ? 'success' : connecting ? 'info' : 'warning'}
        showIcon
        icon={connected ? <SyncOutlined spin={false} /> : <SyncOutlined spin={connecting} />}
        style={{ marginBottom: 16 }}
        action={
          !connected && !connecting && (
            <Button size="small" onClick={connectWebSocket}>
              {t('common:actions.reconnect')}
            </Button>
          )
        }
      />

      <Row gutter={16}>
        {/* Left Column - AI Suggestions */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <RobotOutlined />
                {t('ai_annotation:collaboration.ai_suggestions')}
                {pendingSuggestions.length > 0 && (
                  <Badge count={pendingSuggestions.length} />
                )}
              </Space>
            }
            extra={
              <Button
                type="link"
                icon={<HistoryOutlined />}
                onClick={() => setSuggestions([])}
              >
                {t('common:actions.clear')}
              </Button>
            }
          >
            {suggestions.length === 0 ? (
              <Empty
                image={<BulbOutlined style={{ fontSize: 48, color: '#ccc' }} />}
                description={t('ai_annotation:collaboration.no_suggestions')}
              />
            ) : (
              <List
                dataSource={suggestions}
                renderItem={(suggestion) => (
                  <SuggestionItem
                    suggestion={suggestion}
                    onAccept={() => handleAcceptSuggestion(suggestion)}
                    onReject={() => {
                      setSelectedSuggestion(suggestion);
                      setRejectModalOpen(true);
                    }}
                    getConfidenceColor={getConfidenceColor}
                    t={t}
                  />
                )}
              />
            )}
          </Card>

          {/* Conflicts Section */}
          {pendingConflicts.length > 0 && (
            <Card
              title={
                <Space>
                  <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                  {t('ai_annotation:collaboration.conflicts')}
                  <Badge count={pendingConflicts.length} />
                </Space>
              }
              style={{ marginTop: 16 }}
            >
              <List
                dataSource={pendingConflicts}
                renderItem={(conflict) => (
                  <List.Item
                    actions={[
                      <Button
                        key="resolve"
                        type="primary"
                        size="small"
                        onClick={() => {
                          setSelectedConflict(conflict);
                          setConflictDrawerOpen(true);
                        }}
                      >
                        {t('common:actions.resolve')}
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<ExclamationCircleOutlined style={{ fontSize: 24, color: '#faad14' }} />}
                      title={t(`ai_annotation:collaboration.conflict_types.${conflict.conflictType}`)}
                      description={
                        <Space direction="vertical" size="small">
                          <span>{t('ai_annotation:collaboration.document')}: {conflict.documentId}</span>
                          <Space>
                            {conflict.users.map(user => (
                              <Tag key={user.id} icon={<UserOutlined />}>
                                {user.name}
                              </Tag>
                            ))}
                          </Space>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          )}
        </Col>

        {/* Right Column - Users & Progress */}
        <Col xs={24} lg={8}>
          {/* Online Users */}
          <Card
            title={
              <Space>
                <TeamOutlined />
                {t('ai_annotation:collaboration.online_users')}
                <Badge count={onlineUsers.length} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
            size="small"
          >
            {onlineUsers.length === 0 ? (
              <Empty description={t('ai_annotation:collaboration.no_users_online')} />
            ) : (
              <List
                size="small"
                dataSource={onlineUsers}
                renderItem={(user) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Badge dot color={getUserStatusColor(user.status)}>
                          <Avatar size="small" icon={<UserOutlined />} src={user.avatar} />
                        </Badge>
                      }
                      title={user.name}
                      description={
                        user.currentDocument
                          ? t('ai_annotation:collaboration.working_on', { doc: user.currentDocument })
                          : t(`ai_annotation:collaboration.status.${user.status}`)
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>

          {/* Progress Metrics */}
          {progress && (
            <Card
              title={
                <Space>
                  <ThunderboltOutlined />
                  {t('ai_annotation:collaboration.progress')}
                </Space>
              }
              size="small"
              style={{ marginTop: 16 }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <span>{t('ai_annotation:collaboration.completion')}</span>
                  <Progress
                    percent={Math.round(progress.completionRate * 100)}
                    status={progress.completionRate >= 1 ? 'success' : 'active'}
                  />
                </div>
                <Row gutter={8}>
                  <Col span={12}>
                    <Statistic
                      title={t('ai_annotation:collaboration.completed')}
                      value={progress.completedTasks}
                      suffix={`/ ${progress.totalTasks}`}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t('ai_annotation:collaboration.in_progress')}
                      value={progress.inProgressTasks}
                    />
                  </Col>
                </Row>
                <Row gutter={8}>
                  <Col span={12}>
                    <Statistic
                      title={t('ai_annotation:collaboration.annotators')}
                      value={progress.activeAnnotators}
                      prefix={<UserOutlined />}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={t('ai_annotation:collaboration.avg_time')}
                      value={progress.avgTimePerTaskMinutes.toFixed(1)}
                      suffix="min"
                    />
                  </Col>
                </Row>
              </Space>
            </Card>
          )}
        </Col>
      </Row>

      {/* Reject Reason Modal */}
      <Modal
        title={t('ai_annotation:collaboration.reject_suggestion')}
        open={rejectModalOpen}
        onOk={handleRejectSuggestion}
        onCancel={() => {
          setRejectModalOpen(false);
          setSelectedSuggestion(null);
          setRejectReason('');
        }}
        okText={t('common:actions.confirm')}
        cancelText={t('common:actions.cancel')}
      >
        <Form layout="vertical">
          <Form.Item label={t('ai_annotation:collaboration.reject_reason')}>
            <Input.TextArea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder={t('ai_annotation:collaboration.reject_reason_placeholder')}
              rows={3}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Conflict Resolution Drawer */}
      <Drawer
        title={t('ai_annotation:collaboration.resolve_conflict')}
        open={conflictDrawerOpen}
        onClose={() => {
          setConflictDrawerOpen(false);
          setSelectedConflict(null);
        }}
        width={500}
      >
        {selectedConflict && (
          <ConflictResolutionPanel
            conflict={selectedConflict}
            onResolve={handleResolveConflict}
            t={t}
          />
        )}
      </Drawer>
    </div>
  );
};

// Import Statistic from antd
import { Statistic } from 'antd';


// Suggestion Item Component
interface SuggestionItemProps {
  suggestion: AISuggestion;
  onAccept: () => void;
  onReject: () => void;
  getConfidenceColor: (confidence: number) => string;
  t: any;
}

const SuggestionItem: React.FC<SuggestionItemProps> = ({
  suggestion,
  onAccept,
  onReject,
  getConfidenceColor,
  t,
}) => {
  const isProcessed = suggestion.status !== 'pending';

  return (
    <List.Item
      style={{
        opacity: isProcessed ? 0.6 : 1,
        backgroundColor: isProcessed
          ? suggestion.status === 'accepted'
            ? '#f6ffed'
            : '#fff2f0'
          : undefined,
      }}
      actions={
        !isProcessed
          ? [
              <Tooltip key="accept" title={t('common:actions.accept')}>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  size="small"
                  onClick={onAccept}
                >
                  {t('common:actions.accept')}
                </Button>
              </Tooltip>,
              <Tooltip key="reject" title={t('common:actions.reject')}>
                <Button
                  danger
                  icon={<CloseOutlined />}
                  size="small"
                  onClick={onReject}
                >
                  {t('common:actions.reject')}
                </Button>
              </Tooltip>,
            ]
          : [
              <Tag
                key="status"
                color={suggestion.status === 'accepted' ? 'success' : 'error'}
              >
                {t(`ai_annotation:collaboration.status.${suggestion.status}`)}
              </Tag>,
            ]
      }
    >
      <List.Item.Meta
        avatar={
          <Tooltip title={`${t('ai_annotation:collaboration.confidence')}: ${(suggestion.confidence * 100).toFixed(0)}%`}>
            <Badge
              count={`${(suggestion.confidence * 100).toFixed(0)}%`}
              style={{ backgroundColor: getConfidenceColor(suggestion.confidence) }}
            >
              <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#1890ff' }} />
            </Badge>
          </Tooltip>
        }
        title={
          <Space>
            <span>{suggestion.text.substring(0, 50)}...</span>
            <Tag color="blue">{suggestion.latencyMs.toFixed(0)}ms</Tag>
          </Space>
        }
        description={
          <Space wrap>
            {suggestion.annotations.map((ann, idx) => (
              <Tag key={idx} color="purple">
                {ann.label}: "{ann.text}"
              </Tag>
            ))}
          </Space>
        }
      />
    </List.Item>
  );
};

// Conflict Resolution Panel Component
interface ConflictResolutionPanelProps {
  conflict: AnnotationConflict;
  onResolve: (resolution: string, annotation?: AnnotationItem) => void;
  t: any;
}

const ConflictResolutionPanel: React.FC<ConflictResolutionPanelProps> = ({
  conflict,
  onResolve,
  t,
}) => {
  const [selectedResolution, setSelectedResolution] = useState<string>('');
  const [selectedAnnotation, setSelectedAnnotation] = useState<number | null>(null);
  const [customAnnotation, setCustomAnnotation] = useState<AnnotationItem | null>(null);

  const handleResolve = () => {
    if (selectedResolution === 'select' && selectedAnnotation !== null) {
      onResolve('accepted', conflict.annotations[selectedAnnotation]);
    } else if (selectedResolution === 'custom' && customAnnotation) {
      onResolve('modified', customAnnotation);
    } else if (selectedResolution === 'reject') {
      onResolve('rejected');
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Alert
        message={t(`ai_annotation:collaboration.conflict_types.${conflict.conflictType}`)}
        description={t('ai_annotation:collaboration.conflict_description')}
        type="warning"
        showIcon
      />

      <Divider>{t('ai_annotation:collaboration.conflicting_annotations')}</Divider>

      <Radio.Group
        value={selectedResolution === 'select' ? selectedAnnotation : undefined}
        onChange={(e) => {
          setSelectedResolution('select');
          setSelectedAnnotation(e.target.value);
        }}
        style={{ width: '100%' }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {conflict.annotations.map((ann, idx) => (
            <Radio key={idx} value={idx} style={{ width: '100%' }}>
              <Card size="small" style={{ width: '100%' }}>
                <Space direction="vertical">
                  <Tag color="blue">{ann.label}</Tag>
                  <span>"{ann.text}"</span>
                  <span style={{ color: '#999' }}>
                    {t('ai_annotation:collaboration.position')}: {ann.start}-{ann.end}
                  </span>
                  <span style={{ color: '#999' }}>
                    {t('ai_annotation:collaboration.by')}: {conflict.users[idx]?.name || t('common:unknown')}
                  </span>
                </Space>
              </Card>
            </Radio>
          ))}
        </Space>
      </Radio.Group>

      <Divider>{t('ai_annotation:collaboration.or')}</Divider>

      <Space>
        <Button
          type={selectedResolution === 'custom' ? 'primary' : 'default'}
          onClick={() => setSelectedResolution('custom')}
        >
          {t('ai_annotation:collaboration.create_custom')}
        </Button>
        <Button
          danger
          type={selectedResolution === 'reject' ? 'primary' : 'default'}
          onClick={() => setSelectedResolution('reject')}
        >
          {t('ai_annotation:collaboration.reject_all')}
        </Button>
      </Space>

      {selectedResolution === 'custom' && (
        <Card size="small" style={{ marginTop: 16 }}>
          <Form layout="vertical">
            <Form.Item label={t('ai_annotation:collaboration.label')}>
              <Input
                value={customAnnotation?.label || ''}
                onChange={(e) =>
                  setCustomAnnotation((prev) => ({
                    ...prev!,
                    label: e.target.value,
                    text: prev?.text || '',
                    start: prev?.start || 0,
                    end: prev?.end || 0,
                    confidence: 1.0,
                  }))
                }
              />
            </Form.Item>
            <Form.Item label={t('ai_annotation:collaboration.text')}>
              <Input
                value={customAnnotation?.text || ''}
                onChange={(e) =>
                  setCustomAnnotation((prev) => ({
                    ...prev!,
                    text: e.target.value,
                    label: prev?.label || '',
                    start: prev?.start || 0,
                    end: prev?.end || 0,
                    confidence: 1.0,
                  }))
                }
              />
            </Form.Item>
          </Form>
        </Card>
      )}

      <Divider />

      <Button
        type="primary"
        block
        disabled={!selectedResolution}
        onClick={handleResolve}
      >
        {t('ai_annotation:collaboration.apply_resolution')}
      </Button>
    </Space>
  );
};

export default AnnotationCollaboration;
