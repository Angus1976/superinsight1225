/**
 * Label Studio iframe Integration End-to-End Tests
 * 
 * Comprehensive end-to-end tests covering:
 * - Complete annotation workflow from start to finish
 * - Error recovery flows and resilience testing
 * - Performance metrics and monitoring
 * - Real-world usage scenarios
 * 
 * **Feature: label-studio-iframe-integration**
 * **Validates: Requirements 1-10**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { IframeManager } from './IframeManager';
import { PostMessageBridge } from './PostMessageBridge';
import { ContextManager } from './ContextManager';
import { PermissionController } from './PermissionController';
import { SyncManager } from './SyncManager';
import { EventEmitter, AnnotationEvent } from './EventEmitter';
import { UICoordinator } from './UICoordinator';
import { ErrorHandler } from './ErrorHandler';
import { PerformanceMonitor } from './PerformanceMonitor';
import type {
  IframeConfig,
  AnnotationContext,
  Permission,
  AnnotationData,
  UserInfo,
  ProjectInfo,
  TaskInfo,
} from './types';

// Mock DOM APIs
const mockDocument = {
  createElement: vi.fn(() => ({
    style: {},
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    setAttribute: vi.fn(),
    getAttribute: vi.fn(),
    remove: vi.fn(),
    contentWindow: {
      postMessage: vi.fn(),
    },
    focus: vi.fn(),
    onload: null,
    onerror: null,
  })),
  body: {
    appendChild: vi.fn(),
    removeChild: vi.fn(),
  },
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
};

const mockWindow = {
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  postMessage: vi.fn(),
  location: {
    origin: 'https://app.example.com',
    protocol: 'https:',
  },
  parent: {
    postMessage: vi.fn(),
  },
};

Object.defineProperty(global, 'document', { value: mockDocument, writable: true });
Object.defineProperty(global, 'window', { value: mockWindow, writable: true });

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(global, 'localStorage', { value: mockLocalStorage, writable: true });

// Mock performance API
Object.defineProperty(global, 'performance', {
  value: {
    now: vi.fn(() => Date.now()),
    memory: {
      usedJSHeapSize: 50 * 1024 * 1024,
      totalJSHeapSize: 100 * 1024 * 1024,
      jsHeapSizeLimit: 2 * 1024 * 1024 * 1024,
    },
  },
  writable: true,
});

// Mock fetch
global.fetch = vi.fn();

describe('Label Studio iframe Integration End-to-End Tests', () => {
  let iframeManager: IframeManager;
  let postMessageBridge: PostMessageBridge;
  let contextManager: ContextManager;
  let permissionController: PermissionController;
  let syncManager: SyncManager;
  let eventEmitter: EventEmitter;
  let uiCoordinator: UICoordinator;
  let errorHandler: ErrorHandler;
  let performanceMonitor: PerformanceMonitor;
  
  let container: HTMLElement;
  let mockConfig: IframeConfig;
  let mockContext: AnnotationContext;
  let mockPermissions: Permission[];

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    
    // Setup successful API responses by default
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });

    // Setup mock data
    mockPermissions = [
      { action: 'read', resource: 'annotations', allowed: true },
      { action: 'write', resource: 'annotations', allowed: true },
      { action: 'delete', resource: 'annotations', allowed: false },
    ];

    mockConfig = {
      url: 'https://labelstudio.example.com/projects/1/data/1',
      projectId: 'project-123',
      taskId: 'task-456',
      userId: 'user-789',
      token: 'jwt-token-123',
      permissions: mockPermissions,
      theme: 'light',
      fullscreen: false,
      timeout: 10000,
      retryAttempts: 3,
    };

    const userInfo: UserInfo = {
      id: 'user-789',
      name: 'Test User',
      email: 'test@example.com',
      role: 'annotator',
    };

    const projectInfo: ProjectInfo = {
      id: 'project-123',
      name: 'Test Project',
      description: 'E2E test project',
      status: 'active',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    };

    const taskInfo: TaskInfo = {
      id: 'task-456',
      name: 'Test Task',
      status: 'active',
      progress: 0,
    };

    mockContext = {
      user: userInfo,
      project: projectInfo,
      task: taskInfo,
      permissions: mockPermissions,
      timestamp: Date.now(),
      sessionId: 'session-123',
    };

    // Create container element
    container = {
      appendChild: vi.fn(),
      removeChild: vi.fn(),
      style: {},
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as any;

    // Initialize components
    iframeManager = new IframeManager();
    postMessageBridge = new PostMessageBridge({
      targetOrigin: 'https://labelstudio.example.com',
      timeout: 5000,
      maxRetries: 3,
    });
    contextManager = new ContextManager();
    permissionController = new PermissionController();
    syncManager = new SyncManager({
      enableIncrementalSync: true,
      syncInterval: 1000,
      maxRetries: 3,
    });
    eventEmitter = new EventEmitter();
    uiCoordinator = new UICoordinator();
    errorHandler = new ErrorHandler();
    performanceMonitor = new PerformanceMonitor({
      sampleInterval: 100,
      enableMemoryMonitoring: true,
      enableCpuMonitoring: true,
    });
  });

  afterEach(() => {
    // Cleanup all components
    iframeManager.destroy();
    postMessageBridge.cleanup();
    // contextManager doesn't have cleanup method
    // permissionController doesn't have cleanup method
    syncManager.destroy();
    eventEmitter.destroy();
    uiCoordinator.cleanup();
    errorHandler.cleanup();
    performanceMonitor.stop();
  });

  describe('Complete Annotation Workflow', () => {
    it('should execute complete annotation workflow from initialization to completion', async () => {
      const workflowEvents: Array<{ event: string; timestamp: number; data?: any }> = [];
      const performanceMetrics: Array<{ metric: string; value: number; timestamp: number }> = [];
      
      // Track all workflow events
      const eventTypes = [
        AnnotationEvent.STARTED,
        AnnotationEvent.UPDATED,
        AnnotationEvent.SAVED,
        AnnotationEvent.COMPLETED,
        AnnotationEvent.ERROR,
      ];
      
      eventTypes.forEach(eventType => {
        eventEmitter.on(eventType, (data) => {
          workflowEvents.push({
            event: eventType,
            timestamp: Date.now(),
            data,
          });
        });
      });

      // Track performance metrics
      performanceMonitor.on('metric', (data: any) => {
        performanceMetrics.push({
          metric: data.name,
          value: data.value,
          timestamp: Date.now(),
        });
      });

      // Start performance monitoring
      performanceMonitor.start();

      // Phase 1: System Initialization
      const initStartTime = Date.now();
      
      // Initialize context and permissions
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      // Create and initialize iframe
      const iframe = await iframeManager.create(mockConfig, container);
      expect(iframe).toBeTruthy();
      expect(iframe.src).toBe(mockConfig.url);
      
      // Initialize PostMessage bridge
      await postMessageBridge.initialize(iframe.contentWindow);
      
      // Initialize UI coordinator
      uiCoordinator.initialize(iframe, container);
      
      // Start sync manager - SyncManager starts automatically in constructor
      
      const initEndTime = Date.now();
      const initDuration = initEndTime - initStartTime;
      
      // Verify initialization performance
      expect(initDuration).toBeLessThan(1000); // Should initialize within 1 second
      
      // Phase 2: Context and Permission Setup
      const contextSetupStartTime = Date.now();
      
      // Send context to iframe
      const contextMessage = {
        id: 'context-setup',
        type: 'context:set',
        payload: contextManager.getEncryptedContext(),
        timestamp: Date.now(),
      };
      
      await postMessageBridge.send(contextMessage);
      
      // Send permissions to iframe
      const permissionMessage = {
        id: 'permissions-setup',
        type: 'permissions:set',
        payload: mockPermissions,
        timestamp: Date.now(),
      };
      
      await postMessageBridge.send(permissionMessage);
      
      const contextSetupEndTime = Date.now();
      const contextSetupDuration = contextSetupEndTime - contextSetupStartTime;
      
      // Verify context setup performance
      expect(contextSetupDuration).toBeLessThan(500); // Should setup within 500ms
      
      // Phase 3: Annotation Workflow Execution
      const annotationStartTime = Date.now();
      
      // Start annotation
      await eventEmitter.emit(AnnotationEvent.STARTED, {
        taskId: mockConfig.taskId,
        userId: mockConfig.userId,
        projectId: mockConfig.projectId,
        timestamp: Date.now(),
      });
      
      // Simulate annotation updates from iframe
      const messageHandler = mockWindow.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )?.[1];
      
      expect(messageHandler).toBeDefined();
      
      // Simulate multiple annotation updates
      const annotationUpdates = [
        { label: 'cat', confidence: 0.7, bbox: [10, 10, 50, 50] },
        { label: 'cat', confidence: 0.85, bbox: [12, 12, 48, 48] },
        { label: 'cat', confidence: 0.95, bbox: [15, 15, 45, 45] },
      ];
      
      for (let i = 0; i < annotationUpdates.length; i++) {
        const update = annotationUpdates[i];
        
        // Simulate message from iframe
        messageHandler({
          origin: 'https://labelstudio.example.com',
          data: {
            type: 'annotation:update',
            id: `update-${i}`,
            payload: {
              taskId: mockConfig.taskId,
              data: update,
              progress: ((i + 1) / annotationUpdates.length) * 100,
            },
          },
        });
        
        // Emit update event
        await eventEmitter.emit(AnnotationEvent.UPDATED, {
          taskId: mockConfig.taskId,
          data: update,
          progress: ((i + 1) / annotationUpdates.length) * 100,
        });
        
        // Small delay to simulate real annotation timing
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // Phase 4: Data Synchronization
      const finalAnnotationData: AnnotationData = {
        id: 'final-annotation',
        taskId: mockConfig.taskId!,
        userId: mockConfig.userId,
        data: annotationUpdates[annotationUpdates.length - 1],
        timestamp: Date.now(),
        version: 1,
        status: 'completed',
      };
      
      // Add annotation to sync queue
      await syncManager.addOperation('create', finalAnnotationData);
      
      // Emit save event
      await eventEmitter.emit(AnnotationEvent.SAVED, {
        taskId: mockConfig.taskId,
        annotationId: finalAnnotationData.id,
        data: finalAnnotationData,
      });
      
      // Wait for sync to complete
      await new Promise(resolve => setTimeout(resolve, 1200));
      
      // Phase 5: Workflow Completion
      await eventEmitter.emit(AnnotationEvent.COMPLETED, {
        taskId: mockConfig.taskId,
        annotationId: finalAnnotationData.id,
        totalTime: Date.now() - annotationStartTime,
      });
      
      const annotationEndTime = Date.now();
      const annotationDuration = annotationEndTime - annotationStartTime;
      
      // Phase 6: Verification and Cleanup
      
      // Verify workflow events occurred in correct order
      const eventOrder = workflowEvents.map(e => e.event);
      expect(eventOrder).toContain(AnnotationEvent.STARTED);
      expect(eventOrder).toContain(AnnotationEvent.UPDATED);
      expect(eventOrder).toContain(AnnotationEvent.SAVED);
      expect(eventOrder).toContain(AnnotationEvent.COMPLETED);
      
      // Verify no errors occurred
      const errorEvents = workflowEvents.filter(e => e.event === AnnotationEvent.ERROR);
      expect(errorEvents).toHaveLength(0);
      
      // Verify sync completed successfully
      const syncStats = syncManager.getStats();
      expect(syncStats.totalOperations).toBe(1);
      expect(syncStats.completedOperations).toBe(1);
      expect(syncStats.failedOperations).toBe(0);
      
      // Verify API calls were made
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/annotations'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining(finalAnnotationData.id),
        })
      );
      
      // Verify performance metrics
      expect(annotationDuration).toBeLessThan(5000); // Complete workflow within 5 seconds
      expect(performanceMetrics.length).toBeGreaterThan(0);
      
      // Verify iframe state
      expect(iframeManager.getStatus()).toBe('ready');
      expect(postMessageBridge.getStatus()).toBe('connected');
      
      // Verify UI state
      expect(uiCoordinator.isLoading()).toBe(false);
      
      // Stop performance monitoring
      performanceMonitor.stop();
      
      // Verify final performance report
      const performanceReport = performanceMonitor.getReport();
      expect(performanceReport).toBeTruthy();
      expect(performanceReport.summary.totalDuration).toBeGreaterThan(0);
    });

    it('should handle concurrent annotation workflows efficiently', async () => {
      const concurrentTasks = 5;
      const workflowResults: Array<{ taskId: string; success: boolean; duration: number }> = [];
      
      // Setup context and permissions
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      // Create iframe
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      uiCoordinator.initialize(iframe, container);
      // syncManager starts automatically
      
      // Execute concurrent workflows
      const concurrentPromises = Array.from({ length: concurrentTasks }, async (_, index) => {
        const taskId = `concurrent-task-${index}`;
        const startTime = Date.now();
        
        try {
          // Start annotation
          await eventEmitter.emit(AnnotationEvent.STARTED, {
            taskId,
            userId: mockConfig.userId,
            projectId: mockConfig.projectId,
          });
          
          // Simulate annotation work
          const annotationData: AnnotationData = {
            id: `annotation-${index}`,
            taskId,
            userId: mockConfig.userId,
            data: { label: `label-${index}`, confidence: 0.9 },
            timestamp: Date.now(),
            version: 1,
            status: 'completed',
          };
          
          // Update and save
          await eventEmitter.emit(AnnotationEvent.UPDATED, { taskId, data: annotationData.data });
          await syncManager.addOperation('create', annotationData);
          await eventEmitter.emit(AnnotationEvent.SAVED, { taskId, annotationId: annotationData.id });
          await eventEmitter.emit(AnnotationEvent.COMPLETED, { taskId });
          
          const endTime = Date.now();
          workflowResults.push({
            taskId,
            success: true,
            duration: endTime - startTime,
          });
        } catch (error) {
          const endTime = Date.now();
          workflowResults.push({
            taskId,
            success: false,
            duration: endTime - startTime,
          });
        }
      });
      
      // Wait for all workflows to complete
      await Promise.all(concurrentPromises);
      
      // Wait for sync to complete
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Verify all workflows completed successfully
      expect(workflowResults).toHaveLength(concurrentTasks);
      
      const successfulWorkflows = workflowResults.filter(r => r.success);
      expect(successfulWorkflows).toHaveLength(concurrentTasks);
      
      // Verify performance is reasonable
      const averageDuration = workflowResults.reduce((sum, r) => sum + r.duration, 0) / workflowResults.length;
      expect(averageDuration).toBeLessThan(2000); // Average workflow should complete within 2 seconds
      
      // Verify sync handled all operations
      const syncStats = syncManager.getStats();
      expect(syncStats.totalOperations).toBe(concurrentTasks);
      expect(syncStats.completedOperations).toBe(concurrentTasks);
    });
  });

  describe('Error Recovery Flows', () => {
    it('should recover from iframe crash and continue workflow', async () => {
      const recoveryEvents: string[] = [];
      
      // Track recovery events
      errorHandler.on('recovery:started', () => recoveryEvents.push('recovery:started'));
      errorHandler.on('recovery:completed', () => recoveryEvents.push('recovery:completed'));
      iframeManager.on('refresh', () => recoveryEvents.push('iframe:refresh'));
      
      // Setup initial state
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      // Create iframe
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      // syncManager starts automatically
      
      // Start annotation workflow
      await eventEmitter.emit(AnnotationEvent.STARTED, {
        taskId: mockConfig.taskId,
        userId: mockConfig.userId,
      });
      
      // Simulate iframe crash
      const errorHandler_iframe = iframe.addEventListener.mock.calls.find(
        call => call[0] === 'error'
      )?.[1];
      
      expect(errorHandler_iframe).toBeDefined();
      errorHandler_iframe(new Error('iframe crashed'));
      
      // Verify error was detected
      expect(iframeManager.getStatus()).toBe('error');
      
      // Trigger recovery
      await iframeManager.refresh();
      
      // Verify recovery
      expect(recoveryEvents).toContain('iframe:refresh');
      expect(iframeManager.getStatus()).toBe('ready');
      
      // Continue workflow after recovery
      const annotationData: AnnotationData = {
        id: 'recovery-annotation',
        taskId: mockConfig.taskId!,
        userId: mockConfig.userId,
        data: { label: 'recovered', confidence: 0.9 },
        timestamp: Date.now(),
        version: 1,
        status: 'completed',
      };
      
      await syncManager.addOperation('create', annotationData);
      await eventEmitter.emit(AnnotationEvent.COMPLETED, {
        taskId: mockConfig.taskId,
        annotationId: annotationData.id,
      });
      
      // Wait for sync
      await new Promise(resolve => setTimeout(resolve, 1200));
      
      // Verify workflow completed successfully after recovery
      const syncStats = syncManager.getStats();
      expect(syncStats.completedOperations).toBe(1);
    });

    it('should handle network failures with offline mode and recovery', async () => {
      const networkEvents: string[] = [];
      
      // Track network events
      syncManager.addEventListener((event) => {
        if (event.type === 'offline_mode') networkEvents.push('offline');
        if (event.type === 'online_mode') networkEvents.push('online');
        if (event.type === 'sync_complete') networkEvents.push('sync_complete');
      });
      
      // Setup
      contextManager.setContext(mockContext);
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      // syncManager starts automatically
      
      // Start annotation
      await eventEmitter.emit(AnnotationEvent.STARTED, {
        taskId: mockConfig.taskId,
        userId: mockConfig.userId,
      });
      
      // Simulate network failure
      (global.fetch as any).mockRejectedValue(new Error('Network error'));
      
      // Try to sync annotation (should fail and go offline)
      const annotationData: AnnotationData = {
        id: 'offline-annotation',
        taskId: mockConfig.taskId!,
        userId: mockConfig.userId,
        data: { label: 'offline', confidence: 0.8 },
        timestamp: Date.now(),
        version: 1,
        status: 'draft',
      };
      
      await syncManager.addOperation('create', annotationData);
      
      // Wait for offline detection
      await new Promise(resolve => setTimeout(resolve, 1200));
      
      // Verify offline mode
      expect(networkEvents).toContain('offline');
      expect(syncManager.getStatus()).toBe('offline');
      
      // Verify data is cached
      const cachedData = syncManager.getCachedData() as any[];
      expect(cachedData).toHaveLength(1);
      expect(cachedData[0].id).toBe('offline-annotation');
      
      // Simulate network recovery
      (global.fetch as any).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });
      
      // Retry failed operations
      await syncManager.forceSync();
      
      // Wait for sync completion
      await new Promise(resolve => setTimeout(resolve, 1200));
      
      // Verify recovery
      expect(syncManager.getStatus()).toBe('idle');
      expect(syncManager.getPendingOperationsCount()).toBe(0);
      
      const syncStats = syncManager.getStats();
      expect(syncStats.completedOperations).toBe(1);
    });

    it('should handle permission changes during workflow', async () => {
      const permissionEvents: string[] = [];
      
      // Track permission events
      permissionController.on('permissions:updated', () => permissionEvents.push('updated'));
      permissionController.on('permissions:denied', () => permissionEvents.push('denied'));
      
      // Setup with initial permissions
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      // syncManager starts automatically
      
      // Start annotation
      await eventEmitter.emit(AnnotationEvent.STARTED, {
        taskId: mockConfig.taskId,
        userId: mockConfig.userId,
      });
      
      // Verify initial permissions
      expect(permissionController.checkPermission(mockContext, 'write', 'annotations')).toBe(true);
      
      // Simulate permission change (remove write permission)
      const restrictedPermissions: Permission[] = [
        { action: 'read', resource: 'annotations', allowed: true },
        { action: 'write', resource: 'annotations', allowed: false }, // Changed
        { action: 'delete', resource: 'annotations', allowed: false },
      ];
      
      const updatedContext = permissionController.updateUserPermissions(mockContext, restrictedPermissions);
      contextManager.setContext(updatedContext);
      
      // Verify permission change
      expect(permissionController.checkPermission(updatedContext, 'write', 'annotations')).toBe(false);
      expect(permissionEvents).toContain('updated');
      
      // Try to perform write operation (should be blocked)
      const annotationData: AnnotationData = {
        id: 'restricted-annotation',
        taskId: mockConfig.taskId!,
        userId: mockConfig.userId,
        data: { label: 'restricted', confidence: 0.9 },
        timestamp: Date.now(),
        version: 1,
        status: 'draft',
      };
      
      // This should be blocked by permission check
      const writeAllowed = permissionController.checkPermission(updatedContext, 'write', 'annotations');
      expect(writeAllowed).toBe(false);
      
      // Restore permissions
      const restoredContext = permissionController.updateUserPermissions(mockContext, mockPermissions);
      contextManager.setContext(restoredContext);
      
      // Now write should be allowed
      expect(permissionController.checkPermission(restoredContext, 'write', 'annotations')).toBe(true);
      
      // Complete annotation with restored permissions
      await syncManager.addOperation('create', annotationData);
      await eventEmitter.emit(AnnotationEvent.COMPLETED, {
        taskId: mockConfig.taskId,
        annotationId: annotationData.id,
      });
      
      // Wait for sync
      await new Promise(resolve => setTimeout(resolve, 1200));
      
      // Verify successful completion
      const syncStats = syncManager.getStats();
      expect(syncStats.completedOperations).toBe(1);
    });
  });

  describe('Performance Metrics and Monitoring', () => {
    it('should maintain performance metrics within acceptable bounds', async () => {
      const performanceData: Array<{ metric: string; value: number; timestamp: number }> = [];
      
      // Setup performance monitoring
      performanceMonitor.on('metric', (data: any) => {
        performanceData.push({
          metric: data.name,
          value: data.value,
          timestamp: Date.now(),
        });
      });
      
      performanceMonitor.start();
      
      // Setup system
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      uiCoordinator.initialize(iframe, container);
      // syncManager starts automatically
      
      // Execute intensive workflow
      const intensiveWorkloadStartTime = Date.now();
      
      // Simulate high-frequency operations
      const operationCount = 50;
      const operations: Promise<void>[] = [];
      
      for (let i = 0; i < operationCount; i++) {
        const operation = async () => {
          // Send message
          await postMessageBridge.send({
            id: `perf-message-${i}`,
            type: 'performance:test',
            payload: { index: i, data: 'performance test data' },
            timestamp: Date.now(),
          });
          
          // Emit event
          await eventEmitter.emit(AnnotationEvent.UPDATED, {
            taskId: `perf-task-${i}`,
            data: { label: `perf-${i}` },
          });
          
          // Add sync operation
          await syncManager.addOperation('create', {
            id: `perf-annotation-${i}`,
            taskId: `perf-task-${i}`,
            userId: mockConfig.userId,
            data: { label: `perf-${i}`, index: i },
            timestamp: Date.now(),
            version: 1,
            status: 'completed',
          });
        };
        
        operations.push(operation());
      }
      
      // Execute all operations concurrently
      await Promise.all(operations);
      
      // Wait for sync completion
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const intensiveWorkloadEndTime = Date.now();
      const workloadDuration = intensiveWorkloadEndTime - intensiveWorkloadStartTime;
      
      // Stop monitoring
      performanceMonitor.stop();
      
      // Verify performance metrics
      expect(workloadDuration).toBeLessThan(10000); // Should complete within 10 seconds
      
      // Verify sync performance
      const syncStats = syncManager.getStats();
      expect(syncStats.totalOperations).toBe(operationCount);
      expect(syncStats.completedOperations).toBe(operationCount);
      expect(syncStats.failedOperations).toBe(0);
      
      // Verify average sync time is reasonable
      const avgSyncTime = syncStats.syncDuration / syncStats.totalOperations;
      expect(avgSyncTime).toBeLessThan(200); // Average sync time should be < 200ms
      
      // Verify performance data was collected
      expect(performanceData.length).toBeGreaterThan(0);
      
      // Check for memory leaks
      const initialMemory = (performance as any).memory.usedJSHeapSize;
      
      // Force cleanup
      iframeManager.destroy();
      postMessageBridge.cleanup();
      syncManager.destroy();
      eventEmitter.destroy();
      
      // Simulate garbage collection
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = (performance as any).memory.usedJSHeapSize;
      const memoryIncrease = finalMemory - initialMemory;
      
      // Memory increase should be minimal
      expect(memoryIncrease).toBeLessThan(20 * 1024 * 1024); // Less than 20MB increase
      
      // Generate performance report
      const performanceReport = performanceMonitor.getReport();
      expect(performanceReport).toBeTruthy();
      expect(performanceReport.summary.totalOperations).toBe(operationCount);
      expect(performanceReport.summary.averageResponseTime).toBeLessThan(1000);
    });

    it('should handle memory pressure gracefully', async () => {
      // Setup monitoring
      performanceMonitor.start();
      
      // Setup system
      contextManager.setContext(mockContext);
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      // syncManager starts automatically
      
      // Simulate memory pressure by creating large datasets
      const largeDataSets: any[] = [];
      const memoryPressureStartTime = Date.now();
      
      // Create memory pressure
      for (let i = 0; i < 100; i++) {
        const largeData = {
          id: `memory-test-${i}`,
          data: new Array(1000).fill(0).map((_, idx) => ({
            index: idx,
            value: Math.random(),
            timestamp: Date.now(),
            metadata: {
              description: `Large data item ${idx} for memory test ${i}`,
              tags: new Array(10).fill(0).map((_, tagIdx) => `tag-${tagIdx}`),
            },
          })),
        };
        
        largeDataSets.push(largeData);
        
        // Add to sync queue
        await syncManager.addOperation('create', {
          id: `memory-annotation-${i}`,
          taskId: 'memory-test-task',
          userId: mockConfig.userId,
          data: largeData,
          timestamp: Date.now(),
          version: 1,
          status: 'completed',
        });
        
        // Check memory usage periodically
        if (i % 20 === 0) {
          const currentMemory = (performance as any).memory.usedJSHeapSize;
          expect(currentMemory).toBeLessThan(500 * 1024 * 1024); // Should stay under 500MB
        }
      }
      
      // Wait for sync to handle the load
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      const memoryPressureEndTime = Date.now();
      const memoryTestDuration = memoryPressureEndTime - memoryPressureStartTime;
      
      // Verify system remained responsive
      expect(memoryTestDuration).toBeLessThan(15000); // Should complete within 15 seconds
      
      // Verify sync handled the load
      const syncStats = syncManager.getStats();
      expect(syncStats.totalOperations).toBe(100);
      expect(syncStats.completedOperations).toBeGreaterThan(50); // At least 50% should complete
      
      // Verify system is still responsive
      expect(iframeManager.getStatus()).toBe('ready');
      expect(postMessageBridge.getStatus()).toBe('connected');
      
      // Clean up large datasets
      largeDataSets.length = 0;
      
      performanceMonitor.stop();
      
      // Verify performance report includes memory metrics
      const performanceReport = performanceMonitor.getReport();
      expect(performanceReport).toBeTruthy();
      expect(performanceReport.summary.peakMemoryUsage).toBeGreaterThan(0);
    });
  });

  describe('Real-world Usage Scenarios', () => {
    it('should handle typical user annotation session', async () => {
      const sessionEvents: Array<{ event: string; timestamp: number }> = [];
      
      // Track session events
      const trackEvent = (event: string) => {
        sessionEvents.push({ event, timestamp: Date.now() });
      };
      
      // Setup session
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      uiCoordinator.initialize(iframe, container);
      // syncManager starts automatically
      
      trackEvent('session:started');
      
      // Simulate typical user session
      const sessionTasks = [
        { id: 'task-1', type: 'image_classification', expectedTime: 30000 },
        { id: 'task-2', type: 'object_detection', expectedTime: 45000 },
        { id: 'task-3', type: 'text_annotation', expectedTime: 20000 },
      ];
      
      for (const task of sessionTasks) {
        trackEvent(`task:started:${task.id}`);
        
        // Start task
        await eventEmitter.emit(AnnotationEvent.STARTED, {
          taskId: task.id,
          userId: mockConfig.userId,
          taskType: task.type,
        });
        
        // Simulate user annotation work
        const annotationSteps = 5;
        for (let step = 0; step < annotationSteps; step++) {
          await eventEmitter.emit(AnnotationEvent.UPDATED, {
            taskId: task.id,
            data: {
              step: step + 1,
              progress: ((step + 1) / annotationSteps) * 100,
              annotation: `${task.type}_step_${step + 1}`,
            },
          });
          
          // Simulate user thinking/working time
          await new Promise(resolve => setTimeout(resolve, 200));
        }
        
        // Complete task
        const finalAnnotation: AnnotationData = {
          id: `annotation-${task.id}`,
          taskId: task.id,
          userId: mockConfig.userId,
          data: {
            type: task.type,
            completed: true,
            quality: 'high',
            timeSpent: task.expectedTime,
          },
          timestamp: Date.now(),
          version: 1,
          status: 'completed',
        };
        
        await syncManager.addOperation('create', finalAnnotation);
        await eventEmitter.emit(AnnotationEvent.SAVED, {
          taskId: task.id,
          annotationId: finalAnnotation.id,
        });
        await eventEmitter.emit(AnnotationEvent.COMPLETED, {
          taskId: task.id,
          annotationId: finalAnnotation.id,
        });
        
        trackEvent(`task:completed:${task.id}`);
      }
      
      // Wait for all syncs to complete
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      trackEvent('session:ended');
      
      // Verify session completed successfully
      const syncStats = syncManager.getStats();
      expect(syncStats.totalOperations).toBe(sessionTasks.length);
      expect(syncStats.completedOperations).toBe(sessionTasks.length);
      expect(syncStats.failedOperations).toBe(0);
      
      // Verify all tasks were processed
      const taskStartEvents = sessionEvents.filter(e => e.event.startsWith('task:started'));
      const taskCompletedEvents = sessionEvents.filter(e => e.event.startsWith('task:completed'));
      
      expect(taskStartEvents).toHaveLength(sessionTasks.length);
      expect(taskCompletedEvents).toHaveLength(sessionTasks.length);
      
      // Verify session timing
      const sessionStart = sessionEvents.find(e => e.event === 'session:started')!;
      const sessionEnd = sessionEvents.find(e => e.event === 'session:ended')!;
      const sessionDuration = sessionEnd.timestamp - sessionStart.timestamp;
      
      // Session should complete in reasonable time
      expect(sessionDuration).toBeLessThan(10000); // Less than 10 seconds for test
      
      // Verify system state
      expect(iframeManager.getStatus()).toBe('ready');
      expect(postMessageBridge.getStatus()).toBe('connected');
      expect(syncManager.getStatus()).toBe('idle');
    });

    it('should handle user switching between tasks rapidly', async () => {
      const taskSwitchEvents: Array<{ from: string; to: string; timestamp: number }> = [];
      
      // Setup
      contextManager.setContext(mockContext);
      // PermissionController uses context-based permission checking
      
      const iframe = await iframeManager.create(mockConfig, container);
      await postMessageBridge.initialize(iframe.contentWindow);
      // syncManager starts automatically
      
      // Simulate rapid task switching
      const tasks = ['task-A', 'task-B', 'task-C', 'task-D', 'task-E'];
      let currentTask = tasks[0];
      
      // Start first task
      await eventEmitter.emit(AnnotationEvent.STARTED, {
        taskId: currentTask,
        userId: mockConfig.userId,
      });
      
      // Rapidly switch between tasks
      for (let i = 0; i < 20; i++) {
        const nextTask = tasks[Math.floor(Math.random() * tasks.length)];
        
        if (nextTask !== currentTask) {
          taskSwitchEvents.push({
            from: currentTask,
            to: nextTask,
            timestamp: Date.now(),
          });
          
          // Cancel current task
          await eventEmitter.emit(AnnotationEvent.CANCELLED, {
            taskId: currentTask,
          });
          
          // Start new task
          await eventEmitter.emit(AnnotationEvent.STARTED, {
            taskId: nextTask,
            userId: mockConfig.userId,
          });
          
          // Do some work on new task
          await eventEmitter.emit(AnnotationEvent.UPDATED, {
            taskId: nextTask,
            data: { progress: Math.random() * 100 },
          });
          
          currentTask = nextTask;
        }
        
        // Small delay between switches
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      
      // Complete final task
      const finalAnnotation: AnnotationData = {
        id: `final-annotation-${currentTask}`,
        taskId: currentTask,
        userId: mockConfig.userId,
        data: { completed: true, finalTask: true },
        timestamp: Date.now(),
        version: 1,
        status: 'completed',
      };
      
      await syncManager.addOperation('create', finalAnnotation);
      await eventEmitter.emit(AnnotationEvent.COMPLETED, {
        taskId: currentTask,
        annotationId: finalAnnotation.id,
      });
      
      // Wait for sync
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Verify system handled rapid switching
      expect(taskSwitchEvents.length).toBeGreaterThan(0);
      
      // Verify final sync
      const syncStats = syncManager.getStats();
      expect(syncStats.completedOperations).toBeGreaterThan(0);
      
      // Verify system stability
      expect(iframeManager.getStatus()).toBe('ready');
      expect(postMessageBridge.getStatus()).toBe('connected');
      
      // Verify no memory leaks from rapid switching
      const finalMemory = (performance as any).memory.usedJSHeapSize;
      expect(finalMemory).toBeLessThan(200 * 1024 * 1024); // Should stay under 200MB
    });
  });
});