/**
 * Suggestion Card Component
 *
 * Displays a single AI suggestion with:
 * - Label and confidence score
 * - Accept/Reject actions
 * - Reasoning and context
 * - Similar examples indicator
 * - Engine type badge
 */

import React, { useState } from 'react';
import {
  Card,
  Space,
  Button,
  Tag,
  Progress,
  Tooltip,
  Modal,
  Input,
  Collapse,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

interface AISuggestion {
  suggestionId: string;
  label: string;
  confidence: number;
  reasoning?: string;
  similarExamples: number;
  engineType: 'pre-annotation' | 'mid-coverage' | 'post-validation';
  metadata?: {
    patterns?: string[];
    context?: string;
  };
}

interface SuggestionCardProps {
  suggestion: AISuggestion;
  onAccept: () => void;
  onReject: (reason?: string) => void;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({
  suggestion,
  onAccept,
  onReject,
}) => {
  const { t } = useTranslation(['annotation', 'common', 'ai_annotation']);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return '#52c41a'; // Green
    if (confidence >= 0.7) return '#1890ff'; // Blue
    if (confidence >= 0.5) return '#faad14'; // Orange
    return '#ff4d4f'; // Red
  };

  const getConfidenceStatus = (confidence: number): 'success' | 'normal' | 'exception' => {
    if (confidence >= 0.7) return 'success';
    if (confidence >= 0.5) return 'normal';
    return 'exception';
  };

  const getEngineTypeColor = (type: string): string => {
    switch (type) {
      case 'pre-annotation':
        return 'blue';
      case 'mid-coverage':
        return 'green';
      case 'post-validation':
        return 'orange';
      default:
        return 'default';
    }
  };

  const handleReject = () => {
    setRejectModalVisible(true);
  };

  const handleRejectConfirm = () => {
    onReject(rejectReason || undefined);
    setRejectModalVisible(false);
    setRejectReason('');
  };

  return (
    <>
      <Card
        size="small"
        className="suggestion-card"
        style={{
          borderLeft: `4px solid ${getConfidenceColor(suggestion.confidence)}`,
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Tag color={getEngineTypeColor(suggestion.engineType)}>
                {t(`ai_annotation:engine_types.${suggestion.engineType.replace('-', '_')}`)}
              </Tag>
              <strong style={{ fontSize: 14 }}>{suggestion.label}</strong>
            </Space>
            <Space>
              {suggestion.similarExamples > 0 && (
                <Tooltip
                  title={t('annotation:tooltips.similar_examples', {
                    count: suggestion.similarExamples,
                  })}
                >
                  <Tag icon={<EyeOutlined />} color="cyan">
                    {suggestion.similarExamples}
                  </Tag>
                </Tooltip>
              )}
            </Space>
          </div>

          {/* Confidence Score */}
          <div>
            <Space style={{ width: '100%', marginBottom: 4 }}>
              <ThunderboltOutlined style={{ color: getConfidenceColor(suggestion.confidence) }} />
              <span style={{ fontSize: 12 }}>
                {t('annotation:labels.confidence')}: <strong>{(suggestion.confidence * 100).toFixed(1)}%</strong>
              </span>
            </Space>
            <Progress
              percent={suggestion.confidence * 100}
              strokeColor={getConfidenceColor(suggestion.confidence)}
              status={getConfidenceStatus(suggestion.confidence)}
              showInfo={false}
              size="small"
            />
          </div>

          {/* Reasoning and Metadata */}
          {(suggestion.reasoning || suggestion.metadata) && (
            <Collapse
              items={[
                {
                  key: 'details',
                  label: (
                    <Space>
                      <InfoCircleOutlined />
                      {t('annotation:labels.details')}
                    </Space>
                  ),
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {suggestion.reasoning && (
                        <div>
                          <strong>{t('annotation:labels.reasoning')}:</strong>
                          <p style={{ margin: '4px 0', fontSize: 12, color: '#666' }}>
                            {suggestion.reasoning}
                          </p>
                        </div>
                      )}
                      {suggestion.metadata?.patterns && suggestion.metadata.patterns.length > 0 && (
                        <div>
                          <strong>{t('annotation:labels.patterns')}:</strong>
                          <div style={{ marginTop: 4 }}>
                            {suggestion.metadata.patterns.map((pattern, idx) => (
                              <Tag key={idx} color="purple" style={{ marginBottom: 4 }}>
                                {pattern}
                              </Tag>
                            ))}
                          </div>
                        </div>
                      )}
                      {suggestion.metadata?.context && (
                        <div>
                          <strong>{t('annotation:labels.context')}:</strong>
                          <p style={{ margin: '4px 0', fontSize: 12, color: '#666' }}>
                            {suggestion.metadata.context}
                          </p>
                        </div>
                      )}
                    </Space>
                  ),
                },
              ]}
              size="small"
              ghost
            />
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={onAccept}
              size="small"
              style={{ flex: 1 }}
            >
              {t('annotation:actions.accept')}
            </Button>
            <Button
              danger
              icon={<CloseOutlined />}
              onClick={handleReject}
              size="small"
              style={{ flex: 1 }}
            >
              {t('annotation:actions.reject')}
            </Button>
          </div>
        </Space>
      </Card>

      {/* Reject Reason Modal */}
      <Modal
        title={t('annotation:modals.reject_suggestion')}
        open={rejectModalVisible}
        onOk={handleRejectConfirm}
        onCancel={() => {
          setRejectModalVisible(false);
          setRejectReason('');
        }}
        okText={t('common:actions.confirm')}
        cancelText={t('common:actions.cancel')}
      >
        <p>{t('annotation:messages.reject_reason_prompt')}</p>
        <Input.TextArea
          rows={4}
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          placeholder={t('annotation:placeholders.reject_reason')}
        />
      </Modal>
    </>
  );
};

export default SuggestionCard;
