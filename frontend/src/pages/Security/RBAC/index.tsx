/**
 * RBAC Configuration Page
 */

import React from 'react';
import { Tabs, Typography } from 'antd';
import { TeamOutlined, KeyOutlined, UserSwitchOutlined } from '@ant-design/icons';
import RoleList from './RoleList';
import PermissionMatrix from './PermissionMatrix';
import UserRoleAssignment from './UserRoleAssignment';

const { Title } = Typography;

const RBACConfig: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <KeyOutlined /> Role-Based Access Control
      </Title>

      <Tabs
        defaultActiveKey="roles"
        items={[
          {
            key: 'roles',
            label: (
              <span>
                <TeamOutlined />
                Roles
              </span>
            ),
            children: <RoleList />,
          },
          {
            key: 'matrix',
            label: (
              <span>
                <KeyOutlined />
                Permission Matrix
              </span>
            ),
            children: <PermissionMatrix />,
          },
          {
            key: 'assignments',
            label: (
              <span>
                <UserSwitchOutlined />
                User Assignments
              </span>
            ),
            children: <UserRoleAssignment />,
          },
        ]}
      />
    </div>
  );
};

export default RBACConfig;
