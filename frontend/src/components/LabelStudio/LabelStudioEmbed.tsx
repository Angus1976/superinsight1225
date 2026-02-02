// Label Studio iframe embed component with SSO authentication and language synchronization
import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Card, Spin, Alert, Button, Space, message, Tag, Tooltip } from 'antd';
import { ReloadOutlined, ExpandOutlined, CompressOutlined, SyncOutlined, InfoCircleOutlined, GlobalOutlined, TeamOutlined } from '@ant-design/icons';
import { useLanguageStore, type LabelStudioLanguageMessage } from '@/stores/languageStore';
import { useTranslation } from 'react-i18next';
import { useLSWorkspaceContext } from '@/hooks/useLSWorkspaces';
import apiClient from '@/services/api/client';
import type { WorkspaceInfo, WorkspaceMessageType } from '@/services/iframe/types';

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
  /** Workspace ID for Label Studio Enterprise integration */
  workspaceId?: string | null;
  /** Callback when workspace context changes */
  onWorkspaceContextChange?: (context: WorkspaceInfo | null) => void;
}

interface LabelStudioMessage {
  type: string;
  payload?: any;
  taskId?: string;
  annotationId?: string;
  progress?: { completed: number; total: number };
  lang?: string;
  source?: string;
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
  workspaceId,
  onWorkspaceContextChange,
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [lastActivity, setLastActivity] = useState<Date | null>(null);
  
  // SSO token state
  const [ssoToken, setSsoToken] = useState<string | null>(null);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [labelStudioUrl, setLabelStudioUrl] = useState<string>('');

  // Language store integration
  const { language, syncToLabelStudio } = useLanguageStore();
  const { t } = useTranslation();

  // Track previous language to detect changes
  const prevLanguageRef = useRef(language);

  // Workspace context integration
  const workspaceContext = useLSWorkspaceContext(workspaceId);

  // Build workspace info for iframe
  const workspaceInfo = useMemo((): WorkspaceInfo | null => {
    if (!workspaceContext.workspace || !workspaceId) return null;
    return {
      id: workspaceContext.workspace.id,
      name: workspaceContext.workspace.name,
      description: workspaceContext.workspace.description,
      role: workspaceContext.userRole || 'viewer',
      permissions: workspaceContext.permissions.map(p => ({
        permission: p,
        granted: true,
      })),
      settings: workspaceContext.workspace.settings,
    };
  }, [workspaceContext.workspace, workspaceContext.userRole, workspaceContext.permissions, workspaceId]);

  // Track workspace changes and notify
  const prevWorkspaceIdRef = useRef(workspaceId);
  useEffect(() => {
    if (prevWorkspaceIdRef.current !== workspaceId) {
      prevWorkspaceIdRef.current = workspaceId;
      onWorkspaceContextChange?.(workspaceInfo);
    }
  }, [workspaceId, workspaceInfo, onWorkspaceContextChange]);

  // Fetch SSO token or login URL on mount
  useEffect(() => {
    const fetchLoginUrl = async () => {
      try {
        const response = await apiClient.get('/api/label-studio/auth/login-url', {
          params: {
            project_id: projectId,
            task_id: taskId,
          },
        });
        
        if (response.data.sso_enabled && response.data.url) {
          // SSO is enabled, extract token from URL using regex (more robust than URL parsing)
          const tokenMatch = response.data.url.match(/[?&]token=([^&]+)/);
          if (tokenMatch && tokenMatch[1]) {
            setSsoToken(tokenMatch[1]);
            console.log('[LabelStudioEmbed] SSO token extracted successfully');
          }
          setSsoEnabled(true);
        }
        // Always use the proxy path for frontend, not the internal Docker URL
        setLabelStudioUrl('/label-studio');
      } catch (err) {
        console.warn('Failed to fetch SSO login URL:', err);
        // Fall back to proxy URL
        setLabelStudioUrl('/label-studio');
      }
    };
    
    fetchLoginUrl();
  }, [projectId, taskId]);
  
  // Build Label Studio URL with authentication, context, language, and workspace
  const getLabelStudioUrl = useCallback(() => {
    const params = new URLSearchParams();

    // Use SSO token if available, otherwise use provided token
    const authToken = ssoToken || token;
    if (authToken) {
      params.append('token', authToken);
    }

    if (taskId) {
      params.append('task', taskId);
    }

    // Add iframe mode and communication flags
    params.append('mode', 'iframe');
    params.append('enable_postmessage', 'true');
    params.append('enable_hotkeys', 'true');

    // Add language parameter for Label Studio localization
    params.append('lang', language);

    // Add workspace ID for Label Studio Enterprise
    if (workspaceId) {
      params.append('workspace', workspaceId);
    }

    // Use the fetched Label Studio URL or fall back to baseUrl
    const effectiveBaseUrl = labelStudioUrl || baseUrl;
    let url = `${effectiveBaseUrl}/projects/${projectId}/data`;
    if (params.toString()) {
      url += `?${params.toString()}`;
    }

    return url;
  }, [baseUrl, projectId, taskId, token, ssoToken, language, workspaceId, labelStudioUrl]);

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
        let lsMessage: LabelStudioMessage;
        
        // Handle both string and object messages
        if (typeof event.data === 'string') {
          try {
            lsMessage = JSON.parse(event.data);
          } catch {
            // Not a JSON message, might be a simple string command
            lsMessage = { type: event.data };
          }
        } else {
          lsMessage = event.data;
        }

        // Update last activity timestamp
        setLastActivity(new Date());

        console.log('Label Studio message received:', lsMessage);

        switch (lsMessage.type) {
          case 'labelStudio:ready':
          case 'ls:ready':
            setLoading(false);
            setError(null);
            setConnectionStatus('connected');
            // Sync language when Label Studio is ready
            syncToLabelStudio();
            message.success(t('labelStudio.ready', 'Label Studio 已就绪'));
            break;

          case 'labelStudio:annotationCreated':
          case 'ls:annotationCreated':
            setConnectionStatus('connected');
            onAnnotationCreate?.(lsMessage.payload);
            break;

          case 'labelStudio:annotationUpdated':
          case 'ls:annotationUpdated':
            setConnectionStatus('connected');
            onAnnotationUpdate?.(lsMessage.payload);
            break;

          case 'labelStudio:taskCompleted':
          case 'ls:taskCompleted':
            setConnectionStatus('connected');
            if (lsMessage.taskId || taskId) {
              onTaskComplete?.(lsMessage.taskId || taskId!);
            }
            break;

          case 'labelStudio:progressUpdate':
          case 'ls:progressUpdate':
            setConnectionStatus('connected');
            if (lsMessage.progress) {
              onProgressUpdate?.(lsMessage.progress);
            }
            break;

          case 'labelStudio:error':
          case 'ls:error':
            setError(String(lsMessage.payload || t('labelStudio.unknownError', 'Unknown error occurred')));
            setConnectionStatus('disconnected');
            setLoading(false);
            break;

          case 'labelStudio:taskChanged':
          case 'ls:taskChanged':
            setConnectionStatus('connected');
            console.log('Task changed to:', lsMessage.taskId);
            break;

          case 'labelStudio:heartbeat':
          case 'ls:heartbeat':
            setConnectionStatus('connected');
            // Respond to heartbeat to maintain connection
            sendMessageToIframe('heartbeat:response', { timestamp: Date.now() });
            break;
            
          case 'languageChanged':
            // Handle language change from Label Studio
            if (lsMessage.lang && (lsMessage.lang === 'zh' || lsMessage.lang === 'en')) {
              console.log('Label Studio language changed to:', lsMessage.lang);
            }
            break;

          // Workspace context message handlers
          case 'workspace:context:request':
            // Label Studio is requesting workspace context
            if (workspaceInfo) {
              sendMessageToIframe('workspace:context', workspaceInfo);
              console.log('Sent workspace context to Label Studio:', workspaceInfo);
            }
            break;

          case 'workspace:permission:check':
            // Handle permission check request from Label Studio
            if (lsMessage.payload && typeof lsMessage.payload === 'object') {
              const permissionPayload = lsMessage.payload as { permission: string };
              const hasPermission = workspaceContext.can(permissionPayload.permission as any);
              sendMessageToIframe('workspace:permission:result', {
                permission: permissionPayload.permission,
                granted: hasPermission,
              });
              console.log(`Permission check for ${permissionPayload.permission}:`, hasPermission);
            }
            break;

          default:
            // Log unknown message types for debugging
            console.log('Unknown Label Studio message type:', lsMessage.type);
        }
      } catch (error) {
        console.error('Error processing Label Studio message:', error);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [onAnnotationCreate, onAnnotationUpdate, onTaskComplete, onProgressUpdate, taskId, syncToLabelStudio, t]);
  
  // Reload iframe when language changes to apply Label Studio's built-in localization
  // Label Studio uses Django's i18n which requires a page reload to change language
  useEffect(() => {
    if (prevLanguageRef.current !== language && connectionStatus === 'connected') {
      console.log(`[LabelStudioEmbed] Language changed from ${prevLanguageRef.current} to ${language}, reloading iframe...`);
      prevLanguageRef.current = language;
      
      // Show loading state and reload iframe
      setLoading(true);
      setConnectionStatus('connecting');
      
      if (iframeRef.current) {
        // Reload the iframe to apply new language
        iframeRef.current.src = getLabelStudioUrl();
      }
      
      // Also try postMessage sync (may work for some Label Studio versions)
      syncToLabelStudio();
      
      message.info(t('labelStudio.languageChanging', '正在切换 Label Studio 语言...'));
    }
  }, [language, connectionStatus, syncToLabelStudio, getLabelStudioUrl, t]);

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
        // Label Studio loaded but didn't send ready message - this is OK
        // Just mark as connected and hide loading
        console.log('[LabelStudioEmbed] Timeout reached, assuming Label Studio is ready');
        setLoading(false);
        setConnectionStatus('connected');
        setError(null);
      }
    }, 30000); // 30 second timeout (increased from 10s)

    // Clear timeout if we receive a ready message
    const clearTimeoutOnReady = () => {
      clearTimeout(timeout);
    };

    // Send initial handshake
    setTimeout(() => {
      sendMessageToIframe('iframe:ready', {
        projectId,
        taskId,
        language,
        timestamp: Date.now()
      });
    }, 1000);

    return clearTimeoutOnReady;
  }, [connectionStatus, sendMessageToIframe, projectId, taskId, language, t]);

  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setError(t('labelStudio.loadError', '无法加载 Label Studio，请检查网络连接和服务状态'));
    setLoading(false);
    setConnectionStatus('disconnected');
  }, [t]);

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
  
  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return t('labelStudio.status.connected', '已连接');
      case 'connecting': return t('labelStudio.status.connecting', '连接中');
      case 'disconnected': return t('labelStudio.status.disconnected', '已断开');
      default: return '';
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
            title={`${t('labelStudio.connectionStatus', '连接状态')}: ${getConnectionStatusText()}`}
          />
        </Space>
      }
      extra={
        <Space>
          <Button
            type="text"
            icon={<GlobalOutlined />}
            title={`${t('common.language', '语言')}: ${language === 'zh' ? '中文' : 'English'}`}
          />
          <Button
            type="text"
            icon={<SyncOutlined spin={connectionStatus === 'connecting'} />}
            onClick={() => sendMessageToIframe('sync:request')}
            title={t('labelStudio.syncStatus', '同步状态')}
            disabled={connectionStatus !== 'connected'}
          />
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={handleReload}
            title={t('common.reload', '重新加载')}
          />
          <Button
            type="text"
            icon={fullscreen ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={handleFullscreenToggle}
            title={fullscreen ? t('labelStudio.exitFullscreen', '退出全屏') : t('labelStudio.fullscreen', '全屏模式')}
          />
          {lastActivity && (
            <Button
              type="text"
              icon={<InfoCircleOutlined />}
              title={`${t('labelStudio.lastActivity', '最后活动')}: ${lastActivity.toLocaleTimeString()}`}
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
          <Spin size="large" tip={t('labelStudio.loading', '正在加载 Label Studio...')} />
          <div style={{ marginTop: 16, color: '#666' }}>
            <p>{t('labelStudio.connectionStatus', '连接状态')}: {getConnectionStatusText()}</p>
            {connectionStatus === 'connecting' && (
              <p style={{ fontSize: 12 }}>
                {t('labelStudio.loadingHint', '如果长时间无响应，请检查 Label Studio 服务是否正常运行')}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Enhanced error alert */}
      {error && (
        <Alert
          type="error"
          message={t('labelStudio.loadErrorTitle', 'Label Studio 加载错误')}
          description={
            <div>
              <p>{error}</p>
              <p style={{ fontSize: 12, marginTop: 8 }}>
                {t('labelStudio.possibleSolutions', '可能的解决方案')}：
              </p>
              <ul style={{ fontSize: 12, paddingLeft: 16 }}>
                <li>{t('labelStudio.solution1', '检查 Label Studio 服务是否正常运行')}</li>
                <li>{t('labelStudio.solution2', '验证网络连接是否正常')}</li>
                <li>{t('labelStudio.solution3', '确认项目 ID 和任务 ID 是否正确')}</li>
                <li>{t('labelStudio.solution4', '检查认证令牌是否有效')}</li>
              </ul>
            </div>
          }
          showIcon
          action={
            <Button size="small" onClick={handleReload}>
              {t('common.retry', '重试')}
            </Button>
          }
          style={{ margin: 16 }}
        />
      )}

      {/* iframe with enhanced attributes and language sync */}
      <iframe
        ref={iframeRef}
        data-label-studio
        src={getLabelStudioUrl()}
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          display: error ? 'none' : 'block',
        }}
        onLoad={handleIframeLoad}
        onError={handleIframeError}
        title={t('labelStudio.title', 'Label Studio 标注界面')}
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
