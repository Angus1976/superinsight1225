/**
 * Network Optimization Monitor Component
 * 
 * Displays network status, request metrics, and optimization features.
 * Provides controls for managing network requests.
 */

import React, { useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Progress,
  Badge,
  Tooltip,
  Button,
  List,
  Typography,
  Space,
  Alert,
} from 'antd';
import {
  WifiOutlined,
  DisconnectOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  StopOutlined,
  CloudOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons';
import {
  useNetworkStatus,
  useRequestMetrics,
  useRequestCancellation,
  useOfflineQueue,
} from '@/hooks/useNetworkOptimization';

const { Text, Title } = Typography;

// ============================================
// Types
// ============================================

interface NetworkOptimizationMonitorProps {
  /** Show detailed metrics */
  detailed?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Show offline queue */
  showOfflineQueue?: boolean;
}

// ============================================
// Helper Functions
// ============================================

function getNetworkTypeColor(effectiveType: string): string {
  switch (effectiveType) {
    case '4g':
      return '#52c41a';
    case '3g':
      return '#faad14';
    case '2g':
    case 'slow-2g':
      return '#ff4d4f';
    default:
      return '#1890ff';
  }
}

function getNetworkTypeLabel(effectiveType: string): string {
  switch (effectiveType) {
    case '4g':
      return 'Fast (4G)';
    case '3g':
      return 'Moderate (3G)';
    case '2g':
      return 'Slow (2G)';
    case 'slow-2g':
      return 'Very Slow';
    default:
      return 'Unknown';
  }
}

// ============================================
// Network Status Badge Component
// ============================================

export const NetworkStatusBadge: React.FC = () => {
  const { isOnline, isSlow, status } = useNetworkStatus();

  if (!isOnline) {
    return (
      <Tooltip title="You are offline. Requests will be queued.">
        <Badge
          status="error"
          text={
            <Text type="danger">
              <DisconnectOutlined /> Offline
            </Text>
          }
        />
      </Tooltip>
    );
  }

  if (isSlow) {
    return (
      <Tooltip title={`Slow network detected (${status.effectiveType}). Requests may take longer.`}>
        <Badge
          status="warning"
          text={
            <Text type="warning">
              <WifiOutlined /> Slow
            </Text>
          }
        />
      </Tooltip>
    );
  }

  return (
    <Tooltip title={`Network: ${getNetworkTypeLabel(status.effectiveType)}`}>
      <Badge
        status="success"
        text={
          <Text type="success">
            <WifiOutlined /> Online
          </Text>
        }
      />
    </Tooltip>
  );
};

// ============================================
// Request Metrics Badge Component
// ============================================

export const RequestMetricsBadge: React.FC = () => {
  const { metrics, successRate, isHealthy } = useRequestMetrics();

  return (
    <Tooltip
      title={
        <div>
          <div>Total Requests: {metrics.totalRequests}</div>
          <div>Success Rate: {successRate}%</div>
          <div>Avg Response: {metrics.averageResponseTime}ms</div>
          <div>Retries: {metrics.retryCount}</div>
        </div>
      }
    >
      <Badge
        status={isHealthy ? 'success' : 'warning'}
        text={
          <span style={{ fontSize: 12 }}>
            <ThunderboltOutlined style={{ marginRight: 4 }} />
            {successRate}% | {metrics.averageResponseTime}ms
          </span>
        }
      />
    </Tooltip>
  );
};

// ============================================
// Main Monitor Component
// ============================================

export const NetworkOptimizationMonitor: React.FC<NetworkOptimizationMonitorProps> = ({
  detailed = false,
  compact = false,
  showOfflineQueue = true,
}) => {
  const { status, isOnline, isSlow, recommendedTimeout } = useNetworkStatus();
  const { metrics, reset: resetMetrics, successRate, isHealthy } = useRequestMetrics();
  const { activeCount, cancelAll } = useRequestCancellation();
  const { queueLength, processQueue, clearQueue, isProcessing } = useOfflineQueue();

  // Calculate health score
  const healthScore = useMemo(() => {
    let score = 100;
    
    // Deduct for offline
    if (!isOnline) score -= 50;
    
    // Deduct for slow network
    if (isSlow) score -= 20;
    
    // Deduct for low success rate
    if (successRate < 90) score -= (90 - successRate);
    
    // Deduct for high response time
    if (metrics.averageResponseTime > 500) {
      score -= Math.min(30, (metrics.averageResponseTime - 500) / 50);
    }
    
    return Math.max(0, Math.round(score));
  }, [isOnline, isSlow, successRate, metrics.averageResponseTime]);

  // Compact view
  if (compact) {
    return (
      <Space>
        <NetworkStatusBadge />
        <RequestMetricsBadge />
        {queueLength > 0 && (
          <Badge count={queueLength} size="small">
            <CloudSyncOutlined />
          </Badge>
        )}
      </Space>
    );
  }

  return (
    <Card
      title={
        <Space>
          <CloudOutlined />
          Network Optimization
          <Tag color={isHealthy ? 'success' : 'warning'}>
            {isHealthy ? 'Healthy' : 'Degraded'}
          </Tag>
        </Space>
      }
      extra={
        <Space>
          <Button
            type="text"
            icon={<StopOutlined />}
            onClick={cancelAll}
            disabled={activeCount === 0}
            title="Cancel All Requests"
          />
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={resetMetrics}
            title="Reset Metrics"
          />
        </Space>
      }
      size="small"
    >
      {/* Offline Alert */}
      {!isOnline && (
        <Alert
          message="You are offline"
          description="Requests will be queued and processed when you're back online."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Network Status */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Statistic
            title="Network Status"
            value={isOnline ? 'Online' : 'Offline'}
            prefix={isOnline ? <WifiOutlined /> : <DisconnectOutlined />}
            valueStyle={{ color: isOnline ? '#52c41a' : '#ff4d4f' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Connection Type"
            value={getNetworkTypeLabel(status.effectiveType)}
            valueStyle={{ color: getNetworkTypeColor(status.effectiveType) }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Latency (RTT)"
            value={status.rtt}
            suffix="ms"
            prefix={<ClockCircleOutlined />}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Bandwidth"
            value={status.downlink}
            suffix="Mbps"
          />
        </Col>
      </Row>

      {/* Health Score */}
      <div style={{ marginTop: 16 }}>
        <Text type="secondary">Network Health Score</Text>
        <Progress
          percent={healthScore}
          status={healthScore >= 80 ? 'success' : healthScore >= 50 ? 'normal' : 'exception'}
          strokeColor={{
            '0%': '#ff4d4f',
            '50%': '#faad14',
            '100%': '#52c41a',
          }}
        />
      </div>

      {/* Request Metrics */}
      <div style={{ marginTop: 16 }}>
        <Title level={5}>Request Metrics</Title>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic
              title="Total Requests"
              value={metrics.totalRequests}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Success Rate"
              value={successRate}
              suffix="%"
              prefix={successRate >= 90 ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              valueStyle={{ color: successRate >= 90 ? '#52c41a' : '#ff4d4f' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Avg Response"
              value={metrics.averageResponseTime}
              suffix="ms"
              valueStyle={{ 
                color: metrics.averageResponseTime <= 500 ? '#52c41a' : '#ff4d4f' 
              }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Active Requests"
              value={activeCount}
            />
          </Col>
        </Row>
      </div>

      {/* Detailed Metrics */}
      {detailed && (
        <div style={{ marginTop: 16 }}>
          <Title level={5}>Detailed Statistics</Title>
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Statistic
                title="Successful"
                value={metrics.successfulRequests}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Failed"
                value={metrics.failedRequests}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Cancelled"
                value={metrics.cancelledRequests}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Retries"
                value={metrics.retryCount}
              />
            </Col>
          </Row>
        </div>
      )}

      {/* Offline Queue */}
      {showOfflineQueue && queueLength > 0 && (
        <div style={{ marginTop: 16 }}>
          <Title level={5}>
            Offline Queue
            <Badge count={queueLength} style={{ marginLeft: 8 }} />
          </Title>
          <Space>
            <Button
              type="primary"
              size="small"
              onClick={processQueue}
              loading={isProcessing}
              disabled={!isOnline}
            >
              Process Queue
            </Button>
            <Button
              size="small"
              onClick={clearQueue}
              danger
            >
              Clear Queue
            </Button>
          </Space>
        </div>
      )}

      {/* Optimization Tips */}
      {detailed && (
        <div style={{ marginTop: 16 }}>
          <Title level={5}>Optimization Tips</Title>
          <List
            size="small"
            dataSource={[
              isSlow && 'Slow network detected - requests will use longer timeouts',
              status.saveData && 'Data saver mode enabled - reduced payload sizes',
              metrics.retryCount > 10 && 'High retry count - check network stability',
              metrics.averageResponseTime > 500 && 'High response times - consider caching',
              activeCount > 10 && 'Many active requests - consider batching',
            ].filter(Boolean) as string[]}
            renderItem={(tip) => (
              <List.Item>
                <Text type="secondary">{tip}</Text>
              </List.Item>
            )}
            locale={{ emptyText: 'No optimization suggestions' }}
          />
        </div>
      )}
    </Card>
  );
};

export default NetworkOptimizationMonitor;
