// Knowledge graph visualization component
import { Card, Row, Col, Select, Button, Space, Tooltip, Badge, Drawer } from 'antd';
import {
  FullscreenOutlined,
  ReloadOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3';

const { Option } = Select;

interface GraphNode {
  id: string;
  name: string;
  type: 'entity' | 'process' | 'data' | 'system';
  category: string;
  size: number;
  color: string;
  description?: string;
  properties?: Record<string, any>;
}

interface GraphLink {
  source: string;
  target: string;
  type: 'dataFlow' | 'dependency' | 'inheritance' | 'association';
  label: string;
  strength: number;
  color: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface KnowledgeGraphProps {
  data?: GraphData;
  loading?: boolean;
  height?: number;
  interactive?: boolean;
}

export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  data,
  loading = false,
  height = 600,
  interactive = true,
}) => {
  const { t } = useTranslation('dashboard');
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [graphType, setGraphType] = useState<'force' | 'hierarchy' | 'circular'>('force');
  const [filterType, setFilterType] = useState<string>('all');

  // Mock data for demonstration
  const mockData: GraphData = {
    nodes: [
      // Data entities
      { id: 'corpus', name: '语料库', type: 'data', category: 'data', size: 20, color: '#1890ff', description: '标注语料数据集' },
      { id: 'annotations', name: '标注数据', type: 'data', category: 'data', size: 18, color: '#52c41a', description: '用户标注结果' },
      { id: 'models', name: 'AI模型', type: 'system', category: 'ai', size: 16, color: '#722ed1', description: '机器学习模型' },
      
      // Business processes
      { id: 'annotation_process', name: '标注流程', type: 'process', category: 'business', size: 15, color: '#faad14', description: '数据标注业务流程' },
      { id: 'quality_control', name: '质量控制', type: 'process', category: 'business', size: 14, color: '#fa8c16', description: '质量管理流程' },
      { id: 'billing_process', name: '计费流程', type: 'process', category: 'business', size: 12, color: '#eb2f96', description: '账单结算流程' },
      
      // System entities
      { id: 'label_studio', name: 'Label Studio', type: 'system', category: 'platform', size: 18, color: '#13c2c2', description: '标注平台' },
      { id: 'database', name: '数据库', type: 'system', category: 'infrastructure', size: 16, color: '#096dd9', description: 'PostgreSQL数据库' },
      { id: 'api_gateway', name: 'API网关', type: 'system', category: 'infrastructure', size: 14, color: '#389e0d', description: 'FastAPI服务' },
      
      // Users and roles
      { id: 'annotators', name: '标注员', type: 'entity', category: 'user', size: 12, color: '#f759ab', description: '数据标注人员' },
      { id: 'reviewers', name: '审核员', type: 'entity', category: 'user', size: 10, color: '#ff85c0', description: '质量审核人员' },
      { id: 'admins', name: '管理员', type: 'entity', category: 'user', size: 8, color: '#ffc069', description: '系统管理员' },
    ],
    links: [
      // Data flow relationships
      { source: 'corpus', target: 'annotation_process', type: 'dataFlow', label: '输入', strength: 1, color: '#1890ff' },
      { source: 'annotation_process', target: 'annotations', type: 'dataFlow', label: '产出', strength: 1, color: '#52c41a' },
      { source: 'annotations', target: 'quality_control', type: 'dataFlow', label: '检查', strength: 0.8, color: '#faad14' },
      { source: 'annotations', target: 'models', type: 'dataFlow', label: '训练', strength: 0.9, color: '#722ed1' },
      
      // System dependencies
      { source: 'annotation_process', target: 'label_studio', type: 'dependency', label: '使用', strength: 1, color: '#13c2c2' },
      { source: 'label_studio', target: 'database', type: 'dependency', label: '存储', strength: 1, color: '#096dd9' },
      { source: 'api_gateway', target: 'database', type: 'dependency', label: '访问', strength: 0.8, color: '#389e0d' },
      
      // User associations
      { source: 'annotators', target: 'annotation_process', type: 'association', label: '执行', strength: 1, color: '#f759ab' },
      { source: 'reviewers', target: 'quality_control', type: 'association', label: '负责', strength: 1, color: '#ff85c0' },
      { source: 'admins', target: 'api_gateway', type: 'association', label: '管理', strength: 0.7, color: '#ffc069' },
      
      // Business process flows
      { source: 'quality_control', target: 'billing_process', type: 'dataFlow', label: '触发', strength: 0.6, color: '#eb2f96' },
    ],
  };

  const graphData = data || mockData;

  // Filter data based on selected type
  const filteredData = {
    nodes: filterType === 'all' ? graphData.nodes : graphData.nodes.filter(node => node.category === filterType),
    links: graphData.links.filter(link => {
      if (filterType === 'all') return true;
      const sourceNode = graphData.nodes.find(n => n.id === link.source);
      const targetNode = graphData.nodes.find(n => n.id === link.target);
      return sourceNode?.category === filterType || targetNode?.category === filterType;
    }),
  };

  useEffect(() => {
    if (!svgRef.current || loading) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create main group for zoom/pan
    const g = svg.append('g');

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Create simulation based on graph type
    let simulation: d3.Simulation<d3.SimulationNodeDatum, d3.SimulationLinkDatum<d3.SimulationNodeDatum>>;

    if (graphType === 'force') {
      simulation = d3.forceSimulation(filteredData.nodes as any)
        .force('link', d3.forceLink(filteredData.links as any).id((d: any) => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius((d: any) => d.size + 5));
    } else if (graphType === 'hierarchy') {
      // Create hierarchical layout
      const root = d3.hierarchy({ children: filteredData.nodes } as any);
      const treeLayout = d3.tree<GraphNode>().size([width - 100, height - 100]);
      treeLayout(root);
      
      // Position nodes based on hierarchy
      filteredData.nodes.forEach((node, i) => {
        const treeNode = root.descendants()[i + 1];
        if (treeNode && treeNode.x !== undefined && treeNode.y !== undefined) {
          (node as any).x = treeNode.x + 50;
          (node as any).y = treeNode.y + 50;
        }
      });

      simulation = d3.forceSimulation(filteredData.nodes as any)
        .force('link', d3.forceLink(filteredData.links as any).id((d: any) => d.id).distance(80))
        .alphaDecay(0.1);
    } else {
      // Circular layout
      const radius = Math.min(width, height) / 3;
      filteredData.nodes.forEach((node, i) => {
        const angle = (i / filteredData.nodes.length) * 2 * Math.PI;
        (node as any).x = width / 2 + radius * Math.cos(angle);
        (node as any).y = height / 2 + radius * Math.sin(angle);
      });

      simulation = d3.forceSimulation(filteredData.nodes as any)
        .force('link', d3.forceLink(filteredData.links as any).id((d: any) => d.id).distance(60))
        .alphaDecay(0.1);
    }

    // Create arrow markers for directed edges
    svg.append('defs').selectAll('marker')
      .data(['dataFlow', 'dependency', 'inheritance', 'association'])
      .enter().append('marker')
      .attr('id', d => `arrow-${d}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 15)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // Create links
    const link = g.append('g')
      .selectAll('line')
      .data(filteredData.links)
      .enter().append('line')
      .attr('stroke', d => d.color)
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.sqrt(d.strength * 3))
      .attr('marker-end', d => `url(#arrow-${d.type})`);

    // Create link labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(filteredData.links)
      .enter().append('text')
      .attr('font-size', '10px')
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .text(d => d.label);

    // Create nodes
    const node = g.append('g')
      .selectAll('circle')
      .data(filteredData.nodes)
      .enter().append('circle')
      .attr('r', d => d.size)
      .attr('fill', d => d.color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', interactive ? 'pointer' : 'default');

    // Create node labels
    const nodeLabel = g.append('g')
      .selectAll('text')
      .data(filteredData.nodes)
      .enter().append('text')
      .attr('font-size', '12px')
      .attr('fill', '#333')
      .attr('text-anchor', 'middle')
      .attr('dy', d => d.size + 15)
      .text(d => d.name)
      .style('pointer-events', 'none');

    // Add interactivity
    if (interactive) {
      node
        .on('click', (_event, d) => {
          setSelectedNode(d);
          setDrawerVisible(true);
        })
        .on('mouseover', function(_event, d) {
          d3.select(this).attr('stroke-width', 4);
          // Highlight connected links
          link.attr('stroke-opacity', l => 
            l.source === d.id || l.target === d.id ? 1 : 0.1
          );
        })
        .on('mouseout', function() {
          d3.select(this).attr('stroke-width', 2);
          link.attr('stroke-opacity', 0.6);
        });

      // Add drag behavior for force layout
      if (graphType === 'force') {
        node.call(d3.drag<SVGCircleElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            (d as any).fx = (d as any).x;
            (d as any).fy = (d as any).y;
          })
          .on('drag', (event, d) => {
            (d as any).fx = event.x;
            (d as any).fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            (d as any).fx = null;
            (d as any).fy = null;
          })
        );
      }
    }

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      linkLabel
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);

      node
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      nodeLabel
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });

    return () => {
      simulation.stop();
    };
  }, [filteredData, graphType, loading, interactive]);

  const handleFullscreen = () => {
    if (svgRef.current) {
      svgRef.current.requestFullscreen?.();
    }
  };

  const handleRefresh = () => {
    // Trigger re-render by updating a state
    setGraphType(graphType);
  };

  const getNodeTypeIcon = (type: string) => {
    switch (type) {
      case 'entity':
        return <InfoCircleOutlined />;
      case 'process':
        return <ApartmentOutlined />;
      case 'data':
        return <NodeIndexOutlined />;
      case 'system':
        return <SettingOutlined />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const categoryOptions = [
    { value: 'all', label: t('graph.allCategories') },
    { value: 'data', label: t('graph.dataCategory') },
    { value: 'business', label: t('graph.businessCategory') },
    { value: 'ai', label: t('graph.aiCategory') },
    { value: 'platform', label: t('graph.platformCategory') },
    { value: 'infrastructure', label: t('graph.infrastructureCategory') },
    { value: 'user', label: t('graph.userCategory') },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <NodeIndexOutlined />
            {t('charts.knowledgeGraph')}
            <Badge count={filteredData.nodes.length} showZero color="#1890ff" />
          </Space>
        }
        extra={
          <Space>
            <Select
              value={graphType}
              onChange={setGraphType}
              style={{ width: 120 }}
            >
              <Option value="force">{t('graph.forceLayout')}</Option>
              <Option value="hierarchy">{t('graph.hierarchyLayout')}</Option>
              <Option value="circular">{t('graph.circularLayout')}</Option>
            </Select>
            <Select
              value={filterType}
              onChange={setFilterType}
              style={{ width: 140 }}
            >
              {categoryOptions.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
            <Tooltip title={t('common.refresh')}>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh} />
            </Tooltip>
            <Tooltip title={t('common.fullscreen')}>
              <Button icon={<FullscreenOutlined />} onClick={handleFullscreen} />
            </Tooltip>
          </Space>
        }
        loading={loading}
      >
        <div style={{ position: 'relative', width: '100%', height }}>
          <svg
            ref={svgRef}
            width="100%"
            height="100%"
            style={{ border: '1px solid #f0f0f0', borderRadius: '6px' }}
          />
          
          {/* Legend */}
          <div
            style={{
              position: 'absolute',
              top: 10,
              right: 10,
              background: 'rgba(255, 255, 255, 0.9)',
              padding: '12px',
              borderRadius: '6px',
              border: '1px solid #d9d9d9',
              fontSize: '12px',
            }}
          >
            <div style={{ fontWeight: 'bold', marginBottom: 8 }}>{t('graph.legend')}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#1890ff', borderRadius: '50%' }} />
                <span>{t('graph.dataNodes')}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#faad14', borderRadius: '50%' }} />
                <span>{t('graph.processNodes')}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#722ed1', borderRadius: '50%' }} />
                <span>{t('graph.systemNodes')}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#f759ab', borderRadius: '50%' }} />
                <span>{t('graph.userNodes')}</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Node Details Drawer */}
      <Drawer
        title={
          <Space>
            {selectedNode && getNodeTypeIcon(selectedNode.type)}
            {selectedNode?.name}
          </Space>
        }
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={400}
      >
        {selectedNode && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Card size="small" title={t('graph.nodeDetails')}>
                  <p><strong>{t('graph.nodeType')}:</strong> {selectedNode.type}</p>
                  <p><strong>{t('graph.nodeCategory')}:</strong> {selectedNode.category}</p>
                  <p><strong>{t('graph.nodeSize')}:</strong> {selectedNode.size}</p>
                  {selectedNode.description && (
                    <p><strong>{t('graph.nodeDescription')}:</strong> {selectedNode.description}</p>
                  )}
                </Card>
              </Col>
              
              {selectedNode.properties && (
                <Col span={24}>
                  <Card size="small" title={t('graph.nodeProperties')}>
                    {Object.entries(selectedNode.properties).map(([key, value]) => (
                      <p key={key}>
                        <strong>{key}:</strong> {String(value)}
                      </p>
                    ))}
                  </Card>
                </Col>
              )}

              <Col span={24}>
                <Card size="small" title={t('graph.connectedNodes')}>
                  {graphData.links
                    .filter(link => link.source === selectedNode.id || link.target === selectedNode.id)
                    .map((link, index) => {
                      const connectedNodeId = link.source === selectedNode.id ? link.target : link.source;
                      const connectedNode = graphData.nodes.find(n => n.id === connectedNodeId);
                      return (
                        <div key={index} style={{ marginBottom: 8 }}>
                          <Space>
                            <div
                              style={{
                                width: 12,
                                height: 12,
                                backgroundColor: connectedNode?.color,
                                borderRadius: '50%',
                              }}
                            />
                            <span>{connectedNode?.name}</span>
                            <span style={{ color: '#999', fontSize: '12px' }}>
                              ({link.label})
                            </span>
                          </Space>
                        </div>
                      );
                    })}
                </Card>
              </Col>
            </Row>
          </div>
        )}
      </Drawer>
    </div>
  );
};