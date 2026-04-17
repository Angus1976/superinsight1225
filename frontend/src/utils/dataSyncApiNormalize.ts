/**
 * FastAPI 默认序列化为 snake_case，前端表单与表格使用 camelCase。
 * 集中处理 /api/v1/data-sync/* 的请求与响应字段对齐。
 */

export type DataSyncSourceType =
  | 'database'
  | 'file'
  | 'api'
  | 'stream'
  | 'lifecycle_temp_data'
  | 'lifecycle_sample'
  | 'lifecycle_enhancement'
  | 'lifecycle_annotation'
  | 'lifecycle_ai_trial';

export interface DataSyncSource {
  id: string;
  name: string;
  type: DataSyncSourceType;
  status: 'active' | 'inactive' | 'error' | 'syncing';
  connectionString: string;
  lastSyncTime: string;
  nextSyncTime: string;
  syncInterval: number;
  totalRecords: number;
  syncedRecords: number;
  errorCount: number;
  enabled: boolean;
  createdAt: string;
  config: Record<string, unknown>;
}

export function normalizeDataSource(raw: Record<string, unknown>): DataSyncSource {
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? ''),
    type: (raw.type ?? 'database') as DataSyncSourceType,
    status: (raw.status ?? 'inactive') as DataSyncSource['status'],
    connectionString: String(raw.connection_string ?? raw.connectionString ?? ''),
    lastSyncTime: String(raw.last_sync_time ?? raw.lastSyncTime ?? ''),
    nextSyncTime: String(raw.next_sync_time ?? raw.nextSyncTime ?? ''),
    syncInterval: Number(raw.sync_interval ?? raw.syncInterval ?? 0),
    totalRecords: Number(raw.total_records ?? raw.totalRecords ?? 0),
    syncedRecords: Number(raw.synced_records ?? raw.syncedRecords ?? 0),
    errorCount: Number(raw.error_count ?? raw.errorCount ?? 0),
    enabled: Boolean(raw.enabled),
    createdAt: String(raw.created_at ?? raw.createdAt ?? ''),
    config: (raw.config ?? {}) as Record<string, unknown>,
  };
}

/** 创建/更新数据源：后端 CreateSourceRequest 使用 snake_case */
export function toCreateSourceRequestBody(values: Record<string, unknown>) {
  return {
    name: values.name,
    type: values.type,
    sync_interval: Number(values.sync_interval ?? values.syncInterval ?? 60),
    config: (values.config ?? {}) as Record<string, unknown>,
    enabled: values.enabled !== false,
  };
}

export interface SecurityConfig {
  encryption: {
    enabled: boolean;
    algorithm: string;
    keyRotationInterval: number;
  };
  authentication: {
    required: boolean;
    method: string;
    tokenExpiration: number;
  };
  authorization: {
    enabled: boolean;
    defaultRole: string;
    strictMode: boolean;
  };
  audit: {
    enabled: boolean;
    logLevel: string;
    retentionDays: number;
  };
  dataProtection: {
    piiDetection: boolean;
    autoDesensitization: boolean;
    complianceMode: string;
  };
}

export interface SecurityRule {
  id: string;
  name: string;
  type: 'encryption' | 'access' | 'audit' | 'compliance';
  enabled: boolean;
  description: string;
  conditions: string[];
  actions: string[];
  priority: number;
  createdAt: string;
}

function num(v: unknown, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export function normalizeSecurityConfig(raw: Record<string, unknown>): SecurityConfig {
  const enc = (raw.encryption ?? {}) as Record<string, unknown>;
  const auth = (raw.authentication ?? {}) as Record<string, unknown>;
  const autz = (raw.authorization ?? {}) as Record<string, unknown>;
  const audit = (raw.audit ?? {}) as Record<string, unknown>;
  const dp = (raw.data_protection ?? raw.dataProtection ?? {}) as Record<string, unknown>;

  return {
    encryption: {
      enabled: Boolean(enc.enabled),
      algorithm: String(enc.algorithm ?? ''),
      keyRotationInterval: num(enc.key_rotation_interval ?? enc.keyRotationInterval, 30),
    },
    authentication: {
      required: Boolean(auth.required),
      method: String(auth.method ?? ''),
      tokenExpiration: num(auth.token_expiration ?? auth.tokenExpiration, 24),
    },
    authorization: {
      enabled: Boolean(autz.enabled),
      defaultRole: String(autz.default_role ?? autz.defaultRole ?? ''),
      strictMode: Boolean(autz.strict_mode ?? autz.strictMode),
    },
    audit: {
      enabled: Boolean(audit.enabled),
      logLevel: String(audit.log_level ?? audit.logLevel ?? 'info'),
      retentionDays: num(audit.retention_days ?? audit.retentionDays, 90),
    },
    dataProtection: {
      piiDetection: Boolean(dp.pii_detection ?? dp.piiDetection),
      autoDesensitization: Boolean(dp.auto_desensitization ?? dp.autoDesensitization),
      complianceMode: String(dp.compliance_mode ?? dp.complianceMode ?? ''),
    },
  };
}

/** 保存安全配置：与后端 SecurityConfig 模型（含 data_protection）一致 */
export function denormalizeSecurityConfig(form: SecurityConfig): Record<string, unknown> {
  return {
    encryption: {
      enabled: form.encryption.enabled,
      algorithm: form.encryption.algorithm,
      key_rotation_interval: form.encryption.keyRotationInterval,
    },
    authentication: {
      required: form.authentication.required,
      method: form.authentication.method,
      token_expiration: form.authentication.tokenExpiration,
    },
    authorization: {
      enabled: form.authorization.enabled,
      default_role: form.authorization.defaultRole,
      strict_mode: form.authorization.strictMode,
    },
    audit: {
      enabled: form.audit.enabled,
      log_level: form.audit.logLevel,
      retention_days: form.audit.retentionDays,
    },
    data_protection: {
      pii_detection: form.dataProtection.piiDetection,
      auto_desensitization: form.dataProtection.autoDesensitization,
      compliance_mode: form.dataProtection.complianceMode,
    },
  };
}

export function normalizeSecurityRule(raw: Record<string, unknown>): SecurityRule {
  const cond = raw.conditions;
  const act = raw.actions;
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? ''),
    type: (raw.type ?? 'encryption') as SecurityRule['type'],
    enabled: Boolean(raw.enabled),
    description: String(raw.description ?? ''),
    conditions: Array.isArray(cond) ? (cond as string[]) : [],
    actions: Array.isArray(act) ? (act as string[]) : [],
    priority: Number(raw.priority ?? 0),
    createdAt: String(raw.created_at ?? raw.createdAt ?? ''),
  };
}
