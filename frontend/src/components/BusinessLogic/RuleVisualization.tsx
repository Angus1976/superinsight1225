// 规则可视化组件
import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Select,
  Button,
  Space,
  Spin,
  message,
  Row,
  Col,
  Typography,
  Tooltip,
} from 'antd';
import {
  BarChartOutlined,
  NodeIndexOutlined,
  PieChartOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import * as echarts from 'echarts';

const { Title, Text } = Typography;
const { Option } = Select;

interface RuleVisualizationProps {
  projectId: string;
  rules: any[];
  patterns: any[];
}

interface VisualizationData {
  chart_data: any;
  chart_config: any;
}

export const RuleVisualization: React.FC<RuleVisualizationProps> = ({
  projectId,
  rules,
  patterns,
}) => {
  const { t } = useTranslation(['businessLogic', 'common']);
  const [visualizationType, setVisualizationType] = useState('rule_network');
  const [loading, setLoading] = useState(false);
  const [visualizationData, setVisualizationData] = useState<VisualizationData | null>(null);
  
  // ECharts 实例引用
  const networkChartRef = useRef<HTMLDivElement>(null);
  const timelineChartRef = useRef<HTMLDivElement>(null);
  const dashboardChartRef = useRef<HTMLDivElement>(null);
  
  const networkChart = useRef<echarts.ECharts | null>(null);
  const timelineChart = useRef<echarts.ECharts | null>(null);
  const dashboardChart = useRef<echarts.ECharts | null>(null);

  // 生成可视化数据
  const generateVisualization = async (type: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/business-logic/visualization', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          visualization_type: type,
          time_range_days: 30,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setVisualizationData(data);
        renderVisualization(type, data);
      } else {
        throw new Error(t('visualization.generateError'));
      }
    } catch (error) {
      console.error('Generate visualization failed:', error);
      message.error(t('visualization.generateError'));
    } finally {
      setLoading(false);
    }
  };

  // 渲染可视化图表
  const renderVisualization = (type: string, data: VisualizationData) => {
    switch (type) {
      case 'rule_network':
        renderNetworkChart(data);
        break;
      case 'pattern_timeline':
        renderTimelineChart(data);
        break;
      case 'insight_dashboard':
        renderDashboardChart(data);
        break;
    }
  };

  // 渲染规则网络图
  const renderNetworkChart = (data: VisualizationData) => {
    if (!networkChartRef.current) return;

    if (networkChart.current) {
      networkChart.current.dispose();
    }

    networkChart.current = echarts.init(networkChartRef.current);

    const option = {
      title: {
        text: t('visualization.ruleNetworkTitle'),
        left: 'center',
      },
      tooltip: {
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `${t('visualization.rule')}: ${params.data.name}<br/>${t('visualization.type')}: ${params.data.type}<br/>${t('visualization.confidence')}: ${(params.data.confidence * 100).toFixed(1)}%`;
          } else {
            return `${t('visualization.linkStrength')}: ${(params.data.strength * 100).toFixed(1)}%`;
          }
        },
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: data.chart_data.nodes?.map((node: any) => ({
            ...node,
            symbolSize: Math.max(20, node.confidence * 50),
            itemStyle: {
              color: getNodeColor(node.type),
            },
          })) || [],
          links: data.chart_data.links?.map((link: any) => ({
            ...link,
            lineStyle: {
              width: Math.max(1, link.strength * 5),
              opacity: 0.6,
            },
          })) || [],
          roam: true,
          force: {
            repulsion: 1000,
            edgeLength: 100,
          },
          label: {
            show: true,
            position: 'right',
            formatter: '{b}',
          },
        },
      ],
    };

    networkChart.current.setOption(option);
  };

  // 渲染时间线图
  const renderTimelineChart = (data: VisualizationData) => {
    if (!timelineChartRef.current) return;

    if (timelineChart.current) {
      timelineChart.current.dispose();
    }

    timelineChart.current = echarts.init(timelineChartRef.current);

    const timeline = data.chart_data.timeline || [];
    const dates = timeline.map((item: any) => item.date);
    const patternCounts = timeline.map((item: any) => item.pattern_count);
    const avgStrengths = timeline.map((item: any) => item.avg_strength * 100);

    const option = {
      title: {
        text: t('visualization.patternTimelineTitle'),
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: [t('visualization.patternCount'), t('visualization.avgStrength')],
        top: 30,
      },
      xAxis: {
        type: 'category',
        data: dates,
      },
      yAxis: [
        {
          type: 'value',
          name: t('visualization.patternCount'),
          position: 'left',
        },
        {
          type: 'value',
          name: t('visualization.avgStrengthPercent'),
          position: 'right',
        },
      ],
      series: [
        {
          name: t('visualization.patternCount'),
          type: 'line',
          data: patternCounts,
          smooth: true,
          itemStyle: {
            color: '#1890ff',
          },
        },
        {
          name: t('visualization.avgStrength'),
          type: 'line',
          yAxisIndex: 1,
          data: avgStrengths,
          smooth: true,
          itemStyle: {
            color: '#52c41a',
          },
        },
      ],
    };

    timelineChart.current.setOption(option);
  };

  // 渲染仪表板图表
  const renderDashboardChart = (data: VisualizationData) => {
    if (!dashboardChartRef.current) return;

    if (dashboardChart.current) {
      dashboardChart.current.dispose();
    }

    dashboardChart.current = echarts.init(dashboardChartRef.current);

    const ruleDistribution = data.chart_data.rule_distribution || [];
    const confidenceDistribution = data.chart_data.confidence_distribution || [];

    const option = {
      title: [
        {
          text: t('visualization.ruleTypeDistribution'),
          left: '25%',
          top: '10%',
          textAlign: 'center',
        },
        {
          text: t('visualization.confidenceDistribution'),
          left: '75%',
          top: '10%',
          textAlign: 'center',
        },
      ],
      series: [
        {
          type: 'pie',
          radius: ['20%', '40%'],
          center: ['25%', '60%'],
          data: ruleDistribution.map((item: any) => ({
            name: getRuleTypeName(item.type),
            value: item.count,
          })),
          label: {
            show: true,
            formatter: '{b}: {c}',
          },
        },
        {
          type: 'pie',
          radius: ['20%', '40%'],
          center: ['75%', '60%'],
          data: confidenceDistribution.map((item: any) => ({
            name: item.range,
            value: item.count,
          })),
          label: {
            show: true,
            formatter: '{b}: {c}',
          },
        },
      ],
    };

    dashboardChart.current.setOption(option);
  };

  // 获取节点颜色
  const getNodeColor = (type: string) => {
    const colorMap: Record<string, string> = {
      sentiment_rule: '#1890ff',
      keyword_rule: '#52c41a',
      temporal_rule: '#faad14',
      behavioral_rule: '#722ed1',
    };
    return colorMap[type] || '#d9d9d9';
  };

  // 获取规则类型名称
  const getRuleTypeName = (type: string) => {
    const typeKeyMap: Record<string, string> = {
      sentiment_rule: 'rules.types.sentimentRule',
      keyword_rule: 'rules.types.keywordRule',
      temporal_rule: 'rules.types.temporalRule',
      behavioral_rule: 'rules.types.behavioralRule',
    };
    return typeKeyMap[type] ? t(typeKeyMap[type]) : type;
  };

  // 处理窗口大小变化
  useEffect(() => {
    const handleResize = () => {
      networkChart.current?.resize();
      timelineChart.current?.resize();
      dashboardChart.current?.resize();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 初始化时生成默认可视化
  useEffect(() => {
    if (projectId) {
      generateVisualization(visualizationType);
    }
  }, [projectId]);

  // 可视化类型变化时重新生成
  useEffect(() => {
    if (projectId && visualizationType) {
      generateVisualization(visualizationType);
    }
  }, [visualizationType]);

  return (
    <div>
      {/* 控制面板 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Text strong>{t('visualization.visualizationType')}:</Text>
              <Select
                value={visualizationType}
                onChange={setVisualizationType}
                style={{ width: 200 }}
              >
                <Option value="rule_network">
                  <NodeIndexOutlined /> {t('visualization.ruleNetwork')}
                </Option>
                <Option value="pattern_timeline">
                  <LineChartOutlined /> {t('visualization.patternTimeline')}
                </Option>
                <Option value="insight_dashboard">
                  <PieChartOutlined /> {t('visualization.insightDashboard')}
                </Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<BarChartOutlined />}
                onClick={() => generateVisualization(visualizationType)}
                loading={loading}
              >
                {t('visualization.refreshChart')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 可视化内容 */}
      <Spin spinning={loading}>
        {visualizationType === 'rule_network' && (
          <Card title={t('visualization.ruleNetworkTitle')} style={{ height: 600 }}>
            <div
              ref={networkChartRef}
              style={{ width: '100%', height: 500 }}
            />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                {t('visualization.ruleNetworkHint')}
              </Text>
            </div>
          </Card>
        )}

        {visualizationType === 'pattern_timeline' && (
          <Card title={t('visualization.patternTimelineTitle')} style={{ height: 600 }}>
            <div
              ref={timelineChartRef}
              style={{ width: '100%', height: 500 }}
            />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                {t('visualization.patternTimelineHint')}
              </Text>
            </div>
          </Card>
        )}

        {visualizationType === 'insight_dashboard' && (
          <Card title={t('visualization.insightDashboardTitle')} style={{ height: 600 }}>
            <div
              ref={dashboardChartRef}
              style={{ width: '100%', height: 500 }}
            />
            <div style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Text type="secondary">
                    {t('visualization.leftChartHint')}
                  </Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">
                    {t('visualization.rightChartHint')}
                  </Text>
                </Col>
              </Row>
            </div>
          </Card>
        )}
      </Spin>

      {/* 图表说明 */}
      <Card title={t('visualization.chartGuide')} style={{ marginTop: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <div>
              <Title level={5}>
                <NodeIndexOutlined /> {t('visualization.ruleNetwork')}
              </Title>
              <Text type="secondary">
                {t('visualization.ruleNetworkDesc')}
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <div>
              <Title level={5}>
                <LineChartOutlined /> {t('visualization.patternTimeline')}
              </Title>
              <Text type="secondary">
                {t('visualization.patternTimelineDesc')}
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <div>
              <Title level={5}>
                <PieChartOutlined /> {t('visualization.insightDashboard')}
              </Title>
              <Text type="secondary">
                {t('visualization.insightDashboardDesc')}
              </Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};