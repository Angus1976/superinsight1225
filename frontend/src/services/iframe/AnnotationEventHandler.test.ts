/**
 * AnnotationEventHandler Unit Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { EventEmitter, AnnotationEvent } from './EventEmitter';
import { AnnotationEventHandler } from './AnnotationEventHandler';
import type { AnnotationEventData } from './AnnotationEventHandler';
import type { AnnotationContext, AnnotationData } from './types';

describe('AnnotationEventHandler', () => {
  let eventEmitter: EventEmitter;
  let annotationHandler: AnnotationEventHandler;
  let mockContext: AnnotationContext;

  beforeEach(() => {
    eventEmitter = new EventEmitter();
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

  describe('Annotation Lifecycle', () => {
    it('should start annotation and emit started event', async () => {
      const startedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.STARTED, startedHandler);

      await annotationHandler.startAnnotation('task123', { source: 'test' });

      expect(startedHandler).toHaveBeenCalledTimes(1);
      expect(startedHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          userId: 'user123',
          projectId: 'project123',
          metadata: { source: 'test' },
        }),
        expect.any(Object)
      );

      const state = annotationHandler.getAnnotationState('task123');
      expect(state).toBeDefined();
      expect(state?.status).toBe('started');
      expect(state?.taskId).toBe('task123');
    });

    it('should update annotation and emit updated event', async () => {
      const updatedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.UPDATED, updatedHandler);

      await annotationHandler.startAnnotation('task123');

      const annotationData: Partial<AnnotationData> = {
        id: 'annotation1',
        data: { label: 'test' },
        status: 'draft',
      };

      const progress = {
        totalItems: 10,
        completedItems: 3,
      };

      await annotationHandler.updateAnnotation('task123', annotationData, progress);

      expect(updatedHandler).toHaveBeenCalledTimes(1);
      expect(updatedHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          data: annotationData,
          progress: 30, // 3/10 * 100
        }),
        expect.any(Object)
      );

      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.status).toBe('in_progress');
      expect(state?.progress.percentage).toBe(30);
      expect(state?.annotations).toHaveLength(1);
    });

    it('should emit progress event when progress is updated', async () => {
      const progressHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.PROGRESS, progressHandler);

      await annotationHandler.startAnnotation('task123');

      const progress = {
        totalItems: 5,
        completedItems: 2,
        currentItem: 'item2',
      };

      await annotationHandler.updateAnnotation('task123', {}, progress);

      expect(progressHandler).toHaveBeenCalledTimes(1);
      expect(progressHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          data: expect.objectContaining({
            totalItems: 5,
            completedItems: 2,
            percentage: 40,
            currentItem: 'item2',
          }),
        }),
        expect.any(Object)
      );
    });

    it('should complete annotation and emit completed event', async () => {
      const completedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.COMPLETED, completedHandler);

      await annotationHandler.startAnnotation('task123');

      const finalData: AnnotationData[] = [
        {
          id: 'annotation1',
          taskId: 'task123',
          userId: 'user123',
          data: { label: 'test1' },
          timestamp: Date.now(),
          version: 1,
          status: 'completed',
        },
        {
          id: 'annotation2',
          taskId: 'task123',
          userId: 'user123',
          data: { label: 'test2' },
          timestamp: Date.now(),
          version: 1,
          status: 'completed',
        },
      ];

      await annotationHandler.completeAnnotation('task123', finalData);

      expect(completedHandler).toHaveBeenCalledTimes(1);
      expect(completedHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          data: finalData,
          progress: 100,
          metadata: expect.objectContaining({
            annotationCount: 2,
            errorCount: 0,
          }),
        }),
        expect.any(Object)
      );

      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.status).toBe('completed');
      expect(state?.progress.percentage).toBe(100);
      expect(state?.endTime).toBeDefined();
    });

    it('should save annotation and emit saved event', async () => {
      const savedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.SAVED, savedHandler);

      await annotationHandler.startAnnotation('task123');

      const annotationData: AnnotationData = {
        id: 'annotation1',
        taskId: 'task123',
        userId: 'user123',
        data: { label: 'saved_test' },
        timestamp: Date.now(),
        version: 1,
        status: 'completed',
      };

      await annotationHandler.saveAnnotation('task123', annotationData);

      expect(savedHandler).toHaveBeenCalledTimes(1);
      expect(savedHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          data: annotationData,
          metadata: { action: 'save' },
        }),
        expect.any(Object)
      );

      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.annotations).toHaveLength(1);
      expect(state?.annotations[0].data).toEqual({ label: 'saved_test' });
    });

    it('should handle annotation error and emit error event', async () => {
      const errorHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.ERROR, errorHandler);

      await annotationHandler.startAnnotation('task123');

      const error = new Error('Test annotation error');
      await annotationHandler.handleAnnotationError('task123', error, true);

      expect(errorHandler).toHaveBeenCalledTimes(1);
      expect(errorHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          error: 'Test annotation error',
          metadata: expect.objectContaining({
            recoverable: true,
            errorCount: 1,
            stack: expect.any(String),
          }),
        }),
        expect.any(Object)
      );

      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.status).toBe('error');
      expect(state?.errorCount).toBe(1);
    });

    it('should cancel annotation and emit cancelled event', async () => {
      const cancelledHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.CANCELLED, cancelledHandler);

      await annotationHandler.startAnnotation('task123');

      await annotationHandler.cancelAnnotation('task123', 'User requested cancellation');

      expect(cancelledHandler).toHaveBeenCalledTimes(1);
      expect(cancelledHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task123',
          metadata: expect.objectContaining({
            reason: 'User requested cancellation',
            partialAnnotations: 0,
          }),
        }),
        expect.any(Object)
      );

      const state = annotationHandler.getAnnotationState('task123');
      expect(state?.status).toBe('cancelled');
      expect(state?.endTime).toBeDefined();
    });
  });

  describe('State Management', () => {
    it('should manage multiple annotation states', async () => {
      await annotationHandler.startAnnotation('task1');
      await annotationHandler.startAnnotation('task2');
      await annotationHandler.startAnnotation('task3');

      const allStates = annotationHandler.getAllAnnotationStates();
      expect(allStates).toHaveLength(3);

      const task1State = annotationHandler.getAnnotationState('task1');
      const task2State = annotationHandler.getAnnotationState('task2');
      const task3State = annotationHandler.getAnnotationState('task3');

      expect(task1State?.taskId).toBe('task1');
      expect(task2State?.taskId).toBe('task2');
      expect(task3State?.taskId).toBe('task3');
    });

    it('should clear specific annotation state', async () => {
      await annotationHandler.startAnnotation('task1');
      await annotationHandler.startAnnotation('task2');

      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(2);

      const cleared = annotationHandler.clearAnnotationState('task1');
      expect(cleared).toBe(true);
      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(1);
      expect(annotationHandler.getAnnotationState('task1')).toBeUndefined();
      expect(annotationHandler.getAnnotationState('task2')).toBeDefined();
    });

    it('should clear all annotation states', async () => {
      await annotationHandler.startAnnotation('task1');
      await annotationHandler.startAnnotation('task2');
      await annotationHandler.startAnnotation('task3');

      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(3);

      annotationHandler.clearAllAnnotationStates();
      expect(annotationHandler.getAllAnnotationStates()).toHaveLength(0);
    });

    it('should update existing annotations', async () => {
      await annotationHandler.startAnnotation('task123');

      // Add first annotation
      const annotation1: Partial<AnnotationData> = {
        id: 'annotation1',
        data: { label: 'initial' },
        status: 'draft',
      };

      await annotationHandler.updateAnnotation('task123', annotation1);

      let state = annotationHandler.getAnnotationState('task123');
      expect(state?.annotations).toHaveLength(1);
      expect(state?.annotations[0].data).toEqual({ label: 'initial' });

      // Update the same annotation
      const updatedAnnotation: Partial<AnnotationData> = {
        id: 'annotation1',
        data: { label: 'updated' },
        status: 'completed',
      };

      await annotationHandler.updateAnnotation('task123', updatedAnnotation);

      state = annotationHandler.getAnnotationState('task123');
      expect(state?.annotations).toHaveLength(1);
      expect(state?.annotations[0].data).toEqual({ label: 'updated' });
      expect(state?.annotations[0].status).toBe('completed');
    });
  });

  describe('Statistics', () => {
    it('should provide annotation statistics', async () => {
      // Start multiple tasks
      await annotationHandler.startAnnotation('task1');
      await annotationHandler.startAnnotation('task2');
      await annotationHandler.startAnnotation('task3');

      // Update progress and add some annotations
      await annotationHandler.updateAnnotation('task1', { id: 'ann1', data: { label: 'test1' } }, { totalItems: 10, completedItems: 5 });
      await annotationHandler.updateAnnotation('task2', { id: 'ann2', data: { label: 'test2' } }, { totalItems: 10, completedItems: 8 });

      // Complete one task
      await annotationHandler.completeAnnotation('task2');

      // Error on one task
      await annotationHandler.handleAnnotationError('task3', 'Test error');

      const stats = annotationHandler.getAnnotationStats();

      expect(stats.totalTasks).toBe(3);
      expect(stats.activeTasks).toBe(1); // task1 is still in progress
      expect(stats.completedTasks).toBe(1); // task2 is completed
      expect(stats.errorTasks).toBe(1); // task3 has error
      expect(stats.totalAnnotations).toBe(2); // task1 has 1, task2 has 1
      expect(stats.averageProgress).toBeCloseTo((50 + 100 + 0) / 3, 1); // Average of 50%, 100%, 0%
    });

    it('should handle empty statistics', () => {
      const stats = annotationHandler.getAnnotationStats();

      expect(stats.totalTasks).toBe(0);
      expect(stats.activeTasks).toBe(0);
      expect(stats.completedTasks).toBe(0);
      expect(stats.errorTasks).toBe(0);
      expect(stats.totalAnnotations).toBe(0);
      expect(stats.averageProgress).toBe(0);
    });
  });

  describe('Error Handling', () => {
    it('should throw error when updating non-existent task', async () => {
      await expect(
        annotationHandler.updateAnnotation('nonexistent', {})
      ).rejects.toThrow('No annotation state found for task nonexistent');
    });

    it('should throw error when completing non-existent task', async () => {
      await expect(
        annotationHandler.completeAnnotation('nonexistent')
      ).rejects.toThrow('No annotation state found for task nonexistent');
    });

    it('should throw error when saving to non-existent task', async () => {
      const annotationData: AnnotationData = {
        id: 'annotation1',
        taskId: 'nonexistent',
        userId: 'user123',
        data: {},
        timestamp: Date.now(),
        version: 1,
        status: 'draft',
      };

      await expect(
        annotationHandler.saveAnnotation('nonexistent', annotationData)
      ).rejects.toThrow('No annotation state found for task nonexistent');
    });

    it('should handle string errors', async () => {
      const errorHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.ERROR, errorHandler);

      await annotationHandler.startAnnotation('task123');
      await annotationHandler.handleAnnotationError('task123', 'String error message');

      expect(errorHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          error: 'String error message',
          metadata: expect.objectContaining({
            stack: undefined,
          }),
        }),
        expect.any(Object)
      );
    });
  });

  describe('iframe Event Integration', () => {
    it('should handle iframe annotation events', async () => {
      const startedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.STARTED, startedHandler);

      const iframeEventData: AnnotationEventData = {
        taskId: 'iframe-task',
        userId: 'user123',
        projectId: 'project123',
        timestamp: Date.now(),
        metadata: { source: 'iframe' },
      };

      await eventEmitter.emit('iframe:annotation:started', iframeEventData);

      expect(startedHandler).toHaveBeenCalledTimes(1);
      expect(annotationHandler.getAnnotationState('iframe-task')).toBeDefined();
    });

    it('should handle iframe annotation updates', async () => {
      const updatedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.UPDATED, updatedHandler);

      // First start the annotation
      await annotationHandler.startAnnotation('iframe-task');

      const iframeEventData: AnnotationEventData = {
        taskId: 'iframe-task',
        userId: 'user123',
        projectId: 'project123',
        timestamp: Date.now(),
        data: { id: 'annotation1', data: { label: 'iframe-test' } },
        progress: 3,
      };

      await eventEmitter.emit('iframe:annotation:updated', iframeEventData);

      expect(updatedHandler).toHaveBeenCalledTimes(1);
    });

    it('should ignore invalid iframe event data', async () => {
      const startedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.STARTED, startedHandler);

      // Invalid data - missing required fields
      await eventEmitter.emit('iframe:annotation:started', { invalid: 'data' });

      expect(startedHandler).not.toHaveBeenCalled();
    });
  });

  describe('Context Management', () => {
    it('should work without context', () => {
      const handlerWithoutContext = new AnnotationEventHandler(eventEmitter);
      
      expect(async () => {
        await handlerWithoutContext.startAnnotation('task123');
      }).not.toThrow();
    });

    it('should use context when available', async () => {
      const startedHandler = vi.fn();
      eventEmitter.on(AnnotationEvent.STARTED, startedHandler);

      await annotationHandler.startAnnotation('task123');

      expect(startedHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 'user123',
          projectId: 'project123',
        }),
        expect.any(Object)
      );
    });
  });
});