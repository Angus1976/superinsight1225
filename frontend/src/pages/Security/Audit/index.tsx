/**
 * Audit Page Index
 */

import React from 'react';
import { Tabs, Typography } from 'antd';
import { AuditOutlined, FileTextOutlined } from '@ant-design/icons';
import AuditLogs from './AuditLogs';
import ComplianceReports from './ComplianceReports';

const { Title } = Typography;

const AuditPage: React.FC = () => {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        <AuditOutlined /> Audit & Compliance
      </Title>

      <Tabs
        defaultActiveKey="logs"
        items={[
          {
            key: 'logs',
            label: (
              <span>
                <AuditOutlined />
                Audit Logs
              </span>
            ),
            children: <AuditLogs />,
          },
          {
            key: 'reports',
            label: (
              <span>
                <FileTextOutlined />
                Compliance Reports
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
