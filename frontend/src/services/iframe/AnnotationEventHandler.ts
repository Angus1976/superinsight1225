/**
 * AnnotationEventHandler - Specialized event handling for annotation workflows
 * 
 * Features:
 * - Annotation lifecycle event handling
 * - Progress tracking
 * - State management
 * - Error recovery
 */

import { EventEmitter, AnnotationEvent } from './EventEmitter';
import { AnnotationData, AnnotationContext } from './types';

export interface AnnotationEventData {
  taskId: string;
  userId: string;
  projectId: string;
  timestamp: number;
  data?: unknown;
  progress?: number;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface AnnotationProgress {
  taskId: string;
  totalItems: number;
  completedItems: number;
  percentage: number;
  estimatedTimeRemaining?: number;
  currentItem?: string;
}

export interface AnnotationState {
  taskId: string;
  status: 'idle' | 'started' | 'in_progress' | 'completed' | 'error' | 'cancelled';
  startTime?: number;
  endTime?: number;
  progress: AnnotationProgress;
  lastUpdate: number;
  errorCount: number;
  annotations: AnnotationData[];
}

export class AnnotationEventHandler {
  private eventEmitter: EventEmitter;
  private annotationStates: Map<string, AnnotationState> = new Map();
  private context: AnnotationContext | null = null;

  constructor(eventEmitter: EventEmitter) {
    this.eventEmitter = eventEmitter;
    this.setupEventHandlers();
  }

  /**
   * Set the annotation context
   */
  setContext(context: AnnotationContext): void {
    this.context = context;
  }

  /**
   * Start annotation for a task
   */
  async startAnnotation(taskId: string, metadata?: Record<string, unknown>): Promise<void> {
    const eventData: AnnotationEventData = {
      taskId,
      userId: this.context?.user.id || 'unknown',
      projectId: this.context?.project.id || 'unknown',
      timestamp: Date.now(),
      metadata,
    };

    // Initialize annotation state
    const state: AnnotationState = {
      taskId,
      status: 'started',
      startTime: Date.now(),
      progress: {
        taskId,
        totalItems: 0,
        completedItems: 0,
        percentage: 0,
      },
      lastUpdate: Date.now(),
      errorCount: 0,
      annotations: [],
    };

    this.annotationStates.set(taskId, state);

    await this.eventEmitter.emit(AnnotationEvent.STARTED, eventData, 'main');
  }

  /**
   * Update annotation progress
   */
  async updateAnnotation(
    taskId: string,
    data: Partial<AnnotationData>,
    progress?: Partial<AnnotationProgress>
  ): Promise<void> {
    const state = this.annotationStates.get(taskId);
    if (!state) {
      throw new Error(`No annotation state found for task ${taskId}`);
    }

    // Update state
    state.status = 'in_progress';
    state.lastUpdate = Date.now();

    if (progress) {
      state.progress = { ...state.progress, ...progress };
      state.progress.percentage = state.progress.totalItems > 0
        ? (state.progress.completedItems / state.progress.totalItems) * 100
        : 0;
    }

    if (data) {
      const annotation: AnnotationData = {
        id: data.id || `annotation_${Date.now()}`,
        taskId,
        userId: this.context?.user.id || 'unknown',
        data: data.data || {},
        timestamp: Date.now(),
        version: data.version || 1,
        status: data.status || 'draft',
        metadata: data.metadata,
      };

      // Update or add annotation
      const existingIndex = state.annotations.findIndex(a => a.id === annotation.id);
      if (existingIndex >= 0) {
        state.annotations[existingIndex] = annotation;
      } else {
        state.annotations.push(annotation);
      }
    }

    const eventData: AnnotationEventData = {
      taskId,
      userId: this.context?.user.id || 'unknown',
      projectId: this.context?.project.id || 'unknown',
      timestamp: Date.now(),
      data,
      progress: state.progress.percentage,
      metadata: { state: state.status },
    };

    await this.eventEmitter.emit(AnnotationEvent.UPDATED, eventData, 'main');

    // Emit progress event if progress was updated
    if (progress) {
      await this.eventEmitter.emit(AnnotationEvent.PROGRESS, {
        ...eventData,
        data: state.progress,
      }, 'main');
    }
  }

  /**
   * Complete annotation for a task
   */
  async completeAnnotation(taskId: string, finalData?: AnnotationData[]): Promise<void> {
    const state = this.annotationStates.get(taskId);
    if (!state) {
      throw new Error(`No annotation state found for task ${taskId}`);
    }

    // Update state
    state.status = 'completed';
    state.endTime = Date.now();
    state.progress.percentage = 100;
    state.progress.completedItems = state.progress.totalItems;

    if (finalData) {
      state.annotations = finalData;
    }

    const eventData: AnnotationEventData = {
      taskId,
      userId: this.context?.user.id || 'unknown',
      projectId: this.context?.project.id || 'unknown',
      timestamp: Date.now(),
      data: state.annotations,
      progress: 100,
      metadata: {
        duration: state.endTime - (state.startTime || 0),
        annotationCount: state.annotations.length,
        errorCount: state.errorCount,
      },
    };

    await this.eventEmitter.emit(AnnotationEvent.COMPLETED, eventData, 'main');
  }

  /**
   * Save annotation data
   */
  async saveAnnotation(taskId: string, annotationData: AnnotationData): Promise<void> {
    const state = this.annotationStates.get(taskId);
    if (!state) {
      throw new Error(`No annotation state found for task ${taskId}`);
    }

    // Update annotation in state
    const existingIndex = state.annotations.findIndex(a => a.id === annotationData.id);
    if (existingIndex >= 0) {
      state.annotations[existingIndex] = annotationData;
    } else {
      state.annotations.push(annotationData);
    }

    state.lastUpdate = Date.now();

    const eventData: AnnotationEventData = {
      taskId,
      userId: this.context?.user.id || 'unknown',
      projectId: this.context?.project.id || 'unknown',
      timestamp: Date.now(),
      data: annotationData,
      metadata: { action: 'save' },
    };

    await this.eventEmitter.emit(AnnotationEvent.SAVED, eventData, 'main');
  }

  /**
   * Handle annotation error
   */
  async handleAnnotationError(taskId: string, error: string | Error, recoverable = true): Promise<void> {
    const state = this.annotationStates.get(taskId);
    if (state) {
      state.status = 'error';
      state.errorCount++;
      state.lastUpdate = Date.now();
    }

    const errorMessage = error instanceof Error ? error.message : error;

    const eventData: AnnotationEventData = {
      taskId,
      userId: this.context?.user.id || 'unknown',
      projectId: this.context?.project.id || 'unknown',
      timestamp: Date.now(),
      error: errorMessage,
      metadata: {
        recoverable,
        errorCount: state?.errorCount || 1,
        stack: error instanceof Error ? error.stack : undefined,
      },
    };

    await this.eventEmitter.emit(AnnotationEvent.ERROR, eventData, 'main');
  }

  /**
   * Cancel annotation for a task
   */
  async cancelAnnotation(taskId: string, reason?: string): Promise<void> {
    const state = this.annotationStates.get(taskId);
    if (state) {
      state.status = 'cancelled';
      state.endTime = Date.now();
      state.lastUpdate = Date.now();
    }

    const eventData: AnnotationEventData = {
      taskId,
      userId: this.context?.user.id || 'unknown',
      projectId: this.context?.project.id || 'unknown',
      timestamp: Date.now(),
      metadata: {
        reason,
        duration: state?.endTime ? state.endTime - (state.startTime || 0) : 0,
        partialAnnotations: state?.annotations.length || 0,
      },
    };

    await this.eventEmitter.emit(AnnotationEvent.CANCELLED, eventData, 'main');
  }

  /**
   * Get annotation state for a task
   */
  getAnnotationState(taskId: string): AnnotationState | undefined {
    return this.annotationStates.get(taskId);
  }

  /**
   * Get all annotation states
   */
  getAllAnnotationStates(): AnnotationState[] {
    return Array.from(this.annotationStates.values());
  }

  /**
   * Clear annotation state for a task
   */
  clearAnnotationState(taskId: string): boolean {
    return this.annotationStates.delete(taskId);
  }

  /**
   * Clear all annotation states
   */
  clearAllAnnotationStates(): void {
    this.annotationStates.clear();
  }

  /**
   * Get annotation statistics
   */
  getAnnotationStats(): {
    totalTasks: number;
    activeTasks: number;
    completedTasks: number;
    errorTasks: number;
    totalAnnotations: number;
    averageProgress: number;
  } {
    const states = Array.from(this.annotationStates.values());
    
    const totalTasks = states.length;
    const activeTasks = states.filter(s => s.status === 'in_progress' || s.status === 'started').length;
    const completedTasks = states.filter(s => s.status === 'completed').length;
    const errorTasks = states.filter(s => s.status === 'error').length;
    const totalAnnotations = states.reduce((sum, s) => sum + s.annotations.length, 0);
    const averageProgress = totalTasks > 0
      ? states.reduce((sum, s) => sum + s.progress.percentage, 0) / totalTasks
      : 0;

    return {
      totalTasks,
      activeTasks,
      completedTasks,
      errorTasks,
      totalAnnotations,
      averageProgress,
    };
  }

  private setupEventHandlers(): void {
    // Listen for iframe events and handle them
    this.eventEmitter.on('iframe:annotation:started', async (data) => {
      if (this.isAnnotationEventData(data)) {
        await this.startAnnotation(data.taskId, data.metadata);
      }
    });

    this.eventEmitter.on('iframe:annotation:updated', async (data) => {
      if (this.isAnnotationEventData(data)) {
        await this.updateAnnotation(data.taskId, data.data as AnnotationData, {
          completedItems: data.progress,
        });
      }
    });

    this.eventEmitter.on('iframe:annotation:completed', async (data) => {
      if (this.isAnnotationEventData(data)) {
        await this.completeAnnotation(data.taskId, data.data as AnnotationData[]);
      }
    });

    this.eventEmitter.on('iframe:annotation:saved', async (data) => {
      if (this.isAnnotationEventData(data)) {
        await this.saveAnnotation(data.taskId, data.data as AnnotationData);
      }
    });

    this.eventEmitter.on('iframe:annotation:error', async (data) => {
      if (this.isAnnotationEventData(data)) {
        await this.handleAnnotationError(data.taskId, data.error || 'Unknown error');
      }
    });

    this.eventEmitter.on('iframe:annotation:cancelled', async (data) => {
      if (this.isAnnotationEventData(data)) {
        await this.cancelAnnotation(data.taskId, data.metadata?.reason as string);
      }
    });
  }

  private isAnnotationEventData(data: unknown): data is AnnotationEventData {
    return (
      typeof data === 'object' &&
      data !== null &&
      'taskId' in data &&
      'userId' in data &&
      'projectId' in data &&
      'timestamp' in data
    );
  }
}

// Export singleton instance for global use
// Note: This should be initialized with a proper EventEmitter instance
export let globalAnnotationEventHandler: AnnotationEventHandler | null = null;

export function initializeGlobalAnnotationEventHandler(eventEmitter: EventEmitter): AnnotationEventHandler {
  globalAnnotationEventHandler = new AnnotationEventHandler(eventEmitter);
  return globalAnnotationEventHandler;
}