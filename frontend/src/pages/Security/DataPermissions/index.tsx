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
import { useTranslation } from 'react-i18next';
import PermissionConfigPage from './PermissionConfigPage';
import PolicyImportWizard from './PolicyImportWizard';
import ApprovalWorkflowPage from './ApprovalWorkflowPage';
import AccessLogPage from './AccessLogPage';
import DataClassificationPage from './DataClassificationPage';
import MaskingConfigPage from './MaskingConfigPage';

const { Title } = Typography;

const DataPermissionsPage: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <SafetyOutlined /> {t('dataPermissions.title')}
      </Title>

      <Tabs
        defaultActiveKey="permissions"
        items={[
          {
            key: 'permissions',
            label: (
              <span>
                <SafetyOutlined />
                {t('dataPermissions.permissions')}
              </span>
            ),
            children: <PermissionConfigPage />,
          },
          {
            key: 'policies',
            label: (
              <span>
                <ImportOutlined />
                {t('dataPermissions.policyImport.title')}
              </span>
            ),
            children: <PolicyImportWizard />,
          },
          {
            key: 'approvals',
            label: (
              <span>
                <CheckCircleOutlined />
                {t('dataPermissions.approvals')}
              </span>
            ),
            children: <ApprovalWorkflowPage />,
          },
          {
            key: 'access-logs',
            label: (
              <span>
                <AuditOutlined />
                {t('dataPermissions.accessLogs')}
              </span>
            ),
            children: <AccessLogPage />,
          },
          {
            key: 'classification',
            label: (
              <span>
                <FileSearchOutlined />
                {t('dataPermissions.classification.title')}
              </span>
            ),
            children: <DataClassificationPage />,
          },
          {
            key: 'masking',
            label: (
              <span>
                <EyeInvisibleOutlined />
                {t('dataPermissions.dataMasking')}
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
