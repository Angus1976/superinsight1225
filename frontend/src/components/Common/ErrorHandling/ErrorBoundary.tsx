/**
 * Enhanced Error Boundary Component
 * 
 * A comprehensive error boundary that catches React errors and displays
 * user-friendly error messages with recovery options.
 */

import React, { Component, type ReactNode, type ErrorInfo } from 'react';
import { Button, Result, Space, Typography, Collapse, Card } from 'antd';
import { 
  ReloadOutlined, 
  HomeOutlined, 
  BugOutlined,
  CopyOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import type { AppError } from '@/types/error';
import { transformError } from '@/utils/errorHandler';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((props: ErrorFallbackProps) => ReactNode);
  onError?: (error: AppError, errorInfo: ErrorInfo) => void;
  onReset?: () => void;
  showTechnicalDetails?: boolean;
  level?: 'page' | 'component' | 'critical';
}

interface State {
  hasError: boolean;
  error: AppError | null;
  errorInfo: ErrorInfo | null;
  copied: boolean;
}

interface ErrorFallbackProps {
  error: AppError;
  errorInfo: ErrorInfo | null;
  resetError: () => void;
}

export class EnhancedErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      copied: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const appError = transformError(error);
    return { hasError: true, error: appError };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const appError = transformError(error);
    
    // Log error
    console.group('🚨 React Error Boundary');
    console.error('Error:', error);
    console.error('Component Stack:', errorInfo.componentStack);
    console.groupEnd();
    
    // Update state with error info
    this.setState({ errorInfo });
    
    // Call custom error handler
    this.props.onError?.(appError, errorInfo);
  }

  handleRetry = (): void => {
    this.props.onReset?.();
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      copied: false,
    });
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  handleRefresh = (): void => {
    window.location.reload();
  };

  handleCopyError = async (): Promise<void> => {
    const { error, errorInfo } = this.state;
    if (!error) return;
    
    const errorReport = `
Error Report
============
Error ID: ${error.id}
Error Code: ${error.code}
Message: ${error.technicalMessage}
Category: ${error.category}
Severity: ${error.severity}
Timestamp: ${new Date(error.timestamp).toISOString()}

Component Stack:
${errorInfo?.componentStack || 'N/A'}

Context:
${JSON.stringify(error.context, null, 2)}
    `.trim();
    
    try {
      await navigator.clipboard.writeText(errorReport);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch (err) {
      console.error('Failed to copy error report:', err);
    }
  };

  renderErrorDetails(): ReactNode {
    const { error, errorInfo, copied } = this.state;
    const { showTechnicalDetails = true } = this.props;
    
    if (!showTechnicalDetails || !error) return null;
    
    return (
      <Collapse 
        ghost 
        style={{ marginTop: 16, textAlign: 'left' }}
      >
        <Panel 
          header={
            <Space>
              <BugOutlined />
              <Text type="secondary">技术详情 / Technical Details</Text>
            </Space>
          } 
          key="details"
        >
          <Card size="small" style={{ background: '#f5f5f5' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text strong>错误代码 / Error Code: </Text>
                <Text code>{error.code}</Text>
              </div>
              <div>
                <Text strong>错误ID / Error ID: </Text>
                <Text code>{error.id}</Text>
              </div>
              <div>
                <Text strong>类别 / Category: </Text>
                <Text>{error.category}</Text>
              </div>
              <div>
                <Text strong>时间 / Time: </Text>
                <Text>{new Date(error.timestamp).toLocaleString()}</Text>
              </div>
              {error.technicalMessage && (
                <div>
                  <Text strong>详细信息 / Details: </Text>
                  <Paragraph 
                    code 
                    style={{ 
                      whiteSpace: 'pre-wrap', 
                      fontSize: 12,
                      maxHeight: 200,
                      overflow: 'auto',
                    }}
                  >
                    {error.technicalMessage}
                  </Paragraph>
                </div>
              )}
              {errorInfo?.componentStack && (
                <div>
                  <Text strong>组件堆栈 / Component Stack: </Text>
                  <Paragraph 
                    code 
                    style={{ 
                      whiteSpace: 'pre-wrap', 
                      fontSize: 11,
                      maxHeight: 150,
                      overflow: 'auto',
                    }}
                  >
                    {errorInfo.componentStack}
                  </Paragraph>
                </div>
              )}
              <Button 
                icon={copied ? <CheckOutlined /> : <CopyOutlined />}
                onClick={this.handleCopyError}
                size="small"
              >
                {copied ? '已复制 / Copied' : '复制错误报告 / Copy Error Report'}
              </Button>
            </Space>
          </Card>
        </Panel>
      </Collapse>
    );
  }

  renderFallback(): ReactNode {
    const { fallback, level = 'page' } = this.props;
    const { error, errorInfo } = this.state;
    
    if (!error) return null;
    
    // Custom fallback
    if (fallback) {
      if (typeof fallback === 'function') {
        return fallback({ 
          error, 
          errorInfo, 
          resetError: this.handleRetry 
        });
      }
      return fallback;
    }
    
    // Default fallback based on level
    const titles: Record<string, { zh: string; en: string }> = {
      page: { zh: '页面出错了', en: 'Page Error' },
      component: { zh: '组件加载失败', en: 'Component Error' },
      critical: { zh: '系统错误', en: 'System Error' },
    };
    
    const subtitles: Record<string, { zh: string; en: string }> = {
      page: { 
        zh: '抱歉，页面发生了一些问题。请尝试刷新页面或返回首页。', 
        en: 'Sorry, something went wrong with this page. Please try refreshing or go back home.' 
      },
      component: { 
        zh: '此组件无法正常加载，但您可以继续使用其他功能。', 
        en: 'This component failed to load, but you can continue using other features.' 
      },
      critical: { 
        zh: '系统遇到了严重错误，请联系技术支持。', 
        en: 'The system encountered a critical error. Please contact support.' 
      },
    };
    
    const title = titles[level] || titles.page;
    const subtitle = subtitles[level] || subtitles.page;
    
    return (
      <div 
        style={{ 
          padding: level === 'component' ? 24 : 48,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: level === 'page' ? '60vh' : 'auto',
        }}
        role="alert"
        aria-live="assertive"
      >
        <Result
          status="error"
          title={`${title.zh} / ${title.en}`}
          subTitle={`${subtitle.zh} / ${subtitle.en}`}
          extra={
            <Space wrap>
              <Button 
                type="primary" 
                icon={<ReloadOutlined />}
                onClick={this.handleRetry}
              >
                重试 / Retry
              </Button>
              {level !== 'component' && (
                <>
                  <Button 
                    icon={<ReloadOutlined />}
                    onClick={this.handleRefresh}
                  >
                    刷新页面 / Refresh
                  </Button>
                  <Button 
                    icon={<HomeOutlined />}
                    onClick={this.handleGoHome}
                  >
                    返回首页 / Go Home
                  </Button>
                </>
              )}
            </Space>
          }
        />
        {this.renderErrorDetails()}
      </div>
    );
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.renderFallback();
    }

    return this.props.children;
  }
}

// Convenience wrapper for page-level errors
export const PageErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <EnhancedErrorBoundary level="page">
    {children}
  </EnhancedErrorBoundary>
);

// Convenience wrapper for component-level errors
export const ComponentErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <EnhancedErrorBoundary level="component" showTechnicalDetails={false}>
    {children}
  </EnhancedErrorBoundary>
);

export default EnhancedErrorBoundary;
