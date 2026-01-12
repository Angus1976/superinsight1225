import React, { useState } from 'react';
import { Card, Row, Col, Statistic, Table, DatePicker, Select, Button, Space, Progress, Tag } from 'antd';
import { DownloadOutlined, ReloadOutlined, BarChartOutlined, LineChartOutlined } from '@ant-design/icons';
import { Line, Bar, Pie } from '@ant-design/plots';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface QualityReport {
  id: string;
  name: string;
  type: 'daily' | 'weekly' | 'monthly' | 'custom';
  overallScore: number;
  semanticScore: number;
  syntacticScore: number;
  completenessScore: number;
  consistencyScore: number;
  accuracyScore: number;
  totalSamples: number;
  passedSamples: number;
  failedSamples: number;
  createdAt: string;
}

interface QualityMetrics {
  overallScore: number;
  totalSamples: number;
  passedSamples: number;
  failedSamples: number;
  trendData: Array<{
    date: string;
    score: number;
    samples: number;
  }>;
  scoreDistribution: Array<{
    type: string;
    score: number;
  }>;
  ruleViolations: Array<{
    rule: string;
    count: number;
    severity: string;
  }>;
}

const QualityReports: React.FC = () => {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);
  const [reportType, setReportType] = useState<string>('all');

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['quality-metrics', dateRange, reportType],
    queryFn: () => api.get('/api/v1/quality/metrics', {
      params: {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
        type: reportType,
      },
    }).then(res => res.data),
  });

  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ['quality-reports', dateRange],
    queryFn: () => api.get('/api/v1/quality/reports', {
      params: {
        startDate: dateRange[0].format('YYYY-MM-DD'),
        endDate: dateRange[1].format('YYYY-MM-DD'),
      },
    }).then(res => res.data),
  });

  const trendConfig = {
    data: metrics?.trendData || [],
    xField: 'date',
    yField: 'score',
    smooth: true,
    point: {
      size: 5,
      shape: 'diamond',
    },
    label: {
      style: {
        fill: '#aaa',
      },
    },
  };

  const distributionConfig = {
    data: metrics?.scoreDistribution || [],
    xField: 'type',
    yField: 'score',
    color: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1'],
  };

  const violationConfig = {
    data: metrics?.ruleViolations || [],
    angleField: 'count',
    colorField: 'rule',
    radius: 0.8,
    label: {
      type: 'outer',
      content: '{name} {percentage}',
    },
    interactions: [
      {
        type: 'element-active',
      },
    ],
  };

  const columns: ColumnsType<QualityReport> = [
    {
      title: '报告名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const labels = {
          daily: '日报',
          weekly: '周报',
          monthly: '月报',
          custom: '自定义',
        };
        return <Tag>{labels[type as keyof typeof labels]}</Tag>;
      },
    },
    {
      title: '总体评分',
      dataIndex: 'overallScore',
      key: 'overallScore',
      render: (score: number) => (
        <Progress
          percent={score * 100}
          size="small"
          status={score >= 0.8 ? 'success' : score >= 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '样本统计',
      key: 'samples',
      render: (_, record) => (
        <div>
          <div>总数: {record.totalSamples}</div>
          <div style={{ color: '#52c41a' }}>通过: {record.passedSamples}</div>
          <div style={{ color: '#f5222d' }}>失败: {record.failedSamples}</div>
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<BarChartOutlined />}
            onClick={() => {
              // 查看详细报告
              console.log('查看报告:', record.id);
            }}
          >
            查看
          </Button>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => {
              // 下载报告
              console.log('下载报告:', record.id);
            }}
          >
            下载
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="quality-reports">
      {/* 控制面板 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <span>时间范围:</span>
              <RangePicker
                value={dateRange}
                onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <span>报告类型:</span>
              <Select
                value={reportType}
                onChange={setReportType}
                style={{ width: 120 }}
              >
                <Select.Option value="all">全部</Select.Option>
                <Select.Option value="daily">日报</Select.Option>
                <Select.Option value="weekly">周报</Select.Option>
                <Select.Option value="monthly">月报</Select.Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Col>
          <Col>
            <Button type="primary" icon={<DownloadOutlined />}>
              导出报告
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 概览统计 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总体质量评分"
              value={metrics?.overallScore * 100 || 0}
              precision={1}
              suffix="%"
              valueStyle={{
                color: (metrics?.overallScore || 0) >= 0.8 ? '#3f8600' : 
                       (metrics?.overallScore || 0) >= 0.6 ? '#1890ff' : '#cf1322'
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总样本数"
              value={metrics?.totalSamples || 0}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="通过样本"
              value={metrics?.passedSamples || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败样本"
              value={metrics?.failedSamples || 0}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 图表展示 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="质量趋势" loading={metricsLoading}>
            <Line {...trendConfig} height={300} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="评分分布" loading={metricsLoading}>
            <Bar {...distributionConfig} height={300} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="规则违规统计" loading={metricsLoading}>
            <Pie {...violationConfig} height={300} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="质量指标详情" loading={metricsLoading}>
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="语义质量"
                  value={metrics?.scoreDistribution?.find(item => item.type === 'semantic')?.score * 100 || 0}
                  precision={1}
                  suffix="%"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="语法质量"
                  value={metrics?.scoreDistribution?.find(item => item.type === 'syntactic')?.score * 100 || 0}
                  precision={1}
                  suffix="%"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="完整性"
                  value={metrics?.scoreDistribution?.find(item => item.type === 'completeness')?.score * 100 || 0}
                  precision={1}
                  suffix="%"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="一致性"
                  value={metrics?.scoreDistribution?.find(item => item.type === 'consistency')?.score * 100 || 0}
                  precision={1}
                  suffix="%"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 报告列表 */}
      <Card title="历史报告">
        <Table
          columns={columns}
          dataSource={reports}
          loading={reportsLoading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  );
};

export default QualityReports;