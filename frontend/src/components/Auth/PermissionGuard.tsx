// 权限保护组件
import React from 'react';
import { Alert, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { LockOutlined } from '@ant-design/icons';
import { usePermissions } from '@/hooks/usePermissions';
import { Permission } from '@/utils/permissions';

interface PermissionGuardProps {
  permission?: Permission;
  permissions?: Permission[];
  requireAll?: boolean; // 是否需要所有权限，默认false（只需要其中一个）
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permission,
  permissions = [],
  requireAll = false,
  fallback,
  children
}) => {
  const { checkPermission, roleDisplayName } = usePermissions();
  const navigate = useNavigate();

  // 构建需要检查的权限列表
  const permissionsToCheck = permission ? [permission] : permissions;

  // 检查权限
  const hasRequiredPermissions = requireAll
    ? permissionsToCheck.every(p => checkPermission(p))
    : permissionsToCheck.some(p => checkPermission(p));

  if (hasRequiredPermissions) {
    return <>{children}</>;
  }

  // 如果提供了fallback，使用fallback
  if (fallback) {
    return <>{fallback}</>;
  }

  // 默认的权限不足提示
  return (
    <Alert
      type="warning"
      showIcon
      icon={<LockOutlined />}
      message="权限不足"
      description={
        <div>
          <p>您当前的角色是：<strong>{roleDisplayName}</strong></p>
          <p>访问此功能需要更高的权限。请联系管理员获取相应权限。</p>
        </div>
      }
      action={
        <Button type="primary" onClick={() => navigate(-1)}>
          返回上一页
        </Button>
      }
      style={{ margin: '20px' }}
    />
  );
};

export default PermissionGuard;