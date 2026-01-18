/**
 * Permission Configuration Page
 * 
 * Provides permission management including:
 * - Permission matrix view
 * - Role-based permission configuration
 * - API permission configuration
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card, Table, Switch, Tag, Space, Button, Select, Tabs, 
  message, Checkbox, Row, Col, Descriptions, Alert
} from 'antd';
import { 
  SafetyOutlined, ApiOutlined, TeamOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tenantApi, Tenant } from '@/services/multiTenantApi';

// Permission definitions - using translation keys
const getPermissions = (t: any) => ({
  workspace: [
    { key: 'workspace.create', name: t('permissionConfig.permissions.workspace.create'), description: t('permissionConfig.permissions.workspace.createDesc') },
    { key: 'workspace.read', name: t('permissionConfig.permissions.workspace.read'), description: t('permissionConfig.permissions.workspace.readDesc') },
    { key: 'workspace.update', name: t('permissionConfig.permissions.workspace.update'), description: t('permissionConfig.permissions.workspace.updateDesc') },
    { key: 'workspace.delete', name: t('permissionConfig.permissions.workspace.delete'), description: t('permissionConfig.permissions.workspace.deleteDesc') },
    { key: 'workspace.archive', name: t('permissionConfig.permissions.workspace.archive'), description: t('permissionConfig.permissions.workspace.archiveDesc') },
  ],
  member: [
    { key: 'member.invite', name: t('permissionConfig.permissions.member.invite'), description: t('permissionConfig.permissions.member.inviteDesc') },
    { key: 'member.add', name: t('permissionConfig.permissions.member.add'), description: t('permissionConfig.permissions.member.addDesc') },
    { key: 'member.remove', name: t('permissionConfig.permissions.member.remove'), description: t('permissionConfig.permissions.member.removeDesc') },
    { key: 'member.role', name: t('permissionConfig.permissions.member.role'), description: t('permissionConfig.permissions.member.roleDesc') },
  ],
  project: [
    { key: 'project.create', name: t('permissionConfig.permissions.project.create'), description: t('permissionConfig.permissions.project.createDesc') },
    { key: 'project.read', name: t('permissionConfig.permissions.project.read'), description: t('permissionConfig.permissions.project.readDesc') },
    { key: 'project.update', name: t('permissionConfig.permissions.project.update'), description: t('permissionConfig.permissions.project.updateDesc') },
    { key: 'project.delete', name: t('permissionConfig.permissions.project.delete'), description: t('permissionConfig.permissions.project.deleteDesc') },
    { key: 'project.export', name: t('permissionConfig.permissions.project.export'), description: t('permissionConfig.permissions.project.exportDesc') },
  ],
  annotation: [
    { key: 'annotation.create', name: t('permissionConfig.permissions.annotation.create'), description: t('permissionConfig.permissions.annotation.createDesc') },
    { key: 'annotation.read', name: t('permissionConfig.permissions.annotation.read'), description: t('permissionConfig.permissions.annotation.readDesc') },
    { key: 'annotation.update', name: t('permissionConfig.permissions.annotation.update'), description: t('permissionConfig.permissions.annotation.updateDesc') },
    { key: 'annotation.delete', name: t('permissionConfig.permissions.annotation.delete'), description: t('permissionConfig.permissions.annotation.deleteDesc') },
    { key: 'annotation.review', name: t('permissionConfig.permissions.annotation.review'), description: t('permissionConfig.permissions.annotation.reviewDesc') },
  ],
});

const ROLES = ['owner', 'admin', 'member', 'guest'];

const PermissionConfig: React.FC = () => {
  const { t } = useTranslation('admin');

  // Get permissions with translations
  const PERMISSIONS = getPermissions(t);

  // Default role permissions
  const DEFAULT_ROLE_PERMISSIONS: Record<string, string[]> = {
    owner: Object.values(PERMISSIONS).flat().map(p => p.key),
    admin: [
      'workspace.read', 'workspace.update',
      'member.invite', 'member.add', 'member.remove', 'member.role',
      'project.create', 'project.read', 'project.update', 'project.delete', 'project.export',
      'annotation.create', 'annotation.read', 'annotation.update', 'annotation.delete', 'annotation.review',
    ],
    member: [
      'workspace.read',
      'project.read', 'project.update',
      'annotation.create', 'annotation.read', 'annotation.update',
    ],
    guest: [
      'workspace.read',
      'project.read',
      'annotation.read',
    ],
  };

  const [selectedTenantId, setSelectedTenantId] = useState<string | undefined>();
  const [rolePermissions, setRolePermissions] = useState<Record<string, string[]>>(DEFAULT_ROLE_PERMISSIONS);
  const queryClient = useQueryClient();

  // Fetch tenants
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantApi.list({ status: 'active' }).then(res => res.data),
  });

  const getRoleName = (role: string) => {
    const names: Record<string, string> = {
      owner: t('permissionConfig.roles.owner'),
      admin: t('permissionConfig.roles.admin'),
      member: t('permissionConfig.roles.member'),
      guest: t('permissionConfig.roles.guest'),
    };
    return names[role] || role;
  };

  const handlePermissionChange = (role: string, permission: string, checked: boolean) => {
    if (role === 'owner') {
      message.warning(t('permissionConfig.ownerPermissionImmutable'));
      return;
    }
    
    setRolePermissions(prev => {
      const current = prev[role] || [];
      if (checked) {
        return { ...prev, [role]: [...current, permission] };
      } else {
        return { ...prev, [role]: current.filter(p => p !== permission) };
      }
    });
  };

  const handleSave = () => {
    // In real implementation, this would save to backend
    message.success(t('permissionConfig.saveSuccess'));
  };

  const handleReset = () => {
    setRolePermissions(DEFAULT_ROLE_PERMISSIONS);
    message.info(t('permissionConfig.resetSuccess'));
  };


  // Permission matrix columns
  const matrixColumns = [
    {
      title: t('permissionConfig.table.permission'),
      dataIndex: 'name',
      key: 'name',
      fixed: 'left' as const,
      width: 150,
      render: (name: string, record: any) => (
        <div>
          <div>{name}</div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.description}</div>
        </div>
      ),
    },
    ...ROLES.map(role => ({
      title: getRoleName(role),
      key: role,
      width: 100,
      align: 'center' as const,
      render: (_: any, record: any) => {
        const hasPermission = rolePermissions[role]?.includes(record.key);
        return (
          <Switch
            checked={hasPermission}
            disabled={role === 'owner'}
            onChange={(checked) => handlePermissionChange(role, record.key, checked)}
            checkedChildren={<CheckCircleOutlined />}
            unCheckedChildren={<CloseCircleOutlined />}
          />
        );
      },
    })),
  ];

  // API permissions
  const apiPermissions = [
    { endpoint: '/api/v1/tenants', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: t('permissionConfig.apiPermissions.tenants') },
    { endpoint: '/api/v1/workspaces', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: t('permissionConfig.apiPermissions.workspaces') },
    { endpoint: '/api/v1/members', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: t('permissionConfig.apiPermissions.members') },
    { endpoint: '/api/v1/projects', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: t('permissionConfig.apiPermissions.projects') },
    { endpoint: '/api/v1/annotations', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: t('permissionConfig.apiPermissions.annotations') },
    { endpoint: '/api/v1/quotas', methods: ['GET', 'PUT'], description: t('permissionConfig.apiPermissions.quotas') },
    { endpoint: '/api/v1/shares', methods: ['GET', 'POST', 'DELETE'], description: t('permissionConfig.apiPermissions.shares') },
    { endpoint: '/api/v1/admin', methods: ['GET', 'PUT'], description: t('permissionConfig.apiPermissions.admin') },
  ];

  const apiColumns = [
    {
      title: t('permissionConfig.apiTable.endpoint'),
      dataIndex: 'endpoint',
      key: 'endpoint',
      render: (endpoint: string) => <code>{endpoint}</code>,
    },
    {
      title: t('permissionConfig.apiTable.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('permissionConfig.apiTable.methods'),
      dataIndex: 'methods',
      key: 'methods',
      render: (methods: string[]) => (
        <Space>
          {methods.map(m => (
            <Tag key={m} color={
              m === 'GET' ? 'green' : 
              m === 'POST' ? 'blue' : 
              m === 'PUT' ? 'orange' : 
              'red'
            }>
              {m}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('permissionConfig.apiTable.roles'),
      key: 'roles',
      render: () => (
        <Select mode="multiple" defaultValue={['admin']} style={{ width: 200 }}>
          <Select.Option value="owner">{t('permissionConfig.roles.owner')}</Select.Option>
          <Select.Option value="admin">{t('permissionConfig.roles.admin')}</Select.Option>
          <Select.Option value="member">{t('permissionConfig.roles.member')}</Select.Option>
          <Select.Option value="guest">{t('permissionConfig.roles.guest')}</Select.Option>
        </Select>
      ),
    },
  ];

  return (
    <div className="permission-config">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <h2 style={{ margin: 0 }}>
              <SafetyOutlined /> {t('permissionConfig.title')}
            </h2>
            <p style={{ margin: 0, color: '#666' }}>
              {t('permissionConfig.subtitle')}
            </p>
          </Col>
          <Col>
            <Space>
              <Select
                placeholder={t('permissionConfig.placeholders.selectTenant')}
                style={{ width: 200 }}
                onChange={setSelectedTenantId}
                value={selectedTenantId}
                allowClear
              >
                {tenants?.map(t => (
                  <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
                ))}
              </Select>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                {t('permissionConfig.buttons.reset')}
              </Button>
              <Button type="primary" onClick={handleSave}>
                {t('permissionConfig.buttons.save')}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Alert
        message={t('permissionConfig.alert.title')}
        description={t('permissionConfig.alert.description')}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Tabs defaultActiveKey="matrix">
        <Tabs.TabPane tab={<span><TeamOutlined /> {t('permissionConfig.tabs.matrix')}</span>} key="matrix">
          {Object.entries(PERMISSIONS).map(([category, permissions]) => (
            <Card
              key={category}
              title={category === 'workspace' ? t('permissionConfig.permissions.workspace.title') :
                     category === 'member' ? t('permissionConfig.permissions.member.title') :
                     category === 'project' ? t('permissionConfig.permissions.project.title') : t('permissionConfig.permissions.annotation.title')}
              size="small"
              style={{ marginBottom: 16 }}
            >
              <Table
                columns={matrixColumns}
                dataSource={permissions}
                rowKey="key"
                pagination={false}
                size="small"
                scroll={{ x: 600 }}
              />
            </Card>
          ))}
        </Tabs.TabPane>

        <Tabs.TabPane tab={<span><ApiOutlined /> {t('permissionConfig.tabs.api')}</span>} key="api">
          <Card>
            <Table
              columns={apiColumns}
              dataSource={apiPermissions}
              rowKey="endpoint"
              pagination={false}
            />
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={<span><SafetyOutlined /> {t('permissionConfig.tabs.roles')}</span>} key="roles">
          <Row gutter={16}>
            {ROLES.map(role => (
              <Col span={6} key={role}>
                <Card title={getRoleName(role)} size="small">
                  <div style={{ maxHeight: 300, overflow: 'auto' }}>
                    {rolePermissions[role]?.map(p => {
                      const perm = Object.values(PERMISSIONS).flat().find(x => x.key === p);
                      return (
                        <Tag key={p} style={{ marginBottom: 4 }}>
                          {perm?.name || p}
                        </Tag>
                      );
                    })}
                  </div>
                  <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                    {t('permissionConfig.stats.permissionCount', { count: rolePermissions[role]?.length || 0 })}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default PermissionConfig;
