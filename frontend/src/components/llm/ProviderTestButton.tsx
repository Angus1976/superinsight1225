/**
 * LLM Provider Test Button Component
 * 
 * Button component for testing LLM provider connections.
 * Shows loading state during test and displays success/error results.
 * 
 * **Requirements: 6.3**
 */

import React, { useState, useCallback } from 'react';
import {
  Button,
  Space,
  Typography,
  Tooltip,
  message,
  Spin,
  Tag,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { ConnectionTestResult } from '@/services/adminApi';

const { Text } = Typography;

export interface TestResult {
  status: 'idle' | 'testing' | 'success' | 'error';
  latency?: number;
  message?: string;
  timestamp?: Date;
}

export interface ProviderTestButtonProps {
  /** Provider configuration ID */
  providerId: string;
  /** Function to call for testing the connection */
  onTest: (providerId: string) => Promise<ConnectionTestResult>;
  /** Button size */
  size?: 'small' | 'middle' | 'large';
  /** Show result inline or as tooltip */
  showResultInline?: boolean;
  /** Custom button text */
  buttonText?: string;
  /** Callback when test completes */
  onTestComplete?: (result: TestResult) => void;
  /** Disable the button */
  disabled?: boolean;
}

export const ProviderTestButton: React.FC<ProviderTestButtonProps> = ({
  providerId,
  onTest,
  size = 'middle',
  showResultInline = true,
  buttonText,
  onTestComplete,
  disabled = false,
}) => {
  const { t } = useTranslation(['admin', 'common']);
  const [testResult, setTestResult] = useState<TestResult>({ status: 'idle' });

  const handleTest = useCallback(async () => {
    setTestResult({ status: 'testing' });
    
    try {
      const result = await onTest(providerId);
      
      const newResult: TestResult = {
        status: result.success ? 'success' : 'error',
        latency: result.latency_ms,
        message: result.error_message || (result.success 
          ? t('llm.status.connectionSuccess')
          : t('llm.status.connectionFailed')),
        timestamp: new Date(),
      };
      
      setTestResult(newResult);
      
      if (result.success) {
        message.success(`${t('llm.status.connectionSuccess')} (${result.latency_ms}ms)`);
      } else {
        message.error(`${t('llm.status.connectionFailed')}: ${result.error_message}`);
      }
      
      onTestComplete?.(newResult);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('llm.status.connectionFailed');
      const newResult: TestResult = {
        status: 'error',
        message: errorMessage,
        timestamp: new Date(),
      };
      
      setTestResult(newResult);
      message.error(errorMessage);
      onTestComplete?.(newResult);
    }
  }, [providerId, onTest, onTestComplete, t]);

  const renderResultTag = () => {
    switch (testResult.status) {
      case 'testing':
        return (
          <Tag icon={<LoadingOutlined spin />} color="processing">
            {t('llm.status.testing')}
          </Tag>
        );
      case 'success':
        return (
          <Tag icon={<CheckCircleOutlined />} color="success">
            {t('llm.status.online')} ({testResult.latency}ms)
          </Tag>
        );
      case 'error':
        return (
          <Tooltip title={testResult.message}>
            <Tag icon={<CloseCircleOutlined />} color="error">
              {t('llm.status.connectionFailed')}
            </Tag>
          </Tooltip>
        );
      default:
        return null;
    }
  };

  const getButtonIcon = () => {
    if (testResult.status === 'testing') {
      return <LoadingOutlined spin />;
    }
    if (testResult.status !== 'idle') {
      return <ReloadOutlined />;
    }
    return <ApiOutlined />;
  };

  return (
    <Space>
      <Tooltip title={testResult.status === 'idle' ? t('llm.actions.testConnection') : t('llm.actions.retestConnection', { defaultValue: '重新测试连接' })}>
        <Button
          type={testResult.status === 'idle' ? 'primary' : 'default'}
          icon={getButtonIcon()}
          onClick={handleTest}
          loading={testResult.status === 'testing'}
          disabled={disabled || testResult.status === 'testing'}
          size={size}
        >
          {buttonText || t('llm.actions.testConnection')}
        </Button>
      </Tooltip>
      
      {showResultInline && testResult.status !== 'idle' && renderResultTag()}
    </Space>
  );
};

/**
 * Compact version of the test button for use in tables
 */
export interface CompactTestButtonProps {
  providerId: string;
  onTest: (providerId: string) => Promise<ConnectionTestResult>;
  disabled?: boolean;
}

export const CompactTestButton: React.FC<CompactTestButtonProps> = ({
  providerId,
  onTest,
  disabled = false,
}) => {
  const { t } = useTranslation(['admin', 'common']);
  const [testing, setTesting] = useState(false);

  const handleTest = useCallback(async () => {
    setTesting(true);
    try {
      const result = await onTest(providerId);
      if (result.success) {
        message.success(`${t('llm.status.connectionSuccess')} (${result.latency_ms}ms)`);
      } else {
        message.error(`${t('llm.status.connectionFailed')}: ${result.error_message}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : t('llm.status.connectionFailed');
      message.error(errorMessage);
    } finally {
      setTesting(false);
    }
  }, [providerId, onTest, t]);

  return (
    <Tooltip title={t('llm.actions.testConnection')}>
      <Button
        type="text"
        icon={testing ? <LoadingOutlined spin /> : <ApiOutlined />}
        onClick={handleTest}
        disabled={disabled || testing}
      />
    </Tooltip>
  );
};

/**
 * Health status indicator component
 */
export interface HealthIndicatorProps {
  status: 'healthy' | 'unhealthy' | 'unknown' | 'checking';
  latency?: number;
  error?: string;
  showLatency?: boolean;
}

export const HealthIndicator: React.FC<HealthIndicatorProps> = ({
  status,
  latency,
  error,
  showLatency = true,
}) => {
  const { t } = useTranslation(['admin', 'common']);

  const getStatusConfig = () => {
    switch (status) {
      case 'healthy':
        return {
          color: 'success',
          icon: <CheckCircleOutlined />,
          text: showLatency && latency 
            ? `${t('llm.status.online')} (${latency}ms)`
            : t('llm.status.online'),
        };
      case 'unhealthy':
        return {
          color: 'error',
          icon: <CloseCircleOutlined />,
          text: t('llm.status.offline'),
        };
      case 'checking':
        return {
          color: 'processing',
          icon: <LoadingOutlined spin />,
          text: t('llm.status.testing'),
        };
      default:
        return {
          color: 'default',
          icon: null,
          text: t('llm.status.unknown', { defaultValue: '未知' }),
        };
    }
  };

  const config = getStatusConfig();

  return (
    <Tooltip title={error}>
      <Tag icon={config.icon} color={config.color}>
        {config.text}
      </Tag>
    </Tooltip>
  );
};

export default ProviderTestButton;
