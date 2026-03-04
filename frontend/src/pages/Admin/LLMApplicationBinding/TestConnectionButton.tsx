/**
 * Test Connection Button Component
 * Tests LLM connectivity and displays results
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, message, Tooltip } from 'antd';
import { ApiOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useLLMConfigStore } from '@/stores/llmConfigStore';

interface TestConnectionButtonProps {
  configId: string;
}

const TestConnectionButton: React.FC<TestConnectionButtonProps> = ({ configId }) => {
  const { t } = useTranslation('llmConfig');
  const { testConnection } = useLLMConfigStore();
  const [testing, setTesting] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testConnection(configId);
      
      if (result.status === 'success') {
        message.success(
          `${t('testConnection.success')} - ${t('testConnection.latency', {
            ms: result.latency_ms,
          })}`
        );
      } else {
        message.error(
          `${t('testConnection.failed')} - ${t('testConnection.error', {
            message: result.error || 'Unknown error',
          })}`
        );
      }
    } catch (error: any) {
      message.error(t('errors.testConnectionFailed'));
    } finally {
      setTesting(false);
    }
  };

  return (
    <Tooltip title={t('testConnection.button')}>
      <Button
        type="link"
        icon={<ApiOutlined />}
        loading={testing}
        onClick={handleTest}
      >
        {testing ? t('testConnection.testing') : t('configList.actions.test')}
      </Button>
    </Tooltip>
  );
};

export default TestConnectionButton;
