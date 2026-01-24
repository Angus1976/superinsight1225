/**
 * useWebSocket Hook Tests
 *
 * Tests for the custom WebSocket hook including:
 * - Connection establishment
 * - Event handling (on/off/emit)
 * - Automatic reconnection
 * - Connection cleanup
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../useWebSocket';

// Mock WebSocket
class MockWebSocket {
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  readyState: number = WebSocket.CONNECTING;
  CONNECTING = WebSocket.CONNECTING;
  OPEN = WebSocket.OPEN;
  CLOSING = WebSocket.CLOSING;
  CLOSED = WebSocket.CLOSED;

  constructor(url: string) {
    this.url = url;
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper to simulate an error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  // Helper to simulate close
  simulateClose() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
}

describe('useWebSocket', () => {
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    // Mock global WebSocket
    (global as any).WebSocket = vi.fn((url: string) => {
      mockWebSocket = new MockWebSocket(url);
      return mockWebSocket;
    });
    (global as any).window = {
      location: {
        protocol: 'http:',
        host: 'localhost:3000',
      },
    };
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('creates WebSocket connection with correct URL', async () => {
    renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:3000/api/ws');
  });

  it('converts http URL to ws protocol', async () => {
    renderHook(() => useWebSocket('http://example.com/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    expect(global.WebSocket).toHaveBeenCalledWith('ws://example.com/ws');
  });

  it('converts https to wss protocol', async () => {
    (global as any).window.location.protocol = 'https:';

    renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    expect(global.WebSocket).toHaveBeenCalledWith('wss://localhost:3000/api/ws');
  });

  it('registers event listeners with on()', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const handler = vi.fn();
    act(() => {
      result.current?.on('test_event', handler);
    });

    // Simulate receiving a message with the event
    act(() => {
      mockWebSocket.simulateMessage({ type: 'test_event', data: { message: 'hello' } });
    });

    expect(handler).toHaveBeenCalledWith({ message: 'hello' });
  });

  it('unregisters event listeners with off()', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const handler = vi.fn();
    act(() => {
      result.current?.on('test_event', handler);
      result.current?.off('test_event');
    });

    act(() => {
      mockWebSocket.simulateMessage({ type: 'test_event', data: { message: 'hello' } });
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it('emits messages to server', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const sendSpy = vi.spyOn(mockWebSocket, 'send');

    act(() => {
      result.current?.emit('custom_event', { key: 'value' });
    });

    expect(sendSpy).toHaveBeenCalledWith(
      JSON.stringify({ type: 'custom_event', data: { key: 'value' } })
    );
  });

  it('triggers connect event when connection opens', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    const connectHandler = vi.fn();
    act(() => {
      result.current?.on('connect', connectHandler);
    });

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    expect(connectHandler).toHaveBeenCalled();
  });

  it('triggers disconnect event when connection closes', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const disconnectHandler = vi.fn();
    act(() => {
      result.current?.on('disconnect', disconnectHandler);
    });

    act(() => {
      mockWebSocket.simulateClose();
    });

    expect(disconnectHandler).toHaveBeenCalled();
  });

  it('attempts to reconnect after connection closes', async () => {
    renderHook(() => useWebSocket('/api/ws', { reconnectInterval: 1000 }));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    // Clear initial WebSocket call
    vi.clearAllMocks();

    // Simulate connection close
    act(() => {
      mockWebSocket.simulateClose();
    });

    // Wait for reconnect interval
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    // Should attempt to reconnect
    expect(global.WebSocket).toHaveBeenCalledTimes(1);
  });

  it('limits reconnection attempts', async () => {
    renderHook(() =>
      useWebSocket('/api/ws', { reconnectAttempts: 3, reconnectInterval: 1000 })
    );

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    // Clear initial call
    vi.clearAllMocks();

    // Simulate multiple connection failures
    for (let i = 0; i < 4; i++) {
      act(() => {
        mockWebSocket.simulateClose();
      });

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });
    }

    // Should only attempt 3 reconnections
    expect(global.WebSocket).toHaveBeenCalledTimes(3);
  });

  it('resets reconnection attempts on successful connection', async () => {
    const { rerender } = renderHook(() =>
      useWebSocket('/api/ws', { reconnectAttempts: 3, reconnectInterval: 1000 })
    );

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    // Simulate close and reconnect
    act(() => {
      mockWebSocket.simulateClose();
    });

    await act(async () => {
      vi.advanceTimersByTime(1020); // Reconnect + open
    });

    // Clear calls
    vi.clearAllMocks();

    // Close again - should be able to reconnect 3 more times
    for (let i = 0; i < 4; i++) {
      act(() => {
        mockWebSocket.simulateClose();
      });

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });
    }

    expect(global.WebSocket).toHaveBeenCalledTimes(3);
  });

  it('cleans up connection on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const closeSpy = vi.spyOn(mockWebSocket, 'close');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  it('handles JSON parse errors gracefully', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const handler = vi.fn();
    act(() => {
      result.current?.on('test_event', handler);
    });

    // Simulate invalid JSON message
    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage(
          new MessageEvent('message', { data: 'invalid json {' })
        );
      }
    });

    // Handler should not be called
    expect(handler).not.toHaveBeenCalled();
  });

  it('handles multiple event listeners for same event', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    const handler1 = vi.fn();
    const handler2 = vi.fn();

    act(() => {
      result.current?.on('test_event', handler1);
      result.current?.on('test_event', handler2);
    });

    act(() => {
      mockWebSocket.simulateMessage({ type: 'test_event', data: { message: 'hello' } });
    });

    expect(handler1).toHaveBeenCalledWith({ message: 'hello' });
    expect(handler2).toHaveBeenCalledWith({ message: 'hello' });
  });

  it('does not emit messages when connection is closed', async () => {
    const { result } = renderHook(() => useWebSocket('/api/ws'));

    await act(async () => {
      vi.advanceTimersByTime(20);
    });

    act(() => {
      mockWebSocket.simulateClose();
    });

    const sendSpy = vi.spyOn(mockWebSocket, 'send');

    act(() => {
      result.current?.emit('test_event', { data: 'test' });
    });

    expect(sendSpy).not.toHaveBeenCalled();
  });

  it('returns null when WebSocket is not available', () => {
    // Remove WebSocket from global
    const originalWebSocket = (global as any).WebSocket;
    delete (global as any).WebSocket;

    const { result } = renderHook(() => useWebSocket('/api/ws'));

    expect(result.current).toBeNull();

    // Restore WebSocket
    (global as any).WebSocket = originalWebSocket;
  });
});
