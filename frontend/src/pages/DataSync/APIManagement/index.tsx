import React, { useState, useEffect } from 'react';
import { Card, Tabs, message, Space } from 'antd';
import { ApiOutlined, BarChartOutlined, ExperimentOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import KeyList from './KeyList';
import UsageStats from './UsageStats';
import APITesting from './APITesting';

const { TabPane } = Tabs;

const APIManagement: React.FC = () => {
  const { t } = useTranslation('dataSync');
  const [activeTab, setActiveTab] = useState('keys');

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
        >
          <TabPane
            tab={
              <Space>
                <ApiOutlined />
                {t('apiManagement.keyList')}
              </Space>
            }
            key="keys"
          >
            <KeyList />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <BarChartOutlined />
                {t('apiManagement.usageStats')}
              </Space>
            }
            key="usage"
          >
            <UsageStats />
          </TabPane>

          <TabPane
            tab={
              <Space>
                <ExperimentOutlined />
                {t('apiManagement.apiTesting')}
              </Space>
            }
            key="testing"
          >
            <APITesting />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default APIManagement;
