/**
 * Performance Profiler Component
 * 
 * Development tool for monitoring component render times.
 * Displays real-time metrics and alerts when components exceed 100ms budget.
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import { Card, Table, Tag, Progress, Space, Button, Tooltip, Badge, Statistic, Row, Col, Switch } from 'antd';
import {
  DashboardOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  CloseOutlined,
  ExpandOutlined,
  CompressOutlined,
} from '@ant-design/icons';
import { getAllComponentStats, clearComponentStats } from './withPerformanceMonitor';
import { getRenderMetricsSummary, clearRenderMetrics } from '@/hooks/useComponentRenderTime';

// Render time budget
const RENDER_TIME_BUDGET = 100;

interface ComponentMetric {
  key: string;
  name: string;
  renderCount: number;
  avgRenderTime: number;
  maxRenderTime: number;
  minRenderTime: number;
  lastRenderTime: number;
  status: 'good' | 'warning' | 'error';
}

interface PerformanceProfilerProps {
  /** Position of the profiler panel */
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  /** Initial collapsed state */
  defaultCollapsed?: boolean;
  /** Auto-refresh interval in ms */
  refreshInterval?: number;
  /** Show only in development */
  devOnly?: boolean;
}

/**
 * Performance Profiler Panel
 */
export const PerformanceProfiler: React.FC<PerformanceProfilerProps> = memo(({
  position = 'bottom-right',
  defaultCollapsed = true,
  refreshInterval = 2000,
  devOnly = true,
}) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [expanded, setExpanded] = useState(false);
  const [metrics, setMetrics] = useState<ComponentMetric[]>([]);
  const [summary, setSummary] = useState({
    totalComponents: 0,
    componentsWithinBudget: 0,
    componentsExceedingBudget: 0,
    averageRenderTime: 0,
  });
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Don't render in production if devOnly is true
  if (devOnly && !import.meta.env.DEV) {
    return null;
  }

  // Refresh metrics
  const refreshMetrics = useCallback(() => {
    const stats = getAllComponentStats();
    const hookSummary = getRenderMetricsSummary();

    const componentMetrics: ComponentMetric[] = [];

    stats.forEach((stat, name) => {
      if (stat.renderCount === 0) return;

      const avgTime = stat.totalRenderTime / stat.renderCount;
      let status: 'good' | 'warning' | 'error' = 'good';
      
      if (avgTime > RENDER_TIME_BUDGET) {
        status = 'error';
      } else if (avgTime > RENDER_TIME_BUDGET * 0.8) {
        status = 'warning';
      }

      componentMetrics.push({
        key: name,
        name,
        renderCount: stat.renderCount,
        avgRenderTime: Math.round(avgTime * 100) / 100,
        maxRenderTime: Math.round(stat.maxRenderTime * 100) / 100,
        minRenderTime: stat.minRenderTime === Infinity ? 0 : Math.round(stat.minRenderTime * 100) / 100,
        lastRenderTime: Math.round(stat.lastRenderTime * 100) / 100,
        status,
      });
    });

    // Sort by average render time descending
    componentMetrics.sort((a, b) => b.avgRenderTime - a.avgRenderTime);

    setMetrics(componentMetrics);
    setSummary({
      totalComponents: componentMetrics.length,
      componentsWithinBudget: componentMetrics.filter(m => m.status === 'good').length,
      componentsExceedingBudget: componentMetrics.filter(m => m.status === 'error').length,
      averageRenderTime: hookSummary.averageRenderTime,
    });
  }, []);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(refreshMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refreshMetrics]);

  // Initial load
  useEffect(() => {
    refreshMetrics();
  }, [refreshMetrics]);

  // Clear all metrics
  const handleClear = useCallback(() => {
    clearComponentStats();
    clearRenderMetrics();
    refreshMetrics();
  }, [refreshMetrics]);

  // Position styles
  const positionStyles: React.CSSProperties = {
    position: 'fixed',
    zIndex: 9999,
    ...(position.includes('bottom') ? { bottom: 16 } : { top: 16 }),
    ...(position.includes('right') ? { right: 16 } : { left: 16 }),
  };

  // Table columns
  const columns = [
    {
      title: 'Component',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Renders',
      dataIndex: 'renderCount',
      key: 'renderCount',
      width: 80,
      sorter: (a: ComponentMetric, b: ComponentMetric) => a.renderCount - b.renderCount,
    },
    {
      title: 'Avg (ms)',
      dataIndex: 'avgRenderTime',
      key: 'avgRenderTime',
      width: 100,
      sorter: (a: ComponentMetric, b: ComponentMetric) => a.avgRenderTime - b.avgRenderTime,
      render: (value: number, record: ComponentMetric) => (
        <Space>
          <span>{value}</span>
          <Progress
            percent={Math.min((value / RENDER_TIME_BUDGET) * 100, 100)}
            size="small"
            showInfo={false}
            status={record.status === 'error' ? 'exception' : record.status === 'warning' ? 'active' : 'success'}
            style={{ width: 50 }}
          />
        </Space>
      ),
    },
    {
      title: 'Max (ms)',
      dataIndex: 'maxRenderTime',
      key: 'maxRenderTime',
      width: 80,
      sorter: (a: ComponentMetric, b: ComponentMetric) => a.maxRenderTime - b.maxRenderTime,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      filters: [
        { text: 'Good', value: 'good' },
        { text: 'Warning', value: 'warning' },
        { text: 'Error', value: 'error' },
      ],
      onFilter: (value: any, record: ComponentMetric) => record.status === value,
      render: (status: string) => {
        const config = {
          good: { color: 'success', icon: <CheckCircleOutlined />, text: 'Good' },
          warning: { color: 'warning', icon: <WarningOutlined />, text: 'Warning' },
          error: { color: 'error', icon: <WarningOutlined />, text: 'Slow' },
        };
        const { color, icon, text } = config[status as keyof typeof config];
        return <Tag color={color} icon={icon}>{text}</Tag>;
      },
    },
  ];

  // Collapsed view - just a badge
  if (collapsed) {
    const hasIssues = summary.componentsExceedingBudget > 0;
    
    return (
      <div style={positionStyles}>
        <Tooltip title="Performance Profiler">
          <Badge count={hasIssues ? summary.componentsExceedingBudget : 0} offset={[-5, 5]}>
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
            <span>Performance Profiler</span>
            <Tag color={summary.componentsExceedingBudget > 0 ? 'error' : 'success'}>
              {summary.componentsExceedingBudget > 0 
                ? `${summary.componentsExceedingBudget} slow` 
                : 'All good'}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="Auto-refresh">
              <Switch
                size="small"
                checked={autoRefresh}
                onChange={setAutoRefresh}
              />
            </Tooltip>
            <Tooltip title="Refresh">
              <Button size="small" icon={<ReloadOutlined />} onClick={refreshMetrics} />
            </Tooltip>
            <Tooltip title="Clear">
              <Button size="small" onClick={handleClear}>Clear</Button>
            </Tooltip>
            <Tooltip title={expanded ? 'Collapse' : 'Expand'}>
              <Button 
                size="small" 
                icon={expanded ? <CompressOutlined /> : <ExpandOutlined />} 
                onClick={() => setExpanded(!expanded)}
              />
            </Tooltip>
            <Tooltip title="Close">
              <Button size="small" icon={<CloseOutlined />} onClick={() => setCollapsed(true)} />
            </Tooltip>
          </Space>
        }
        style={{
          width: expanded ? 800 : 500,
          maxHeight: expanded ? '80vh' : 400,
          overflow: 'auto',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
        size="small"
      >
        {/* Summary Stats */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Statistic
              title="Components"
              value={summary.totalComponents}
              valueStyle={{ fontSize: 16 }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Within Budget"
              value={summary.componentsWithinBudget}
              valueStyle={{ fontSize: 16, color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Exceeding"
              value={summary.componentsExceedingBudget}
              valueStyle={{ fontSize: 16, color: summary.componentsExceedingBudget > 0 ? '#ff4d4f' : '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="Avg Time"
              value={summary.averageRenderTime}
              suffix="ms"
              valueStyle={{ fontSize: 16 }}
            />
          </Col>
        </Row>

        {/* Budget indicator */}
        <div style={{ marginBottom: 16 }}>
          <Space>
            <span>Budget: {RENDER_TIME_BUDGET}ms</span>
            <Progress
              percent={Math.min((summary.averageRenderTime / RENDER_TIME_BUDGET) * 100, 100)}
              status={summary.averageRenderTime > RENDER_TIME_BUDGET ? 'exception' : 'success'}
              style={{ width: 200 }}
            />
          </Space>
        </div>

        {/* Component Table */}
        <Table
          columns={columns}
          dataSource={metrics}
          size="small"
          pagination={{ pageSize: expanded ? 10 : 5, size: 'small' }}
          scroll={{ y: expanded ? 400 : 200 }}
        />
      </Card>
    </div>
  );
});

PerformanceProfiler.displayName = 'PerformanceProfiler';

export default PerformanceProfiler;
