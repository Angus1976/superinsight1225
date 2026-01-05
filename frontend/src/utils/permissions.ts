// 角色权限管理工具
export enum UserRole {
  ADMIN = 'ADMIN',
  BUSINESS_EXPERT = 'BUSINESS_EXPERT', 
  ANNOTATOR = 'ANNOTATOR',
  VIEWER = 'VIEWER'
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
  SYSTEM_ADMIN = 'system_admin'
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
    Permission.SYSTEM_ADMIN
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
    Permission.EXPORT_DATA
  ],
  
  [UserRole.ANNOTATOR]: [
    // 标注员：主要进行标注工作
    Permission.VIEW_ANNOTATION,
    Permission.CREATE_ANNOTATION,
    Permission.EDIT_ANNOTATION,
    Permission.VIEW_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.VIEW_QUALITY
  ],
  
  [UserRole.VIEWER]: [
    // 查看者：只能查看
    Permission.VIEW_ANNOTATION,
    Permission.VIEW_TASKS,
    Permission.VIEW_PROJECTS,
    Permission.VIEW_QUALITY
  ]
};

// 检查用户是否有特定权限
export const hasPermission = (userRole: string, permission: Permission): boolean => {
  const role = userRole.toUpperCase() as UserRole;
  const permissions = ROLE_PERMISSIONS[role] || [];
  return permissions.includes(permission);
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

// 获取角色显示名称
export const getRoleDisplayName = (userRole: string): string => {
  const role = userRole.toUpperCase() as UserRole;
  return ROLE_DISPLAY_NAMES[role] || userRole;
};