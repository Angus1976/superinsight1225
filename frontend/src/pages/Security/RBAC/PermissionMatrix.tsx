/**
 * Permission Matrix Component for RBAC Management
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Table,
  Checkbox,
  Tag,
  Space,
  Select,
  Typography,
  Tooltip,
  Button,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { rbacApi, Role, Permission } from '@/services/rbacApi';

const { Text, Title } = Typography;

// Resource definitions
const RESOURCES = [
  { key: 'projects', label: 'Projects' },
  { key: 'tasks', label: 'Tasks' },
  { key: 'annotations', label: 'Annotations' },
  { key: 'users', label: 'Users' },
  { key: 'billing', label: 'Billing' },
  { key: 'reports', label: 'Reports' },
  { key: 'settings', label: 'Settings' },
  { key: 'admin', label: 'Admin' },
];

const ACTIONS = ['read', 'write', 'delete', '*'];

interface PermissionCell {
  resource: string;
  action: string;
  hasPermission: boolean;
  isWildcard: boolean;
  isInherited: boolean;
}

const PermissionMatrix: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<Map<string, boolean>>(new Map());
  const queryClient = useQueryClient();

  // Fetch roles
  const { data: roles = [], isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rbacApi.listRoles(),
  });

  // Update role mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, permissions }: { id: string; permissions: Permission[] }) =>
      rbacApi.updateRole(id, { permissions }),
    onSuccess: () => {
      message.success('Permissions updated successfully');
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setPendingChanges(new Map());
    },
    onError: () => {
      message.error('Failed to update permissions');
    },
  });

  const currentRole = useMemo(
    () => roles.find((r) => r.id === selectedRole),
    [roles, selectedRole]
  );

  // Build permission matrix for current role
  const permissionMatrix = useMemo(() => {
    if (!currentRole) return [];

    const matrix: PermissionCell[][] = [];
    const permissions = currentRole.permissions;

    // Check for wildcard permissions
    const hasAllAccess = permissions.some(
      (p) => p.resource === '*' && p.action === '*'
    );
    const resourceWildcards = new Set(
      permissions.filter((p) => p.action === '*').map((p) => p.resource)
    );
    const actionWildcards = new Set(
      permissions.filter((p) => p.resource === '*').map((p) => p.action)
    );

    for (const resource of RESOURCES) {
      const row: PermissionCell[] = [];
      for (const action of ACTIONS) {
        const key = `${resource.key}:${action}`;
        const pendingValue = pendingChanges.get(key);

        // Check if permission exists
        const directPermission = permissions.some(
          (p) => p.resource === resource.key && p.action === action
        );

        // Check wildcards
        const isWildcard =
          hasAllAccess ||
          resourceWildcards.has(resource.key) ||
          actionWildcards.has(action) ||
          resourceWildcards.has('*');

        const hasPermission =
          pendingValue !== undefined
            ? pendingValue
            : directPermission || isWildcard;

        row.push({
          resource: resource.key,
          action,
          hasPermission,
          isWildcard: isWildcard && !directPermission,
          isInherited: false, // TODO: Check parent role
        });
      }
      matrix.push(row);
    }

    return matrix;
  }, [currentRole, pendingChanges]);

  const handlePermissionChange = (resource: string, action: string, checked: boolean) => {
    const key = `${resource}:${action}`;
    const newChanges = new Map(pendingChanges);
    newChanges.set(key, checked);
    setPendingChanges(newChanges);
  };

  const handleSaveChanges = () => {
    if (!currentRole) return;

    // Build new permissions list
    const newPermissions: Permission[] = [];

    for (const resource of RESOURCES) {
      for (const action of ACTIONS) {
        const key = `${resource.key}:${action}`;
        const pendingValue = pendingChanges.get(key);
        const currentValue = currentRole.permissions.some(
          (p) => p.resource === resource.key && p.action === action
        );

        const shouldHave = pendingValue !== undefined ? pendingValue : currentValue;
        if (shouldHave) {
          newPermissions.push({ resource: resource.key, action });
        }
      }
    }

    updateMutation.mutate({ id: currentRole.id, permissions: newPermissions });
  };

  const columns = [
    {
      title: 'Resource',
      dataIndex: 'resource',
      key: 'resource',
      fixed: 'left' as const,
      width: 150,
      render: (_: unknown, __: unknown, index: number) => (
        <Text strong>{RESOURCES[index].label}</Text>
      ),
    },
    ...ACTIONS.map((action) => ({
      title: (
        <Tooltip title={action === '*' ? 'All actions' : `${action} permission`}>
          <span>{action === '*' ? 'All' : action.charAt(0).toUpperCase() + action.slice(1)}</span>
        </Tooltip>
      ),
      key: action,
      width: 100,
      align: 'center' as const,
      render: (_: unknown, __: unknown, rowIndex: number) => {
        const cell = permissionMatrix[rowIndex]?.find((c) => c.action === action);
        if (!cell) return null;

        return (
          <Tooltip
            title={
              cell.isWildcard
                ? 'Granted via wildcard'
                : cell.isInherited
                ? 'Inherited from parent role'
                : ''
            }
          >
            <Checkbox
              checked={cell.hasPermission}
              onChange={(e) =>
                handlePermissionChange(cell.resource, cell.action, e.target.checked)
              }
              disabled={!selectedRole}
            />
            {cell.isWildcard && (
              <Tag color="purple" style={{ marginLeft: 4, fontSize: 10 }}>
                *
              </Tag>
            )}
          </Tooltip>
        );
      },
    })),
  ];

  return (
    <Card
      title={
        <Space>
          <Title level={5} style={{ margin: 0 }}>
            Permission Matrix
          </Title>
          <Tooltip title="Configure permissions for each role by resource and action">
            <QuestionCircleOutlined />
          </Tooltip>
        </Space>
      }
      extra={
        <Space>
          <Select
            placeholder="Select a role"
            style={{ width: 200 }}
            value={selectedRole}
            onChange={setSelectedRole}
            loading={isLoading}
            options={roles.map((r) => ({ label: r.name, value: r.id }))}
            allowClear
          />
          {pendingChanges.size > 0 && (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSaveChanges}
              loading={updateMutation.isPending}
            >
              Save Changes ({pendingChanges.size})
            </Button>
          )}
        </Space>
      }
    >
      {!selectedRole ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          Select a role to view and edit its permissions
        </div>
      ) : (
        <>
          <Table
            columns={columns}
            dataSource={RESOURCES.map((r, i) => ({ ...r, key: r.key, index: i }))}
            pagination={false}
            bordered
            size="small"
          />

          <div style={{ marginTop: 16 }}>
            <Space>
              <Tag icon={<CheckCircleOutlined />} color="success">
                Direct Permission
              </Tag>
              <Tag color="purple">* Wildcard</Tag>
              <Tag icon={<CloseCircleOutlined />} color="default">
                No Permission
              </Tag>
            </Space>
          </div>
        </>
      )}
    </Card>
  );
};

export default PermissionMatrix;
