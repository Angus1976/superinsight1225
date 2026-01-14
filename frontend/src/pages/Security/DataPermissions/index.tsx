/**
 * Data Permissions Page Index
 * 
 * Main entry point for data permission management features.
 */

import React from 'react';
import { Tabs, Typography } from 'antd';
import {
  SafetyOutlined,
  ImportOutlined,
  AuditOutlined,
  FileSearchOutlined,
  EyeInvisibleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import PermissionConfigPage from './PermissionConfigPage';
import PolicyImportWizard from './PolicyImportWizard';
import ApprovalWorkflowPage from './ApprovalWorkflowPage';
import AccessLogPage from './AccessLogPage';
import DataClassificationPage from './DataClassificationPage';
import MaskingConfigPage from './MaskingConfigPage';

const { Title } = Typography;

const DataPermissionsPage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SafetyOutlined /> Data Permission Control
      </Title>

      <Tabs
        defaultActiveKey="permissions"
        items={[
          {
            key: 'permissions',
            label: (
              <span>
                <SafetyOutlined />
                Permissions
              </span>
            ),
            children: <PermissionConfigPage />,
          },
          {
            key: 'policies',
            label: (
              <span>
                <ImportOutlined />
                Policy Import
              </span>
            ),
            children: <PolicyImportWizard />,
          },
          {
            key: 'approvals',
            label: (
              <span>
                <CheckCircleOutlined />
                Approvals
              </span>
            ),
            children: <ApprovalWorkflowPage />,
          },
          {
            key: 'access-logs',
            label: (
              <span>
                <AuditOutlined />
                Access Logs
              </span>
            ),
            children: <AccessLogPage />,
          },
          {
            key: 'classification',
            label: (
              <span>
                <FileSearchOutlined />
                Classification
              </span>
            ),
            children: <DataClassificationPage />,
          },
          {
            key: 'masking',
            label: (
              <span>
                <EyeInvisibleOutlined />
                Data Masking
              </span>
            ),
            children: <MaskingConfigPage />,
          },
        ]}
      />
    </div>
  );
};

export default DataPermissionsPage;
