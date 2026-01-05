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
        throw new Error('生成可视化失败');
      }
    } catch (error) {
      console.error('生成可视化失败:', error);
      message.error('生成可视化失败');
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
        text: '业务规则关系网络',
        left: 'center',
      },
      tooltip: {
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `规则: ${params.data.name}<br/>类型: ${params.data.type}<br/>置信度: ${(params.data.confidence * 100).toFixed(1)}%`;
          } else {
            return `关联强度: ${(params.data.strength * 100).toFixed(1)}%`;
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
        text: '业务模式时间趋势',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: ['模式数量', '平均强度'],
        top: 30,
      },
      xAxis: {
        type: 'category',
        data: dates,
      },
      yAxis: [
        {
          type: 'value',
          name: '模式数量',
          position: 'left',
        },
        {
          type: 'value',
          name: '平均强度 (%)',
          position: 'right',
        },
      ],
      series: [
        {
          name: '模式数量',
          type: 'line',
          data: patternCounts,
          smooth: true,
          itemStyle: {
            color: '#1890ff',
          },
        },
        {
          name: '平均强度',
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
          text: '规则类型分布',
          left: '25%',
          top: '10%',
          textAlign: 'center',
        },
        {
          text: '置信度分布',
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
    const nameMap: Record<string, string> = {
      sentiment_rule: '情感规则',
      keyword_rule: '关键词规则',
      temporal_rule: '时间规则',
      behavioral_rule: '行为规则',
    };
    return nameMap[type] || type;
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
              <Text strong>可视化类型:</Text>
              <Select
                value={visualizationType}
                onChange={setVisualizationType}
                style={{ width: 200 }}
              >
                <Option value="rule_network">
                  <NodeIndexOutlined /> 规则网络图
                </Option>
                <Option value="pattern_timeline">
                  <LineChartOutlined /> 模式时间线
                </Option>
                <Option value="insight_dashboard">
                  <PieChartOutlined /> 洞察仪表板
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
                刷新图表
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 可视化内容 */}
      <Spin spinning={loading}>
        {visualizationType === 'rule_network' && (
          <Card title="业务规则关系网络" style={{ height: 600 }}>
            <div
              ref={networkChartRef}
              style={{ width: '100%', height: 500 }}
            />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                节点大小表示规则置信度，连线粗细表示规则间关联强度
              </Text>
            </div>
          </Card>
        )}

        {visualizationType === 'pattern_timeline' && (
          <Card title="业务模式时间趋势" style={{ height: 600 }}>
            <div
              ref={timelineChartRef}
              style={{ width: '100%', height: 500 }}
            />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                显示业务模式数量和平均强度随时间的变化趋势
              </Text>
            </div>
          </Card>
        )}

        {visualizationType === 'insight_dashboard' && (
          <Card title="业务洞察仪表板" style={{ height: 600 }}>
            <div
              ref={dashboardChartRef}
              style={{ width: '100%', height: 500 }}
            />
            <div style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Text type="secondary">
                    左图显示不同类型业务规则的分布情况
                  </Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">
                    右图显示规则置信度的分布情况
                  </Text>
                </Col>
              </Row>
            </div>
          </Card>
        )}
      </Spin>

      {/* 图表说明 */}
      <Card title="图表说明" style={{ marginTop: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <div>
              <Title level={5}>
                <NodeIndexOutlined /> 规则网络图
              </Title>
              <Text type="secondary">
                展示业务规则之间的关联关系，帮助理解规则间的依赖和影响。
                节点大小代表规则置信度，连线粗细代表关联强度。
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <div>
              <Title level={5}>
                <LineChartOutlined /> 模式时间线
              </Title>
              <Text type="secondary">
                显示业务模式随时间的变化趋势，包括模式数量和平均强度的变化。
                有助于识别业务发展的阶段性特征。
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <div>
              <Title level={5}>
                <PieChartOutlined /> 洞察仪表板
              </Title>
              <Text type="secondary">
                提供业务规则和模式的统计概览，包括类型分布、置信度分布等关键指标。
                便于快速了解整体情况。
              </Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};