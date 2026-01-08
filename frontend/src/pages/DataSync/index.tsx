import React, { useState } from 'react';
import { Card, Tabs, Typography, Space, Alert, Button } from 'antd';
import {
  DatabaseOutlined,
  SyncOutlined,
  SecurityScanOutlined,
  InfoCircleOutlined,
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