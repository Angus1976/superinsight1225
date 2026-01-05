/**
 * Unit tests for IframeManager
 * Tests iframe creation, destruction, lifecycle events, and error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { IframeManager } from './IframeManager';
import { IframeStatus } from './types';

describe('IframeManager', () => {
  let manager: IframeManager;
  let container: HTMLElement;

  beforeEach(() => {
    manager = new IframeManager();
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  afterEach(async () => {
    await manager.destroy();
    if (container.parentElement) {
      container.parentElement.removeChild(container);
    }
  });

  describe('create', () => {
    it('should create iframe element and append to container', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const iframe = await manager.create(config, container);

      expect(iframe).toBeDefined();
      expect(iframe.src).toBe('http://localhost:8080/');
      expect(container.contains(iframe)).toBe(true);
    });

    it('should set iframe attributes correctly', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const iframe = await manager.create(config, container);

      expect(iframe.style.width).toBe('100%');
      expect(iframe.style.height).toBe('100%');
      expect(iframe.title).toBe('Label Studio');
      expect(iframe.allow).toContain('clipboard-read');
    });

    it('should throw error if iframe already exists', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);

      await expect(manager.create(config, container)).rejects.toThrow(
        'iframe already exists'
      );
    });

    it('should set initial load state to LOADING', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);

      const state = manager.getLoadState();
      expect(state.status).toBe(IframeStatus.LOADING);
      expect(state.isLoading).toBe(true);
      expect(state.error).toBeNull();
    });
  });

  describe('destroy', () => {
    it('should remove iframe from DOM', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const iframe = await manager.create(config, container);
      expect(container.contains(iframe)).toBe(true);

      await manager.destroy();

      expect(container.contains(iframe)).toBe(false);
    });

    it('should set status to DESTROYED', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);
      await manager.destroy();

      expect(manager.getStatus()).toBe(IframeStatus.DESTROYED);
    });

    it('should not throw error if iframe does not exist', async () => {
      await expect(manager.destroy()).resolves.not.toThrow();
    });

    it('should clear load timeout', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
        timeout: 1000,
      };

      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      await manager.create(config, container);
      await manager.destroy();

      expect(clearTimeoutSpy).toHaveBeenCalled();
      clearTimeoutSpy.mockRestore();
    });
  });

  describe('refresh', () => {
    it('should reload iframe', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const iframe = await manager.create(config, container);
      const originalSrc = iframe.src;

      await manager.refresh();

      // After refresh, src should be reloaded
      expect(iframe.src).toBe(originalSrc);
    });

    it('should reset load state to LOADING', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);
      await manager.refresh();

      const state = manager.getLoadState();
      expect(state.status).toBe(IframeStatus.LOADING);
      expect(state.isLoading).toBe(true);
    });

    it('should throw error if iframe does not exist', async () => {
      await expect(manager.refresh()).rejects.toThrow('iframe does not exist');
    });
  });

  describe('getStatus', () => {
    it('should return current iframe status', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);

      expect(manager.getStatus()).toBe(IframeStatus.LOADING);
    });
  });

  describe('getLoadState', () => {
    it('should return current load state', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);

      const state = manager.getLoadState();
      expect(state).toHaveProperty('isLoading');
      expect(state).toHaveProperty('progress');
      expect(state).toHaveProperty('error');
      expect(state).toHaveProperty('status');
    });

    it('should return a copy of load state', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      await manager.create(config, container);

      const state1 = manager.getLoadState();
      const state2 = manager.getLoadState();

      expect(state1).toEqual(state2);
      expect(state1).not.toBe(state2);
    });
  });

  describe('getIframe', () => {
    it('should return iframe element', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const createdIframe = await manager.create(config, container);
      const retrievedIframe = manager.getIframe();

      expect(retrievedIframe).toBe(createdIframe);
    });

    it('should return null if iframe does not exist', () => {
      expect(manager.getIframe()).toBeNull();
    });
  });

  describe('event listeners', () => {
    it('should register and trigger load event', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const callback = vi.fn();
      manager.on('load', callback);

      await manager.create(config, container);

      expect(callback).toHaveBeenCalled();
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'load',
          timestamp: expect.any(Number),
        })
      );
    });

    it('should register and trigger refresh event', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const callback = vi.fn();
      manager.on('refresh', callback);

      await manager.create(config, container);
      await manager.refresh();

      expect(callback).toHaveBeenCalled();
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'refresh',
          timestamp: expect.any(Number),
        })
      );
    });

    it('should unregister event listener', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const callback = vi.fn();
      manager.on('load', callback);
      manager.off('load', callback);

      await manager.create(config, container);

      expect(callback).not.toHaveBeenCalled();
    });

    it('should trigger destroy event', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const callback = vi.fn();
      manager.on('destroy', callback);

      await manager.create(config, container);
      await manager.destroy();

      expect(callback).toHaveBeenCalled();
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'destroy',
          timestamp: expect.any(Number),
        })
      );
    });

    it('should handle multiple listeners for same event', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const callback1 = vi.fn();
      const callback2 = vi.fn();

      manager.on('load', callback1);
      manager.on('load', callback2);

      await manager.create(config, container);

      expect(callback1).toHaveBeenCalled();
      expect(callback2).toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('should handle iframe error event', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
      };

      const errorCallback = vi.fn();
      manager.on('error', errorCallback);

      const iframe = await manager.create(config, container);

      // Simulate iframe error
      const errorEvent = new Event('error');
      iframe.dispatchEvent(errorEvent);

      expect(errorCallback).toHaveBeenCalled();
    });

    it('should retry on timeout', async () => {
      const config = {
        url: 'http://localhost:8080',
        projectId: 'test-project',
        userId: 'test-user',
        token: 'test-token',
        permissions: [],
        timeout: 100,
        retryAttempts: 2,
      };

      const refreshCallback = vi.fn();
      manager.on('refresh', refreshCallback);

      await manager.create(config, container);

      // Wait for first timeout and retry
      await new Promise((resolve) => setTimeout(resolve, 250));

      // Should have called refresh at least once
      expect(refreshCallback).toHaveBeenCalled();
    });
  });
});
