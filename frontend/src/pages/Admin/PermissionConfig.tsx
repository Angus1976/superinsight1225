/**
 * Permission Configuration Page
 * 
 * Provides permission management including:
 * - Permission matrix view
 * - Role-based permission configuration
 * - API permission configuration
 */

import React, { useState } from 'react';
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

// Permission definitions
const PERMISSIONS = {
  workspace: [
    { key: 'workspace.create', name: '创建工作空间', description: '允许创建新的工作空间' },
    { key: 'workspace.read', name: '查看工作空间', description: '允许查看工作空间信息' },
    { key: 'workspace.update', name: '编辑工作空间', description: '允许编辑工作空间设置' },
    { key: 'workspace.delete', name: '删除工作空间', description: '允许删除工作空间' },
    { key: 'workspace.archive', name: '归档工作空间', description: '允许归档/恢复工作空间' },
  ],
  member: [
    { key: 'member.invite', name: '邀请成员', description: '允许邀请新成员' },
    { key: 'member.add', name: '添加成员', description: '允许直接添加成员' },
    { key: 'member.remove', name: '移除成员', description: '允许移除成员' },
    { key: 'member.role', name: '修改角色', description: '允许修改成员角色' },
  ],
  project: [
    { key: 'project.create', name: '创建项目', description: '允许创建新项目' },
    { key: 'project.read', name: '查看项目', description: '允许查看项目' },
    { key: 'project.update', name: '编辑项目', description: '允许编辑项目' },
    { key: 'project.delete', name: '删除项目', description: '允许删除项目' },
    { key: 'project.export', name: '导出数据', description: '允许导出项目数据' },
  ],
  annotation: [
    { key: 'annotation.create', name: '创建标注', description: '允许创建标注' },
    { key: 'annotation.read', name: '查看标注', description: '允许查看标注' },
    { key: 'annotation.update', name: '编辑标注', description: '允许编辑标注' },
    { key: 'annotation.delete', name: '删除标注', description: '允许删除标注' },
    { key: 'annotation.review', name: '审核标注', description: '允许审核标注' },
  ],
};

const ROLES = ['owner', 'admin', 'member', 'guest'];

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

const PermissionConfig: React.FC = () => {
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
      owner: '所有者',
      admin: '管理员',
      member: '成员',
      guest: '访客',
    };
    return names[role] || role;
  };

  const handlePermissionChange = (role: string, permission: string, checked: boolean) => {
    if (role === 'owner') {
      message.warning('所有者权限不可修改');
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
    message.success('权限配置已保存');
  };

  const handleReset = () => {
    setRolePermissions(DEFAULT_ROLE_PERMISSIONS);
    message.info('已重置为默认配置');
  };


  // Permission matrix columns
  const matrixColumns = [
    {
      title: '权限',
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
    { endpoint: '/api/v1/tenants', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: '租户管理' },
    { endpoint: '/api/v1/workspaces', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: '工作空间管理' },
    { endpoint: '/api/v1/members', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: '成员管理' },
    { endpoint: '/api/v1/projects', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: '项目管理' },
    { endpoint: '/api/v1/annotations', methods: ['GET', 'POST', 'PUT', 'DELETE'], description: '标注管理' },
    { endpoint: '/api/v1/quotas', methods: ['GET', 'PUT'], description: '配额管理' },
    { endpoint: '/api/v1/shares', methods: ['GET', 'POST', 'DELETE'], description: '共享管理' },
    { endpoint: '/api/v1/admin', methods: ['GET', 'PUT'], description: '管理员功能' },
  ];

  const apiColumns = [
    {
      title: 'API 端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      render: (endpoint: string) => <code>{endpoint}</code>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '允许的方法',
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
      title: '所需角色',
      key: 'roles',
      render: () => (
        <Select mode="multiple" defaultValue={['admin']} style={{ width: 200 }}>
          <Select.Option value="owner">所有者</Select.Option>
          <Select.Option value="admin">管理员</Select.Option>
          <Select.Option value="member">成员</Select.Option>
          <Select.Option value="guest">访客</Select.Option>
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
              <SafetyOutlined /> 权限配置
            </h2>
            <p style={{ margin: 0, color: '#666' }}>
              配置角色权限和 API 访问控制
            </p>
          </Col>
          <Col>
            <Space>
              <Select
                placeholder="选择租户"
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
                重置
              </Button>
              <Button type="primary" onClick={handleSave}>
                保存配置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Alert
        message="权限说明"
        description="所有者拥有全部权限且不可修改。其他角色的权限可以根据需要进行配置。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Tabs defaultActiveKey="matrix">
        <Tabs.TabPane tab={<span><TeamOutlined /> 权限矩阵</span>} key="matrix">
          {Object.entries(PERMISSIONS).map(([category, permissions]) => (
            <Card 
              key={category} 
              title={category === 'workspace' ? '工作空间权限' :
                     category === 'member' ? '成员权限' :
                     category === 'project' ? '项目权限' : '标注权限'}
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

        <Tabs.TabPane tab={<span><ApiOutlined /> API 权限</span>} key="api">
          <Card>
            <Table
              columns={apiColumns}
              dataSource={apiPermissions}
              rowKey="endpoint"
              pagination={false}
            />
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={<span><SafetyOutlined /> 角色概览</span>} key="roles">
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
                    共 {rolePermissions[role]?.length || 0} 项权限
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
