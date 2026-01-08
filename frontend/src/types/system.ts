// System management types
export interface SystemTenant {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'inactive' | 'suspended';
  plan: 'free' | 'pro' | 'enterprise';
  users_count: number;
  storage_used: number;
  storage_limit: number;
  cpu_quota: number;
  memory_quota: number;
  api_rate_limit: number;
  features: string[];
  settings: TenantSettings;
  created_at: string;
  updated_at: string;
}

export interface TenantSettings {
  theme: 'light' | 'dark' | 'auto';
  language: 'zh' | 'en';
  timezone: string;
  notification_enabled: boolean;
  audit_log_retention: number;
  backup_enabled: boolean;
  backup_frequency: 'daily' | 'weekly' | 'monthly';
}

export interface TenantUsage {
  tenant_id: string;
  period: string;
  metrics: {
    active_users: number;
    total_tasks: number;
    annotations_count: number;
    storage_usage: number;
    api_calls: number;
    cpu_usage: number;
    memory_usage: number;
  };
  costs: {
    compute: number;
    storage: number;
    api: number;
    total: number;
  };
}

export interface SystemMetrics {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: {
    bytes_in: number;
    bytes_out: number;
  };
  database: {
    connections: number;
    queries_per_second: number;
    slow_queries: number;
  };
  services: ServiceHealth[];
}

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  response_time: number;
  error_rate: number;
  last_check: string;
  details?: Record<string, any>;
}

export interface SystemAlert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  source: string;
  tenant_id?: string;
  acknowledged: boolean;
  resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface SystemAuditLog {
  id: string;
  tenant_id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, any>;
  ip_address: string;
  user_agent: string;
  timestamp: string;
}

export interface SystemConfig {
  maintenance_mode: boolean;
  registration_enabled: boolean;
  max_tenants: number;
  default_tenant_quota: {
    users: number;
    storage: number;
    cpu: number;
    memory: number;
  };
  security: {
    password_policy: {
      min_length: number;
      require_uppercase: boolean;
      require_lowercase: boolean;
      require_numbers: boolean;
      require_symbols: boolean;
    };
    session_timeout: number;
    max_login_attempts: number;
    lockout_duration: number;
  };
  features: {
    ai_models: string[];
    integrations: string[];
    export_formats: string[];
  };
}

// API request/response types
export interface CreateTenantRequest {
  name: string;
  description?: string;
  plan: 'free' | 'pro' | 'enterprise';
  admin_email: string;
  admin_username: string;
  settings?: Partial<TenantSettings>;
}

export interface UpdateTenantRequest {
  name?: string;
  description?: string;
  status?: 'active' | 'inactive' | 'suspended';
  plan?: 'free' | 'pro' | 'enterprise';
  storage_limit?: number;
  cpu_quota?: number;
  memory_quota?: number;
  api_rate_limit?: number;
  settings?: Partial<TenantSettings>;
}

export interface SystemMetricsQuery {
  start_time: string;
  end_time: string;
  interval: '1m' | '5m' | '15m' | '1h' | '1d';
  metrics?: string[];
}

export interface TenantUsageQuery {
  tenant_id?: string;
  start_date: string;
  end_date: string;
  group_by?: 'day' | 'week' | 'month';
}