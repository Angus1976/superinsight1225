/**
 * LLM Application Binding Management Page
 * Main page component with tabs for configurations and bindings
 */

import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Tabs, Card } from 'antd';
import { SettingOutlined, LinkOutlined, AppstoreOutlined } from '@ant-design/icons';
import { useLLMConfigStore } from '@/stores/llmConfigStore';
import LLMConfigList from './LLMConfigList';
import ApplicationBindings from './ApplicationBindings';
import ConfigurationMatrix from './ConfigurationMatrix';

const LLMApplicationBindingPage: React.FC = () => {
  const { t } = useTranslation('llmConfig');
  const { fetchConfigs, fetchApplications, fetchBindings } = useLLMConfigStore();

  useEffect(() => {
    fetchConfigs();
    fetchApplications();
    fetchBindings();
  }, [fetchConfigs, fetchApplications, fetchBindings]);

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <h1>{t('pageTitle')}</h1>
        <p>{t('pageDescription')}</p>
        
        <Tabs defaultActiveKey="matrix">
          <Tabs.TabPane
            tab={
              <span>
                <AppstoreOutlined />
                {t('tabs.matrix')}
              </span>
            }
            key="matrix"
          >
            <ConfigurationMatrix />
          </Tabs.TabPane>
          
          <Tabs.TabPane
            tab={
              <span>
                <SettingOutlined />
                {t('tabs.configs')}
              </span>
            }
            key="configs"
          >
            <LLMConfigList />
          </Tabs.TabPane>
          
          <Tabs.TabPane
            tab={
              <span>
                <LinkOutlined />
                {t('tabs.bindings')}
              </span>
            }
            key="bindings"
          >
            <ApplicationBindings />
          </Tabs.TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default LLMApplicationBindingPage;
