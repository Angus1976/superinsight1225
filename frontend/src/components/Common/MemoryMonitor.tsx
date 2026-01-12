/**
 * Memory Monitor Component
 * 
 * Development tool for monitoring memory usage in real-time.
 * Displays memory metrics, trends, and leak detection alerts.
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import {
  Card,
  Progress,
  Space,
  Button,
  Tooltip,
  Badge,
  Statistic,
  Row,
  Col,
  Tag,
  Alert,
  List,
  Typography,
} from 'antd';
import {
  DashboardOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  CloseOutlined,
  ExpandOutlined,
  CompressOutlined,
  DeleteOutlined,
  LineChartOutlined,
  BugOutlined,
} from '@ant-design/icons';
import { useMemoryMonitor } from '@/hooks/useMemoryOptimization';
import { formatMemorySize, MEMORY_BUDGET } from '@/utils/memoryOptimization';

const { Text } = Typography;

interface MemoryMonitorProps {
  /** Position of the monitor panel */
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  /** Initial collapsed state */
  defaultCollapsed?: boolean;
  /** Sample interval in milliseconds */
  sampleInterval?: number;
  /** Show only in development */
  devOnly?: boolean;
}

/**
 * Memory Monitor Panel Component
 */
export const MemoryMonitor: React.FC<MemoryMonitorProps> = memo(({
  position = 'bottom-left',
  defaultCollapsed = true,
  sampleInterval = 5000,
  devOnly = true,
}) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [expanded, setExpanded] = useState(false);

  const {
    current,
    status,
    trend,
    leakDetection,
    history,
    recommendations,
    isSupported,
    refresh,
    clearHistory,
  } = useMemoryMonitor({ sampleInterval });

  // Don't render in production if devOnly is true
  if (devOnly && !import.meta.env.DEV) {
    return null;
  }

  // Don't render if memory API is not supported
  if (!isSupported) {
    return null;
  }

  // Position styles
  const positionStyles: React.CSSProperties = {
    position: 'fixed',
    zIndex: 9998,
    ...(position.includes('bottom') ? { bottom: 16 } : { top: 16 }),
    ...(position.includes('right') ? { right: 16 } : { left: 16 }),
  };

  // Status colors
  const statusConfig = {
    good: { color: '#52c41a', text: 'Good', icon: <CheckCircleOutlined /> },
    warning: { color: '#faad14', text: 'Warning', icon: <WarningOutlined /> },
    critical: { color: '#ff4d4f', text: 'Critical', icon: <WarningOutlined /> },
  };

  const currentStatus = statusConfig[status];

  // Calculate usage percentage for progress bar
  const usagePercent = current
    ? Math.min((current.usedJSHeapSize / (MEMORY_BUDGET.max * 1024 * 1024)) * 100, 100)
    : 0;

  // Collapsed view - just a badge
  if (collapsed) {
    const hasIssues = status !== 'good' || leakDetection?.isLeaking;

    return (
      <div style={positionStyles}>
        <Tooltip title="Memory Monitor">
          <Badge
            count={hasIssues ? '!' : 0}
            offset={[-5, 5]}
            style={{ backgroundColor: hasIssues ? '#ff4d4f' : undefined }}
          >
            <Button
              type={hasIssues ? 'primary' : 'default'}
              danger={hasIssues}
              icon={<DashboardOutlined />}
              onClick={() => setCollapsed(false)}
              style={{
                borderRadius: '50%',
                width: 48,
                height: 48,
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              }}
            />
          </Badge>
        </Tooltip>
      </div>
    );
  }

  return (
    <div style={positionStyles}>
      <Card
        title={
          <Space>
            <DashboardOutlined />
            <span>Memory Monitor</span>
            <Tag color={currentStatus.color} icon={currentStatus.icon}>
              {currentStatus.text}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="Refresh">
              <Button size="small" icon={<ReloadOutlined />} onClick={refresh} />
            </Tooltip>
            <Tooltip title="Clear History">
              <Button size="small" icon={<DeleteOutlined />} onClick={clearHistory} />
            </Tooltip>
            <Tooltip title={expanded ? 'Collapse' : 'Expand'}>
              <Button
                size="small"
                icon={expanded ? <CompressOutlined /> : <ExpandOutlined />}
                onClick={() => setExpanded(!expanded)}
              />
            </Tooltip>
            <Tooltip title="Close">
              <Button
                size="small"
                icon={<CloseOutlined />}
                onClick={() => setCollapsed(true)}
              />
            </Tooltip>
          </Space>
        }
        style={{
          width: expanded ? 600 : 400,
          maxHeight: expanded ? '80vh' : 500,
          overflow: 'auto',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
        size="small"
      >
        {/* Memory Usage Stats */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Statistic
              title="Used"
              value={current ? formatMemorySize(current.usedJSHeapSize) : 'N/A'}
              valueStyle={{ fontSize: 14, color: currentStatus.color }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Total"
              value={current ? formatMemorySize(current.totalJSHeapSize) : 'N/A'}
              valueStyle={{ fontSize: 14 }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="Limit"
              value={current ? formatMemorySize(current.jsHeapSizeLimit) : 'N/A'}
              valueStyle={{ fontSize: 14 }}
            />
          </Col>
        </Row>

        {/* Usage Progress Bar */}
        <div style={{ marginBottom: 16 }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Text type="secondary">Memory Usage</Text>
            <Text>{usagePercent.toFixed(1)}%</Text>
          </Space>
          <Progress
            percent={usagePercent}
            status={status === 'critical' ? 'exception' : status === 'warning' ? 'active' : 'success'}
            showInfo={false}
          />
          <Space style={{ width: '100%', justifyContent: 'space-between', marginTop: 4 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Budget: {MEMORY_BUDGET.warning}MB (warn) / {MEMORY_BUDGET.critical}MB (crit)
            </Text>
          </Space>
        </div>

        {/* Memory Trend */}
        {trend && (
          <div style={{ marginBottom: 16 }}>
            <Space>
              <LineChartOutlined />
              <Text strong>Trend:</Text>
              <Tag
                color={
                  trend.direction === 'increasing'
                    ? 'orange'
                    : trend.direction === 'decreasing'
                    ? 'green'
                    : 'blue'
                }
              >
                {trend.direction === 'increasing'
                  ? '📈 Increasing'
                  : trend.direction === 'decreasing'
                  ? '📉 Decreasing'
                  : '➡️ Stable'}
              </Tag>
              {trend.direction !== 'stable' && (
                <Text type="secondary">
                  ({formatMemorySize(Math.abs(trend.rate))}/s)
                </Text>
              )}
            </Space>
          </div>
        )}

        {/* Leak Detection Alert */}
        {leakDetection && leakDetection.isLeaking && (
          <Alert
            message="Potential Memory Leak Detected"
            description={leakDetection.recommendation}
            type="warning"
            icon={<BugOutlined />}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Recommendations */}
        {expanded && recommendations.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text strong>Recommendations:</Text>
            <List
              size="small"
              dataSource={recommendations}
              renderItem={(item) => (
                <List.Item style={{ padding: '4px 0' }}>
                  <Text style={{ fontSize: 12 }}>{item}</Text>
                </List.Item>
              )}
            />
          </div>
        )}

        {/* History Chart (simplified) */}
        {expanded && history.length > 0 && (
          <div>
            <Text strong>Memory History ({history.length} samples):</Text>
            <div
              style={{
                height: 100,
                marginTop: 8,
                display: 'flex',
                alignItems: 'flex-end',
                gap: 2,
                backgroundColor: '#f5f5f5',
                padding: 8,
                borderRadius: 4,
              }}
            >
              {history.slice(-50).map((sample, index) => {
                const height =
                  (sample.usedJSHeapSize / (MEMORY_BUDGET.max * 1024 * 1024)) * 80;
                const sampleStatus =
                  sample.usedJSHeapSize > MEMORY_BUDGET.critical * 1024 * 1024
                    ? '#ff4d4f'
                    : sample.usedJSHeapSize > MEMORY_BUDGET.warning * 1024 * 1024
                    ? '#faad14'
                    : '#52c41a';

                return (
                  <Tooltip
                    key={index}
                    title={`${formatMemorySize(sample.usedJSHeapSize)} at ${new Date(
                      sample.timestamp
                    ).toLocaleTimeString()}`}
                  >
                    <div
                      style={{
                        width: 6,
                        height: Math.max(height, 4),
                        backgroundColor: sampleStatus,
                        borderRadius: 2,
                        transition: 'height 0.3s',
                      }}
                    />
                  </Tooltip>
                );
              })}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
});

MemoryMonitor.displayName = 'MemoryMonitor';

export default MemoryMonitor;
