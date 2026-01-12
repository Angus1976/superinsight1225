// 角色权限管理工具
export enum UserRole {
  ADMIN = 'ADMIN',
  BUSINESS_EXPERT = 'BUSINESS_EXPERT', 
  ANNOTATOR = 'ANNOTATOR',
  VIEWER = 'VIEWER'
}

// 租户角色枚举
export enum TenantRole {
  TENANT_ADMIN = 'TENANT_ADMIN',
  TENANT_MANAGER = 'TENANT_MANAGER',
  TENANT_MEMBER = 'TENANT_MEMBER',
  TENANT_VIEWER = 'TENANT_VIEWER'
}

// 工作空间角色枚举
export enum WorkspaceRole {
  WORKSPACE_OWNER = 'WORKSPACE_OWNER',
  WORKSPACE_ADMIN = 'WORKSPACE_ADMIN',
  WORKSPACE_MEMBER = 'WORKSPACE_MEMBER',
  WORKSPACE_VIEWER = 'WORKSPACE_VIEWER'
}

export enum Permission {
  // 标注相关权限
  VIEW_ANNOTATION = 'view_annotation',
  CREATE_ANNOTATION = 'create_annotation',
  EDIT_ANNOTATION = 'edit_annotation',
  DELETE_ANNOTATION = 'delete_annotation',
  
  // 任务管理权限
  VIEW_TASKS = 'view_tasks',
  CREATE_TASKS = 'create_tasks',
  EDIT_TASKS = 'edit_tasks',
  DELETE_TASKS = 'delete_tasks',
  
  // 项目管理权限
  VIEW_PROJECTS = 'view_projects',
  CREATE_PROJECTS = 'create_projects',
  EDIT_PROJECTS = 'edit_projects',
  DELETE_PROJECTS = 'delete_projects',
  
  // 用户管理权限
  VIEW_USERS = 'view_users',
  CREATE_USERS = 'create_users',
  EDIT_USERS = 'edit_users',
  DELETE_USERS = 'delete_users',
  
  // 质量管理权限
  VIEW_QUALITY = 'view_quality',
  MANAGE_QUALITY = 'manage_quality',
  
  // 数据导出权限
  EXPORT_DATA = 'export_data',
  
  // 系统管理权限
  SYSTEM_ADMIN = 'system_admin',
  
  // 租户管理权限
  VIEW_TENANT = 'view_tenant',
  MANAGE_TENANT = 'manage_tenant',
  SWITCH_TENANT = 'switch_tenant',
  
  // 工作空间管理权限
  VIEW_WORKSPACE = 'view_workspace',
  CREATE_WORKSPACE = 'create_workspace',
  EDIT_WORKSPACE = 'edit_workspace',
  DELETE_WORKSPACE = 'delete_workspace',
  MANAGE_WORKSPACE_MEMBERS = 'manage_workspace_members',
  SWITCH_WORKSPACE = 'switch_workspace'
}

// 角色权限映射
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  [UserRole.ADMIN]: [
    // 管理员拥有所有权限
    Permission.VIEW_ANNOTATION,
    Permission.CREATE_ANNOTATION,
    Permission.EDIT_ANNOTATION,
    Permission.DELETE_ANNOTATION,
    Permission.VIEW_TASKS,
    Permission.CREATE_TASKS,
    Permission.EDIT_TASKS,
    Permission.DELETE_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECTS,
    Permission.EDIT_PROJECTS,
    Permission.DELETE_PROJECTS,
    Permission.VIEW_USERS,
    Permission.CREATE_USERS,
    Permission.EDIT_USERS,
    Permission.DELETE_USERS,
    Permission.VIEW_QUALITY,
    Permission.MANAGE_QUALITY,
    Permission.EXPORT_DATA,
    Permission.SYSTEM_ADMIN,
    // 租户和工作空间权限
    Permission.VIEW_TENANT,
    Permission.MANAGE_TENANT,
    Permission.SWITCH_TENANT,
    Permission.VIEW_WORKSPACE,
    Permission.CREATE_WORKSPACE,
    Permission.EDIT_WORKSPACE,
    Permission.DELETE_WORKSPACE,
    Permission.MANAGE_WORKSPACE_MEMBERS,
    Permission.SWITCH_WORKSPACE
  ],
  
  [UserRole.BUSINESS_EXPERT]: [
    // 业务专家：可以查看、创建和编辑标注，管理任务和项目
    Permission.VIEW_ANNOTATION,
    Permission.CREATE_ANNOTATION,
    Permission.EDIT_ANNOTATION,
    Permission.VIEW_TASKS,
    Permission.CREATE_TASKS,
    Permission.EDIT_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECTS,
    Permission.EDIT_PROJECTS,
    Permission.VIEW_QUALITY,
    Permission.MANAGE_QUALITY,
    Permission.EXPORT_DATA,
    // 工作空间权限
    Permission.VIEW_WORKSPACE,
    Permission.CREATE_WORKSPACE,
    Permission.EDIT_WORKSPACE,
    Permission.MANAGE_WORKSPACE_MEMBERS,
    Permission.SWITCH_WORKSPACE
  ],
  
  [UserRole.ANNOTATOR]: [
    // 标注员：主要进行标注工作
    Permission.VIEW_ANNOTATION,
    Permission.CREATE_ANNOTATION,
    Permission.EDIT_ANNOTATION,
    Permission.VIEW_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.VIEW_QUALITY,
    // 工作空间权限
    Permission.VIEW_WORKSPACE,
    Permission.SWITCH_WORKSPACE
  ],
  
  [UserRole.VIEWER]: [
    // 查看者：只能查看
    Permission.VIEW_ANNOTATION,
    Permission.VIEW_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.VIEW_QUALITY,
    // 工作空间权限
    Permission.VIEW_WORKSPACE,
    Permission.SWITCH_WORKSPACE
  ]
};

// 租户角色权限映射
export const TENANT_ROLE_PERMISSIONS: Record<TenantRole, Permission[]> = {
  [TenantRole.TENANT_ADMIN]: [
    Permission.VIEW_TENANT,
    Permission.MANAGE_TENANT,
    Permission.SWITCH_TENANT,
    Permission.VIEW_WORKSPACE,
    Permission.CREATE_WORKSPACE,
    Permission.EDIT_WORKSPACE,
    Permission.DELETE_WORKSPACE,
    Permission.MANAGE_WORKSPACE_MEMBERS,
    Permission.SWITCH_WORKSPACE,
    Permission.VIEW_USERS,
    Permission.CREATE_USERS,
    Permission.EDIT_USERS,
    Permission.DELETE_USERS
  ],
  [TenantRole.TENANT_MANAGER]: [
    Permission.VIEW_TENANT,
    Permission.SWITCH_TENANT,
    Permission.VIEW_WORKSPACE,
    Permission.CREATE_WORKSPACE,
    Permission.EDIT_WORKSPACE,
    Permission.MANAGE_WORKSPACE_MEMBERS,
    Permission.SWITCH_WORKSPACE,
    Permission.VIEW_USERS,
    Permission.EDIT_USERS
  ],
  [TenantRole.TENANT_MEMBER]: [
    Permission.VIEW_TENANT,
    Permission.VIEW_WORKSPACE,
    Permission.SWITCH_WORKSPACE
  ],
  [TenantRole.TENANT_VIEWER]: [
    Permission.VIEW_TENANT,
    Permission.VIEW_WORKSPACE
  ]
};

// 工作空间角色权限映射
export const WORKSPACE_ROLE_PERMISSIONS: Record<WorkspaceRole, Permission[]> = {
  [WorkspaceRole.WORKSPACE_OWNER]: [
    Permission.VIEW_WORKSPACE,
    Permission.EDIT_WORKSPACE,
    Permission.DELETE_WORKSPACE,
    Permission.MANAGE_WORKSPACE_MEMBERS,
    Permission.VIEW_TASKS,
    Permission.CREATE_TASKS,
    Permission.EDIT_TASKS,
    Permission.DELETE_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECTS,
    Permission.EDIT_PROJECTS,
    Permission.DELETE_PROJECTS,
    Permission.EXPORT_DATA
  ],
  [WorkspaceRole.WORKSPACE_ADMIN]: [
    Permission.VIEW_WORKSPACE,
    Permission.EDIT_WORKSPACE,
    Permission.MANAGE_WORKSPACE_MEMBERS,
    Permission.VIEW_TASKS,
    Permission.CREATE_TASKS,
    Permission.EDIT_TASKS,
    Permission.DELETE_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.CREATE_PROJECTS,
    Permission.EDIT_PROJECTS,
    Permission.DELETE_PROJECTS,
    Permission.EXPORT_DATA
  ],
  [WorkspaceRole.WORKSPACE_MEMBER]: [
    Permission.VIEW_WORKSPACE,
    Permission.VIEW_TASKS,
    Permission.CREATE_TASKS,
    Permission.EDIT_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.VIEW_ANNOTATION,
    Permission.CREATE_ANNOTATION,
    Permission.EDIT_ANNOTATION
  ],
  [WorkspaceRole.WORKSPACE_VIEWER]: [
    Permission.VIEW_WORKSPACE,
    Permission.VIEW_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.VIEW_ANNOTATION
  ]
};

// 检查用户是否有特定权限
export const hasPermission = (userRole: string, permission: Permission): boolean => {
  const role = userRole.toUpperCase() as UserRole;
  const permissions = ROLE_PERMISSIONS[role] || [];
  return permissions.includes(permission);
};

// 租户隔离上下文接口
export interface TenantContext {
  tenantId: string;
  tenantRole?: TenantRole;
  workspaceId?: string;
  workspaceRole?: WorkspaceRole;
}

// 资源访问上下文接口
export interface ResourceContext {
  resourceTenantId: string;
  resourceWorkspaceId?: string;
  resourceOwnerId?: string;
}

// 检查租户级别权限
export const hasTenantPermission = (
  tenantRole: string | undefined,
  permission: Permission
): boolean => {
  if (!tenantRole) return false;
  const role = tenantRole.toUpperCase() as TenantRole;
  const permissions = TENANT_ROLE_PERMISSIONS[role] || [];
  return permissions.includes(permission);
};

// 检查工作空间级别权限
export const hasWorkspacePermission = (
  workspaceRole: string | undefined,
  permission: Permission
): boolean => {
  if (!workspaceRole) return false;
  const role = workspaceRole.toUpperCase() as WorkspaceRole;
  const permissions = WORKSPACE_ROLE_PERMISSIONS[role] || [];
  return permissions.includes(permission);
};

// 检查租户隔离 - 确保用户只能访问自己租户的资源
export const checkTenantIsolation = (
  userTenantId: string | undefined,
  resourceTenantId: string | undefined
): boolean => {
  // 如果没有租户ID，拒绝访问
  if (!userTenantId || !resourceTenantId) {
    return false;
  }
  // 用户只能访问自己租户的资源
  return userTenantId === resourceTenantId;
};

// 检查工作空间隔离 - 确保用户只能访问自己工作空间的资源
export const checkWorkspaceIsolation = (
  userWorkspaceId: string | undefined,
  resourceWorkspaceId: string | undefined
): boolean => {
  // 如果资源没有工作空间限制，允许访问
  if (!resourceWorkspaceId) {
    return true;
  }
  // 如果用户没有当前工作空间，拒绝访问
  if (!userWorkspaceId) {
    return false;
  }
  // 用户只能访问自己工作空间的资源
  return userWorkspaceId === resourceWorkspaceId;
};

// 综合权限检查 - 包含租户隔离
export const checkPermissionWithTenantIsolation = (
  userRole: string,
  permission: Permission,
  tenantContext: TenantContext,
  resourceContext: ResourceContext
): boolean => {
  // 1. 首先检查租户隔离
  if (!checkTenantIsolation(tenantContext.tenantId, resourceContext.resourceTenantId)) {
    return false;
  }
  
  // 2. 检查工作空间隔离（如果适用）
  if (resourceContext.resourceWorkspaceId) {
    if (!checkWorkspaceIsolation(tenantContext.workspaceId, resourceContext.resourceWorkspaceId)) {
      return false;
    }
  }
  
  // 3. 检查基本角色权限
  if (hasPermission(userRole, permission)) {
    return true;
  }
  
  // 4. 检查租户角色权限
  if (tenantContext.tenantRole && hasTenantPermission(tenantContext.tenantRole, permission)) {
    return true;
  }
  
  // 5. 检查工作空间角色权限
  if (tenantContext.workspaceRole && hasWorkspacePermission(tenantContext.workspaceRole, permission)) {
    return true;
  }
  
  return false;
};

// 检查是否可以访问特定租户
export const canAccessTenant = (
  userTenantId: string | undefined,
  targetTenantId: string,
  userRole: string
): boolean => {
  // 系统管理员可以访问所有租户
  if (hasPermission(userRole, Permission.SYSTEM_ADMIN)) {
    return true;
  }
  // 其他用户只能访问自己的租户
  return checkTenantIsolation(userTenantId, targetTenantId);
};

// 检查是否可以访问特定工作空间
export const canAccessWorkspace = (
  userTenantId: string | undefined,
  userWorkspaceIds: string[],
  targetWorkspaceId: string,
  targetTenantId: string,
  userRole: string
): boolean => {
  // 首先检查租户隔离
  if (!canAccessTenant(userTenantId, targetTenantId, userRole)) {
    return false;
  }
  // 系统管理员可以访问所有工作空间
  if (hasPermission(userRole, Permission.SYSTEM_ADMIN)) {
    return true;
  }
  // 检查用户是否是工作空间成员
  return userWorkspaceIds.includes(targetWorkspaceId);
};

// 检查用户是否可以访问标注功能
export const canAccessAnnotation = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.VIEW_ANNOTATION);
};

// 检查用户是否可以创建标注
export const canCreateAnnotation = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.CREATE_ANNOTATION);
};

// 检查用户是否可以编辑标注
export const canEditAnnotation = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.EDIT_ANNOTATION);
};

// 检查用户是否可以删除标注
export const canDeleteAnnotation = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.DELETE_ANNOTATION);
};

// 检查用户是否可以管理任务
export const canManageTasks = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.CREATE_TASKS) || 
         hasPermission(userRole, Permission.EDIT_TASKS);
};

// 检查用户是否可以管理项目
export const canManageProjects = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.CREATE_PROJECTS) || 
         hasPermission(userRole, Permission.EDIT_PROJECTS);
};

// 检查用户是否可以导出数据
export const canExportData = (userRole: string): boolean => {
  return hasPermission(userRole, Permission.EXPORT_DATA);
};

// 获取用户的所有权限
export const getUserPermissions = (userRole: string): Permission[] => {
  const role = userRole.toUpperCase() as UserRole;
  return ROLE_PERMISSIONS[role] || [];
};

// 角色显示名称映射
export const ROLE_DISPLAY_NAMES: Record<UserRole, string> = {
  [UserRole.ADMIN]: '系统管理员',
  [UserRole.BUSINESS_EXPERT]: '业务专家',
  [UserRole.ANNOTATOR]: '数据标注员',
  [UserRole.VIEWER]: '报表查看者'
};

// 租户角色显示名称映射
export const TENANT_ROLE_DISPLAY_NAMES: Record<TenantRole, string> = {
  [TenantRole.TENANT_ADMIN]: '租户管理员',
  [TenantRole.TENANT_MANAGER]: '租户经理',
  [TenantRole.TENANT_MEMBER]: '租户成员',
  [TenantRole.TENANT_VIEWER]: '租户查看者'
};

// 工作空间角色显示名称映射
export const WORKSPACE_ROLE_DISPLAY_NAMES: Record<WorkspaceRole, string> = {
  [WorkspaceRole.WORKSPACE_OWNER]: '工作空间所有者',
  [WorkspaceRole.WORKSPACE_ADMIN]: '工作空间管理员',
  [WorkspaceRole.WORKSPACE_MEMBER]: '工作空间成员',
  [WorkspaceRole.WORKSPACE_VIEWER]: '工作空间查看者'
};

// 获取角色显示名称
export const getRoleDisplayName = (userRole: string): string => {
  const role = userRole.toUpperCase() as UserRole;
  return ROLE_DISPLAY_NAMES[role] || userRole;
};

// 获取租户角色显示名称
export const getTenantRoleDisplayName = (tenantRole: string): string => {
  const role = tenantRole.toUpperCase() as TenantRole;
  return TENANT_ROLE_DISPLAY_NAMES[role] || tenantRole;
};

// 获取工作空间角色显示名称
export const getWorkspaceRoleDisplayName = (workspaceRole: string): string => {
  const role = workspaceRole.toUpperCase() as WorkspaceRole;
  return WORKSPACE_ROLE_DISPLAY_NAMES[role] || workspaceRole;
};