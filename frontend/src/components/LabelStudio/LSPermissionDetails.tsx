/**
 * Label Studio Permission Details Component
 *
 * Displays role permission matrix with expand/collapse functionality.
 * Shows which permissions each role has in the workspace.
 */

import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Table,
  Tag,
  Collapse,
  Tooltip,
  Typography,
  Space,
  Card,
  Badge,
} from 'antd';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  InfoCircleOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  AuditOutlined,
  EditOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { WorkspaceMemberRole, WorkspacePermission } from '@/types/ls-workspace';

const { Text, Title } = Typography;
const { Panel } = Collapse;

// ============================================================================
// Types
// ============================================================================

export interface LSPermissionDetailsProps {
  /** Current user's role (optional, to highlight their permissions) */
  currentRole?: WorkspaceMemberRole;
  /** Show as compact card view */
  compact?: boolean;
  /** Show only specific roles */
  showRoles?: WorkspaceMemberRole[];
  /** Custom class name */
  className?: string;
}

interface PermissionCategory {
  key: string;
  titleKey: string;
  permissions: {
    key: WorkspacePermission;
    labelKey: string;
    descriptionKey: string;
  }[];
}

interface RoleInfo {
  role: WorkspaceMemberRole;
  labelKey: string;
  descriptionKey: string;
  color: string;
  icon: React.ReactNode;
}

interface PermissionRowData {
  key: string;
  permission: string;
  description: string;
  category: string;
  owner: boolean;
  admin: boolean;
  manager: boolean;
  reviewer: boolean;
  annotator: boolean;
}

// ============================================================================
// Permission Matrix Data
// ============================================================================

/** Permission categories with their permissions */
const PERMISSION_CATEGORIES: PermissionCategory[] = [
  {
    key: 'workspace',
    titleKey: 'lsWorkspace.permissions.categories.workspace',
    permissions: [
      {
        key: 'workspace:view',
        labelKey: 'lsWorkspace.permissions.workspace.view',
        descriptionKey: 'lsWorkspace.permissions.workspace.viewDesc',
      },
      {
        key: 'workspace:edit',
        labelKey: 'lsWorkspace.permissions.workspace.edit',
        descriptionKey: 'lsWorkspace.permissions.workspace.editDesc',
      },
      {
        key: 'workspace:delete',
        labelKey: 'lsWorkspace.permissions.workspace.delete',
        descriptionKey: 'lsWorkspace.permissions.workspace.deleteDesc',
      },
      {
        key: 'workspace:manage_members',
        labelKey: 'lsWorkspace.permissions.workspace.manageMembers',
        descriptionKey: 'lsWorkspace.permissions.workspace.manageMembersDesc',
      },
    ],
  },
  {
    key: 'project',
    titleKey: 'lsWorkspace.permissions.categories.project',
    permissions: [
      {
        key: 'project:view',
        labelKey: 'lsWorkspace.permissions.project.view',
        descriptionKey: 'lsWorkspace.permissions.project.viewDesc',
      },
      {
        key: 'project:create',
        labelKey: 'lsWorkspace.permissions.project.create',
        descriptionKey: 'lsWorkspace.permissions.project.createDesc',
      },
      {
        key: 'project:edit',
        labelKey: 'lsWorkspace.permissions.project.edit',
        descriptionKey: 'lsWorkspace.permissions.project.editDesc',
      },
      {
        key: 'project:delete',
        labelKey: 'lsWorkspace.permissions.project.delete',
        descriptionKey: 'lsWorkspace.permissions.project.deleteDesc',
      },
      {
        key: 'project:manage_members',
        labelKey: 'lsWorkspace.permissions.project.manageMembers',
        descriptionKey: 'lsWorkspace.permissions.project.manageMembersDesc',
      },
    ],
  },
  {
    key: 'task',
    titleKey: 'lsWorkspace.permissions.categories.task',
    permissions: [
      {
        key: 'task:view',
        labelKey: 'lsWorkspace.permissions.task.view',
        descriptionKey: 'lsWorkspace.permissions.task.viewDesc',
      },
      {
        key: 'task:annotate',
        labelKey: 'lsWorkspace.permissions.task.annotate',
        descriptionKey: 'lsWorkspace.permissions.task.annotateDesc',
      },
      {
        key: 'task:review',
        labelKey: 'lsWorkspace.permissions.task.review',
        descriptionKey: 'lsWorkspace.permissions.task.reviewDesc',
      },
      {
        key: 'task:assign',
        labelKey: 'lsWorkspace.permissions.task.assign',
        descriptionKey: 'lsWorkspace.permissions.task.assignDesc',
      },
    ],
  },
  {
    key: 'data',
    titleKey: 'lsWorkspace.permissions.categories.data',
    permissions: [
      {
        key: 'data:export',
        labelKey: 'lsWorkspace.permissions.data.export',
        descriptionKey: 'lsWorkspace.permissions.data.exportDesc',
      },
      {
        key: 'data:import',
        labelKey: 'lsWorkspace.permissions.data.import',
        descriptionKey: 'lsWorkspace.permissions.data.importDesc',
      },
    ],
  },
];

/** Role definitions */
const ROLES: RoleInfo[] = [
  {
    role: 'owner',
    labelKey: 'lsWorkspace.roles.owner',
    descriptionKey: 'lsWorkspace.roles.ownerDesc',
    color: 'gold',
    icon: <CrownOutlined />,
  },
  {
    role: 'admin',
    labelKey: 'lsWorkspace.roles.admin',
    descriptionKey: 'lsWorkspace.roles.adminDesc',
    color: 'purple',
    icon: <SafetyCertificateOutlined />,
  },
  {
    role: 'manager',
    labelKey: 'lsWorkspace.roles.manager',
    descriptionKey: 'lsWorkspace.roles.managerDesc',
    color: 'blue',
    icon: <TeamOutlined />,
  },
  {
    role: 'reviewer',
    labelKey: 'lsWorkspace.roles.reviewer',
    descriptionKey: 'lsWorkspace.roles.reviewerDesc',
    color: 'green',
    icon: <AuditOutlined />,
  },
  {
    role: 'annotator',
    labelKey: 'lsWorkspace.roles.annotator',
    descriptionKey: 'lsWorkspace.roles.annotatorDesc',
    color: 'default',
    icon: <EditOutlined />,
  },
];

/** Permission matrix: which role has which permission */
const ROLE_PERMISSIONS: Record<WorkspaceMemberRole, WorkspacePermission[]> = {
  owner: [
    'workspace:view',
    'workspace:edit',
    'workspace:delete',
    'workspace:manage_members',
    'project:view',
    'project:create',
    'project:edit',
    'project:delete',
    'project:manage_members',
    'task:view',
    'task:annotate',
    'task:review',
    'task:assign',
    'data:export',
    'data:import',
  ],
  admin: [
    'workspace:view',
    'workspace:edit',
    'workspace:manage_members',
    'project:view',
    'project:create',
    'project:edit',
    'project:delete',
    'project:manage_members',
    'task:view',
    'task:annotate',
    'task:review',
    'task:assign',
    'data:export',
    'data:import',
  ],
  manager: [
    'workspace:view',
    'project:view',
    'project:create',
    'project:edit',
    'project:manage_members',
    'task:view',
    'task:annotate',
    'task:review',
    'task:assign',
    'data:export',
  ],
  reviewer: [
    'workspace:view',
    'project:view',
    'task:view',
    'task:annotate',
    'task:review',
    'data:export',
  ],
  annotator: [
    'workspace:view',
    'project:view',
    'task:view',
    'task:annotate',
  ],
};

// ============================================================================
// Helper Functions
// ============================================================================

const hasPermission = (role: WorkspaceMemberRole, permission: WorkspacePermission): boolean => {
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
};

// ============================================================================
// Component
// ============================================================================

/**
 * LSPermissionDetails - Role permission matrix component
 *
 * Displays a comprehensive view of workspace roles and their permissions.
 * Supports expand/collapse for permission categories and highlights
 * the current user's role.
 */
export const LSPermissionDetails: React.FC<LSPermissionDetailsProps> = ({
  currentRole,
  compact = false,
  showRoles,
  className,
}) => {
  const { t } = useTranslation();
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['workspace', 'project']);

  // Filter roles if specified
  const displayRoles = useMemo(() => {
    if (showRoles && showRoles.length > 0) {
      return ROLES.filter((r) => showRoles.includes(r.role));
    }
    return ROLES;
  }, [showRoles]);

  // Build table data
  const tableData = useMemo((): PermissionRowData[] => {
    const data: PermissionRowData[] = [];

    PERMISSION_CATEGORIES.forEach((category) => {
      category.permissions.forEach((perm) => {
        data.push({
          key: perm.key,
          permission: t(perm.labelKey),
          description: t(perm.descriptionKey),
          category: t(category.titleKey),
          owner: hasPermission('owner', perm.key),
          admin: hasPermission('admin', perm.key),
          manager: hasPermission('manager', perm.key),
          reviewer: hasPermission('reviewer', perm.key),
          annotator: hasPermission('annotator', perm.key),
        });
      });
    });

    return data;
  }, [t]);

  // Build table columns
  const columns = useMemo((): ColumnsType<PermissionRowData> => {
    const permissionColumn: ColumnsType<PermissionRowData>[0] = {
      title: t('lsWorkspace.permissions.permission'),
      dataIndex: 'permission',
      key: 'permission',
      fixed: 'left',
      width: 200,
      render: (text: string, record: PermissionRowData) => (
        <Tooltip title={record.description}>
          <Space>
            <Text>{text}</Text>
            <InfoCircleOutlined style={{ color: '#999', fontSize: 12 }} />
          </Space>
        </Tooltip>
      ),
    };

    const roleColumns: ColumnsType<PermissionRowData> = displayRoles.map((roleInfo) => ({
      title: (
        <Tooltip title={t(roleInfo.descriptionKey)}>
          <Space direction="vertical" size={0} align="center">
            <Tag
              color={roleInfo.color}
              icon={roleInfo.icon}
              style={currentRole === roleInfo.role ? { border: '2px solid #1890ff' } : undefined}
            >
              {t(roleInfo.labelKey)}
            </Tag>
          </Space>
        </Tooltip>
      ),
      dataIndex: roleInfo.role,
      key: roleInfo.role,
      align: 'center' as const,
      width: 100,
      render: (hasAccess: boolean) =>
        hasAccess ? (
          <CheckCircleFilled style={{ color: '#52c41a', fontSize: 18 }} />
        ) : (
          <CloseCircleFilled style={{ color: '#ff4d4f', fontSize: 18 }} />
        ),
    }));

    return [permissionColumn, ...roleColumns];
  }, [t, displayRoles, currentRole]);

  // Render compact card view
  if (compact) {
    return (
      <Card className={className} size="small">
        <Title level={5}>{t('lsWorkspace.permissions.title')}</Title>
        <Collapse
          activeKey={expandedCategories}
          onChange={(keys) => setExpandedCategories(keys as string[])}
          ghost
        >
          {PERMISSION_CATEGORIES.map((category) => (
            <Panel
              header={
                <Badge
                  count={category.permissions.length}
                  style={{ backgroundColor: '#1890ff' }}
                  offset={[10, 0]}
                >
                  <Text strong>{t(category.titleKey)}</Text>
                </Badge>
              }
              key={category.key}
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                {category.permissions.map((perm) => (
                  <div
                    key={perm.key}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '4px 0',
                    }}
                  >
                    <Tooltip title={t(perm.descriptionKey)}>
                      <Text>{t(perm.labelKey)}</Text>
                    </Tooltip>
                    <Space size={4}>
                      {displayRoles.map((roleInfo) => (
                        <Tooltip
                          key={roleInfo.role}
                          title={t(roleInfo.labelKey)}
                        >
                          {hasPermission(roleInfo.role, perm.key) ? (
                            <Tag
                              color={roleInfo.color}
                              style={{
                                margin: 0,
                                minWidth: 24,
                                textAlign: 'center',
                                opacity: currentRole === roleInfo.role ? 1 : 0.6,
                              }}
                            >
                              {roleInfo.icon}
                            </Tag>
                          ) : (
                            <Tag
                              style={{
                                margin: 0,
                                minWidth: 24,
                                textAlign: 'center',
                                opacity: 0.3,
                              }}
                            >
                              -
                            </Tag>
                          )}
                        </Tooltip>
                      ))}
                    </Space>
                  </div>
                ))}
              </Space>
            </Panel>
          ))}
        </Collapse>
      </Card>
    );
  }

  // Render full table view
  return (
    <div className={className}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div>
          <Title level={4}>{t('lsWorkspace.permissions.title')}</Title>
          <Text type="secondary">{t('lsWorkspace.permissions.subtitle')}</Text>
        </div>

        {/* Role Legend */}
        <Card size="small">
          <Space wrap>
            {displayRoles.map((roleInfo) => (
              <Tooltip key={roleInfo.role} title={t(roleInfo.descriptionKey)}>
                <Tag
                  color={roleInfo.color}
                  icon={roleInfo.icon}
                  style={{
                    cursor: 'help',
                    ...(currentRole === roleInfo.role
                      ? { border: '2px solid #1890ff', fontWeight: 'bold' }
                      : {}),
                  }}
                >
                  {t(roleInfo.labelKey)}
                  {currentRole === roleInfo.role && (
                    <Text style={{ marginLeft: 4, fontSize: 10 }}>
                      ({t('lsWorkspace.permissions.currentRole')})
                    </Text>
                  )}
                </Tag>
              </Tooltip>
            ))}
          </Space>
        </Card>

        {/* Permission Matrix Table */}
        <Table<PermissionRowData>
          columns={columns}
          dataSource={tableData}
          pagination={false}
          size="small"
          bordered
          scroll={{ x: 'max-content' }}
          rowClassName={(record) => {
            // Highlight row if current role has this permission
            if (currentRole && record[currentRole]) {
              return 'permission-row-highlight';
            }
            return '';
          }}
        />

        {/* Permission Count Summary */}
        <Card size="small">
          <Space wrap size={[16, 8]}>
            {displayRoles.map((roleInfo) => {
              const permCount = ROLE_PERMISSIONS[roleInfo.role].length;
              const totalPerms = 15; // Total permissions
              return (
                <Tooltip
                  key={roleInfo.role}
                  title={t('lsWorkspace.permissions.permissionCount', {
                    count: permCount,
                    total: totalPerms,
                  })}
                >
                  <Tag
                    color={roleInfo.color}
                    style={currentRole === roleInfo.role ? { border: '2px solid #1890ff' } : undefined}
                  >
                    {roleInfo.icon} {t(roleInfo.labelKey)}: {permCount}/{totalPerms}
                  </Tag>
                </Tooltip>
              );
            })}
          </Space>
        </Card>
      </Space>

      <style>{`
        .permission-row-highlight {
          background-color: #e6f7ff !important;
        }
        .permission-row-highlight:hover > td {
          background-color: #bae7ff !important;
        }
      `}</style>
    </div>
  );
};

// Export for testing
export { ROLE_PERMISSIONS, PERMISSION_CATEGORIES, ROLES, hasPermission };

export default LSPermissionDetails;
