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
import { useTranslation } from 'react-i18next';
import { rbacApi, Role, Permission } from '@/services/rbacApi';

const { Text, Title } = Typography;

const ACTIONS = ['read', 'write', 'delete', '*'];

interface PermissionCell {
  resource: string;
  action: string;
  hasPermission: boolean;
  isWildcard: boolean;
  isInherited: boolean;
}

const PermissionMatrix: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<Map<string, boolean>>(new Map());
  const queryClient = useQueryClient();

  // Resource definitions with i18n
  const RESOURCES = [
    { key: 'projects', label: t('rbac.resources.projects') },
    { key: 'tasks', label: t('rbac.resources.tasks') },
    { key: 'annotations', label: t('rbac.resources.annotations') },
    { key: 'users', label: t('rbac.resources.users') },
    { key: 'billing', label: t('rbac.resources.billing') },
    { key: 'reports', label: t('rbac.resources.reports') },
    { key: 'settings', label: t('rbac.resources.settings') },
    { key: 'admin', label: t('rbac.resources.admin') },
  ];

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
      message.success(t('rbac.permissionsUpdated'));
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      setPendingChanges(new Map());
    },
    onError: () => {
      message.error(t('rbac.permissionsUpdateFailed'));
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
      title: t('audit.resource'),
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
        <Tooltip title={action === '*' ? t('rbac.actions.all') : t(`rbac.actions.${action}`)}>
          <span>{action === '*' ? t('rbac.actions.all') : t(`rbac.actions.${action}`)}</span>
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
                ? t('rbac.grantedViaWildcard')
                : cell.isInherited
                ? t('rbac.inheritedFromParent')
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
            {t('rbac.permissionMatrix')}
          </Title>
          <Tooltip title={t('rbac.selectRoleHint')}>
            <QuestionCircleOutlined />
          </Tooltip>
        </Space>
      }
      extra={
        <Space>
          <Select
            placeholder={t('rbac.selectRole')}
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
              {t('rbac.saveChanges')} ({pendingChanges.size})
            </Button>
          )}
        </Space>
      }
    >
      {!selectedRole ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          {t('rbac.selectRoleHint')}
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
                {t('rbac.directPermission')}
              </Tag>
              <Tag color="purple">* {t('rbac.wildcard')}</Tag>
              <Tag icon={<CloseCircleOutlined />} color="default">
                {t('rbac.noPermission')}
              </Tag>
            </Space>
          </div>
        </>
      )}
    </Card>
  );
};

export default PermissionMatrix;
