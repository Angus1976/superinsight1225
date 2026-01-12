// 租户隔离守卫组件
import React from 'react';
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
        title="访问受限"
        subTitle={
          denialType === 'tenant' 
            ? '您没有权限访问此租户的资源' 
            : '您没有权限访问此工作空间的资源'
        }
        extra={
          <Button type="primary" onClick={() => navigate(-1)}>
            返回上一页
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
          {denialType === 'tenant' ? '租户隔离保护' : '工作空间隔离保护'}
        </Space>
      }
      description={
        <div style={{ marginTop: 12 }}>
          <p style={{ marginBottom: 16 }}>
            {denialType === 'tenant' 
              ? '您正在尝试访问其他租户的资源。出于数据安全考虑，系统已阻止此操作。'
              : '您正在尝试访问其他工作空间的资源。请切换到正确的工作空间或联系管理员获取访问权限。'
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
                  <span style={{ color: '#666', marginRight: 8 }}>当前租户：</span>
                  <Tag color="blue">{currentTenant?.name || '未知'}</Tag>
                </div>
                {currentWorkspace && (
                  <div>
                    <span style={{ color: '#666', marginRight: 8 }}>当前工作空间：</span>
                    <Tag color="green">{currentWorkspace.name}</Tag>
                  </div>
                )}
                <div>
                  <span style={{ color: '#666', marginRight: 8 }}>您的角色：</span>
                  <Tag color="orange">{roleDisplayName}</Tag>
                </div>
                <div>
                  <span style={{ color: '#666', marginRight: 8 }}>租户角色：</span>
                  <Tag color="purple">{tenantRoleDisplayName}</Tag>
                </div>
                {currentWorkspace && (
                  <div>
                    <span style={{ color: '#666', marginRight: 8 }}>工作空间角色：</span>
                    <Tag color="cyan">{workspaceRoleDisplayName}</Tag>
                  </div>
                )}
              </Space>
            </div>
            
            <div style={{ marginTop: 8 }}>
              <span style={{ color: '#999', fontSize: '12px' }}>
                如需访问此资源，请联系系统管理员或切换到正确的租户/工作空间。
              </span>
            </div>
          </Space>
        </div>
      }
      action={
        <Space direction="vertical" size="small">
          <Button type="primary" onClick={() => navigate(-1)}>
            返回上一页
          </Button>
          <Button onClick={() => navigate('/')}>
            返回首页
          </Button>
        </Space>
      }
      style={{ margin: '20px' }}
    />
  );
};

export default TenantIsolationGuard;
