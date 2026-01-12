// 权限检查Hook
import { useMemo, useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import {
  Permission,
  TenantRole,
  WorkspaceRole,
  hasPermission,
  hasTenantPermission,
  hasWorkspacePermission,
  canAccessAnnotation,
  canCreateAnnotation,
  canEditAnnotation,
  canDeleteAnnotation,
  canManageTasks,
  canManageProjects,
  canExportData,
  getUserPermissions,
  getRoleDisplayName,
  getTenantRoleDisplayName,
  getWorkspaceRoleDisplayName,
  checkTenantIsolation,
  checkWorkspaceIsolation,
  checkPermissionWithTenantIsolation,
  canAccessTenant,
  canAccessWorkspace,
  TenantContext,
  ResourceContext
} from '@/utils/permissions';

export const usePermissions = () => {
  const { user, currentTenant, currentWorkspace, workspaces } = useAuthStore();
  const userRole = user?.role || '';
  
  // 获取用户的租户角色（从用户对象或默认值）
  const tenantRole = useMemo(() => {
    // 如果用户是系统管理员，给予租户管理员权限
    if (userRole.toUpperCase() === 'ADMIN') {
      return TenantRole.TENANT_ADMIN;
    }
    // 默认为租户成员
    return TenantRole.TENANT_MEMBER;
  }, [userRole]);
  
  // 获取用户在当前工作空间的角色
  const workspaceRole = useMemo(() => {
    // 如果用户是系统管理员，给予工作空间所有者权限
    if (userRole.toUpperCase() === 'ADMIN') {
      return WorkspaceRole.WORKSPACE_OWNER;
    }
    // 业务专家默认为工作空间管理员
    if (userRole.toUpperCase() === 'BUSINESS_EXPERT') {
      return WorkspaceRole.WORKSPACE_ADMIN;
    }
    // 标注员默认为工作空间成员
    if (userRole.toUpperCase() === 'ANNOTATOR') {
      return WorkspaceRole.WORKSPACE_MEMBER;
    }
    // 默认为工作空间查看者
    return WorkspaceRole.WORKSPACE_VIEWER;
  }, [userRole]);

  // 构建租户上下文
  const tenantContext: TenantContext = useMemo(() => ({
    tenantId: currentTenant?.id || user?.tenant_id || '',
    tenantRole: tenantRole,
    workspaceId: currentWorkspace?.id,
    workspaceRole: workspaceRole
  }), [currentTenant, currentWorkspace, user, tenantRole, workspaceRole]);

  const permissions = useMemo(() => {
    if (!userRole) return [];
    return getUserPermissions(userRole);
  }, [userRole]);

  // 基本权限检查（不含租户隔离）
  const checkPermission = useMemo(() => {
    return (permission: Permission) => {
      if (!userRole) return false;
      return hasPermission(userRole, permission);
    };
  }, [userRole]);

  // 带租户隔离的权限检查
  const checkPermissionWithIsolation = useCallback((
    permission: Permission,
    resourceContext: ResourceContext
  ): boolean => {
    if (!userRole || !tenantContext.tenantId) return false;
    return checkPermissionWithTenantIsolation(
      userRole,
      permission,
      tenantContext,
      resourceContext
    );
  }, [userRole, tenantContext]);

  // 检查是否可以访问指定租户的资源
  const canAccessTenantResource = useCallback((targetTenantId: string): boolean => {
    return canAccessTenant(tenantContext.tenantId, targetTenantId, userRole);
  }, [tenantContext.tenantId, userRole]);

  // 检查是否可以访问指定工作空间的资源
  const canAccessWorkspaceResource = useCallback((
    targetWorkspaceId: string,
    targetTenantId: string
  ): boolean => {
    const userWorkspaceIds = workspaces.map(w => w.id);
    return canAccessWorkspace(
      tenantContext.tenantId,
      userWorkspaceIds,
      targetWorkspaceId,
      targetTenantId,
      userRole
    );
  }, [tenantContext.tenantId, workspaces, userRole]);

  // 检查租户隔离
  const checkTenantAccess = useCallback((resourceTenantId: string): boolean => {
    return checkTenantIsolation(tenantContext.tenantId, resourceTenantId);
  }, [tenantContext.tenantId]);

  // 检查工作空间隔离
  const checkWorkspaceAccess = useCallback((resourceWorkspaceId: string): boolean => {
    return checkWorkspaceIsolation(tenantContext.workspaceId, resourceWorkspaceId);
  }, [tenantContext.workspaceId]);

  const annotationPermissions = useMemo(() => ({
    canView: canAccessAnnotation(userRole),
    canCreate: canCreateAnnotation(userRole),
    canEdit: canEditAnnotation(userRole),
    canDelete: canDeleteAnnotation(userRole)
  }), [userRole]);

  const taskPermissions = useMemo(() => ({
    canView: hasPermission(userRole, Permission.VIEW_TASKS),
    canCreate: hasPermission(userRole, Permission.CREATE_TASKS),
    canEdit: hasPermission(userRole, Permission.EDIT_TASKS),
    canDelete: hasPermission(userRole, Permission.DELETE_TASKS),
    canManage: canManageTasks(userRole)
  }), [userRole]);

  const projectPermissions = useMemo(() => ({
    canView: hasPermission(userRole, Permission.VIEW_PROJECTS),
    canCreate: hasPermission(userRole, Permission.CREATE_PROJECTS),
    canEdit: hasPermission(userRole, Permission.EDIT_PROJECTS),
    canDelete: hasPermission(userRole, Permission.DELETE_PROJECTS),
    canManage: canManageProjects(userRole)
  }), [userRole]);

  const qualityPermissions = useMemo(() => ({
    canView: hasPermission(userRole, Permission.VIEW_QUALITY),
    canManage: hasPermission(userRole, Permission.MANAGE_QUALITY)
  }), [userRole]);

  const systemPermissions = useMemo(() => ({
    canViewUsers: hasPermission(userRole, Permission.VIEW_USERS),
    canManageUsers: hasPermission(userRole, Permission.CREATE_USERS) || 
                   hasPermission(userRole, Permission.EDIT_USERS),
    canExportData: canExportData(userRole),
    isSystemAdmin: hasPermission(userRole, Permission.SYSTEM_ADMIN)
  }), [userRole]);

  // 租户权限
  const tenantPermissions = useMemo(() => ({
    canView: hasPermission(userRole, Permission.VIEW_TENANT) || 
             hasTenantPermission(tenantRole, Permission.VIEW_TENANT),
    canManage: hasPermission(userRole, Permission.MANAGE_TENANT) || 
               hasTenantPermission(tenantRole, Permission.MANAGE_TENANT),
    canSwitch: hasPermission(userRole, Permission.SWITCH_TENANT) || 
               hasTenantPermission(tenantRole, Permission.SWITCH_TENANT)
  }), [userRole, tenantRole]);

  // 工作空间权限
  const workspacePermissions = useMemo(() => ({
    canView: hasPermission(userRole, Permission.VIEW_WORKSPACE) || 
             hasWorkspacePermission(workspaceRole, Permission.VIEW_WORKSPACE),
    canCreate: hasPermission(userRole, Permission.CREATE_WORKSPACE) || 
               hasTenantPermission(tenantRole, Permission.CREATE_WORKSPACE),
    canEdit: hasPermission(userRole, Permission.EDIT_WORKSPACE) || 
             hasWorkspacePermission(workspaceRole, Permission.EDIT_WORKSPACE),
    canDelete: hasPermission(userRole, Permission.DELETE_WORKSPACE) || 
               hasWorkspacePermission(workspaceRole, Permission.DELETE_WORKSPACE),
    canManageMembers: hasPermission(userRole, Permission.MANAGE_WORKSPACE_MEMBERS) || 
                      hasWorkspacePermission(workspaceRole, Permission.MANAGE_WORKSPACE_MEMBERS),
    canSwitch: hasPermission(userRole, Permission.SWITCH_WORKSPACE) || 
               hasWorkspacePermission(workspaceRole, Permission.SWITCH_WORKSPACE)
  }), [userRole, tenantRole, workspaceRole]);

  return {
    userRole,
    roleDisplayName: getRoleDisplayName(userRole),
    tenantRole,
    tenantRoleDisplayName: getTenantRoleDisplayName(tenantRole),
    workspaceRole,
    workspaceRoleDisplayName: getWorkspaceRoleDisplayName(workspaceRole),
    tenantContext,
    permissions,
    checkPermission,
    checkPermissionWithIsolation,
    canAccessTenantResource,
    canAccessWorkspaceResource,
    checkTenantAccess,
    checkWorkspaceAccess,
    annotation: annotationPermissions,
    task: taskPermissions,
    project: projectPermissions,
    quality: qualityPermissions,
    system: systemPermissions,
    tenant: tenantPermissions,
    workspace: workspacePermissions
  };
};

export default usePermissions;