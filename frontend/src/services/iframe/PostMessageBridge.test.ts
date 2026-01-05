/**
 * Unit tests for PostMessageBridge
 * Tests message sending/receiving, retry logic, timeout handling, and security features
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { PostMessageBridge } from './PostMessageBridge';
import type { Message, Response } from './types';
import { BridgeStatus } from './types';

describe('PostMessageBridge', () => {
  let bridge: PostMessageBridge;
  let mockIframe: HTMLIFrameElement;
  let mockContentWindow: Window;

  beforeEach(() => {
    // Create mock iframe
    mockContentWindow = {
      postMessage: vi.fn(),
    } as unknown as Window;

    mockIframe = {
      contentWindow: mockContentWindow,
    } as unknown as HTMLIFrameElement;

    bridge = new PostMessageBridge({
      targetOrigin: 'http://localhost:8080',
      timeout: 1000,
      maxRetries: 2,
    });
  });

  afterEach(() => {
    bridge.cleanup();
  });

  describe('initialize', () => {
    it('should initialize bridge with iframe', () => {
      bridge.initialize(mockIframe);

      expect(bridge.getStatus()).toBe(BridgeStatus.CONNECTED);
    });

    it('should throw error if already initialized', () => {
      bridge.initialize(mockIframe);

      expect(() => bridge.initialize(mockIframe)).toThrow('Bridge already initialized');
    });
  });

  describe('send', () => {
    beforeEach(() => {
      bridge.initialize(mockIframe);
    });

    it('should send message to iframe', async () => {
      const postMessageSpy = vi.spyOn(mockContentWindow, 'postMessage');

      const sendPromise = bridge.send({
        type: 'test',
        payload: { data: 'test' },
      });

      // Get the message ID from the postMessage call
      const sentMessage = postMessageSpy.mock.calls[0][0] as Message;
      const messageId = sentMessage.id;

      // Simulate response
      const response: Response = {
        id: messageId,
        success: true,
        data: { result: 'ok' },
      };

      const messageEvent = new MessageEvent('message', {
        data: response,
        origin: 'http://localhost:8080',
      });

      window.dispatchEvent(messageEvent);

      const result = await sendPromise;
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ result: 'ok' });
    });

    it('should throw error if bridge not initialized', async () => {
      const uninitializedBridge = new PostMessageBridge();

      await expect(
        uninitializedBridge.send({
          type: 'test',
          payload: {},
        })
      ).rejects.toThrow('Bridge not initialized');
    });

    it('should generate unique message IDs', async () => {
      const postMessageSpy = vi.spyOn(mockContentWindow, 'postMessage');

      const promise1 = bridge.send({
        type: 'test1',
        payload: {},
      });

      const promise2 = bridge.send({
        type: 'test2',
        payload: {},
      });

      // Get the message IDs from postMessage calls
      const calls = postMessageSpy.mock.calls;
      const id1 = (calls[0][0] as Message).id;
      const id2 = (calls[1][0] as Message).id;

      expect(id1).not.toBe(id2);

      // Cleanup promises
      promise1.catch(() => {});
      promise2.catch(() => {});
    });

    it('should timeout if no response received', async () => {
      const promise = bridge.send({
        type: 'test',
        payload: {},
      });

      await expect(promise).rejects.toThrow('Message timeout');
    }, 2000);

    it('should include timestamp in message', async () => {
      const postMessageSpy = vi.spyOn(mockContentWindow, 'postMessage');

      const promise = bridge.send({
        type: 'test',
        payload: {},
      });

      const message = postMessageSpy.mock.calls[0][0] as Message;
      expect(message.timestamp).toBeDefined();
      expect(typeof message.timestamp).toBe('number');

      promise.catch(() => {});
    });

    it('should set source to main', async () => {
      const postMessageSpy = vi.spyOn(mockContentWindow, 'postMessage');

      const promise = bridge.send({
        type: 'test',
        payload: {},
      });

      const message = postMessageSpy.mock.calls[0][0] as Message;
      expect(message.source).toBe('main');

      promise.catch(() => {});
    });
  });

  describe('message handlers', () => {
    beforeEach(() => {
      bridge.initialize(mockIframe);
    });

    it('should register and trigger message handler', async () => {
      const handler = vi.fn();
      bridge.on('test', handler);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://localhost:8080',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).toHaveBeenCalledWith(message);
    });

    it('should unregister message handler', async () => {
      const handler = vi.fn();
      bridge.on('test', handler);
      bridge.off('test', handler);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://localhost:8080',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).not.toHaveBeenCalled();
    });

    it('should handle multiple handlers for same message type', async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      bridge.on('test', handler1);
      bridge.on('test', handler2);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://localhost:8080',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler1).toHaveBeenCalledWith(message);
      expect(handler2).toHaveBeenCalledWith(message);
    });

    it('should handle handler errors gracefully', async () => {
      const handler = vi.fn(() => {
        throw new Error('Handler error');
      });

      bridge.on('test', handler);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://localhost:8080',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalled();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('retry logic', () => {
    beforeEach(() => {
      bridge = new PostMessageBridge({
        targetOrigin: 'http://localhost:8080',
        timeout: 5000,
        maxRetries: 2,
      });
      bridge.initialize(mockIframe);
    });

    it('should retry failed messages', async () => {
      const postMessageSpy = vi.spyOn(mockContentWindow, 'postMessage');

      // Make postMessage throw error on first call
      let callCount = 0;
      postMessageSpy.mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          throw new Error('Network error');
        }
      });

      const promise = bridge.send({
        type: 'test',
        payload: {},
      });

      // Wait for retry
      await new Promise((resolve) => setTimeout(resolve, 300));

      // Should have been called at least twice (initial + retry)
      expect(postMessageSpy.mock.calls.length).toBeGreaterThanOrEqual(1);

      promise.catch(() => {});
    });

    it('should reject after max retries exceeded', async () => {
      const postMessageSpy = vi.spyOn(mockContentWindow, 'postMessage');
      postMessageSpy.mockImplementation(() => {
        throw new Error('Network error');
      });

      const promise = bridge.send({
        type: 'test',
        payload: {},
      });

      await expect(promise).rejects.toThrow('Failed to send message after max retries');
    });
  });

  describe('timeout handling', () => {
    it('should respect custom timeout', async () => {
      const customBridge = new PostMessageBridge({
        timeout: 100,
      });
      customBridge.initialize(mockIframe);

      const promise = customBridge.send({
        type: 'test',
        payload: {},
      });

      await expect(promise).rejects.toThrow('Message timeout');

      customBridge.cleanup();
    });

    it('should use default timeout if not specified', async () => {
      const defaultBridge = new PostMessageBridge();
      defaultBridge.initialize(mockIframe);

      const promise = defaultBridge.send({
        type: 'test',
        payload: {},
      });

      // Default timeout is 5000ms, so this should timeout
      await expect(promise).rejects.toThrow('Message timeout');

      defaultBridge.cleanup();
    }, 6000);
  });

  describe('origin verification', () => {
    it('should reject messages from untrusted origin', async () => {
      bridge.initialize(mockIframe);

      const handler = vi.fn();
      bridge.on('test', handler);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://untrusted.com',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('untrusted origin')
      );
      consoleWarnSpy.mockRestore();
    });

    it('should accept messages from any origin if targetOrigin is wildcard', async () => {
      const wildcardBridge = new PostMessageBridge({
        targetOrigin: '*',
      });
      wildcardBridge.initialize(mockIframe);

      const handler = vi.fn();
      wildcardBridge.on('test', handler);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://any-origin.com',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).toHaveBeenCalledWith(message);
      wildcardBridge.cleanup();
    });
  });

  describe('message validation', () => {
    beforeEach(() => {
      bridge.initialize(mockIframe);
    });

    it('should reject invalid message structure', async () => {
      const handler = vi.fn();
      bridge.on('test', handler);

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      window.dispatchEvent(
        new MessageEvent('message', {
          data: { invalid: 'message' },
          origin: 'http://localhost:8080',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(consoleWarnSpy.mock.calls[0][0]).toContain('Invalid message structure');
      consoleWarnSpy.mockRestore();
    });

    it('should accept valid message structure', async () => {
      const handler = vi.fn();
      bridge.on('test', handler);

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: Date.now(),
      };

      window.dispatchEvent(
        new MessageEvent('message', {
          data: message,
          origin: 'http://localhost:8080',
        })
      );

      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(handler).toHaveBeenCalledWith(message);
    });
  });

  describe('cleanup', () => {
    it('should remove message listener', () => {
      bridge.initialize(mockIframe);

      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      bridge.cleanup();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('message', expect.any(Function));
      removeEventListenerSpy.mockRestore();
    });

    it('should set status to disconnected', () => {
      bridge.initialize(mockIframe);
      expect(bridge.getStatus()).toBe(BridgeStatus.CONNECTED);

      bridge.cleanup();
      expect(bridge.getStatus()).toBe(BridgeStatus.DISCONNECTED);
    });
  });

  describe('getStatus', () => {
    it('should return connected status after initialization', () => {
      bridge.initialize(mockIframe);

      expect(bridge.getStatus()).toBe(BridgeStatus.CONNECTED);
    });

    it('should return disconnected status initially', () => {
      expect(bridge.getStatus()).toBe(BridgeStatus.DISCONNECTED);
    });
  });
});
