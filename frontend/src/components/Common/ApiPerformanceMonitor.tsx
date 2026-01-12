/**
 * API Performance Monitor Component
 * 
 * Displays real-time API performance metrics and alerts.
 * Shows response time tracking against the 500ms budget.
 */

import React from 'react';
import { Card, Progress, Statistic, Row, Col, Tag, List, Typography, Badge, Tooltip, Button } from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  ReloadOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import {
  useApiResponseTime,
  useApiPerformanceAlerts,
  API_RESPONSE_BUDGET,
  API_WARNING_THRESHOLD,
} from '@/hooks/useApiResponseTime';

const { Text, Title } = Typography;

interface ApiPerformanceMonitorProps {
  /** Show detailed metrics */
  detailed?: boolean;
  /** Show alerts */
  showAlerts?: boolean;
  /** Compact mode */
  compact?: boolean;
}

/**
 * Get status color based on response time
 */
function getStatusColor(responseTime: number): string {
  if (responseTime <= API_WARNING_THRESHOLD) return '#52c41a'; // green
  if (responseTime <= API_RESPONSE_BUDGET) return '#faad14'; // orange
  return '#ff4d4f'; // red
}

/**
 * Get status icon based on response time
 */
function getStatusIcon(responseTime: number): React.ReactNode {
  if (responseTime <= API_WARNING_THRESHOLD) {
    return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
  }
  if (responseTime <= API_RESPONSE_BUDGET) {
    return <WarningOutlined style={{ color: '#faad14' }} />;
  }
  return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
}

/**
 * API Performance Monitor Component
 */
export const ApiPerformanceMonitor: React.FC<ApiPerformanceMonitorProps> = ({
  detailed = false,
  showAlerts = true,
  compact = false,
}) => {
  const {
    latestMetrics,
    summary,
    isHealthy,
    clearMetrics,
    clearCache,
  } = useApiResponseTime();
  
  const { alerts, clearAlerts } = useApiPerformanceAlerts();

  // Calculate success rate
  const successRate = summary.totalCalls > 0
    ? Math.round((summary.withinBudget / summary.totalCalls) * 100)
    : 100;

  // Compact view
  if (compact) {
    return (
      <Tooltip title={`API Performance: ${summary.averageResponseTime}ms avg, ${successRate}% within budget`}>
        <Badge
          status={isHealthy ? 'success' : 'error'}
          text={
            <Text type={isHealthy ? 'success' : 'danger'}>
              <ThunderboltOutlined /> {summary.averageResponseTime}ms
            </Text>
          }
        />
      </Tooltip>
    );
  }

  return (
    <Card
      title={
        <span>
          <ThunderboltOutlined /> API Performance Monitor
          <Tag color={isHealthy ? 'success' : 'error'} style={{ marginLeft: 8 }}>
            {isHealthy ? 'Healthy' : 'Degraded'}
          </Tag>
        </span>
      }
      extra={
        <span>
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={clearCache}
            title="Clear Cache"
          />
          <Button
            type="text"
            icon={<DeleteOutlined />}
            onClick={() => {
              clearMetrics();
              clearAlerts();
            }}
            title="Clear Metrics"
          />
        </span>
      }
      size="small"
    >
      {/* Summary Statistics */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Statistic
            title="Avg Response Time"
            value={summary.averageResponseTime}
            suffix="ms"
            valueStyle={{ color: getStatusColor(summary.averageResponseTime) }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Success Rate"
            value={successRate}
            suffix="%"
            valueStyle={{ color: successRate >= 90 ? '#52c41a' : '#ff4d4f' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Cache Hit Rate"
            value={summary.cacheHitRate}
            suffix="%"
            valueStyle={{ color: '#1890ff' }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="Total Calls"
            value={summary.totalCalls}
          />
        </Col>
      </Row>

      {/* Budget Progress */}
      <div style={{ marginTop: 16 }}>
        <Text type="secondary">Response Time Budget ({API_RESPONSE_BUDGET}ms)</Text>
        <Progress
          percent={Math.min(100, (summary.averageResponseTime / API_RESPONSE_BUDGET) * 100)}
          status={summary.averageResponseTime <= API_RESPONSE_BUDGET ? 'success' : 'exception'}
          strokeColor={{
            '0%': '#52c41a',
            '80%': '#faad14',
            '100%': '#ff4d4f',
          }}
        />
      </div>

      {/* Latest Request */}
      {latestMetrics && (
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Latest Request</Text>
          <div style={{ marginTop: 8 }}>
            {getStatusIcon(latestMetrics.responseTime)}
            <Text style={{ marginLeft: 8 }}>
              {latestMetrics.method} {latestMetrics.endpoint}
            </Text>
            <Tag
              color={latestMetrics.isWithinBudget ? 'success' : 'error'}
              style={{ marginLeft: 8 }}
            >
              {latestMetrics.responseTime}ms
            </Tag>
            {latestMetrics.cached && (
              <Tag color="blue">Cached</Tag>
            )}
          </div>
        </div>
      )}

      {/* Detailed Metrics */}
      {detailed && summary.slowestEndpoints.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Title level={5}>Slowest Endpoints</Title>
          <List
            size="small"
            dataSource={summary.slowestEndpoints}
            renderItem={(item) => (
              <List.Item>
                <Text ellipsis style={{ maxWidth: '70%' }}>{item.endpoint}</Text>
                <Tag color={getStatusColor(item.avgTime)}>{item.avgTime}ms</Tag>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* Alerts */}
      {showAlerts && alerts.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Title level={5}>
            Recent Alerts
            <Button
              type="link"
              size="small"
              onClick={clearAlerts}
            >
              Clear
            </Button>
          </Title>
          <List
            size="small"
            dataSource={alerts.slice(-5)}
            renderItem={(alert) => (
              <List.Item>
                <Badge
                  status={alert.type === 'error' ? 'error' : 'warning'}
                  text={
                    <Text type={alert.type === 'error' ? 'danger' : 'warning'} ellipsis>
                      {alert.message}
                    </Text>
                  }
                />
              </List.Item>
            )}
          />
        </div>
      )}
    </Card>
  );
};

/**
 * Inline API Performance Badge
 * Shows a compact performance indicator
 */
export const ApiPerformanceBadge: React.FC = () => {
  const { summary, isHealthy } = useApiResponseTime();

  return (
    <Tooltip
      title={
        <div>
          <div>Avg Response: {summary.averageResponseTime}ms</div>
          <div>Success Rate: {summary.totalCalls > 0 ? Math.round((summary.withinBudget / summary.totalCalls) * 100) : 100}%</div>
          <div>Cache Hit Rate: {summary.cacheHitRate}%</div>
        </div>
      }
    >
      <Badge
        status={isHealthy ? 'success' : 'error'}
        text={
          <span style={{ fontSize: 12 }}>
            <ThunderboltOutlined style={{ marginRight: 4 }} />
            {summary.averageResponseTime}ms
          </span>
        }
      />
    </Tooltip>
  );
};

export default ApiPerformanceMonitor;
