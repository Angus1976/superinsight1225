import React, { useState, useMemo } from 'react';
import { Card, Row, Col, Statistic, Spin, Empty, Select, Tag, Table, Space, Typography } from 'antd';
import {
  DashboardOutlined, DatabaseOutlined, CheckCircleOutlined,
  CloseCircleOutlined, CloudOutlined, ClockCircleOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { Line, Bar } from '@ant-design/plots';
import { useTranslation } from 'react-i18next';
import {
  useDashboardOverview,
  useVolumeTrends,
  useQueryPerformance,
  useDataFlow,
} from '@/hooks/useDatalake';
import type {
  DashboardOverview,
  VolumeTrendData,
  QueryPerformanceData,
  DataFlowGraph,
  FlowNode,
  FlowEdge,
} from '@/types/datalake';

const { Title } = Typography;

// ============================================================================
// OverviewCards — 5 stat cards in a row
// ============================================================================

interface OverviewCardsProps {
  data: DashboardOverview | undefined;
  loading: boolean;
}

const OverviewCards: React.FC<OverviewCardsProps> = ({ data, loading }) => {
  const { t } = useTranslation(['dataSync']);

  if (loading) return <Spin style={{ display: 'block', textAlign: 'center', padding: 24 }} />;
  if (!data) return <Empty description={t('datalake.dashboard.noData', '暂无数据')} />;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} lg={4} xl={4}>
        <Card hoverable>
          <Statistic
            title={t('datalake.dashboard.totalSources', '数据源总数')}
            value={data.total_sources}
            prefix={<DatabaseOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5} xl={5}>
        <Card hoverable>
          <Statistic
            title={t('datalake.dashboard.activeSources', '活跃数据源')}
            value={data.active_sources}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5} xl={5}>
        <Card hoverable>
          <Statistic
            title={t('datalake.dashboard.errorSources', '异常数据源')}
            value={data.error_sources}
            prefix={<CloseCircleOutlined />}
            valueStyle={{ color: '#cf1322' }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5} xl={5}>
        <Card hoverable>
          <Statistic
            title={t('datalake.dashboard.dataVolume', '总数据量')}
            value={data.total_data_volume_gb}
            precision={2}
            suffix="GB"
            prefix={<CloudOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} sm={12} lg={5} xl={5}>
        <Card hoverable>
          <Statistic
            title={t('datalake.dashboard.avgLatency', '平均查询延迟')}
            value={data.avg_query_latency_ms}
            precision={1}
            suffix="ms"
            prefix={<ClockCircleOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
};

// ============================================================================
// VolumeTrendsChart — Line chart with period selector
// ============================================================================

const PERIOD_OPTIONS = [
  { label: '7 天', value: '7d' },
  { label: '30 天', value: '30d' },
  { label: '90 天', value: '90d' },
];

interface VolumeTrendsChartProps {
  data: VolumeTrendData | undefined;
  loading: boolean;
  period: string;
  onPeriodChange: (val: string) => void;
}

const VolumeTrendsChart: React.FC<VolumeTrendsChartProps> = ({
  data, loading, period, onPeriodChange,
}) => {
  const { t } = useTranslation(['dataSync']);

  const chartData = useMemo(() => {
    if (!data?.data_points?.length) return [];
    return data.data_points.map((p) => ({
      timestamp: p.timestamp,
      volume_gb: p.volume_gb,
      source_name: p.source_name,
    }));
  }, [data]);

  const lineConfig = useMemo(() => ({
    data: chartData,
    xField: 'timestamp',
    yField: 'volume_gb',
    colorField: 'source_name',
    smooth: true,
    axis: {
      y: { title: 'GB' },
    },
  }), [chartData]);

  return (
    <Card
      title={t('datalake.dashboard.volumeTrends', '数据量趋势')}
      loading={loading}
      extra={
        <Select
          value={period}
          onChange={onPeriodChange}
          options={PERIOD_OPTIONS}
          style={{ width: 100 }}
          size="small"
        />
      }
    >
      {!chartData.length ? (
        <Empty description={t('datalake.dashboard.noData', '暂无数据')} />
      ) : (
        <Line {...lineConfig} height={300} />
      )}
    </Card>
  );
};

// ============================================================================
// QueryPerformanceChart — Bar chart for latency metrics
// ============================================================================

interface QueryPerformanceChartProps {
  data: QueryPerformanceData | undefined;
  loading: boolean;
}

const QueryPerformanceChart: React.FC<QueryPerformanceChartProps> = ({ data, loading }) => {
  const { t } = useTranslation(['dataSync']);

  const barData = useMemo(() => {
    if (!data) return [];
    return [
      { metric: t('datalake.dashboard.avgLatency', '平均延迟'), value: data.avg_latency_ms },
      { metric: 'P95', value: data.p95_latency_ms },
      { metric: 'P99', value: data.p99_latency_ms },
    ];
  }, [data, t]);

  const barConfig = useMemo(() => ({
    data: barData,
    xField: 'metric',
    yField: 'value',
    color: '#1890ff',
    axis: {
      y: { title: 'ms' },
    },
  }), [barData]);

  return (
    <Card title={t('datalake.dashboard.queryPerformance', '查询性能')} loading={loading}>
      {!data ? (
        <Empty description={t('datalake.dashboard.noData', '暂无数据')} />
      ) : (
        <>
          <Bar {...barConfig} height={240} />
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Statistic
                title={t('datalake.dashboard.totalQueries', '总查询数')}
                value={data.total_queries}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title={t('datalake.dashboard.failedQueries', '失败查询数')}
                value={data.failed_queries}
                valueStyle={data.failed_queries > 0 ? { color: '#cf1322' } : undefined}
              />
            </Col>
          </Row>
        </>
      )}
    </Card>
  );
};

// ============================================================================
// DataFlowView — Table-based flow visualization
// ============================================================================

const STATUS_COLOR_MAP: Record<string, string> = {
  active: 'success',
  healthy: 'success',
  syncing: 'processing',
  error: 'error',
  down: 'error',
  idle: 'default',
};

interface DataFlowViewProps {
  data: DataFlowGraph | undefined;
  loading: boolean;
}

const DataFlowView: React.FC<DataFlowViewProps> = ({ data, loading }) => {
  const { t } = useTranslation(['dataSync']);

  const nodeMap = useMemo(() => {
    if (!data?.nodes) return new Map<string, FlowNode>();
    return new Map(data.nodes.map((n) => [n.id, n]));
  }, [data?.nodes]);

  const edgeColumns = useMemo(() => [
    {
      title: t('datalake.dashboard.flowSource', '源节点'),
      dataIndex: 'source',
      key: 'source',
      render: (id: string) => nodeMap.get(id)?.label ?? id,
    },
    {
      title: '',
      key: 'arrow',
      width: 50,
      render: () => <ArrowRightOutlined style={{ color: '#999' }} />,
    },
    {
      title: t('datalake.dashboard.flowTarget', '目标节点'),
      dataIndex: 'target',
      key: 'target',
      render: (id: string) => nodeMap.get(id)?.label ?? id,
    },
    {
      title: t('datalake.dashboard.flowVolume', '数据量 (GB)'),
      dataIndex: 'volume_gb',
      key: 'volume_gb',
      render: (val: number) => val?.toFixed(2) ?? '-',
    },
    {
      title: t('datalake.dashboard.flowStatus', '同步状态'),
      dataIndex: 'sync_status',
      key: 'sync_status',
      render: (status: string) => (
        <Tag color={STATUS_COLOR_MAP[status] ?? 'default'}>{status}</Tag>
      ),
    },
  ], [t, nodeMap]);

  return (
    <Card title={t('datalake.dashboard.dataFlow', '数据流向')} loading={loading}>
      {!data?.edges?.length ? (
        <Empty description={t('datalake.dashboard.noData', '暂无数据')} />
      ) : (
        <>
          {/* Node summary */}
          <Space wrap style={{ marginBottom: 16 }}>
            {data.nodes.map((node) => (
              <Tag
                key={node.id}
                color={STATUS_COLOR_MAP[node.status] ?? 'default'}
                icon={<DatabaseOutlined />}
              >
                {node.label} ({node.type})
              </Tag>
            ))}
          </Space>

          <Table<FlowEdge>
            rowKey={(_, idx) => String(idx)}
            columns={edgeColumns}
            dataSource={data.edges}
            pagination={false}
            size="small"
          />
        </>
      )}
    </Card>
  );
};

// ============================================================================
// DatalakeDashboard — Main page
// ============================================================================

const DatalakeDashboard: React.FC = () => {
  const { t } = useTranslation(['dataSync']);
  const [volumePeriod, setVolumePeriod] = useState('7d');

  const { data: overview, isLoading: overviewLoading } = useDashboardOverview();
  const { data: volumeTrends, isLoading: volumeLoading } = useVolumeTrends(volumePeriod);
  const { data: queryPerf, isLoading: perfLoading } = useQueryPerformance();
  const { data: dataFlow, isLoading: flowLoading } = useDataFlow();

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        <DashboardOutlined style={{ marginRight: 8 }} />
        {t('datalake.dashboard.title', '数据湖/数仓看板')}
      </Title>

      {/* Overview stat cards */}
      <OverviewCards data={overview} loading={overviewLoading} />

      {/* Charts row */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <VolumeTrendsChart
            data={volumeTrends}
            loading={volumeLoading}
            period={volumePeriod}
            onPeriodChange={setVolumePeriod}
          />
        </Col>
        <Col xs={24} lg={12}>
          <QueryPerformanceChart data={queryPerf} loading={perfLoading} />
        </Col>
      </Row>

      {/* Data flow */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <DataFlowView data={dataFlow} loading={flowLoading} />
        </Col>
      </Row>
    </div>
  );
};

export default DatalakeDashboard;
