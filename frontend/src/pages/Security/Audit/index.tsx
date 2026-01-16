/**
 * Audit Page Index
 */

import React from 'react';
import { Tabs, Typography } from 'antd';
import { AuditOutlined, FileTextOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import AuditLogs from './AuditLogs';
import ComplianceReports from './ComplianceReports';

const { Title } = Typography;

const AuditPage: React.FC = () => {
  const { t } = useTranslation(['security', 'common']);

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <AuditOutlined /> {t('audit.title')}
      </Title>

      <Tabs
        defaultActiveKey="logs"
        items={[
          {
            key: 'logs',
            label: (
              <span>
                <AuditOutlined />
                {t('audit.logs')}
              </span>
            ),
            children: <AuditLogs />,
          },
          {
            key: 'reports',
            label: (
              <span>
                <FileTextOutlined />
                {t('audit.complianceReports')}
              </span>
            ),
            children: <ComplianceReports />,
          },
        ]}
      />
    </div>
  );
};

export default AuditPage;
