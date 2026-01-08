// Label Studio iframe embed component
import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Spin, Alert, Button, Space, message } from 'antd';
import { ReloadOutlined, ExpandOutlined, CompressOutlined, SyncOutlined, InfoCircleOutlined } from '@ant-design/icons';

interface LabelStudioEmbedProps {
  projectId: string;
  taskId?: string;
  baseUrl?: string;
  token?: string;
  onAnnotationCreate?: (annotation: unknown) => void;
  onAnnotationUpdate?: (annotation: unknown) => void;
  onTaskComplete?: (taskId: string) => void;
  onProgressUpdate?: (progress: { completed: number; total: number }) => void;
  height?: number | string;
}

interface LabelStudioMessage {
  type: string;
  payload?: any;
  taskId?: string;
  annotationId?: string;
  progress?: { completed: number; total: number };
}

export const LabelStudioEmbed: React.FC<LabelStudioEmbedProps> = ({
  projectId,
  taskId,
  baseUrl = '/label-studio',
  token,
  onAnnotationCreate,
  onAnnotationUpdate,
  onTaskComplete,
  onProgressUpdate,
  height = 600,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [lastActivity, setLastActivity] = useState<Date | null>(null);

  // Build Label Studio URL with authentication and context
  const getLabelStudioUrl = useCallback(() => {
    const params = new URLSearchParams();
    
    if (token) {
      params.append('token', token);
    }
    
    if (taskId) {
      params.append('task', taskId);
    }
    
    // Add iframe mode and communication flags
    params.append('mode', 'iframe');
    params.append('enable_postmessage', 'true');
    params.append('enable_hotkeys', 'true');
    
    let url = `${baseUrl}/projects/${projectId}/data`;
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    return url;
  }, [baseUrl, projectId, taskId, token]);

  // Enhanced message handling with better error handling and logging
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Enhanced origin verification
      const allowedOrigins = [
        window.location.origin,
        'http://localhost:8080',
        'http://localhost:8081',
        'https://labelstudio.heartex.com'
      ];
      
      if (!allowedOrigins.some(origin => event.origin.includes(origin.split('://')[1]))) {
        console.warn('Rejected message from unauthorized origin:', event.origin);
        return;
      }

      try {
        let message: LabelStudioMessage;
        
        // Handle both string and object messages
        if (typeof event.data === 'string') {
          try {
            message = JSON.parse(event.data);
          } catch {
            // Not a JSON message, might be a simple string command
            message = { type: event.data };
          }
        } else {
          message = event.data;
        }

        // Update last activity timestamp
        setLastActivity(new Date());

        console.log('Label Studio message received:', message);

        switch (message.type) {
          case 'labelStudio:ready':
          case 'ls:ready':
            setLoading(false);
            setError(null);
            setConnectionStatus('connected');
            message.success('Label Studio 已就绪');
            break;

          case 'labelStudio:annotationCreated':
          case 'ls:annotationCreated':
            setConnectionStatus('connected');
            onAnnotationCreate?.(message.payload);
            break;

          case 'labelStudio:annotationUpdated':
          case 'ls:annotationUpdated':
            setConnectionStatus('connected');
            onAnnotationUpdate?.(message.payload);
            break;

          case 'labelStudio:taskCompleted':
          case 'ls:taskCompleted':
            setConnectionStatus('connected');
            if (message.taskId || taskId) {
              onTaskComplete?.(message.taskId || taskId!);
            }
            break;

          case 'labelStudio:progressUpdate':
          case 'ls:progressUpdate':
            setConnectionStatus('connected');
            if (message.progress) {
              onProgressUpdate?.(message.progress);
            }
            break;

          case 'labelStudio:error':
          case 'ls:error':
            setError(String(message.payload || 'Unknown error occurred'));
            setConnectionStatus('disconnected');
            setLoading(false);
            break;

          case 'labelStudio:taskChanged':
          case 'ls:taskChanged':
            setConnectionStatus('connected');
            console.log('Task changed to:', message.taskId);
            break;

          case 'labelStudio:heartbeat':
          case 'ls:heartbeat':
            setConnectionStatus('connected');
            // Respond to heartbeat to maintain connection
            sendMessageToIframe('heartbeat:response', { timestamp: Date.now() });
            break;

          default:
            // Log unknown message types for debugging
            console.log('Unknown Label Studio message type:', message.type);
        }
      } catch (error) {
        console.error('Error processing Label Studio message:', error);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onAnnotationCreate, onAnnotationUpdate, onTaskComplete, onProgressUpdate, taskId]);

  // Enhanced bi-directional communication
  const sendMessageToIframe = useCallback((type: string, payload?: any) => {
    if (iframeRef.current?.contentWindow) {
      const message = { type, payload, timestamp: Date.now() };
      iframeRef.current.contentWindow.postMessage(message, '*');
      console.log('Sent message to Label Studio:', message);
    }
  }, []);

  // Connection health check
  useEffect(() => {
    const healthCheck = setInterval(() => {
      if (connectionStatus === 'connected') {
        sendMessageToIframe('healthCheck');
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(healthCheck);
  }, [connectionStatus, sendMessageToIframe]);

  // Reload iframe with enhanced error handling
  const handleReload = useCallback(() => {
    setLoading(true);
    setError(null);
    setConnectionStatus('connecting');
    setLastActivity(null);
    
    if (iframeRef.current) {
      iframeRef.current.src = getLabelStudioUrl();
    }
  }, [getLabelStudioUrl]);

  // Toggle fullscreen
  const handleFullscreenToggle = useCallback(() => {
    setFullscreen((prev) => !prev);
  }, []);

  // Handle iframe load with timeout
  const handleIframeLoad = useCallback(() => {
    // Set a timeout to detect if Label Studio doesn't respond
    const timeout = setTimeout(() => {
      if (connectionStatus === 'connecting') {
        setError('Label Studio 响应超时，请检查服务是否正常运行');
        setLoading(false);
        setConnectionStatus('disconnected');
      }
    }, 10000); // 10 second timeout

    // Clear timeout if we receive a ready message
    const clearTimeoutOnReady = () => {
      clearTimeout(timeout);
    };

    // Send initial handshake
    setTimeout(() => {
      sendMessageToIframe('iframe:ready', {
        projectId,
        taskId,
        timestamp: Date.now()
      });
    }, 1000);

    return clearTimeoutOnReady;
  }, [connectionStatus, sendMessageToIframe, projectId, taskId]);

  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setError('无法加载 Label Studio，请检查网络连接和服务状态');
    setLoading(false);
    setConnectionStatus('disconnected');
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

  // Connection status indicator
  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return '#52c41a';
      case 'connecting': return '#1890ff';
      case 'disconnected': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  return (
    <Card
      style={containerStyle}
      styles={{ body: { padding: 0, height: iframeHeight } }}
      title={
        <Space>
          <span>Label Studio</span>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: getConnectionStatusColor(),
              display: 'inline-block'
            }}
            title={`连接状态: ${connectionStatus}`}
          />
        </Space>
      }
      extra={
        <Space>
          <Button
            type="text"
            icon={<SyncOutlined spin={connectionStatus === 'connecting'} />}
            onClick={() => sendMessageToIframe('sync:request')}
            title="同步状态"
            disabled={connectionStatus !== 'connected'}
          />
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={handleReload}
            title="重新加载"
          />
          <Button
            type="text"
            icon={fullscreen ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={handleFullscreenToggle}
            title={fullscreen ? '退出全屏' : '全屏模式'}
          />
          {lastActivity && (
            <Button
              type="text"
              icon={<InfoCircleOutlined />}
              title={`最后活动: ${lastActivity.toLocaleTimeString()}`}
            />
          )}
        </Space>
      }
    >
      {/* Loading indicator with enhanced feedback */}
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 10,
            textAlign: 'center'
          }}
        >
          <Spin size="large" tip="正在加载 Label Studio..." />
          <div style={{ marginTop: 16, color: '#666' }}>
            <p>连接状态: {connectionStatus}</p>
            {connectionStatus === 'connecting' && (
              <p style={{ fontSize: 12 }}>
                如果长时间无响应，请检查 Label Studio 服务是否正常运行
              </p>
            )}
          </div>
        </div>
      )}

      {/* Enhanced error alert */}
      {error && (
        <Alert
          type="error"
          message="Label Studio 加载错误"
          description={
            <div>
              <p>{error}</p>
              <p style={{ fontSize: 12, marginTop: 8 }}>
                可能的解决方案：
              </p>
              <ul style={{ fontSize: 12, paddingLeft: 16 }}>
                <li>检查 Label Studio 服务是否正常运行</li>
                <li>验证网络连接是否正常</li>
                <li>确认项目 ID 和任务 ID 是否正确</li>
                <li>检查认证令牌是否有效</li>
              </ul>
            </div>
          }
          showIcon
          action={
            <Button size="small" onClick={handleReload}>
              重试
            </Button>
          }
          style={{ margin: 16 }}
        />
      )}

      {/* iframe with enhanced attributes */}
      <iframe
        ref={iframeRef}
        src={getLabelStudioUrl()}
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          display: error ? 'none' : 'block',
        }}
        onLoad={handleIframeLoad}
        onError={handleIframeError}
        title="Label Studio 标注界面"
        allow="clipboard-read; clipboard-write; fullscreen"
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
      />
    </Card>
  );
};

// Enhanced utility functions for external use
export const labelStudioUtils = {
  // Send annotation to Label Studio
  submitAnnotation: (iframe: HTMLIFrameElement, annotation: unknown) => {
    iframe.contentWindow?.postMessage(
      { 
        type: 'labelStudio:submitAnnotation', 
        payload: annotation,
        timestamp: Date.now()
      },
      '*'
    );
  },

  // Navigate to specific task
  navigateToTask: (iframe: HTMLIFrameElement, taskId: string) => {
    iframe.contentWindow?.postMessage(
      { 
        type: 'labelStudio:navigateToTask', 
        payload: { taskId },
        timestamp: Date.now()
      },
      '*'
    );
  },

  // Skip current task
  skipTask: (iframe: HTMLIFrameElement) => {
    iframe.contentWindow?.postMessage(
      { 
        type: 'labelStudio:skipTask',
        timestamp: Date.now()
      }, 
      '*'
    );
  },

  // Request current status
  requestStatus: (iframe: HTMLIFrameElement) => {
    iframe.contentWindow?.postMessage(
      { 
        type: 'labelStudio:requestStatus',
        timestamp: Date.now()
      }, 
      '*'
    );
  },

  // Save current annotation
  saveAnnotation: (iframe: HTMLIFrameElement) => {
    iframe.contentWindow?.postMessage(
      { 
        type: 'labelStudio:saveAnnotation',
        timestamp: Date.now()
      }, 
      '*'
    );
  }
};
