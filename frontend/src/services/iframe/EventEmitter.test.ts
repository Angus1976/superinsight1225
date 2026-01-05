/**
 * EventEmitter Unit Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { EventEmitter, AnnotationEvent } from './EventEmitter';
import { EventHandler } from './types';

describe('EventEmitter', () => {
  let eventEmitter: EventEmitter;

  beforeEach(() => {
    eventEmitter = new EventEmitter();
  });

  afterEach(() => {
    eventEmitter.destroy();
  });

  describe('Basic Event Handling', () => {
    it('should subscribe to events and emit them', async () => {
      const handler = vi.fn();
      const testData = { message: 'test' };

      eventEmitter.on('test-event', handler);
      await eventEmitter.emit('test-event', testData);

      expect(handler).toHaveBeenCalledTimes(1);
      expect(handler).toHaveBeenCalledWith(testData, expect.objectContaining({
        event: 'test-event',
        data: testData,
        source: 'main',
      }));
    });

    it('should handle multiple subscribers for the same event', async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      const testData = { message: 'test' };

      eventEmitter.on('test-event', handler1);
      eventEmitter.on('test-event', handler2);
      await eventEmitter.emit('test-event', testData);

      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(1);
    });

    it('should unsubscribe from events', async () => {
      const handler = vi.fn();
      const testData = { message: 'test' };

      eventEmitter.on('test-event', handler);
      eventEmitter.off('test-event', handler);
      await eventEmitter.emit('test-event', testData);

      expect(handler).not.toHaveBeenCalled();
    });

    it('should unsubscribe by subscription ID', async () => {
      const handler = vi.fn();
      const testData = { message: 'test' };

      const subscriptionId = eventEmitter.on('test-event', handler);
      eventEmitter.off('test-event', subscriptionId);
      await eventEmitter.emit('test-event', testData);

      expect(handler).not.toHaveBeenCalled();
    });

    it('should handle once-only subscriptions', async () => {
      const handler = vi.fn();
      const testData = { message: 'test' };

      eventEmitter.once('test-event', handler);
      await eventEmitter.emit('test-event', testData);
      await eventEmitter.emit('test-event', testData);

      expect(handler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Event Priority', () => {
    it('should execute handlers in priority order', async () => {
      const executionOrder: number[] = [];
      const handler1: EventHandler = () => { executionOrder.push(1); };
      const handler2: EventHandler = () => { executionOrder.push(2); };
      const handler3: EventHandler = () => { executionOrder.push(3); };

      // Subscribe with different priorities (higher number = higher priority)
      eventEmitter.on('test-event', handler1, 1);
      eventEmitter.on('test-event', handler2, 3);
      eventEmitter.on('test-event', handler3, 2);

      await eventEmitter.emit('test-event', {});

      expect(executionOrder).toEqual([2, 3, 1]); // Priority order: 3, 2, 1
    });

    it('should handle same priority handlers', async () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      eventEmitter.on('test-event', handler1, 1);
      eventEmitter.on('test-event', handler2, 1);

      await eventEmitter.emit('test-event', {});

      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(1);
    });
  });

  describe('Event History', () => {
    it('should record event history', async () => {
      const testData1 = { message: 'test1' };
      const testData2 = { message: 'test2' };

      await eventEmitter.emit('event1', testData1);
      await eventEmitter.emit('event2', testData2);

      const history = eventEmitter.getHistory();
      expect(history).toHaveLength(2);
      expect(history[0]).toMatchObject({
        event: 'event1',
        data: testData1,
        source: 'main',
      });
      expect(history[1]).toMatchObject({
        event: 'event2',
        data: testData2,
        source: 'main',
      });
    });

    it('should filter history by event type', async () => {
      await eventEmitter.emit('event1', { data: 1 });
      await eventEmitter.emit('event2', { data: 2 });
      await eventEmitter.emit('event1', { data: 3 });

      const event1History = eventEmitter.getHistory('event1');
      expect(event1History).toHaveLength(2);
      expect(event1History[0].data).toEqual({ data: 1 });
      expect(event1History[1].data).toEqual({ data: 3 });
    });

    it('should clear history', async () => {
      await eventEmitter.emit('event1', { data: 1 });
      await eventEmitter.emit('event2', { data: 2 });

      eventEmitter.clearHistory();
      const history = eventEmitter.getHistory();
      expect(history).toHaveLength(0);
    });

    it('should clear history for specific event', async () => {
      await eventEmitter.emit('event1', { data: 1 });
      await eventEmitter.emit('event2', { data: 2 });

      eventEmitter.clearHistory('event1');
      const history = eventEmitter.getHistory();
      expect(history).toHaveLength(1);
      expect(history[0].event).toBe('event2');
    });

    it('should limit history size', async () => {
      const limitedEmitter = new EventEmitter({ maxHistorySize: 2 });

      await limitedEmitter.emit('event1', { data: 1 });
      await limitedEmitter.emit('event2', { data: 2 });
      await limitedEmitter.emit('event3', { data: 3 });

      const history = limitedEmitter.getHistory();
      expect(history).toHaveLength(2);
      expect(history[0].event).toBe('event2');
      expect(history[1].event).toBe('event3');

      limitedEmitter.destroy();
    });
  });

  describe('Subscription Management', () => {
    it('should get subscriptions for specific event', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      eventEmitter.on('event1', handler1);
      eventEmitter.on('event2', handler2);

      const event1Subs = eventEmitter.getSubscriptions('event1');
      expect(event1Subs).toHaveLength(1);
      expect(event1Subs[0].event).toBe('event1');
    });

    it('should get all subscriptions', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      eventEmitter.on('event1', handler1);
      eventEmitter.on('event2', handler2);

      const allSubs = eventEmitter.getSubscriptions();
      expect(allSubs).toHaveLength(2);
    });

    it('should count subscriptions', () => {
      const handler = vi.fn();

      eventEmitter.on('event1', handler);
      eventEmitter.on('event1', handler);
      eventEmitter.on('event2', handler);

      expect(eventEmitter.getSubscriptionCount('event1')).toBe(2);
      expect(eventEmitter.getSubscriptionCount('event2')).toBe(1);
      expect(eventEmitter.getSubscriptionCount()).toBe(3);
    });

    it('should toggle subscription active state', async () => {
      const handler = vi.fn();
      const subscriptionId = eventEmitter.on('test-event', handler);

      // Disable subscription
      eventEmitter.toggleSubscription(subscriptionId, false);
      await eventEmitter.emit('test-event', {});
      expect(handler).not.toHaveBeenCalled();

      // Re-enable subscription
      eventEmitter.toggleSubscription(subscriptionId, true);
      await eventEmitter.emit('test-event', {});
      expect(handler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Handling', () => {
    it('should handle errors in event handlers', async () => {
      const errorHandler = vi.fn();
      const faultyHandler: EventHandler = () => {
        throw new Error('Handler error');
      };

      eventEmitter.on('error', errorHandler);
      eventEmitter.on('test-event', faultyHandler);

      await eventEmitter.emit('test-event', {});

      expect(errorHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          originalEvent: 'test-event',
          error: expect.any(Error),
        }),
        expect.any(Object)
      );
    });

    it('should continue executing other handlers after error', async () => {
      const handler1: EventHandler = () => {
        throw new Error('Handler 1 error');
      };
      const handler2 = vi.fn();

      eventEmitter.on('test-event', handler1);
      eventEmitter.on('test-event', handler2);

      await eventEmitter.emit('test-event', {});

      expect(handler2).toHaveBeenCalledTimes(1);
    });
  });

  describe('Statistics', () => {
    it('should provide event statistics', () => {
      const handler = vi.fn();

      eventEmitter.on('event1', handler);
      eventEmitter.on('event2', handler);
      const subscriptionId = eventEmitter.on('event1', handler);
      eventEmitter.toggleSubscription(subscriptionId, false);

      const stats = eventEmitter.getStats();
      expect(stats.totalSubscriptions).toBe(3);
      expect(stats.activeSubscriptions).toBe(2);
      expect(stats.eventTypes).toEqual(['event1', 'event2']);
    });
  });

  describe('Annotation Events', () => {
    it('should handle annotation event constants', async () => {
      const handler = vi.fn();
      const annotationData = { taskId: '123', progress: 50 };

      eventEmitter.on(AnnotationEvent.STARTED, handler);
      await eventEmitter.emit(AnnotationEvent.STARTED, annotationData);

      expect(handler).toHaveBeenCalledWith(annotationData, expect.any(Object));
    });

    it('should handle all annotation event types', async () => {
      const handlers = {
        started: vi.fn(),
        updated: vi.fn(),
        completed: vi.fn(),
        saved: vi.fn(),
        error: vi.fn(),
        progress: vi.fn(),
        cancelled: vi.fn(),
      };

      eventEmitter.on(AnnotationEvent.STARTED, handlers.started);
      eventEmitter.on(AnnotationEvent.UPDATED, handlers.updated);
      eventEmitter.on(AnnotationEvent.COMPLETED, handlers.completed);
      eventEmitter.on(AnnotationEvent.SAVED, handlers.saved);
      eventEmitter.on(AnnotationEvent.ERROR, handlers.error);
      eventEmitter.on(AnnotationEvent.PROGRESS, handlers.progress);
      eventEmitter.on(AnnotationEvent.CANCELLED, handlers.cancelled);

      await eventEmitter.emit(AnnotationEvent.STARTED, {});
      await eventEmitter.emit(AnnotationEvent.UPDATED, {});
      await eventEmitter.emit(AnnotationEvent.COMPLETED, {});
      await eventEmitter.emit(AnnotationEvent.SAVED, {});
      await eventEmitter.emit(AnnotationEvent.ERROR, {});
      await eventEmitter.emit(AnnotationEvent.PROGRESS, {});
      await eventEmitter.emit(AnnotationEvent.CANCELLED, {});

      Object.values(handlers).forEach(handler => {
        expect(handler).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Async Handling', () => {
    it('should handle async event handlers', async () => {
      const asyncHandler: EventHandler = async (data) => {
        await new Promise(resolve => setTimeout(resolve, 10));
        return data;
      };

      const spy = vi.fn(asyncHandler);
      eventEmitter.on('async-event', spy);

      await eventEmitter.emit('async-event', { test: true });

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('should handle mixed sync and async handlers', async () => {
      const syncHandler = vi.fn();
      const asyncHandler: EventHandler = async () => {
        await new Promise(resolve => setTimeout(resolve, 10));
      };

      eventEmitter.on('mixed-event', syncHandler);
      eventEmitter.on('mixed-event', asyncHandler);

      await eventEmitter.emit('mixed-event', {});

      expect(syncHandler).toHaveBeenCalledTimes(1);
    });
  });

  describe('Configuration', () => {
    it('should respect configuration options', () => {
      const configuredEmitter = new EventEmitter({
        maxHistorySize: 5,
        enablePriority: false,
        enableAsync: false,
        defaultPriority: 10,
      });

      expect(configuredEmitter).toBeInstanceOf(EventEmitter);
      configuredEmitter.destroy();
    });
  });

  describe('Cleanup', () => {
    it('should destroy all subscriptions and history', () => {
      const handler = vi.fn();

      eventEmitter.on('event1', handler);
      eventEmitter.on('event2', handler);
      eventEmitter.emit('event1', {});

      eventEmitter.destroy();

      expect(eventEmitter.getSubscriptionCount()).toBe(0);
      expect(eventEmitter.getHistory()).toHaveLength(0);
    });
  });
});