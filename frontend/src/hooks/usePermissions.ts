// 权限检查Hook
import { useMemo } from 'react';
import { useAuthStore } from '@/stores/authStore';
import {
  Permission,
  hasPermission,
  canAccessAnnotation,
  canCreateAnnotation,
  canEditAnnotation,
  canDeleteAnnotation,
  canManageTasks,
  canManageProjects,
  canExportData,
  getUserPermissions,
  getRoleDisplayName
} from '@/utils/permissions';

export const usePermissions = () => {
  const { user } = useAuthStore();
  const userRole = user?.role || '';

  const permissions = useMemo(() => {
    if (!userRole) return [];
    return getUserPermissions(userRole);
  }, [userRole]);

  const checkPermission = useMemo(() => {
    return (permission: Permission) => {
      if (!userRole) return false;
      return hasPermission(userRole, permission);
    };
  }, [userRole]);

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

  return {
    userRole,
    roleDisplayName: getRoleDisplayName(userRole),
    permissions,
    checkPermission,
    annotation: annotationPermissions,
    task: taskPermissions,
    project: projectPermissions,
    quality: qualityPermissions,
    system: systemPermissions
  };
};

export default usePermissions;