// 权限保护组件 - 包含租户隔离
import React, { useEffect, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Space, Tag, Skeleton, Spin } from 'antd';
import { useNavigate } from 'react-router-dom';
import { LockOutlined, TeamOutlined, AppstoreOutlined, LoadingOutlined } from '@ant-design/icons';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission, ResourceContext } from '@/utils/permissions';

// 降级模式类型
export type FallbackMode = 'alert' | 'skeleton' | 'hidden' | 'custom';

interface PermissionGuardProps {
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean; // 是否需要所有权限，默认false（只需要其中一个）
  fallback?: React.ReactNode;
  fallbackMode?: FallbackMode; // 降级模式，默认'alert'
  children: React.ReactNode;
  // 租户隔离相关属性
  resourceTenantId?: string; // 资源所属租户ID
  resourceWorkspaceId?: string; // 资源所属工作空间ID
  resourceOwnerId?: string; // 资源所有者ID
  requireTenantIsolation?: boolean; // 是否需要租户隔离检查，默认true
  requireWorkspaceIsolation?: boolean; // 是否需要工作空间隔离检查，默认false
  // 实时响应相关属性
  onPermissionChange?: (hasAccess: boolean) => void; // 权限变更回调
  showLoading?: boolean; // 是否显示加载状态
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permission,
  permissions = [],
  requireAll = false,
  fallback,
  fallbackMode = 'alert',
  children,
  resourceTenantId,
  resourceWorkspaceId,
  resourceOwnerId,
  requireTenantIsolation = true,
  requireWorkspaceIsolation = false,
  onPermissionChange,
  showLoading = false
}) => {
  const { 
    checkPermission, 
    checkPermissionWithIsolation,
    checkTenantAccess,
    checkWorkspaceAccess,
    roleDisplayName,
    tenantRoleDisplayName,
    workspaceRoleDisplayName,
    tenantContext
  } = usePermissions();
  const navigate = useNavigate();
  const { t } = useTranslation(['auth', 'common']);
  
  // 加载状态（用于异步权限检查场景）
  const [isChecking, setIsChecking] = useState(showLoading);

  // 构建需要检查的权限列表
  const permissionsToCheck = permission ? [permission] : permissions;

  // 检查租户隔离
  const passesTenantIsolation = React.useMemo(() => {
    if (!requireTenantIsolation || !resourceTenantId) {
      return true;
    }
    return checkTenantAccess(resourceTenantId);
  }, [requireTenantIsolation, resourceTenantId, checkTenantAccess]);

  // 检查工作空间隔离
  const passesWorkspaceIsolation = React.useMemo(() => {
    if (!requireWorkspaceIsolation || !resourceWorkspaceId) {
      return true;
    }
    return checkWorkspaceAccess(resourceWorkspaceId);
  }, [requireWorkspaceIsolation, resourceWorkspaceId, checkWorkspaceAccess]);

  // 检查权限（带租户隔离）
  const hasRequiredPermissions = React.useMemo(() => {
    // 如果需要租户隔离检查且有资源上下文
    if ((requireTenantIsolation && resourceTenantId) || 
        (requireWorkspaceIsolation && resourceWorkspaceId)) {
      const resourceContext: ResourceContext = {
        resourceTenantId: resourceTenantId || tenantContext.tenantId,
        resourceWorkspaceId: resourceWorkspaceId,
        resourceOwnerId: resourceOwnerId
      };

      if (requireAll) {
        return permissionsToCheck.every(p => 
          checkPermissionWithIsolation(p, resourceContext)
        );
      }
      return permissionsToCheck.some(p => 
        checkPermissionWithIsolation(p, resourceContext)
      );
    }

    // 基本权限检查（不含租户隔离）
    if (requireAll) {
      return permissionsToCheck.every(p => checkPermission(p));
    }
    return permissionsToCheck.some(p => checkPermission(p));
  }, [
    permissionsToCheck, 
    requireAll, 
    checkPermission, 
    checkPermissionWithIsolation,
    requireTenantIsolation,
    requireWorkspaceIsolation,
    resourceTenantId,
    resourceWorkspaceId,
    resourceOwnerId,
    tenantContext.tenantId
  ]);

  // 综合检查：权限 + 租户隔离 + 工作空间隔离
  const hasAccess = hasRequiredPermissions && passesTenantIsolation && passesWorkspaceIsolation;

  // 权限变更实时响应
  useEffect(() => {
    if (onPermissionChange) {
      onPermissionChange(hasAccess);
    }
  }, [hasAccess, onPermissionChange]);

  // 模拟加载完成（用于showLoading场景）
  useEffect(() => {
    if (showLoading && isChecking) {
      // 短暂延迟后完成检查，模拟异步权限验证
      const timer = setTimeout(() => setIsChecking(false), 100);
      return () => clearTimeout(timer);
    }
  }, [showLoading, isChecking]);

  // 显示加载状态
  if (isChecking) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} tip={t('permission.verifying')} />
      </div>
    );
  }

  if (hasAccess) {
    return <>{children}</>;
  }

  // 如果提供了fallback，使用fallback
  if (fallback) {
    return <>{fallback}</>;
  }

  // 根据fallbackMode选择降级方式
  if (fallbackMode === 'hidden') {
    return null;
  }

  if (fallbackMode === 'skeleton') {
    return (
      <div style={{ padding: '20px' }}>
        <Skeleton active paragraph={{ rows: 4 }} />
      </div>
    );
  }

  // 确定拒绝原因
  const getDenialReason = () => {
    if (!passesTenantIsolation) {
      return {
        title: t('permission.tenantAccessDenied'),
        description: t('permission.tenantAccessDeniedDesc'),
        icon: <TeamOutlined />
      };
    }
    if (!passesWorkspaceIsolation) {
      return {
        title: t('permission.workspaceAccessDenied'),
        description: t('permission.workspaceAccessDeniedDesc'),
        icon: <AppstoreOutlined />
      };
    }
    return {
      title: t('permission.insufficientPermission'),
      description: t('permission.insufficientPermissionDesc'),
      icon: <LockOutlined />
    };
  };

  const denialReason = getDenialReason();

  // 默认的权限不足提示
  return (
    <Alert
      type="warning"
      showIcon
      icon={denialReason.icon}
      message={denialReason.title}
      description={
        <div>
          <p>{denialReason.description}</p>
          <Space direction="vertical" size="small" style={{ marginTop: 8 }}>
            <div>
              <span>{t('permission.currentRole')}：</span>
              <Tag color="blue">{roleDisplayName}</Tag>
            </div>
            {tenantContext.tenantId && (
              <div>
                <span>{t('permission.tenantRole')}：</span>
                <Tag color="green">{tenantRoleDisplayName}</Tag>
              </div>
            )}
            {tenantContext.workspaceId && (
              <div>
                <span>{t('permission.workspaceRole')}：</span>
                <Tag color="orange">{workspaceRoleDisplayName}</Tag>
              </div>
            )}
          </Space>
        </div>
      }
      action={
        <Button type="primary" onClick={() => navigate(-1)}>
          {t('permission.goBack')}
        </Button>
      }
      style={{ margin: '20px' }}
    />
  );
};

export default PermissionGuard;