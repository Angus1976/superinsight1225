/**
 * Error Display Components
 * 
 * A collection of components for displaying errors in various formats:
 * - Inline errors
 * - Error alerts
 * - Error cards
 * - Empty state with error
 */

import React from 'react';
import { 
  Alert, 
  Button, 
  Card, 
  Empty, 
  Result, 
  Space, 
  Typography,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  CloseOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  StopOutlined,
  WifiOutlined,
  LockOutlined,
  ClockCircleOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { AppError, ErrorCategory, ErrorSeverity } from '@/types/error';

const { Text, Paragraph } = Typography;

// Icon mapping for error categories
const categoryIcons: Record<ErrorCategory, React.ReactNode> = {
  network: <WifiOutlined />,
  auth: <LockOutlined />,
  validation: <ExclamationCircleOutlined />,
  server: <StopOutlined />,
  client: <ExclamationCircleOutlined />,
  timeout: <ClockCircleOutlined />,
  permission: <LockOutlined />,
  notFound: <FileSearchOutlined />,
  conflict: <WarningOutlined />,
  rateLimit: <ClockCircleOutlined />,
  maintenance: <InfoCircleOutlined />,
  unknown: <ExclamationCircleOutlined />,
};

// Alert type mapping for severity
const severityAlertType: Record<ErrorSeverity, 'success' | 'info' | 'warning' | 'error'> = {
  info: 'info',
  warning: 'warning',
  error: 'error',
  critical: 'error',
};

// ============================================
// Inline Error Component
// ============================================

interface InlineErrorProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const InlineError: React.FC<InlineErrorProps> = ({
  message,
  onRetry,
  onDismiss,
}) => {
  const { t } = useTranslation('common');
  
  return (
    <Space size="small" style={{ color: '#ff4d4f' }}>
      <ExclamationCircleOutlined />
      <Text type="danger">{message}</Text>
      {onRetry && (
        <Tooltip title={t('error.actions.retry')}>
          <Button 
            type="link" 
            size="small" 
            icon={<ReloadOutlined />}
            onClick={onRetry}
            style={{ padding: 0 }}
          />
        </Tooltip>
      )}
      {onDismiss && (
        <Tooltip title={t('error.actions.dismiss')}>
          <Button 
            type="link" 
            size="small" 
            icon={<CloseOutlined />}
            onClick={onDismiss}
            style={{ padding: 0 }}
          />
        </Tooltip>
      )}
    </Space>
  );
};

// ============================================
// Error Alert Component
// ============================================

interface ErrorAlertProps {
  error: AppError;
  onRetry?: () => void;
  onDismiss?: () => void;
  showActions?: boolean;
  showDetails?: boolean;
  closable?: boolean;
  banner?: boolean;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
  error,
  onRetry,
  onDismiss,
  showActions = true,
  showDetails = false,
  closable = true,
  banner = false,
}) => {
  const { t } = useTranslation('common');
  
  const message = t(error.message, { defaultValue: error.technicalMessage });
  const icon = categoryIcons[error.category];
  const type = severityAlertType[error.severity];
  
  const description = showDetails ? (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      <Text>{message}</Text>
      {error.technicalMessage && error.technicalMessage !== message && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {error.technicalMessage}
        </Text>
      )}
      <Text type="secondary" style={{ fontSize: 11 }}>
        {t('error.code')}: {error.code} | {t('error.id')}: {error.id}
      </Text>
    </Space>
  ) : undefined;
  
  const action = showActions && (onRetry || onDismiss) ? (
    <Space>
      {onRetry && error.canRetry && (
        <Button size="small" onClick={onRetry}>
          {t('error.actions.retry')}
        </Button>
      )}
      {onDismiss && (
        <Button size="small" type="text" onClick={onDismiss}>
          {t('error.actions.dismiss')}
        </Button>
      )}
    </Space>
  ) : undefined;
  
  return (
    <Alert
      type={type}
      message={showDetails ? t('error.title') : message}
      description={description}
      icon={icon}
      showIcon
      closable={closable}
      onClose={onDismiss}
      action={action}
      banner={banner}
      style={{ marginBottom: 16 }}
    />
  );
};

// ============================================
// Error Card Component
// ============================================

interface ErrorCardProps {
  error: AppError;
  onRetry?: () => void;
  onDismiss?: () => void;
  title?: string;
}

export const ErrorCard: React.FC<ErrorCardProps> = ({
  error,
  onRetry,
  onDismiss,
  title,
}) => {
  const { t } = useTranslation('common');
  
  const message = t(error.message, { defaultValue: error.technicalMessage });
  const icon = categoryIcons[error.category];
  
  return (
    <Card
      size="small"
      style={{ 
        borderColor: error.severity === 'critical' ? '#ff4d4f' : '#ffa940',
        marginBottom: 16,
      }}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <span style={{ 
            color: error.severity === 'critical' ? '#ff4d4f' : '#ffa940',
            fontSize: 20,
          }}>
            {icon}
          </span>
          <Text strong>{title || t('error.title')}</Text>
        </Space>
        
        <Paragraph style={{ marginBottom: 8 }}>
          {message}
        </Paragraph>
        
        {error.fieldErrors && error.fieldErrors.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('error.fieldErrors')}:
            </Text>
            <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
              {error.fieldErrors.map((fe, index) => (
                <li key={index}>
                  <Text type="danger" style={{ fontSize: 12 }}>
                    {fe.field}: {fe.message}
                  </Text>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        <Space>
          {onRetry && error.canRetry && (
            <Button 
              size="small" 
              type="primary"
              icon={<ReloadOutlined />}
              onClick={onRetry}
            >
              {t('error.actions.retry')}
            </Button>
          )}
          {onDismiss && (
            <Button 
              size="small"
              icon={<CloseOutlined />}
              onClick={onDismiss}
            >
              {t('error.actions.dismiss')}
            </Button>
          )}
        </Space>
      </Space>
    </Card>
  );
};

// ============================================
// Error Empty State Component
// ============================================

interface ErrorEmptyStateProps {
  error: AppError;
  onRetry?: () => void;
  onGoBack?: () => void;
  onGoHome?: () => void;
}

export const ErrorEmptyState: React.FC<ErrorEmptyStateProps> = ({
  error,
  onRetry,
  onGoBack,
  onGoHome,
}) => {
  const { t } = useTranslation('common');
  
  const message = t(error.message, { defaultValue: error.technicalMessage });
  
  // Map category to Result status
  const statusMap: Record<ErrorCategory, '403' | '404' | '500' | 'error' | 'warning'> = {
    network: 'error',
    auth: '403',
    validation: 'warning',
    server: '500',
    client: 'error',
    timeout: 'error',
    permission: '403',
    notFound: '404',
    conflict: 'warning',
    rateLimit: 'warning',
    maintenance: '500',
    unknown: 'error',
  };
  
  const status = statusMap[error.category];
  
  return (
    <Result
      status={status}
      title={t(`error.titles.${error.category}`, { defaultValue: t('error.title') })}
      subTitle={message}
      extra={
        <Space>
          {onRetry && error.canRetry && (
            <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
              {t('error.actions.retry')}
            </Button>
          )}
          {onGoBack && (
            <Button onClick={onGoBack}>
              {t('error.actions.goBack')}
            </Button>
          )}
          {onGoHome && (
            <Button onClick={onGoHome}>
              {t('error.actions.goHome')}
            </Button>
          )}
        </Space>
      }
    />
  );
};

// ============================================
// Field Error Display Component
// ============================================

interface FieldErrorDisplayProps {
  errors: Map<string, string>;
  fields?: string[];
}

export const FieldErrorDisplay: React.FC<FieldErrorDisplayProps> = ({
  errors,
  fields,
}) => {
  const displayErrors = fields 
    ? fields.filter(f => errors.has(f)).map(f => ({ field: f, message: errors.get(f)! }))
    : Array.from(errors.entries()).map(([field, message]) => ({ field, message }));
  
  if (displayErrors.length === 0) return null;
  
  return (
    <div style={{ marginTop: 8 }}>
      {displayErrors.map(({ field, message }) => (
        <div key={field} style={{ marginBottom: 4 }}>
          <Text type="danger" style={{ fontSize: 12 }}>
            <ExclamationCircleOutlined style={{ marginRight: 4 }} />
            {message}
          </Text>
        </div>
      ))}
    </div>
  );
};

// ============================================
// Network Error Component
// ============================================

interface NetworkErrorProps {
  onRetry?: () => void;
}

export const NetworkError: React.FC<NetworkErrorProps> = ({ onRetry }) => {
  const { t } = useTranslation('common');
  
  return (
    <Empty
      image={<WifiOutlined style={{ fontSize: 64, color: '#bfbfbf' }} />}
      description={
        <Space direction="vertical" size="small">
          <Text strong>{t('error.titles.network')}</Text>
          <Text type="secondary">{t('error.messages.network')}</Text>
        </Space>
      }
    >
      {onRetry && (
        <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
          {t('error.actions.retry')}
        </Button>
      )}
    </Empty>
  );
};

export default {
  InlineError,
  ErrorAlert,
  ErrorCard,
  ErrorEmptyState,
  FieldErrorDisplay,
  NetworkError,
};
