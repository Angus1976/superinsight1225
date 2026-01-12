// Tenant selector component for switching tenants
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Select, message, Spin, Tooltip, Badge, Space, Typography } from 'antd';
import { TeamOutlined, CheckCircleOutlined, SwapOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/auth';
import type { Tenant } from '@/types';

const { Text } = Typography;

interface TenantSelectorProps {
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
  onTenantChange?: (tenant: Tenant) => void;
  showLabel?: boolean;
  autoReload?: boolean;
  className?: string;
}

export const TenantSelector: React.FC<TenantSelectorProps> = ({
  size = 'middle',
  style,
  onTenantChange,
  showLabel = false,
  autoReload = true,
  className,
}) => {
  const { t } = useTranslation('auth');
  const { currentTenant, setTenant, user } = useAuthStore();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available tenants
  const loadTenants = useCallback(async () => {
    if (!user) return;
    
    setLoading(true);
    setError(null);
    try {
      const tenantList = await authService.getTenants();
      setTenants(tenantList);
      
      // If current tenant is not in the list, set the first one
      if (tenantList.length > 0 && !tenantList.find(t => t.id === currentTenant?.id)) {
        setTenant(tenantList[0]);
      }
    } catch (err) {
      console.error('Failed to load tenants:', err);
      const errorMessage = err instanceof Error ? err.message : t('tenant.loadFailed');
      setError(errorMessage);
      message.error(t('tenant.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [user, currentTenant?.id, setTenant, t]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  // Handle tenant change with confirmation for important switch
  const handleTenantChange = useCallback(async (tenantId: string) => {
    if (tenantId === currentTenant?.id) return;
    
    const selectedTenant = tenants.find(t => t.id === tenantId);
    if (!selectedTenant) {
      message.error(t('tenant.switchFailed'));
      return;
    }

    setSwitching(true);
    try {
      // Call API to switch tenant context
      await authService.switchTenant(tenantId);
      
      // Update local state
      setTenant(selectedTenant);
      onTenantChange?.(selectedTenant);
      
      message.success(t('tenant.switchSuccess', { name: selectedTenant.name }));
      
      // Optionally reload the page to refresh all data with new tenant context
      if (autoReload) {
        // Small delay to show success message
        setTimeout(() => {
          window.location.reload();
        }, 500);
      }
    } catch (err) {
      console.error('Failed to switch tenant:', err);
      const errorMessage = err instanceof Error ? err.message : t('tenant.switchFailed');
      message.error(errorMessage);
    } finally {
      setSwitching(false);
    }
  }, [currentTenant?.id, tenants, setTenant, onTenantChange, autoReload, t]);

  // Filter function for search
  const filterOption = useCallback((input: string, option?: { label?: string; value?: string; children?: React.ReactNode }) => {
    if (!option) return false;
    const tenant = tenants.find(t => t.id === option?.value);
    if (!tenant) return false;
    return tenant.name.toLowerCase().includes(input.toLowerCase());
  }, [tenants]);

  // Memoized tenant options
  const tenantOptions = useMemo(() => {
    return tenants.map((tenant) => ({
      value: tenant.id,
      label: tenant.name,
      tenant,
    }));
  }, [tenants]);

  // Don't show selector if not logged in
  if (!user) {
    return null;
  }

  // Show loading state while fetching tenants
  if (loading && tenants.length === 0) {
    return (
      <Tooltip title={t('tenant.loading', '加载租户...')}>
        <Spin size="small" />
      </Tooltip>
    );
  }

  // Show error state with retry option
  if (error && tenants.length === 0) {
    return (
      <Tooltip title={error}>
        <Badge status="error" text={t('tenant.loadFailed')} />
      </Tooltip>
    );
  }

  // Don't show selector if only one tenant
  if (tenants.length <= 1) {
    // Optionally show current tenant name without selector
    if (showLabel && currentTenant) {
      return (
        <Space size={4}>
          <TeamOutlined style={{ color: '#1890ff' }} />
          <Text type="secondary">{currentTenant.name}</Text>
        </Space>
      );
    }
    return null;
  }

  return (
    <Space size={4} className={className}>
      {showLabel && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {t('tenant.select')}:
        </Text>
      )}
      <Select
        value={currentTenant?.id}
        onChange={handleTenantChange}
        loading={loading || switching}
        size={size}
        style={{ minWidth: 150, ...style }}
        placeholder={t('tenant.selectPlaceholder')}
        suffixIcon={switching ? <SwapOutlined spin /> : <TeamOutlined />}
        showSearch
        filterOption={filterOption}
        disabled={switching}
        optionLabelProp="label"
        popupMatchSelectWidth={false}
        styles={{ popup: { root: { minWidth: 200 } } }}
        aria-label={t('tenant.select')}
        notFoundContent={loading ? <Spin size="small" /> : t('tenant.noTenants', '无可用租户')}
      >
        {tenantOptions.map(({ value, tenant }) => (
          <Select.Option 
            key={value} 
            value={value} 
            label={tenant.name}
          >
            <div 
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between',
                gap: 8,
                padding: '4px 0',
              }}
            >
              <Space size={8}>
                {tenant.logo ? (
                  <img 
                    src={tenant.logo} 
                    alt={tenant.name} 
                    style={{ 
                      width: 20, 
                      height: 20, 
                      borderRadius: 4,
                      objectFit: 'cover',
                    }}
                    onError={(e) => {
                      // Fallback to icon if image fails to load
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                ) : (
                  <TeamOutlined style={{ fontSize: 16, color: '#1890ff' }} />
                )}
                <span style={{ fontWeight: tenant.id === currentTenant?.id ? 500 : 400 }}>
                  {tenant.name}
                </span>
              </Space>
              {tenant.id === currentTenant?.id && (
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
              )}
            </div>
          </Select.Option>
        ))}
      </Select>
    </Space>
  );
};