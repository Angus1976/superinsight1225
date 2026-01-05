/**
 * IframeContainer - React component for Label Studio iframe with loading and error handling
 * Provides progress bar, error display, and retry mechanism
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Spin, Alert, Button, Space, Progress } from 'antd';
import { ReloadOutlined, ExpandOutlined, CompressOutlined } from '@ant-design/icons';
import { IframeManager, IframeConfig, IframeStatus } from '../../services/iframe';

interface IframeContainerProps {
  config: IframeConfig;
  onReady?: () => void;
  onError?: (error: string) => void;
  onStatusChange?: (status: IframeStatus) => void;
  height?: number | string;
  showToolbar?: boolean;
}

export const IframeContainer: React.FC<IframeContainerProps> = ({
  config,
  onReady,
  onError,
  onStatusChange,
  height = 600,
  showToolbar = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const managerRef = useRef<IframeManager | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [status, setStatus] = useState<IframeStatus>(IframeStatus.LOADING);

  // Initialize iframe manager
  useEffect(() => {
    if (!containerRef.current) return;

    const manager = new IframeManager();
    managerRef.current = manager;

    // Setup event listeners
    manager.on('load', () => {
      setProgress(30);
    });

    manager.on('ready', () => {
      setLoading(false);
      setError(null);
      setProgress(100);
      setStatus(IframeStatus.READY);
      onStatusChange?.(IframeStatus.READY);
      onReady?.();
    });

    manager.on('error', (event) => {
      const errorMsg = (event.data as { error?: string })?.error || 'Failed to load iframe';
      setLoading(false);
      setError(errorMsg);
      setProgress(0);
      setStatus(IframeStatus.ERROR);
      onStatusChange?.(IframeStatus.ERROR);
      onError?.(errorMsg);
    });

    manager.on('refresh', () => {
      setLoading(true);
      setError(null);
      setProgress(0);
      setStatus(IframeStatus.LOADING);
      onStatusChange?.(IframeStatus.LOADING);
    });

    manager.on('destroy', () => {
      setStatus(IframeStatus.DESTROYED);
      onStatusChange?.(IframeStatus.DESTROYED);
    });

    // Create iframe
    manager.create(config, containerRef.current).catch((err) => {
      console.error('Failed to create iframe:', err);
      setError(err.message);
      setLoading(false);
      setStatus(IframeStatus.ERROR);
      onStatusChange?.(IframeStatus.ERROR);
      onError?.(err.message);
    });

    // Cleanup on unmount
    return () => {
      manager.destroy().catch((err) => {
        console.error('Failed to destroy iframe:', err);
      });
    };
  }, [config, onReady, onError, onStatusChange]);

  // Handle reload
  const handleReload = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.refresh().catch((err) => {
        console.error('Failed to refresh iframe:', err);
      });
    }
  }, []);

  // Handle fullscreen toggle
  const handleFullscreenToggle = useCallback(() => {
    setFullscreen((prev) => !prev);
  }, []);

  const containerStyle: React.CSSProperties = fullscreen
    ? {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 1000,
        background: '#fff',
      }
    : {};

  const iframeHeight = fullscreen ? '100vh' : height;

  return (
    <Card
      style={containerStyle}
      styles={{ body: { padding: 0, height: iframeHeight, position: 'relative' } }}
      title="Label Studio"
      extra={
        showToolbar && (
          <Space>
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={handleReload}
              title="Reload"
              disabled={loading}
            />
            <Button
              type="text"
              icon={fullscreen ? <CompressOutlined /> : <ExpandOutlined />}
              onClick={handleFullscreenToggle}
              title={fullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            />
          </Space>
        )
      }
    >
      {/* Loading indicator with progress */}
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
            background: 'rgba(255, 255, 255, 0.9)',
          }}
        >
          <Spin size="large" tip="Loading Label Studio..." />
          {progress > 0 && (
            <div style={{ marginTop: 16, width: 200 }}>
              <Progress percent={progress} status="active" />
            </div>
          )}
        </div>
      )}

      {/* Error alert with retry button */}
      {error && (
        <Alert
          type="error"
          message="Label Studio Error"
          description={error}
          showIcon
          action={
            <Button size="small" onClick={handleReload}>
              Retry
            </Button>
          }
          style={{ margin: 16 }}
        />
      )}

      {/* iframe container */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          display: error ? 'none' : 'block',
        }}
      />
    </Card>
  );
};
