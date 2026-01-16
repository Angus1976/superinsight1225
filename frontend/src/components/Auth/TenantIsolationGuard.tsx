// 租户隔离守卫组件
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Space, Tag, Result } from 'antd';
import { useNavigate } from 'react-router-dom';
import { TeamOutlined, AppstoreOutlined, SafetyOutlined } from '@ant-design/icons';
import { usePermissions } from '@/hooks/usePermissions';
import { useAuthStore } from '@/stores/authStore';

interface TenantIsolationGuardProps {
  children: React.ReactNode;
  // 资源所属租户ID
  resourceTenantId: string;
  // 资源所属工作空间ID（可选）
  resourceWorkspaceId?: string;
  // 自定义拒绝访问时的渲染内容
  fallback?: React.ReactNode;
  // 是否显示详细的拒绝原因
  showDetailedReason?: boolean;
  // 拒绝访问时的回调
  onAccessDenied?: (reason: 'tenant' | 'workspace') => void;
}

export const TenantIsolationGuard: React.FC<TenantIsolationGuardProps> = ({
  children,
  resourceTenantId,
  resourceWorkspaceId,
  fallback,
  showDetailedReason = true,
  onAccessDenied
}) => {
  const { t } = useTranslation(['auth', 'common']);
  const navigate = useNavigate();
  const { currentTenant, currentWorkspace } = useAuthStore();
  const { 
    checkTenantAccess, 
    checkWorkspaceAccess,
    roleDisplayName,
    tenantRoleDisplayName,
    workspaceRoleDisplayName,
    system
  } = usePermissions();

  // 检查租户访问权限
  const hasTenantAccess = React.useMemo(() => {
    // 系统管理员可以访问所有租户
    if (system.isSystemAdmin) {
      return true;
    }
    return checkTenantAccess(resourceTenantId);
  }, [resourceTenantId, checkTenantAccess, system.isSystemAdmin]);

  // 检查工作空间访问权限
  const hasWorkspaceAccess = React.useMemo(() => {
    if (!resourceWorkspaceId) {
      return true; // 如果没有指定工作空间，则不检查
    }
    // 系统管理员可以访问所有工作空间
    if (system.isSystemAdmin) {
      return true;
    }
    return checkWorkspaceAccess(resourceWorkspaceId);
  }, [resourceWorkspaceId, checkWorkspaceAccess, system.isSystemAdmin]);

  // 触发拒绝访问回调
  React.useEffect(() => {
    if (!hasTenantAccess) {
      onAccessDenied?.('tenant');
    } else if (!hasWorkspaceAccess) {
      onAccessDenied?.('workspace');
    }
  }, [hasTenantAccess, hasWorkspaceAccess, onAccessDenied]);

  // 如果有访问权限，渲染子组件
  if (hasTenantAccess && hasWorkspaceAccess) {
    return <>{children}</>;
  }

  // 如果提供了自定义fallback，使用它
  if (fallback) {
    return <>{fallback}</>;
  }

  // 确定拒绝原因
  const denialType = !hasTenantAccess ? 'tenant' : 'workspace';

  // 简单模式：只显示基本信息
  if (!showDetailedReason) {
    return (
      <Result
        status="403"
        title={t('permission.accessDenied')}
        subTitle={
          denialType === 'tenant' 
            ? t('permission.tenantAccessDeniedDesc')
            : t('permission.workspaceAccessDeniedDesc')
        }
        extra={
          <Button type="primary" onClick={() => navigate(-1)}>
            {t('permission.goBack')}
          </Button>
        }
      />
    );
  }

  // 详细模式：显示完整的访问拒绝信息
  return (
    <Alert
      type="error"
      showIcon
      icon={denialType === 'tenant' ? <TeamOutlined /> : <AppstoreOutlined />}
      message={
        <Space>
          <SafetyOutlined />
          {denialType === 'tenant' ? t('permission.tenantIsolation') : t('permission.workspaceIsolation')}
        </Space>
      }
      description={
        <div style={{ marginTop: 12 }}>
          <p style={{ marginBottom: 16 }}>
            {denialType === 'tenant' 
              ? t('permission.tenantIsolationDesc')
              : t('permission.workspaceIsolationDesc')
            }
          </p>
          
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div style={{ 
              background: '#fafafa', 
              padding: '12px', 
              borderRadius: '4px',
              border: '1px solid #f0f0f0'
            }}>
              <Space direction="vertical" size={4}>
                <div>
                  <span style={{ color: '#666', marginRight: 8 }}>{t('permission.currentTenant')}：</span>
                  <Tag color="blue">{currentTenant?.name || t('common:status.noData')}</Tag>
                </div>
                {currentWorkspace && (
                  <div>
                    <span style={{ color: '#666', marginRight: 8 }}>{t('permission.currentWorkspace')}：</span>
                    <Tag color="green">{currentWorkspace.name}</Tag>
                  </div>
                )}
                <div>
                  <span style={{ color: '#666', marginRight: 8 }}>{t('permission.yourRole')}：</span>
                  <Tag color="orange">{roleDisplayName}</Tag>
                </div>
                <div>
                  <span style={{ color: '#666', marginRight: 8 }}>{t('permission.tenantRole')}：</span>
                  <Tag color="purple">{tenantRoleDisplayName}</Tag>
                </div>
                {currentWorkspace && (
                  <div>
                    <span style={{ color: '#666', marginRight: 8 }}>{t('permission.workspaceRole')}：</span>
                    <Tag color="cyan">{workspaceRoleDisplayName}</Tag>
                  </div>
                )}
              </Space>
            </div>
            
            <div style={{ marginTop: 8 }}>
              <span style={{ color: '#999', fontSize: '12px' }}>
                {t('permission.contactAdmin')}
              </span>
            </div>
          </Space>
        </div>
      }
      action={
        <Space direction="vertical" size="small">
          <Button type="primary" onClick={() => navigate(-1)}>
            {t('permission.goBack')}
          </Button>
          <Button onClick={() => navigate('/')}>
            {t('permission.goHome')}
          </Button>
        </Space>
      }
      style={{ margin: '20px' }}
    />
  );
};

export default TenantIsolationGuard;
