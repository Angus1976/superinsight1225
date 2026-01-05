/**
 * Event System Integration Tests
 * 
 * Tests the complete event handling system including:
 * - EventEmitter and AnnotationEventHandler integration
 * - Event flow from iframe to main window
 * - Event history and statistics
 * - Error handling and recovery
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { EventEmitter, AnnotationEvent } from './EventEmitter';
import { AnnotationEventHandler, initializeGlobalAnnotationEventHandler } from './AnnotationEventHandler';
import type { AnnotationContext, AnnotationData } from './types';

describe('Event System Integration', () => {
  let eventEmitter: EventEmitter;
  let annotationHandler: AnnotationEventHandler;
  let mockContext: AnnotationContext;

  beforeEach(() => {
    eventEmitter = new EventEmitter({
      maxHistorySize: 100,
      enablePriority: true,
      enableAsync: true,
    });

    annotationHandler = new AnnotationEventHandler(eventEmitter);

    mockContext = {
      user: {
        id: 'user123',
        name: 'Test User',
        email: 'test@example.com',
        role: 'annotator',
      },
      project: {
        id: 'project123',
        name: 'Test Project',
        description: 'Test project description',
        status: 'active',
        createdAt: '2024-01-01',
        updatedAt: '2024-01-01',
      },
      task: {
        id: 'task123',
        name: 'Test Task',
        status: 'active',
        progress: 0,
      },
      permissions: [],
      timestamp: Date.now(),
    };

    annotationHandler.setContext(mockContext);
  });

  afterEach(() => {
    eventEmitter.destroy();
    annotationHandler.clearAllAnnotationStates();
  });

  describe('Complete Annotation Workflow', () => {
    it('should handle complete annotation lifecycle with events', async () => {
      const eventLog: string[] = [];

      // Set up event listeners
      eventEmitter.on(AnnotationEvent.STARTED, () => eventLog.push('started'));
      eventEmitter.on(AnnotationEvent.UPDATED, () => eventLog.push('updated'));
      eventEmitter.on(AnnotationEvent.PROGRESS, () => eventLog.push('progress'));
      eventEmitter.on(AnnotationEvent.SAVED, () => eventLog.push('saved'));
      eventEmitter.on(AnnotationEvent.COMPLETED, () => eventLog.push('completed'));

      // Start annotation
      await annotationHandler.startAnnotation('task123', { source: 'integration-test' });

      // Update annotation with progress
      await annotationHandler.updateAnnotation(
        'task123',
        {
          id: 'annotation1',
          data: { label: 'test-label' },
          status: 'draft',
        },
        {
          totalItems: 10,
          completedItems: 3,
          currentItem: 'item3',
        }
      );

      // Save annotation
      const annotationData: AnnotationData = {
        id: 'annotation1',
        taskId: 'task123',
        userId: 'user123',
        data: { label: 'test-label', confidence: 0.95 },
        timestamp: Date.now(),
        version: 1,
        status: 'completed',
      };

      await annotationHandler.saveAnnotation('task123', annotationData);

      // Complete annotation
      await annotationHandler.completeAnnotation('task123', [annotationData]);

      // Verify event sequence
      expect(eventLog).toEqual(['started', 'updated', 'progress', 'saved', 'completed']);

      // Verify final state
      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.status).toBe('completed');
      expect(state?.progress.percentage).toBe(100);
      expect(state?.annotations).toHaveLength(1);

      // Verify event history
      const history = eventEmitter.getHistory();
      expect(history.length).toBeGreaterThan(0);
      
      const startedEvents = eventEmitter.getHistory(AnnotationEvent.STARTED);
      const completedEvents = eventEmitter.getHistory(AnnotationEvent.COMPLETED);
      expect(startedEvents).toHaveLength(1);
      expect(completedEvents).toHaveLength(1);
    });

    it('should handle annotation errors and recovery', async () => {
      const errorLog: Array<{ event: string; error?: string }> = [];

      eventEmitter.on(AnnotationEvent.ERROR, (data) => {
        errorLog.push({ event: 'error', error: (data as any).error });
      });

      eventEmitter.on(AnnotationEvent.STARTED, () => {
        errorLog.push({ event: 'started' });
      });

      // Start annotation
      await annotationHandler.startAnnotation('task123');

      // Simulate error
      const error = new Error('Network connection failed');
      await annotationHandler.handleAnnotationError('task123', error, true);

      // Verify error was logged
      expect(errorLog).toHaveLength(2);
      expect(errorLog[0].event).toBe('started');
      expect(errorLog[1].event).toBe('error');
      expect(errorLog[1].error).toBe('Network connection failed');

      // Verify state
      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.status).toBe('error');
      expect(state?.errorCount).toBe(1);

      // Recovery: restart annotation
      await annotationHandler.startAnnotation('task123-recovery');
      await annotationHandler.completeAnnotation('task123-recovery');

      const recoveryState = annotationHandler.getAnnotationState('task123-recovery');
      expect(recoveryState?.status).toBe('completed');
    });

    it('should handle concurrent annotations', async () => {
      const completedTasks: string[] = [];

      eventEmitter.on(AnnotationEvent.COMPLETED, (data) => {
        completedTasks.push((data as any).taskId);
      });

      // Start multiple annotations concurrently
      const tasks = ['task1', 'task2', 'task3'];
      
      await Promise.all(
        tasks.map(async (taskId) => {
          await annotationHandler.startAnnotation(taskId);
          await annotationHandler.updateAnnotation(taskId, {
            id: `annotation-${taskId}`,
            data: { label: `label-${taskId}` },
          });
          await annotationHandler.completeAnnotation(taskId);
        })
      );

      // Verify all tasks completed
      expect(completedTasks).toHaveLength(3);
      expect(completedTasks).toEqual(expect.arrayContaining(tasks));

      // Verify states
      tasks.forEach(taskId => {
        const state = annotationHandler.getAnnotationState(taskId);
        expect(state?.status).toBe('completed');
        expect(state?.annotations).toHaveLength(1);
      });

      // Verify statistics
      const stats = annotationHandler.getAnnotationStats();
      expect(stats.totalTasks).toBe(3);
      expect(stats.completedTasks).toBe(3);
      expect(stats.totalAnnotations).toBe(3);
      expect(stats.averageProgress).toBe(100);
    });
  });

  describe('Event Priority and Ordering', () => {
    it('should execute event handlers in priority order', async () => {
      const executionOrder: number[] = [];

      // Add handlers with different priorities
      eventEmitter.on(AnnotationEvent.STARTED, () => executionOrder.push(1), 1);
      eventEmitter.on(AnnotationEvent.STARTED, () => executionOrder.push(3), 3);
      eventEmitter.on(AnnotationEvent.STARTED, () => executionOrder.push(2), 2);

      await annotationHandler.startAnnotation('task123');

      // Should execute in priority order: 3, 2, 1
      expect(executionOrder).toEqual([3, 2, 1]);
    });

    it('should handle event handler errors without stopping other handlers', async () => {
      const successfulHandlers: number[] = [];

      // Add handlers, one of which will throw an error
      eventEmitter.on(AnnotationEvent.STARTED, () => successfulHandlers.push(1));
      eventEmitter.on(AnnotationEvent.STARTED, () => {
        throw new Error('Handler error');
      });
      eventEmitter.on(AnnotationEvent.STARTED, () => successfulHandlers.push(3));

      await annotationHandler.startAnnotation('task123');

      // Both successful handlers should have executed
      expect(successfulHandlers).toEqual([1, 3]);
    });
  });

  describe('iframe Event Integration', () => {
    it('should handle events from iframe and trigger annotation workflow', async () => {
      const workflowEvents: string[] = [];

      // Monitor annotation events
      Object.values(AnnotationEvent).forEach(event => {
        eventEmitter.on(event, () => workflowEvents.push(event));
      });

      // Simulate iframe events
      await eventEmitter.emit('iframe:annotation:started', {
        taskId: 'iframe-task',
        userId: 'user123',
        projectId: 'project123',
        timestamp: Date.now(),
        metadata: { source: 'iframe' },
      });

      await eventEmitter.emit('iframe:annotation:updated', {
        taskId: 'iframe-task',
        userId: 'user123',
        projectId: 'project123',
        timestamp: Date.now(),
        data: { id: 'iframe-annotation', data: { label: 'iframe-label' } },
        progress: 5,
      });

      await eventEmitter.emit('iframe:annotation:completed', {
        taskId: 'iframe-task',
        userId: 'user123',
        projectId: 'project123',
        timestamp: Date.now(),
        data: [{ id: 'iframe-annotation', data: { label: 'iframe-label' } }],
      });

      // Verify workflow events were triggered
      expect(workflowEvents).toContain(AnnotationEvent.STARTED);
      expect(workflowEvents).toContain(AnnotationEvent.UPDATED);
      expect(workflowEvents).toContain(AnnotationEvent.COMPLETED);

      // Verify state was created and updated
      const state = annotationHandler.getAnnotationState('iframe-task');
      expect(state).toBeDefined();
      expect(state?.status).toBe('completed');
    });

    it('should ignore malformed iframe events', async () => {
      const eventCount = eventEmitter.getHistory().length;

      // Send malformed events
      await eventEmitter.emit('iframe:annotation:started', { invalid: 'data' });
      await eventEmitter.emit('iframe:annotation:updated', null);
      await eventEmitter.emit('iframe:annotation:completed', undefined);

      // Events should be recorded in history but not processed
      const newEventCount = eventEmitter.getHistory().length;
      expect(newEventCount).toBe(eventCount + 3);

      // No annotation states should be created
      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(0);
    });
  });

  describe('Performance and Memory', () => {
    it('should handle large number of events efficiently', async () => {
      const startTime = Date.now();
      const eventCount = 1000;

      // Create many events
      for (let i = 0; i < eventCount; i++) {
        await eventEmitter.emit(`test-event-${i % 10}`, { index: i });
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should complete within reasonable time (adjust threshold as needed)
      expect(duration).toBeLessThan(1000); // 1 second

      // Verify history management
      const history = eventEmitter.getHistory();
      expect(history.length).toBeLessThanOrEqual(100); // Respects maxHistorySize
    });

    it('should clean up resources properly', () => {
      // Create some state
      annotationHandler.startAnnotation('task1');
      annotationHandler.startAnnotation('task2');
      eventEmitter.on('test-event', () => {});

      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(2);
      expect(eventEmitter.getSubscriptionCount()).toBeGreaterThan(0);

      // Clean up
      annotationHandler.clearAllAnnotationStates();
      eventEmitter.destroy();

      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(0);
      expect(eventEmitter.getSubscriptionCount()).toBe(0);
      expect(eventEmitter.getHistory()).toHaveLength(0);
    });
  });

  describe('Global Instance Integration', () => {
    it('should initialize global annotation event handler', () => {
      const globalHandler = initializeGlobalAnnotationEventHandler(eventEmitter);
      
      expect(globalHandler).toBeInstanceOf(AnnotationEventHandler);
      expect(globalHandler).toBeDefined();
    });

    it('should work with global event emitter instance', async () => {
      const globalHandler = initializeGlobalAnnotationEventHandler(eventEmitter);
      globalHandler.setContext(mockContext);

      const completedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.COMPLETED, completedHandler);

      await globalHandler.startAnnotation('global-task');
      await globalHandler.completeAnnotation('global-task');

      expect(completedHandler).toHaveBeenCalledTimes(1);
      
      const state = globalHandler.getAnnotationState('global-task');
      expect(state?.status).toBe('completed');
    });
  });

  describe('Event System Statistics', () => {
    it('should provide comprehensive system statistics', async () => {
      // Create various annotation states
      await annotationHandler.startAnnotation('task1');
      await annotationHandler.startAnnotation('task2');
      await annotationHandler.startAnnotation('task3');

      await annotationHandler.updateAnnotation('task1', { id: 'ann1', data: {} });
      await annotationHandler.updateAnnotation('task2', { id: 'ann2', data: {} });

      await annotationHandler.completeAnnotation('task1');
      await annotationHandler.handleAnnotationError('task3', 'Test error');

      // Get annotation statistics
      const annotationStats = annotationHandler.getAnnotationStats();
      expect(annotationStats.totalTasks).toBe(3);
      expect(annotationStats.activeTasks).toBe(1); // task2
      expect(annotationStats.completedTasks).toBe(1); // task1
      expect(annotationStats.errorTasks).toBe(1); // task3

      // Get event emitter statistics
      const eventStats = eventEmitter.getStats();
      expect(eventStats.totalSubscriptions).toBeGreaterThan(0);
      expect(eventStats.eventTypes.length).toBeGreaterThan(0);
      expect(eventStats.historySize).toBeGreaterThan(0);
    });
  });
});