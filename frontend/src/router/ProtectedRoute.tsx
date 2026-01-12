// Protected route component with tenant isolation
import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Alert, Button, Space, Spin } from 'antd';
import { TeamOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { usePermissions } from '@/hooks/usePermissions';
import { ROUTES } from '@/constants';
import { Permission } from '@/utils/permissions';

interface ProtectedRouteProps {
  children: ReactNode;
  // 可选：要求特定权限
  requiredPermission?: Permission;
  requiredPermissions?: Permission[];
  requireAll?: boolean;
  // 可选：要求特定租户
  requiredTenantId?: string;
  // 可选：要求特定工作空间
  requiredWorkspaceId?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children,
  requiredPermission,
  requiredPermissions = [],
  requireAll = false,
  requiredTenantId,
  requiredWorkspaceId
}) => {
  const { isAuthenticated, token, currentTenant, currentWorkspace } = useAuthStore();
  const { 
    checkPermission, 
    checkTenantAccess, 
    checkWorkspaceAccess,
    roleDisplayName 
  } = usePermissions();
  const location = useLocation();
  const [isChecking, setIsChecking] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    // Give a small delay to ensure store is properly hydrated
    const timer = setTimeout(() => {
      setIsChecking(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // Show loading while checking authentication
  if (isChecking) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Space direction="vertical" align="center">
          <Spin size="large" />
          <span>正在验证身份...</span>
        </Space>
      </div>
    );
  }

  // 检查认证状态
  if (!isAuthenticated || !token) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  // 检查租户是否已加载
  if (!currentTenant) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Space direction="vertical" align="center">
          <Spin size="large" />
          <span>正在加载租户信息...</span>
        </Space>
      </div>
    );
  }

  // 检查租户隔离
  if (requiredTenantId && !checkTenantAccess(requiredTenantId)) {
    return (
      <Alert
        type="error"
        showIcon
        icon={<TeamOutlined />}
        message="租户访问受限"
        description={
          <div>
            <p>您没有权限访问此租户的资源。</p>
            <p>当前租户：<strong>{currentTenant.name}</strong></p>
            <p>您的角色：<strong>{roleDisplayName}</strong></p>
          </div>
        }
        action={
          <Button type="primary" onClick={() => window.history.back()}>
            返回上一页
          </Button>
        }
        style={{ margin: '20px' }}
      />
    );
  }

  // 检查工作空间隔离
  if (requiredWorkspaceId && !checkWorkspaceAccess(requiredWorkspaceId)) {
    return (
      <Alert
        type="error"
        showIcon
        icon={<TeamOutlined />}
        message="工作空间访问受限"
        description={
          <div>
            <p>您没有权限访问此工作空间的资源。</p>
            <p>当前工作空间：<strong>{currentWorkspace?.name || '未选择'}</strong></p>
            <p>您的角色：<strong>{roleDisplayName}</strong></p>
          </div>
        }
        action={
          <Button type="primary" onClick={() => window.history.back()}>
            返回上一页
          </Button>
        }
        style={{ margin: '20px' }}
      />
    );
  }

  // 检查权限
  const permissionsToCheck = requiredPermission 
    ? [requiredPermission] 
    : requiredPermissions;

  if (permissionsToCheck.length > 0) {
    const hasRequiredPermissions = requireAll
      ? permissionsToCheck.every(p => checkPermission(p))
      : permissionsToCheck.some(p => checkPermission(p));

    if (!hasRequiredPermissions) {
      return (
        <Alert
          type="warning"
          showIcon
          message="权限不足"
          description={
            <div>
              <p>您没有访问此页面的权限。</p>
              <p>您的角色：<strong>{roleDisplayName}</strong></p>
              <p>请联系管理员获取相应权限。</p>
            </div>
          }
          action={
            <Button type="primary" onClick={() => window.history.back()}>
              返回上一页
            </Button>
          }
          style={{ margin: '20px' }}
        />
      );
    }
  }

  return <>{children}</>;
};
