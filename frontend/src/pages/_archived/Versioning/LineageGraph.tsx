/**
 * Lineage Graph Component
 * 
 * Interactive visualization of data lineage:
 * - Graph visualization using AntV G6
 * - Upstream/downstream navigation
 * - Path highlighting
 * - Export functionality
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Space,
  Button,
  Select,
  InputNumber,
  Spin,
  Empty,
  message,
  Tooltip,
  Tag,
  Drawer,
  Descriptions,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  FullscreenOutlined,
  DownloadOutlined,
  NodeIndexOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { lineageApi, LineageGraph as LineageGraphType, LineageNode } from '../../services/lineageApi';

const { Text, Title } = Typography;
const { Option } = Select;

interface LineageGraphProps {
  entityType: string;
  entityId: string;
  tenantId?: string;
  onNodeClick?: (node: LineageNode) => void;
}

const LineageGraph: React.FC<LineageGraphProps> = ({
  entityType,
  entityId,
  tenantId,
  onNodeClick,
}) => {
  const { t } = useTranslation(['lineage', 'common']);
  const containerRef = useRef<HTMLDivElement>(null);
  const [lineageData, setLineageData] = useState<LineageGraphType | null>(null);
  const [loading, setLoading] = useState(false);
  const [direction, setDirection] = useState<'full' | 'upstream' | 'downstream'>('full');
  const [depth, setDepth] = useState(3);
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);

  useEffect(() => {
    loadLineage();
  }, [entityType, entityId, tenantId, direction, depth]);

  const loadLineage = async () => {
    setLoading(true);
    try {
      let result;
      switch (direction) {
        case 'upstream':
          result = await lineageApi.getUpstream(entityType, entityId, depth, tenantId);
          break;
        case 'downstream':
          result = await lineageApi.getDownstream(entityType, entityId, depth, tenantId);
          break;
        default:
          result = await lineageApi.getFullLineage(entityType, entityId, depth, depth, tenantId);
      }
      setLineageData(result.lineage);
    } catch (error) {
      message.error(t('loadError', 'Failed to load lineage data'));
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (node: LineageNode) => {
    setSelectedNode(node);
    setDrawerVisible(true);
    onNodeClick?.(node);
  };

  const handleExport = () => {
    if (!lineageData) return;
    
    const dataStr = JSON.stringify(lineageData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lineage_${entityType}_${entityId}.json`;
    link.click();
    URL.revokeObjectURL(url);
    message.success(t('exported', 'Lineage data exported'));
  };

  const getNodeColor = (node: LineageNode) => {
    const isRoot = node.entity_type === entityType && node.entity_id === entityId;
    if (isRoot) return '#1890ff';
    
    const depth = node.metadata?.depth as number || 0;
    const colors = ['#52c41a', '#faad14', '#ff7a45', '#ff4d4f'];
    return colors[Math.min(depth, colors.length - 1)];
  };

  const renderSimpleGraph = () => {
    if (!lineageData || lineageData.nodes.length === 0) {
      return <Empty description={t('noData', 'No lineage data')} />;
    }

    // Simple list-based visualization (can be replaced with G6 or other graph library)
    return (
      <div style={{ padding: 16 }}>
        <Title level={5}>
          {t('nodes', 'Nodes')} ({lineageData.node_count})
        </Title>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 24 }}>
          {lineageData.nodes.map((node, index) => {
            const isRoot = node.entity_type === entityType && node.entity_id === entityId;
            return (
              <Tag
                key={`${node.entity_type}-${node.entity_id}-${index}`}
                color={getNodeColor(node)}
                style={{ cursor: 'pointer', padding: '4px 8px' }}
                onClick={() => handleNodeClick(node)}
              >
                <Space>
                  <NodeIndexOutlined />
                  <span>
                    {node.name || `${node.entity_type}:${node.entity_id.slice(0, 8)}`}
                  </span>
                  {isRoot && <Tag color="blue">ROOT</Tag>}
                </Space>
              </Tag>
            );
          })}
        </div>

        <Title level={5}>
          {t('edges', 'Relationships')} ({lineageData.edge_count})
        </Title>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lineageData.edges.map((edge, index) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: 8,
                background: '#fafafa',
                borderRadius: 4,
              }}
            >
              <Tag color="blue">
                {edge.source_type}:{edge.source_id.slice(0, 8)}
              </Tag>
              <span>→</span>
              <Tag color="green">{edge.relationship}</Tag>
              <span>→</span>
              <Tag color="orange">
                {edge.target_type}:{edge.target_id.slice(0, 8)}
              </Tag>
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card
        title={
          <Space>
            <ApartmentOutlined />
            <span>{t('graph', 'Lineage Graph')}</span>
          </Space>
        }
        extra={
          <Space>
            <Select
              value={direction}
              onChange={setDirection}
              style={{ width: 120 }}
            >
              <Option value="full">
                <Space>
                  <ApartmentOutlined />
                  {t('full', 'Full')}
                </Space>
              </Option>
              <Option value="upstream">
                <Space>
                  <ArrowUpOutlined />
                  {t('upstream', 'Upstream')}
                </Space>
              </Option>
              <Option value="downstream">
                <Space>
                  <ArrowDownOutlined />
                  {t('downstream', 'Downstream')}
                </Space>
              </Option>
            </Select>
            
            <InputNumber
              min={1}
              max={10}
              value={depth}
              onChange={(v) => setDepth(v || 3)}
              addonBefore={t('depth', 'Depth')}
              style={{ width: 120 }}
            />
            
            <Tooltip title={t('export', 'Export')}>
              <Button icon={<DownloadOutlined />} onClick={handleExport} />
            </Tooltip>
          </Space>
        }
      >
        <div
          ref={containerRef}
          style={{ minHeight: 400, border: '1px solid #f0f0f0', borderRadius: 4 }}
        >
          {renderSimpleGraph()}
        </div>
      </Card>

      <Drawer
        title={t('nodeDetails', 'Node Details')}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={400}
      >
        {selectedNode && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('entityType', 'Entity Type')}>
              <Tag>{selectedNode.entity_type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('entityId', 'Entity ID')}>
              <Text copyable>{selectedNode.entity_id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label={t('name', 'Name')}>
              {selectedNode.name || '-'}
            </Descriptions.Item>
            {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
              <Descriptions.Item label={t('metadata', 'Metadata')}>
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedNode.metadata, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Drawer>
    </>
  );
};

export default LineageGraph;
