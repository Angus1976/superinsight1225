/**
 * Data Flow Visualization Component
 * 
 * Visual representation of all 13 lifecycle stages with data flow connections.
 * Uses SVG for rendering with interactive stage nodes.
 */

import { useState, useCallback } from 'react';
import { Card, Tooltip, Tag, Space, Typography, Badge } from 'antd';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';

const { Text, Title } = Typography;

// ============================================================================
// Types
// ============================================================================

interface LifecycleStage {
  id: string;
  name: string;
  key: string;
  color: string;
  icon: string;
  description: string;
  dataCount: number;
}

interface DataFlowVisualizationProps {
  stages?: LifecycleStage[];
  onStageClick?: (stageId: string) => void;
  showCounts?: boolean;
  height?: number;
}

// ============================================================================
// Lifecycle Stages Configuration
// ============================================================================

const DEFAULT_STAGES: LifecycleStage[] = [
  { id: 'temp_stored', name: 'Temp Stored', key: 'TEMP_STORED', color: '#1890ff', icon: '📥', description: 'Temporary data storage', dataCount: 0 },
  { id: 'under_review', name: 'Under Review', key: 'UNDER_REVIEW', color: '#722ed1', icon: '👀', description: 'Data under review', dataCount: 0 },
  { id: 'review_passed', name: 'Review Passed', key: 'REVIEW_PASSED', color: '#52c41a', icon: '✅', description: 'Review completed successfully', dataCount: 0 },
  { id: 'review_rejected', name: 'Review Rejected', key: 'REVIEW_REJECTED', color: '#ff4d4f', icon: '❌', description: 'Review rejected', dataCount: 0 },
  { id: 'sample_ready', name: 'Sample Ready', key: 'SAMPLE_READY', color: '#13c2c2', icon: '⭐', description: 'Sample data ready', dataCount: 0 },
  { id: 'annotation_pending', name: 'Annotation Pending', key: 'ANNOTATION_PENDING', color: '#fa8c16', icon: '📝', description: 'Waiting for annotation', dataCount: 0 },
  { id: 'annotation_in_progress', name: 'Annotation In Progress', key: 'ANNOTATION_IN_PROGRESS', color: '#1890ff', icon: '✏️', description: 'Annotation in progress', dataCount: 0 },
  { id: 'annotation_completed', name: 'Annotation Completed', key: 'ANNOTATION_COMPLETED', color: '#52c41a', icon: '📋', description: 'Annotation completed', dataCount: 0 },
  { id: 'enhancement_pending', name: 'Enhancement Pending', key: 'ENHANCEMENT_PENDING', color: '#fa8c16', icon: '🔧', description: 'Waiting for enhancement', dataCount: 0 },
  { id: 'enhancement_in_progress', name: 'Enhancement In Progress', key: 'ENHANCEMENT_IN_PROGRESS', color: '#1890ff', icon: '⚙️', description: 'Enhancement in progress', dataCount: 0 },
  { id: 'enhancement_completed', name: 'Enhancement Completed', key: 'ENHANCEMENT_COMPLETED', color: '#52c41a', icon: '✨', description: 'Enhancement completed', dataCount: 0 },
  { id: 'ai_trial_pending', name: 'AI Trial Pending', key: 'AI_TRIAL_PENDING', color: '#fa8c16', icon: '🤖', description: 'Waiting for AI trial', dataCount: 0 },
  { id: 'ai_trial_completed', name: 'AI Trial Completed', key: 'AI_TRIAL_COMPLETED', color: '#52c41a', icon: '🎯', description: 'AI trial completed', dataCount: 0 },
];

// ============================================================================
// Stage Node Component
// ============================================================================

interface StageNodeProps {
  stage: LifecycleStage;
  position: { x: number; y: number };
  isActive: boolean;
  onClick: () => void;
  showCount: boolean;
}

const StageNode: React.FC<StageNodeProps> = ({ stage, position, isActive, onClick, showCount }) => {
  const { t } = useTranslation('dataLifecycle');
  
  return (
    <g
      transform={`translate(${position.x}, ${position.y})`}
      style={{ cursor: 'pointer' }}
      onClick={onClick}
    >
      {/* Node background */}
      <rect
        x="-50"
        y="-25"
        width="100"
        height="50"
        rx="8"
        ry="8"
        fill={isActive ? stage.color : '#f5f5f5'}
        stroke={isActive ? stage.color : '#d9d9d9'}
        strokeWidth={isActive ? 3 : 1}
        style={{ transition: 'all 0.3s ease' }}
      />
      
      {/* Icon */}
      <text
        x="-35"
        y="5"
        fontSize="20"
        textAnchor="middle"
        style={{ pointerEvents: 'none' }}
      >
        {stage.icon}
      </text>
      
      {/* Stage name */}
      <text
        x="0"
        y="5"
        fontSize="11"
        fontWeight={isActive ? 600 : 400}
        fill={isActive ? '#fff' : '#333'}
        textAnchor="middle"
        style={{ pointerEvents: 'none' }}
      >
        {stage.name}
      </text>
      
      {/* Data count badge */}
      {showCount && (
        <g transform="translate(35, -15)">
          <circle r="12" fill="#ff4d4f" />
          <text
            y="4"
            fontSize="10"
            fontWeight="600"
            fill="#fff"
            textAnchor="middle"
            style={{ pointerEvents: 'none' }}
          >
            {stage.dataCount}
          </text>
        </g>
      )}
      
      {/* Tooltip */}
      <title>{stage.name}: {stage.description} ({stage.dataCount} items)</title>
    </g>
  );
};

// ============================================================================
// Connection Line Component
// ============================================================================

interface ConnectionProps {
  start: { x: number; y: number };
  end: { x: number; y: number };
  isActive: boolean;
  label?: string;
}

const Connection: React.FC<ConnectionProps> = ({ start, end, isActive, label }) => {
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  
  return (
    <g>
      {/* Main line */}
      <line
        x1={start.x + 50}
        y1={start.y}
        x2={end.x - 50}
        y2={end.y}
        stroke={isActive ? '#1890ff' : '#d9d9d9'}
        strokeWidth={isActive ? 3 : 1}
        strokeDasharray={isActive ? '0' : '5,5'}
        style={{ transition: 'all 0.3s ease' }}
      />
      
      {/* Arrow head */}
      <polygon
        points={`${end.x - 55},${end.y - 5} ${end.x - 50},${end.y} ${end.x - 55},${end.y + 5}`}
        fill={isActive ? '#1890ff' : '#d9d9d9'}
      />
      
      {/* Label */}
      {label && (
        <text
          x={midX}
          y={midY - 8}
          fontSize="10"
          fill="#8c8c8c"
          textAnchor="middle"
        >
          {label}
        </text>
      )}
    </g>
  );
};

// ============================================================================
// Main Visualization Component
// ============================================================================

const DataFlowVisualization: React.FC<DataFlowVisualizationProps> = ({
  stages = DEFAULT_STAGES,
  onStageClick,
  showCounts = true,
  height = 400,
}) => {
  const { t } = useTranslation('dataLifecycle');
  const { hasPermission } = useAuthStore();
  const [activeStage, setActiveStage] = useState<string | null>(null);
  const [hoveredStage, setHoveredStage] = useState<string | null>(null);

  // Calculate node positions (2 rows layout)
  const getNodePosition = useCallback((index: number): { x: number; y: number } => {
    const cols = 7;
    const row = Math.floor(index / cols);
    const col = index % cols;
    const spacingX = 110;
    const spacingY = 80;
    const startX = 60;
    const startY = 40;
    
    return {
      x: startX + col * spacingX,
      y: startY + row * spacingY,
    };
  }, []);

  // Define connections between stages
  const connections = [
    { from: 0, to: 1, label: 'Submit' },
    { from: 1, to: 2, label: 'Pass' },
    { from: 1, to: 3, label: 'Reject' },
    { from: 2, to: 4, label: 'Ready' },
    { from: 4, to: 5, label: 'Annotate' },
    { from: 5, to: 6, label: 'Start' },
    { from: 6, to: 7, label: 'Complete' },
    { from: 7, to: 8, label: 'Enhance' },
    { from: 8, to: 9, label: 'Start' },
    { from: 9, to: 10, label: 'Complete' },
    { from: 10, to: 11, label: 'Trial' },
    { from: 11, to: 12, label: 'Complete' },
  ];

  const handleStageClick = (stageId: string) => {
    setActiveStage(activeStage === stageId ? null : stageId);
    onStageClick?.(stageId);
  };

  // Calculate SVG dimensions
  const svgWidth = Math.max(800, stages.length * 110 + 100);
  const svgHeight = height;

  return (
    <Card
      title={
        <Space>
          <span>{t('dataFlowVisualization.title')}</span>
          <Tag color="blue">{stages.length} {t('dataFlowVisualization.stages')}</Tag>
        </Space>
      }
      extra={
        <Space>
          <Text type="secondary">{t('dataFlowVisualization.clickToNavigate')}</Text>
        </Space>
      }
    >
      <div style={{ overflowX: 'auto', overflowY: 'hidden' }}>
        <svg
          width={svgWidth}
          height={svgHeight}
          style={{ display: 'block', margin: '0 auto' }}
        >
          {/* Background grid */}
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#f0f0f0" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Connections */}
          {connections.map((conn, index) => {
            const fromStage = stages[conn.from];
            const toStage = stages[conn.to];
            
            // Skip connection if either stage doesn't exist
            if (!fromStage || !toStage) {
              return null;
            }
            
            const fromPos = getNodePosition(conn.from);
            const toPos = getNodePosition(conn.to);
            const isActive = 
              activeStage === fromStage.id || 
              activeStage === toStage.id ||
              hoveredStage === fromStage.id ||
              hoveredStage === toStage.id;

            return (
              <Connection
                key={index}
                start={fromPos}
                end={toPos}
                isActive={isActive}
                label={conn.label}
              />
            );
          })}

          {/* Stage nodes */}
          {stages.map((stage, index) => {
            const position = getNodePosition(index);
            const isActive = activeStage === stage.id;
            const isHovered = hoveredStage === stage.id;

            return (
              <g
                key={stage.id}
                onMouseEnter={() => setHoveredStage(stage.id)}
                onMouseLeave={() => setHoveredStage(null)}
              >
                <StageNode
                  stage={stage}
                  position={position}
                  isActive={isActive || isHovered}
                  onClick={() => handleStageClick(stage.id)}
                  showCount={showCounts}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div style={{ marginTop: 16, padding: '16px', background: '#fafafa', borderRadius: 8 }}>
        <Text strong style={{ marginBottom: 8, display: 'block' }}>{t('dataFlowVisualization.legend')}</Text>
        <Space size={16}>
          <Space size={4}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: '#1890ff' }} />
            <Text type="secondary">{t('dataFlowVisualization.active')}</Text>
          </Space>
          <Space size={4}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: '#52c41a' }} />
            <Text type="secondary">{t('dataFlowVisualization.completed')}</Text>
          </Space>
          <Space size={4}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: '#ff4d4f' }} />
            <Text type="secondary">{t('dataFlowVisualization.rejected')}</Text>
          </Space>
          <Space size={4}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: '#fa8c16' }} />
            <Text type="secondary">{t('dataFlowVisualization.pending')}</Text>
          </Space>
        </Space>
      </div>

      {/* Active stage details */}
      {activeStage && (
        <div style={{ marginTop: 16, padding: 16, background: '#e6f7ff', borderRadius: 8, border: '1px solid #91d5ff' }}>
          <Text strong>
            {stages.find(s => s.id === activeStage)?.name}
          </Text>
          <Text type="secondary" style={{ marginLeft: 8 }}>
            {stages.find(s => s.id === activeStage)?.description}
          </Text>
          <Tag color={stages.find(s => s.id === activeStage)?.color} style={{ marginLeft: 8 }}>
            {stages.find(s => s.id === activeStage)?.dataCount} {t('dataFlowVisualization.items')}
          </Tag>
        </div>
      )}
    </Card>
  );
};

export default DataFlowVisualization;