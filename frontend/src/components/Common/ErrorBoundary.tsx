// Error boundary component
import { Component, type ReactNode, type ErrorInfo } from 'react';
import { Button, Result } from 'antd';
import i18n from '../../locales/config';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: undefined });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const t = i18n.t.bind(i18n);

      return (
        <Result
          status="error"
          title={t('common:error.title')}
          subTitle={t('common:errorBoundary.pageError')}
          extra={[
            <Button key="retry" type="primary" onClick={this.handleRetry}>
              {t('common:retry')}
            </Button>,
            <Button key="home" onClick={() => (window.location.href = '/')}>
              {t('common:errorBoundary.backHome')}
            </Button>,
          ]}
        />
      );
    }

    return this.props.children;
  }
}
