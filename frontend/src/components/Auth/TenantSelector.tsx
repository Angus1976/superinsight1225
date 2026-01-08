// Tenant selector component for switching tenants
import { useState, useEffect } from 'react';
import { Select, message, Spin } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/auth';
import type { Tenant } from '@/types';

interface TenantSelectorProps {
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
  onTenantChange?: (tenant: Tenant) => void;
}

export const TenantSelector: React.FC<TenantSelectorProps> = ({
  size = 'middle',
  style,
  onTenantChange,
}) => {
  const { t } = useTranslation('auth');
  const { currentTenant, setTenant, user } = useAuthStore();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState(false);

  // Load available tenants
  useEffect(() => {
    const loadTenants = async () => {
      setLoading(true);
      try {
        const tenantList = await authService.getTenants();
        setTenants(tenantList);
      } catch (error) {
        console.error('Failed to load tenants:', error);
        message.error(t('tenant.loadFailed'));
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      loadTenants();
    }
  }, [user, t]);

  const handleTenantChange = async (tenantId: string) => {
    const selectedTenant = tenants.find(t => t.id === tenantId);
    if (!selectedTenant) return;

    setSwitching(true);
    try {
      // Call API to switch tenant context
      await authService.switchTenant(tenantId);
      
      // Update local state
      setTenant(selectedTenant);
      onTenantChange?.(selectedTenant);
      
      message.success(t('tenant.switchSuccess', { name: selectedTenant.name }));
      
      // Optionally reload the page to refresh all data with new tenant context
      window.location.reload();
    } catch (error) {
      console.error('Failed to switch tenant:', error);
      message.error(t('tenant.switchFailed'));
    } finally {
      setSwitching(false);
    }
  };

  if (!user || tenants.length <= 1) {
    return null; // Don't show selector if not logged in or only one tenant
  }

  return (
    <Select
      value={currentTenant?.id}
      onChange={handleTenantChange}
      loading={loading || switching}
      size={size}
      style={{ minWidth: 150, ...style }}
      placeholder={t('tenant.selectPlaceholder')}
      suffixIcon={loading ? <Spin size="small" /> : <TeamOutlined />}
      showSearch
      optionFilterProp="children"
      disabled={switching}
    >
      {tenants.map((tenant) => (
        <Select.Option key={tenant.id} value={tenant.id}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {tenant.logo && (
              <img 
                src={tenant.logo} 
                alt={tenant.name} 
                style={{ width: 16, height: 16, borderRadius: 2 }}
              />
            )}
            <span>{tenant.name}</span>
            {tenant.id === currentTenant?.id && (
              <span style={{ color: '#1890ff', fontSize: '12px' }}>
                ({t('tenant.current')})
              </span>
            )}
          </div>
        </Select.Option>
      ))}
    </Select>
  );
};