/**
 * TypeScript type interfaces for Datalake/Warehouse integration.
 * Mirrors backend Pydantic schemas in src/sync/connectors/datalake/schemas.py
 */

// ============================================================================
// Enums
// ============================================================================

/** Datalake/warehouse data source types */
export enum DatalakeSourceType {
  HIVE = 'hive',
  CLICKHOUSE = 'clickhouse',
  DORIS = 'doris',
  SPARK_SQL = 'spark_sql',
  PRESTO_TRINO = 'presto_trino',
  DELTA_LAKE = 'delta_lake',
  ICEBERG = 'iceberg',
}

/** Data source status */
export enum DataSourceStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  TESTING = 'testing',
}

// ============================================================================
// Data Source CRUD
// ============================================================================

export interface DatalakeSourceCreate {
  name: string;
  description?: string;
  source_type: DatalakeSourceType;
  connection_config: Record<string, unknown>;
}

export interface DatalakeSourceUpdate {
  name?: string;
  description?: string;
  connection_config?: Record<string, unknown>;
}

export interface DatalakeSourceResponse {
  id: string;
  name: string;
  source_type: DatalakeSourceType;
  status: DataSourceStatus;
  health_check_status?: string | null;
  last_health_check?: string | null;
  created_at: string;
  connection_config: Record<string, unknown>;
}

export interface ConnectionTestResult {
  status: string; // 'connected' | 'error'
  latency_ms: number;
  error_message?: string | null;
}

// ============================================================================
// Dashboard
// ============================================================================

export interface SourceSummary {
  source_id: string;
  name: string;
  source_type: DatalakeSourceType;
  status: DataSourceStatus;
  health_check_status?: string | null;
}

export interface DashboardOverview {
  total_sources: number;
  active_sources: number;
  error_sources: number;
  total_data_volume_gb: number;
  avg_query_latency_ms: number;
  sources: SourceSummary[];
}

export interface SourceHealthStatus {
  source_id: string;
  source_name: string;
  source_type: DatalakeSourceType;
  status: string; // 'healthy' | 'degraded' | 'down'
  latency_ms: number;
  last_check: string;
  error_message?: string | null;
}

// ============================================================================
// Volume Trends
// ============================================================================

export interface VolumeDataPoint {
  timestamp: string;
  source_id: string;
  source_name: string;
  volume_gb: number;
  row_count: number;
}

export interface VolumeTrendData {
  period: string;
  data_points: VolumeDataPoint[];
}

// ============================================================================
// Query Performance
// ============================================================================

export interface SourceQueryStats {
  source_id: string;
  source_name: string;
  total_queries: number;
  failed_queries: number;
  avg_latency_ms: number;
}

export interface QueryPerformanceData {
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  total_queries: number;
  failed_queries: number;
  queries_by_source: SourceQueryStats[];
}

// ============================================================================
// Data Flow Graph
// ============================================================================

export interface FlowNode {
  id: string;
  label: string;
  type: string; // 'source' | 'warehouse' | 'lake'
  status: string;
}

export interface FlowEdge {
  source: string;
  target: string;
  volume_gb: number;
  sync_status: string;
}

export interface DataFlowGraph {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

// ============================================================================
// Schema Browsing
// ============================================================================

/** Table info returned by list tables API */
export interface TableInfo {
  name: string;
  row_count?: number;
  size_bytes?: number;
  comment?: string;
}

/** Column info for table schema */
export interface ColumnInfo {
  name: string;
  type: string;
  comment?: string;
}

/** Table schema response */
export interface TableSchema {
  database: string;
  table: string;
  columns: ColumnInfo[];
}

/** Table data preview response */
export interface TablePreview {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
}
