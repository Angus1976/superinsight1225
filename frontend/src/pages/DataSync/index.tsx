import React, { useState } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Card, Tabs, Typography, Space, Alert, Button, Menu } from 'antd';
import {
  DatabaseOutlined,
  SyncOutlined,
  SecurityScanOutlined,
  InfoCircleOutlined,
  DashboardOutlined,
  SafetyOutlined,
  ExportOutlined,
  HistoryOutlined,
  ScheduleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import DataSourceManager from '../../components/DataSync/DataSourceManager';
import SyncTaskConfig from '../../components/DataSync/SyncTaskConfig';
import DataDesensitizationConfig from '../../components/DataSync/DataDesensitizationConfig';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;

const DataSyncPage: React.FC = () => {
  const { t } = useTranslation(['dataSync', 'common']);
  const [activeTab, setActiveTab] = useState('dataSources');
  const location = useLocation();

  // Check if we're on a sub-route
  const isSubRoute = location.pathname !== '/data-sync';

  // If on sub-route, render the child component
  if (isSubRoute) {
    return (
      <div>
        <Card style={{ marginBottom: 16 }}>
          <Menu mode="horizontal" selectedKeys={[location.pathname.split('/').pop() || '']}>
            <Menu.Item key="data-sync">
              <Link to="/data-sync">
                <DashboardOutlined /> {t('dataSync:nav.overview', '同步概览')}
              </Link>
            </Menu.Item>
            <Menu.Item key="sources">
              <Link to="/data-sync/sources">
                <DatabaseOutlined /> {t('dataSync:nav.sources', '数据源管理')}
              </Link>
            </Menu.Item>
            <Menu.Item key="history">
              <Link to="/data-sync/history">
                <HistoryOutlined /> {t('dataSync:nav.history', '同步历史')}
              </Link>
            </Menu.Item>
            <Menu.Item key="scheduler">
              <Link to="/data-sync/scheduler">
                <ScheduleOutlined /> {t('dataSync:nav.scheduler', '调度配置')}
              </Link>
            </Menu.Item>
            <Menu.Item key="security">
              <Link to="/data-sync/security">
                <SafetyOutlined /> {t('dataSync:nav.security', '安全配置')}
              </Link>
            </Menu.Item>
            <Menu.Item key="export">
              <Link to="/data-sync/export">
                <ExportOutlined /> {t('dataSync:nav.export', '数据导出')}
              </Link>
            </Menu.Item>
          </Menu>
        </Card>
        <Outlet />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={2}>
            <SyncOutlined style={{ marginRight: 8 }} />
            {t('dataSync:title')}
          </Title>
          <Paragraph type="secondary">
            {t('dataSync:description')}
          </Paragraph>
        </div>

        <Alert
          message={t('dataSync:notice.title')}
          description={t('dataSync:notice.description')}
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
          closable
        />

        <Card>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            tabBarStyle={{ marginBottom: 24 }}
          >
            <TabPane
              tab={
                <Space>
                  <DatabaseOutlined />
                  {t('dataSync:tabs.dataSources')}
                </Space>
              }
              key="dataSources"
            >
              <DataSourceManager />
            </TabPane>

            <TabPane
              tab={
                <Space>
                  <SyncOutlined />
                  {t('dataSync:tabs.syncTasks')}
                </Space>
              }
              key="syncTasks"
            >
              <SyncTaskConfig />
            </TabPane>

            <TabPane
              tab={
                <Space>
                  <SecurityScanOutlined />
                  {t('dataSync:tabs.security')}
                </Space>
              }
              key="security"
            >
              <DataDesensitizationConfig />
            </TabPane>
          </Tabs>
        </Card>
      </Space>
    </div>
  );
};

export default DataSyncPage;