/**
 * WebSocket Hook
 *
 * Provides WebSocket connection management with:
 * - Automatic reconnection
 * - Event handling
 * - Connection state management
 * - Error handling
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { message } from 'antd';

type EventHandler = (data: any) => void;

interface WebSocketInstance {
  on: (event: string, handler: EventHandler) => void;
  off: (event: string, handler?: EventHandler) => void;
  emit: (event: string, data?: any) => void;
  close: () => void;
  isConnected: () => boolean;
}

interface UseWebSocketOptions {
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

/**
 * Custom hook for WebSocket connections
 *
 * @param url WebSocket URL
 * @param options Connection options
 * @returns WebSocket instance with event methods
 */
export const useWebSocket = (
  url: string,
  options: UseWebSocketOptions = {}
): WebSocketInstance | null => {
  const {
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const eventHandlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const manualCloseRef = useRef(false);
  const isConnectedRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);
  const isWebSocketSupported = typeof WebSocket !== 'undefined';

  const connect = useCallback(() => {
    if (!isWebSocketSupported) {
      return;
    }

    try {
      // If a previous socket instance exists, we avoid force-closing it here.
      // Closing can trigger additional `onclose` events in some test / browser
      // implementations and distort reconnect bookkeeping. Cleanup is handled
      // by the effect cleanup and by the socket's own lifecycle.
      wsRef.current = null;

      // Convert HTTP URL to WebSocket URL
      const wsUrl = url.startsWith('http')
        ? url.replace(/^http/, 'ws')
        : url.startsWith('ws')
        ? url
        : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${url}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        isConnectedRef.current = true;
        reconnectAttemptsRef.current = 0;
        manualCloseRef.current = false;
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }

        // Trigger connect event
        const handlers = eventHandlersRef.current.get('connect');
        if (handlers) {
          handlers.forEach((handler) => handler({}));
        }

        if (onConnect) {
          onConnect();
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        isConnectedRef.current = false;

        // Trigger disconnect event
        const handlers = eventHandlersRef.current.get('disconnect');
        if (handlers) {
          handlers.forEach((handler) => handler({}));
        }

        if (onDisconnect) {
          onDisconnect();
        }

        // Attempt reconnection (skip if we intentionally closed during reconnect/switch).
        // Also avoid scheduling multiple pending reconnect timers.
        if (
          !manualCloseRef.current &&
          reconnectTimeoutRef.current == null &&
          reconnectAttemptsRef.current < reconnectAttempts
        ) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);

        if (onError) {
          onError(error);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Support both legacy `{ type, data }` and `{ event, data }` shapes.
          const eventName = (data?.type ?? data?.event) as string | undefined;
          const eventData = data?.data;
          if (!eventName) {
            return;
          }

          // Trigger event handlers
          const handlers = eventHandlersRef.current.get(eventName);
          if (handlers) {
            handlers.forEach((handler) => handler(eventData));
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }, [isWebSocketSupported, url, reconnectAttempts, reconnectInterval, onConnect, onDisconnect, onError]);

  useEffect(() => {
    connect();

    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const on = useCallback((event: string, handler: EventHandler) => {
    if (!eventHandlersRef.current.has(event)) {
      eventHandlersRef.current.set(event, new Set());
    }

    eventHandlersRef.current.get(event)!.add(handler);
  }, []);

  const off = useCallback((event: string, handler?: EventHandler) => {
    if (!eventHandlersRef.current.has(event)) {
      return;
    }

    if (handler) {
      eventHandlersRef.current.get(event)!.delete(handler);
    } else {
      eventHandlersRef.current.delete(event);
    }
  }, []);

  const emit = useCallback((event: string, data?: any) => {
    // Some test environments do not provide reliable `readyState` constants.
    // Treat "connected" as having seen `onopen`.
    if (wsRef.current && isConnectedRef.current) {
      wsRef.current.send(
        JSON.stringify({
          type: event,
          data,
        })
      );
    } else {
      console.warn('WebSocket is not connected. Cannot emit event:', event);
    }
  }, []);

  const close = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, []);

  const isConnectedCheck = useCallback(() => {
    return isConnected;
  }, [isConnected]);

  if (!isWebSocketSupported) {
    return null;
  }

  return {
    on,
    off,
    emit,
    close,
    isConnected: isConnectedCheck,
  };
};

export default useWebSocket;
