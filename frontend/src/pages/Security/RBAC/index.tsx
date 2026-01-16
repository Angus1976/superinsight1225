/**
 * RBAC Configuration Page
 */

import React from 'react';
import { Tabs, Typography } from 'antd';
import { TeamOutlined, KeyOutlined, UserSwitchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import RoleList from './RoleList';
import PermissionMatrix from './PermissionMatrix';
import UserRoleAssignment from './UserRoleAssignment';

const { Title } = Typography;

const RBACConfig: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <KeyOutlined /> {t('rbac.title')}
      </Title>

      <Tabs
        defaultActiveKey="roles"
        items={[
          {
            key: 'roles',
            label: (
              <span>
                <TeamOutlined />
                {t('rbac.roles')}
              </span>
            ),
            children: <RoleList />,
          },
          {
            key: 'matrix',
            label: (
              <span>
                <KeyOutlined />
                {t('rbac.permissionMatrix')}
              </span>
            ),
            children: <PermissionMatrix />,
          },
          {
            key: 'assignments',
            label: (
              <span>
                <UserSwitchOutlined />
                {t('rbac.userAssignments')}
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
