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
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    try {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

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
        reconnectAttemptsRef.current = 0;

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

        // Trigger disconnect event
        const handlers = eventHandlersRef.current.get('disconnect');
        if (handlers) {
          handlers.forEach((handler) => handler({}));
        }

        if (onDisconnect) {
          onDisconnect();
        }

        // Attempt reconnection
        if (reconnectAttemptsRef.current < reconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
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
          const { event: eventName, data: eventData } = data;

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
  }, [url, reconnectAttempts, reconnectInterval, onConnect, onDisconnect, onError]);

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
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event,
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

  return {
    on,
    off,
    emit,
    close,
    isConnected: isConnectedCheck,
  };
};

export default useWebSocket;
