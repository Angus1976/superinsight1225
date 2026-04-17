/**
 * AI Assistance Panel Component
 *
 * Provides real-time AI suggestions and assistance during annotation:
 * - Display AI-generated label suggestions with confidence scores
 * - Accept/reject suggestions with feedback
 * - Show similar annotation examples
 * - Real-time quality alerts
 * - Pattern-based recommendations
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Space,
  Button,
  Tag,
  Progress,
  Alert,
  Collapse,
  Tooltip,
  Badge,
  Divider,
  Empty,
  Spin,
  message,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  BulbOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  RobotOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

import SuggestionCard from './SuggestionCard';
import { useWebSocket } from '@/hooks/useWebSocket';
import { fetchJsonBody, fetchJsonResponseToSnake, apiResponseToSnake } from '@/utils/jsonCase';

interface AISuggestion {
  suggestion_id: string;
  label: string;
  confidence: number;
  reasoning?: string;
  similar_examples: number;
  engine_type: 'pre-annotation' | 'mid-coverage' | 'post-validation';
  metadata?: {
    patterns?: string[];
    context?: string;
  };
}

interface QualityAlert {
  alert_id: string;
  type: 'warning' | 'error' | 'info';
  message: string;
  metric?: string;
  threshold?: number;
  current_value?: number;
  timestamp: string;
}

interface AIAssistancePanelProps {
  taskId: number;
  projectId: number;
  onSuggestionAccept: (suggestion: AISuggestion) => void;
  onSuggestionReject: (suggestion: AISuggestion, reason?: string) => void;
}

const AIAssistancePanel: React.FC<AIAssistancePanelProps> = ({
  taskId,
  projectId,
  onSuggestionAccept,
  onSuggestionReject,
}) => {
  const { t } = useTranslation(['annotation', 'common', 'ai_annotation']);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [qualityAlerts, setQualityAlerts] = useState<QualityAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);

  // WebSocket connection for real-time updates
  const ws = useWebSocket(`/api/v1/annotation/ws?task_id=${taskId}&project_id=${projectId}`);

  useEffect(() => {
    if (!ws) return;

    ws.on('connect', () => {
      setWsConnected(true);
      message.success(t('annotation:messages.ai_connected'));
    });

    ws.on('disconnect', () => {
      setWsConnected(false);
      message.warning(t('annotation:messages.ai_disconnected'));
    });

    ws.on('suggestion', (raw: unknown) => {
      const data = apiResponseToSnake<{ suggestions?: AISuggestion[] }>(raw);
      const list = data.suggestions ?? [];
      setSuggestions(list);
      if (list.length > 0) {
        message.info(
          t('annotation:messages.ai_suggestions_received', {
            count: list.length,
          })
        );
      }
    });

    ws.on('quality_alert', (raw: unknown) => {
      const data = apiResponseToSnake<QualityAlert>(raw);
      setQualityAlerts((prev) => [data, ...prev].slice(0, 5)); // Keep last 5 alerts

      if (data.type === 'error') {
        message.error(data.message);
      } else if (data.type === 'warning') {
        message.warning(data.message);
      } else {
        message.info(data.message);
      }
    });

    ws.on('suggestion_updated', (raw: unknown) => {
      const data = apiResponseToSnake<{ suggestion_id?: string; suggestionId?: string; updates?: Partial<AISuggestion> }>(
        raw
      );
      const sid = data.suggestion_id ?? data.suggestionId;
      const updates = data.updates ?? {};
      if (!sid) return;
      setSuggestions((prev) =>
        prev.map((s) => (s.suggestion_id === sid ? { ...s, ...updates } : s))
      );
    });

    return () => {
      ws.off('connect');
      ws.off('disconnect');
      ws.off('suggestion');
      ws.off('quality_alert');
      ws.off('suggestion_updated');
    };
  }, [ws, t]);

  const handleRequestSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/annotation/suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: fetchJsonBody({
          task_id: taskId,
          project_id: projectId,
        }),
      });

      if (!response.ok) throw new Error('Failed to fetch suggestions');

      const data = await fetchJsonResponseToSnake<{ suggestions?: AISuggestion[] }>(response);
      setSuggestions(data.suggestions || []);
      message.success(
        t('annotation:messages.ai_suggestions_loaded', {
          count: data.suggestions?.length || 0,
        })
      );
    } catch (error) {
      message.error(t('annotation:errors.ai_suggestions_failed'));
      console.error('Failed to fetch suggestions:', error);
    } finally {
      setLoading(false);
    }
  }, [taskId, projectId, t]);

  const handleAcceptSuggestion = async (suggestion: AISuggestion) => {
    try {
      // Submit feedback
      await fetch('/api/v1/annotation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: fetchJsonBody({
          suggestion_id: suggestion.suggestion_id,
          accepted: true,
          task_id: taskId,
        }),
      });

      // Remove from suggestions
      setSuggestions((prev) =>
        prev.filter((s) => s.suggestion_id !== suggestion.suggestion_id)
      );

      // Callback to parent
      onSuggestionAccept(suggestion);

      message.success(t('annotation:messages.suggestion_accepted'));
    } catch (error) {
      message.error(t('annotation:errors.suggestion_feedback_failed'));
      console.error('Failed to accept suggestion:', error);
    }
  };

  const handleRejectSuggestion = async (suggestion: AISuggestion, reason?: string) => {
    try {
      // Submit feedback
      await fetch('/api/v1/annotation/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: fetchJsonBody({
          suggestion_id: suggestion.suggestion_id,
          accepted: false,
          reason,
          task_id: taskId,
        }),
      });

      // Remove from suggestions
      setSuggestions((prev) =>
        prev.filter((s) => s.suggestion_id !== suggestion.suggestion_id)
      );

      // Callback to parent
      onSuggestionReject(suggestion, reason);

      message.success(t('annotation:messages.suggestion_rejected'));
    } catch (error) {
      message.error(t('annotation:errors.suggestion_feedback_failed'));
      console.error('Failed to reject suggestion:', error);
    }
  };

  const getAlertIcon = (type: QualityAlert['type']) => {
    switch (type) {
      case 'error':
        return <CloseOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
    }
  };

  const getAlertType = (type: QualityAlert['type']): 'error' | 'warning' | 'info' => {
    return type;
  };

  return (
    <div className="ai-assistance-panel">
      <Card
        title={
          <Space>
            <RobotOutlined />
            {t('annotation:titles.ai_assistance')}
            <Badge
              status={wsConnected ? 'success' : 'default'}
              text={wsConnected ? t('common:status.connected') : t('common:status.disconnected')}
            />
          </Space>
        }
        extra={
          <Button
            icon={<SyncOutlined spin={loading} />}
            onClick={handleRequestSuggestions}
            loading={loading}
            size="small"
          >
            {t('annotation:actions.refresh_suggestions')}
          </Button>
        }
        size="small"
      >
        {/* Quality Alerts */}
        {qualityAlerts.length > 0 && (
          <>
            <Collapse
              items={[
                {
                  key: 'alerts',
                  label: (
                    <Space>
                      <WarningOutlined />
                      {t('annotation:sections.quality_alerts')} ({qualityAlerts.length})
                    </Space>
                  ),
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {qualityAlerts.map((alert) => (
                        <Alert
                          key={alert.alert_id}
                          message={alert.message}
                          type={getAlertType(alert.type)}
                          icon={getAlertIcon(alert.type)}
                          showIcon
                          closable
                          onClose={() =>
                            setQualityAlerts((prev) =>
                              prev.filter((a) => a.alert_id !== alert.alert_id)
                            )
                          }
                          description={
                            alert.metric && alert.threshold != null && alert.current_value != null ? (
                              <div style={{ fontSize: 12 }}>
                                {alert.metric}: {alert.current_value.toFixed(2)} (
                                {t('ai_annotation:fields.threshold')}: {alert.threshold.toFixed(2)})
                              </div>
                            ) : undefined
                          }
                        />
                      ))}
                    </Space>
                  ),
                },
              ]}
              size="small"
              style={{ marginBottom: 16 }}
            />
          </>
        )}

        <Divider orientation="left" style={{ margin: '12px 0' }}>
          <Space>
            <ThunderboltOutlined />
            {t('annotation:sections.ai_suggestions')} ({suggestions.length})
          </Space>
        </Divider>

        {/* AI Suggestions */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin tip={t('annotation:messages.loading_suggestions')} />
          </div>
        ) : suggestions.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical">
                <span>{t('annotation:messages.no_suggestions')}</span>
                <Button
                  type="primary"
                  icon={<BulbOutlined />}
                  onClick={handleRequestSuggestions}
                  size="small"
                >
                  {t('annotation:actions.request_suggestions')}
                </Button>
              </Space>
            }
          />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="small">
            {suggestions.map((suggestion) => (
              <SuggestionCard
                key={suggestion.suggestion_id}
                suggestion={suggestion}
                onAccept={() => handleAcceptSuggestion(suggestion)}
                onReject={(reason) => handleRejectSuggestion(suggestion, reason)}
              />
            ))}
          </Space>
        )}

        {/* Tips */}
        {suggestions.length > 0 && (
          <Alert
            message={t('annotation:tips.ai_suggestions')}
            description={t('annotation:tips.ai_suggestions_desc')}
            type="info"
            showIcon
            icon={<BulbOutlined />}
            style={{ marginTop: 16 }}
            closable
          />
        )}
      </Card>
    </div>
  );
};

export default AIAssistancePanel;
