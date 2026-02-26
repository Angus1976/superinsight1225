import React, { useState, useMemo, useCallback } from 'react';
import {
  Card, Row, Col, Select, Tree, Table, Tabs, Spin, Empty,
  InputNumber, Space, Typography,
} from 'antd';
import {
  TableOutlined, DatabaseOutlined, FolderOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  useDatalakeSources,
  useDatalakeDatabases,
  useDatalakeTables,
} from '@/hooks/useDatalake';
import { datalakeApi } from '@/services/datalakeApi';
import type { ColumnInfo, TableInfo } from '@/types/datalake';
import type { DataNode } from 'antd/es/tree';

const { Title } = Typography;

const DEFAULT_PREVIEW_LIMIT = 100;
const MAX_PREVIEW_LIMIT = 1000;

// ============================================================================
// Tree data helpers
// ============================================================================

/** Build tree nodes from databases list */
function buildDatabaseNodes(databases: string[]): DataNode[] {
  return databases.map((db) => ({
    key: `db:${db}`,
    title: db,
    icon: <DatabaseOutlined />,
    children: [],
    isLeaf: false,
  }));
}

/** Build table child nodes for a database */
function buildTableNodes(database: string, tables: TableInfo[]): DataNode[] {
  return tables.map((t) => ({
    key: `table:${database}:${t.name}`,
    title: t.name,
    icon: <TableOutlined />,
    isLeaf: true,
  }));
}

/** Parse selected tree key into database + table */
function parseTableKey(key: string): { database: string; table: string } | null {
  if (!key.startsWith('table:')) return null;
  const parts = key.split(':');
  if (parts.length < 3) return null;
  return { database: parts[1], table: parts.slice(2).join(':') };
}

// ============================================================================
// StructureTab - shows column info
// ============================================================================

interface StructureTabProps {
  sourceId: string;
  database: string;
  table: string;
}

const STRUCTURE_COLUMNS = (t: (key: string, fallback: string) => string) => [
  {
    title: t('datalake.schemaBrowser.columnName', '列名'),
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: t('datalake.schemaBrowser.columnType', '类型'),
    dataIndex: 'type',
    key: 'type',
  },
  {
    title: t('datalake.schemaBrowser.columnComment', '注释'),
    dataIndex: 'comment',
    key: 'comment',
    render: (val: string | undefined) => val || '-',
  },
];

const StructureTab: React.FC<StructureTabProps> = ({ sourceId, database, table }) => {
  const { t } = useTranslation(['dataSync']);

  const { data, isLoading } = useQuery({
    queryKey: ['datalake', 'schema', sourceId, database, table],
    queryFn: () => datalakeApi.getTableSchema(sourceId, database, table),
    enabled: !!sourceId && !!database && !!table,
  });

  if (isLoading) return <Spin />;
  if (!data?.columns?.length) return <Empty description={t('datalake.schemaBrowser.noColumns', '暂无列信息')} />;

  return (
    <Table<ColumnInfo>
      rowKey="name"
      columns={STRUCTURE_COLUMNS(t)}
      dataSource={data.columns}
      pagination={false}
      size="small"
    />
  );
};

// ============================================================================
// PreviewTab - shows data preview
// ============================================================================

interface PreviewTabProps {
  sourceId: string;
  database: string;
  table: string;
}

const PreviewTab: React.FC<PreviewTabProps> = ({ sourceId, database, table }) => {
  const { t } = useTranslation(['dataSync']);
  const [limit, setLimit] = useState(DEFAULT_PREVIEW_LIMIT);

  const { data, isLoading } = useQuery({
    queryKey: ['datalake', 'preview', sourceId, database, table, limit],
    queryFn: () => datalakeApi.getTablePreview(sourceId, database, table, limit),
    enabled: !!sourceId && !!database && !!table,
  });

  const columns = useMemo(() => {
    if (!data?.columns?.length) return [];
    return data.columns.map((col) => ({
      title: col,
      dataIndex: col,
      key: col,
      ellipsis: true,
      width: 150,
    }));
  }, [data?.columns]);

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <span>{t('datalake.schemaBrowser.rowLimit', '行数限制')}:</span>
        <InputNumber
          min={1}
          max={MAX_PREVIEW_LIMIT}
          value={limit}
          onChange={(val) => val && setLimit(val)}
          style={{ width: 100 }}
        />
      </Space>
      {isLoading ? (
        <Spin />
      ) : !data?.rows?.length ? (
        <Empty description={t('datalake.schemaBrowser.noData', '暂无数据')} />
      ) : (
        <Table
          rowKey={(_, idx) => String(idx)}
          columns={columns}
          dataSource={data.rows}
          pagination={{ pageSize: 50, showSizeChanger: true }}
          scroll={{ x: 'max-content' }}
          size="small"
        />
      )}
    </div>
  );
};

// ============================================================================
// SchemaBrowser - Main component
// ============================================================================

const SchemaBrowser: React.FC = () => {
  const { t } = useTranslation(['dataSync']);

  const [sourceId, setSourceId] = useState<string>('');
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [selectedTable, setSelectedTable] = useState<{ database: string; table: string } | null>(null);
  const [loadedDbs, setLoadedDbs] = useState<Set<string>>(new Set());
  const [treeData, setTreeData] = useState<DataNode[]>([]);

  const { data: sources, isLoading: sourcesLoading } = useDatalakeSources();
  const { data: databases, isLoading: dbLoading } = useDatalakeDatabases(sourceId, { enabled: !!sourceId });

  // Sync databases into tree when they load
  React.useEffect(() => {
    if (!databases?.length) {
      setTreeData([]);
      return;
    }
    setTreeData(buildDatabaseNodes(databases));
    setLoadedDbs(new Set());
    setSelectedTable(null);
    setExpandedKeys([]);
  }, [databases]);

  // Reset state when source changes
  const handleSourceChange = useCallback((value: string) => {
    setSourceId(value);
    setSelectedTable(null);
    setTreeData([]);
    setExpandedKeys([]);
    setLoadedDbs(new Set());
  }, []);

  // Load tables on expand
  const handleLoadData = useCallback(
    async (node: DataNode) => {
      const key = String(node.key);
      if (!key.startsWith('db:')) return;

      const database = key.slice(3);
      if (loadedDbs.has(database)) return;

      const tables = (await datalakeApi.getTables(sourceId, database)) as TableInfo[];
      const childNodes = buildTableNodes(database, tables);

      setTreeData((prev) =>
        prev.map((dbNode) =>
          dbNode.key === key ? { ...dbNode, children: childNodes } : dbNode,
        ),
      );
      setLoadedDbs((prev) => new Set(prev).add(database));
    },
    [sourceId, loadedDbs],
  );

  const handleSelect = useCallback((_: React.Key[], info: { node: DataNode }) => {
    const parsed = parseTableKey(String(info.node.key));
    setSelectedTable(parsed);
  }, []);

  const sourceOptions = useMemo(
    () => (sources ?? []).map((s) => ({ label: s.name, value: s.id })),
    [sources],
  );

  const tabItems = useMemo(() => {
    if (!selectedTable || !sourceId) return [];
    const { database, table } = selectedTable;
    return [
      {
        key: 'structure',
        label: t('datalake.schemaBrowser.structure', '表结构'),
        children: <StructureTab sourceId={sourceId} database={database} table={table} />,
      },
      {
        key: 'preview',
        label: t('datalake.schemaBrowser.preview', '数据预览'),
        children: <PreviewTab sourceId={sourceId} database={database} table={table} />,
      },
    ];
  }, [selectedTable, sourceId, t]);

  return (
    <Card>
      <Title level={4} style={{ marginBottom: 16 }}>
        <TableOutlined style={{ marginRight: 8 }} />
        {t('datalake.schemaBrowser.title', 'Schema 浏览器')}
      </Title>

      <Row gutter={16} style={{ minHeight: 400 }}>
        {/* Left panel: source selector + database/table tree */}
        <Col span={7}>
          <Select
            showSearch
            allowClear
            placeholder={t('datalake.schemaBrowser.selectSource', '选择数据源')}
            loading={sourcesLoading}
            options={sourceOptions}
            value={sourceId || undefined}
            onChange={handleSourceChange}
            style={{ width: '100%', marginBottom: 12 }}
            filterOption={(input, option) =>
              String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          />

          {dbLoading ? (
            <Spin style={{ display: 'block', marginTop: 24, textAlign: 'center' }} />
          ) : !sourceId ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t('datalake.schemaBrowser.selectSourceHint', '请先选择数据源')}
            />
          ) : !treeData.length ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={t('datalake.schemaBrowser.noDatabases', '暂无数据库')}
            />
          ) : (
            <Tree
              showIcon
              treeData={treeData}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys)}
              loadData={handleLoadData}
              onSelect={handleSelect}
              blockNode
              style={{ overflowY: 'auto', maxHeight: 500 }}
            />
          )}
        </Col>

        {/* Right panel: structure / preview tabs */}
        <Col span={17}>
          {selectedTable ? (
            <Tabs items={tabItems} defaultActiveKey="structure" />
          ) : (
            <Empty
              style={{ marginTop: 80 }}
              description={t('datalake.schemaBrowser.selectTable', '请选择一个表查看详情')}
            />
          )}
        </Col>
      </Row>
    </Card>
  );
};

export default SchemaBrowser;
