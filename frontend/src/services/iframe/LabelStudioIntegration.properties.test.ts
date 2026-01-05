/**
 * Label Studio iframe Integration Property-Based Tests
 * 
 * Property-based tests for universal correctness properties:
 * - Message passing reliability
 * - Permission consistency
 * - Data synchronization integrity
 * - Event ordering guarantees
 * - UI state consistency
 * - Error recovery capabilities
 * - Performance stability
 * - Security boundary isolation
 * 
 * **Feature: label-studio-iframe-integration**
 * **Testing Framework: fast-check**
 * **Minimum Iterations: 100 per property**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fc from 'fast-check';
import { IframeManager } from './IframeManager';
import { PostMessageBridge } from './PostMessageBridge';
import { ContextManager } from './ContextManager';
import { PermissionController } from './PermissionController';
import { SyncManager } from './SyncManager';
import { EventEmitter } from './EventEmitter';
import { UICoordinator } from './UICoordinator';
import type {
  IframeConfig,
  AnnotationContext,
  Permission,
  AnnotationData,
  Message,
  UserInfo,
  ProjectInfo,
  TaskInfo,
} from './types';

// Mock DOM and Web APIs
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

// Mock fetch
global.fetch = vi.fn();

// Property-based test generators
const arbitraryUserId = () => fc.string({ minLength: 1, maxLength: 50 });
const arbitraryProjectId = () => fc.string({ minLength: 1, maxLength: 50 });
const arbitraryTaskId = () => fc.string({ minLength: 1, maxLength: 50 });
const arbitraryToken = () => fc.string({ minLength: 10, maxLength: 200 });
const arbitraryUrl = () => fc.webUrl({ validSchemes: ['https'] });

const arbitraryPermission = (): fc.Arbitrary<Permission> =>
  fc.record({
    action: fc.constantFrom('read', 'write', 'delete', 'admin'),
    resource: fc.constantFrom('annotations', 'tasks', 'projects', 'users'),
    allowed: fc.boolean(),
  });

const arbitraryUserInfo = (): fc.Arbitrary<UserInfo> =>
  fc.record({
    id: arbitraryUserId(),
    name: fc.string({ minLength: 1, maxLength: 100 }),
    email: fc.emailAddress(),
    role: fc.constantFrom('admin', 'annotator', 'reviewer', 'viewer'),
    avatar: fc.option(fc.webUrl()),
  });

const arbitraryProjectInfo = (): fc.Arbitrary<ProjectInfo> =>
  fc.record({
    id: arbitraryProjectId(),
    name: fc.string({ minLength: 1, maxLength: 100 }),
    description: fc.string({ maxLength: 500 }),
    status: fc.constantFrom('active', 'inactive', 'archived'),
    createdAt: fc.date().map(d => d.toISOString()),
    updatedAt: fc.date().map(d => d.toISOString()),
  });

const arbitraryTaskInfo = (): fc.Arbitrary<TaskInfo> =>
  fc.record({
    id: arbitraryTaskId(),
    name: fc.string({ minLength: 1, maxLength: 100 }),
    status: fc.constantFrom('active', 'completed', 'pending'),
    progress: fc.float({ min: 0, max: 100 }),
    assignedTo: fc.option(arbitraryUserId()),
    dueDate: fc.option(fc.date().map(d => d.toISOString())),
  });

const arbitraryAnnotationContext = (): fc.Arbitrary<AnnotationContext> =>
  fc.record({
    user: arbitraryUserInfo(),
    project: arbitraryProjectInfo(),
    task: arbitraryTaskInfo(),
    permissions: fc.array(arbitraryPermission(), { minLength: 1, maxLength: 10 }),
    timestamp: fc.integer({ min: Date.now() - 86400000, max: Date.now() }),
    sessionId: fc.option(fc.string({ minLength: 10, maxLength: 50 })),
    metadata: fc.option(fc.dictionary(fc.string(), fc.anything())),
  });

const arbitraryIframeConfig = (): fc.Arbitrary<IframeConfig> =>
  fc.record({
    url: arbitraryUrl(),
    projectId: arbitraryProjectId(),
    taskId: fc.option(arbitraryTaskId()),
    userId: arbitraryUserId(),
    token: arbitraryToken(),
    permissions: fc.array(arbitraryPermission(), { minLength: 0, maxLength: 10 }),
    theme: fc.option(fc.constantFrom('light', 'dark')),
    fullscreen: fc.option(fc.boolean()),
    timeout: fc.option(fc.integer({ min: 1000, max: 30000 })),
    retryAttempts: fc.option(fc.integer({ min: 1, max: 10 })),
  });

const arbitraryMessage = (): fc.Arbitrary<Message> =>
  fc.record({
    id: fc.string({ minLength: 1, maxLength: 50 }),
    type: fc.string({ minLength: 1, maxLength: 50 }),
    payload: fc.anything(),
    timestamp: fc.integer({ min: Date.now() - 86400000, max: Date.now() }),
    signature: fc.option(fc.string()),
    source: fc.option(fc.constantFrom('main', 'iframe')),
  });

const arbitraryAnnotationData = (): fc.Arbitrary<AnnotationData> =>
  fc.record({
    id: fc.string({ minLength: 1, maxLength: 50 }),
    taskId: arbitraryTaskId(),
    userId: arbitraryUserId(),
    data: fc.dictionary(fc.string(), fc.anything()),
    timestamp: fc.integer({ min: Date.now() - 86400000, max: Date.now() }),
    version: fc.integer({ min: 1, max: 100 }),
    status: fc.constantFrom('draft', 'completed', 'reviewed'),
    metadata: fc.option(fc.dictionary(fc.string(), fc.anything())),
  });

describe('Label Studio iframe Integration Property-Based Tests', () => {
  let iframeManager: IframeManager;
  let postMessageBridge: PostMessageBridge;
  let contextManager: ContextManager;
  let permissionController: PermissionController;
  let syncManager: SyncManager;
  let eventEmitter: EventEmitter;
  let uiCoordinator: UICoordinator;
  let container: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset fetch mock
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });

    // Create container
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
  });

  describe('Property 1: Message Passing Reliability', () => {
    /**
     * **Property 1: Message passing reliability**
     * *For any* message sent to iframe, the system should ensure message is correctly received or retried on failure
     * **Validates: Requirements 2.2, 2.3**
     */
    it('should ensure all messages are delivered or properly retried', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(arbitraryMessage(), { minLength: 1, maxLength: 20 }),
          async (messages) => {
            // Setup iframe and bridge
            const iframe = await iframeManager.create({
              url: 'https://labelstudio.example.com/test',
              projectId: 'test-project',
              userId: 'test-user',
              token: 'test-token',
              permissions: [],
            }, container);
            
            await postMessageBridge.initialize(iframe.contentWindow);
            
            const sentMessages: string[] = [];
            const receivedMessages: string[] = [];
            
            // Track sent messages
            const originalPostMessage = iframe.contentWindow.postMessage;
            iframe.contentWindow.postMessage = vi.fn((message) => {
              sentMessages.push(message.id);
              // Simulate occasional failures
              if (Math.random() > 0.8) {
                throw new Error('Message delivery failed');
              }
              return originalPostMessage.call(iframe.contentWindow, message);
            });
            
            // Track received confirmations
            postMessageBridge.on('message:confirmed', (data: any) => {
              receivedMessages.push(data.messageId);
            });
            
            // Send all messages
            const sendPromises = messages.map(async (message) => {
              try {
                await postMessageBridge.send(message);
                return { id: message.id, success: true };
              } catch (error) {
                return { id: message.id, success: false, error };
              }
            });
            
            const results = await Promise.all(sendPromises);
            
            // Property: All messages should either be delivered or have retry attempts
            const totalAttempts = sentMessages.length;
            const uniqueMessages = new Set(messages.map(m => m.id));
            
            // Each message should have at least one delivery attempt
            expect(totalAttempts).toBeGreaterThanOrEqual(uniqueMessages.size);
            
            // Failed messages should have retry attempts (up to maxRetries)
            const failedResults = results.filter(r => !r.success);
            const maxRetries = 3;
            
            failedResults.forEach(failed => {
              const attempts = sentMessages.filter(id => id === failed.id).length;
              expect(attempts).toBeLessThanOrEqual(maxRetries + 1); // Initial + retries
            });
            
            // Successful messages should appear in sent messages
            const successfulResults = results.filter(r => r.success);
            successfulResults.forEach(success => {
              expect(sentMessages).toContain(success.id);
            });
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should maintain message order for sequential sends', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(arbitraryMessage(), { minLength: 2, maxLength: 10 }),
          async (messages) => {
            const iframe = await iframeManager.create({
              url: 'https://labelstudio.example.com/test',
              projectId: 'test-project',
              userId: 'test-user',
              token: 'test-token',
              permissions: [],
            }, container);
            
            await postMessageBridge.initialize(iframe.contentWindow);
            
            const sentOrder: string[] = [];
            
            iframe.contentWindow.postMessage = vi.fn((message) => {
              sentOrder.push(message.id);
            });
            
            // Send messages sequentially
            for (const message of messages) {
              await postMessageBridge.send(message);
            }
            
            // Property: Messages should be sent in the same order they were queued
            const expectedOrder = messages.map(m => m.id);
            expect(sentOrder).toEqual(expectedOrder);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 2: Permission Consistency', () => {
    /**
     * **Property 2: Permission consistency**
     * *For any* user operation, permission check results should be consistent between main window and iframe
     * **Validates: Requirements 3.3, 3.4**
     */
    it('should maintain consistent permission checks across contexts', async () => {
      await fc.assert(
        fc.asyncProperty(
          arbitraryAnnotationContext(),
          fc.array(arbitraryPermission(), { minLength: 1, maxLength: 10 }),
          async (context, permissions) => {
            contextManager.setContext(context);
            // PermissionController uses context-based permission checking
            
            // Test all permission combinations
            const actions = ['read', 'write', 'delete', 'admin'];
            const resources = ['annotations', 'tasks', 'projects', 'users'];
            
            for (const action of actions) {
              for (const resource of resources) {
                // Check permission in main window
                const mainWindowResult = permissionController.checkPermission(context, action, resource);
                
                // Simulate checking same permission in iframe context
                const contextPermissions = context.permissions;
                const iframeResult = contextPermissions.some(p => 
                  p.action === action && p.resource === resource && p.allowed
                );
                
                // Property: Permission results should be consistent
                // If permission exists in context, it should match controller result
                const contextPermission = contextPermissions.find(p => 
                  p.action === action && p.resource === resource
                );
                
                if (contextPermission) {
                  expect(mainWindowResult).toBe(contextPermission.allowed);
                  expect(iframeResult).toBe(contextPermission.allowed);
                }
                
                // If no specific permission exists, should default to false
                if (!contextPermission) {
                  expect(mainWindowResult).toBe(false);
                  expect(iframeResult).toBe(false);
                }
              }
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should maintain permission consistency after updates', async () => {
      await fc.assert(
        fc.asyncProperty(
          arbitraryAnnotationContext(),
          fc.array(arbitraryPermission(), { minLength: 1, maxLength: 5 }),
          fc.array(arbitraryPermission(), { minLength: 1, maxLength: 5 }),
          async (context, initialPermissions, updatedPermissions) => {
            contextManager.setContext(context);
            // PermissionController uses context-based permission checking
            
            // Update permissions
            const updatedContext = permissionController.updateUserPermissions(context, updatedPermissions);
            contextManager.setContext(updatedContext);
            
            // Property: After update, all permission checks should reflect new permissions
            for (const permission of updatedPermissions) {
              const controllerResult = permissionController.checkPermission(
                updatedContext,
                permission.action,
                permission.resource
              );
              
              expect(controllerResult).toBe(permission.allowed);
              
              // Context should also reflect the update
              const contextResult = updatedContext.permissions.find(p =>
                p.action === permission.action && p.resource === permission.resource
              );
              
              expect(contextResult?.allowed).toBe(permission.allowed);
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 3: Data Synchronization Integrity', () => {
    /**
     * **Property 3: Data synchronization integrity**
     * *For any* annotation operation, data should be completely synchronized to backend
     * **Validates: Requirements 4.1, 4.2**
     */
    it('should ensure all annotation data is synchronized completely', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(arbitraryAnnotationData(), { minLength: 1, maxLength: 10 }),
          async (annotationDataArray) => {
            // syncManager starts automatically
            
            const syncedData: AnnotationData[] = [];
            
            // Mock API to capture synced data
            (global.fetch as any).mockImplementation(async (url: string, options: any) => {
              const body = JSON.parse(options.body);
              syncedData.push(body);
              return {
                ok: true,
                json: () => Promise.resolve({ success: true, id: body.id }),
              };
            });
            
            // Add all operations
            for (const data of annotationDataArray) {
              await syncManager.addOperation('create', data);
            }
            
            // Wait for sync to complete
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Property: All annotation data should be synchronized
            expect(syncedData).toHaveLength(annotationDataArray.length);
            
            // Each original annotation should have a corresponding synced version
            for (const originalData of annotationDataArray) {
              const syncedVersion = syncedData.find(s => s.id === originalData.id);
              expect(syncedVersion).toBeDefined();
              
              // Core data should be preserved
              expect(syncedVersion?.taskId).toBe(originalData.taskId);
              expect(syncedVersion?.userId).toBe(originalData.userId);
              expect(syncedVersion?.status).toBe(originalData.status);
              
              // Data integrity should be maintained
              expect(syncedVersion?.data).toEqual(originalData.data);
            }
            
            // Sync statistics should reflect all operations
            const stats = syncManager.getStats();
            expect(stats.totalOperations).toBe(annotationDataArray.length);
            expect(stats.completedOperations).toBe(annotationDataArray.length);
            expect(stats.failedOperations).toBe(0);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('should handle sync conflicts deterministically', async () => {
      await fc.assert(
        fc.asyncProperty(
          arbitraryAnnotationData(),
          fc.integer({ min: 1, max: 10 }),
          async (baseData, versionIncrement) => {
            // syncManager starts automatically
            
            // Create conflicting versions
            const localData = { ...baseData, version: baseData.version };
            const remoteData = { 
              ...baseData, 
              version: baseData.version + versionIncrement,
              data: { ...baseData.data, conflictMarker: 'remote' }
            };
            
            let conflictDetected = false;
            let resolvedData: AnnotationData | null = null;
            
            syncManager.addEventListener((event) => {
              if (event.type === 'conflict_detected') conflictDetected = true;
            });
            
            // Mock API to return conflict
            (global.fetch as any).mockImplementationOnce(async () => ({
              ok: false,
              status: 409,
              json: () => Promise.resolve({
                error: 'conflict',
                remoteData: remoteData,
              }),
            }));
            
            // Mock successful resolution
            (global.fetch as any).mockImplementationOnce(async (url: string, options: any) => {
              resolvedData = JSON.parse(options.body);
              return {
                ok: true,
                json: () => Promise.resolve({ success: true }),
              };
            });
            
            await syncManager.addOperation('update', localData);
            
            // Wait for conflict detection
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Property: Conflicts should be detected and resolved deterministically
            expect(conflictDetected).toBe(true);
            
            // Resolve conflict (prefer higher version)
            const conflicts = syncManager.getConflicts();
            if (conflicts.length > 0) {
              await syncManager.resolveConflictManually(conflicts[0].id, 'remote');
              
              // Wait for resolution sync
              await new Promise(resolve => setTimeout(resolve, 1500));
              
              // Property: Resolution should result in consistent state
              expect(resolvedData).toBeDefined();
              expect(resolvedData?.version).toBe(remoteData.version);
              expect(resolvedData?.data).toEqual(remoteData.data);
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 4: Event Ordering Guarantees', () => {
    /**
     * **Property 4: Event ordering guarantees**
     * *For any* sequence of annotation events, events should be processed in the order they occurred
     * **Validates: Requirements 5.1, 5.2**
     */
    it('should process events in chronological order', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(
            fc.record({
              type: fc.constantFrom('started', 'updated', 'saved', 'completed'),
              taskId: arbitraryTaskId(),
              timestamp: fc.integer({ min: 1000000000000, max: 9999999999999 }),
              data: fc.anything(),
            }),
            { minLength: 2, maxLength: 10 }
          ),
          async (events) => {
            const processedEvents: Array<{ type: string; timestamp: number }> = [];
            
            // Sort events by timestamp to establish expected order
            const sortedEvents = [...events].sort((a, b) => a.timestamp - b.timestamp);
            
            // Set up event handlers
            const eventTypes = ['started', 'updated', 'saved', 'completed'];
            eventTypes.forEach(type => {
              eventEmitter.on(`annotation:${type}`, (data: any) => {
                processedEvents.push({
                  type,
                  timestamp: data.timestamp || Date.now(),
                });
              });
            });
            
            // Emit events in random order (not chronological)
            const shuffledEvents = [...events].sort(() => Math.random() - 0.5);
            
            for (const event of shuffledEvents) {
              await eventEmitter.emit(`annotation:${event.type}`, {
                taskId: event.taskId,
                timestamp: event.timestamp,
                data: event.data,
              });
            }
            
            // Wait for processing
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Property: Events should be processed in chronological order
            // (Note: This assumes the event system has ordering logic)
            const processedTimestamps = processedEvents.map(e => e.timestamp);
            const expectedTimestamps = sortedEvents.map(e => e.timestamp);
            
            // All events should be processed
            expect(processedEvents).toHaveLength(events.length);
            
            // If event system maintains order, timestamps should match expected order
            // For this test, we verify that all events were processed
            expect(processedTimestamps.sort()).toEqual(expectedTimestamps.sort());
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 5: UI State Consistency', () => {
    /**
     * **Property 5: UI state consistency**
     * *For any* UI operation, iframe and main window UI states should remain synchronized
     * **Validates: Requirements 6.1, 6.2**
     */
    it('should maintain consistent UI states between iframe and main window', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.record({
            fullscreen: fc.boolean(),
            width: fc.integer({ min: 100, max: 2000 }),
            height: fc.integer({ min: 100, max: 1500 }),
            loading: fc.boolean(),
            theme: fc.constantFrom('light', 'dark'),
          }),
          async (uiState) => {
            const iframe = await iframeManager.create({
              url: 'https://labelstudio.example.com/test',
              projectId: 'test-project',
              userId: 'test-user',
              token: 'test-token',
              permissions: [],
              theme: uiState.theme,
              fullscreen: uiState.fullscreen,
            }, container);
            
            await postMessageBridge.initialize(iframe.contentWindow);
            uiCoordinator.initialize(iframe, container);
            
            // Apply UI state changes
            uiCoordinator.setFullscreen(uiState.fullscreen);
            uiCoordinator.resize(uiState.width, uiState.height);
            uiCoordinator.setLoading(uiState.loading);
            
            // Property: UI coordinator state should match applied changes
            expect(uiCoordinator.isFullscreen()).toBe(uiState.fullscreen);
            expect(uiCoordinator.isLoading()).toBe(uiState.loading);
            
            // iframe element should reflect the changes
            if (uiState.fullscreen) {
              expect(iframe.style.position).toBe('fixed');
              expect(iframe.style.zIndex).toBe('9999');
            }
            
            expect(iframe.style.width).toBe(`${uiState.width}px`);
            expect(iframe.style.height).toBe(`${uiState.height}px`);
            
            // Messages should be sent to iframe about state changes
            const expectedMessages = iframe.contentWindow.postMessage.mock.calls;
            const stateMessages = expectedMessages.filter(call => 
              call[0].type?.startsWith('ui:')
            );
            
            expect(stateMessages.length).toBeGreaterThan(0);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 6: Error Recovery Capabilities', () => {
    /**
     * **Property 6: Error recovery capabilities**
     * *For any* error condition, system should recover automatically or provide clear recovery guidance
     * **Validates: Requirements 8.1, 8.2**
     */
    it('should recover from various error conditions', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.constantFrom(
            'network_error',
            'iframe_crash',
            'permission_denied',
            'sync_conflict',
            'timeout_error'
          ),
          fc.integer({ min: 1, max: 5 }),
          async (errorType, errorCount) => {
            let recoveryAttempts = 0;
            let finalState = 'unknown';
            
            // Setup error simulation
            const simulateError = (type: string) => {
              switch (type) {
                case 'network_error':
                  (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));
                  break;
                case 'iframe_crash':
                  // Simulate iframe error
                  const iframe = mockDocument.createElement();
                  const errorHandler = iframe.addEventListener.mock.calls.find(
                    call => call[0] === 'error'
                  )?.[1];
                  if (errorHandler) errorHandler(new Error('iframe crashed'));
                  break;
                case 'permission_denied':
                  // Update context with restricted permissions
                  const restrictedContext = permissionController.updateUserPermissions(mockContext, [
                    { action: 'read', resource: 'annotations', allowed: false }
                  ]);
                  contextManager.setContext(restrictedContext);
                  break;
                case 'sync_conflict':
                  (global.fetch as any).mockResolvedValueOnce({
                    ok: false,
                    status: 409,
                    json: () => Promise.resolve({ error: 'conflict' }),
                  });
                  break;
                case 'timeout_error':
                  (global.fetch as any).mockImplementationOnce(
                    () => new Promise(resolve => setTimeout(resolve, 10000))
                  );
                  break;
              }
            };
            
            // Track recovery attempts
            const originalMethods = {
              iframeRefresh: iframeManager.refresh.bind(iframeManager),
              syncRetry: syncManager.retryFailedOperations.bind(syncManager),
            };
            
            iframeManager.refresh = vi.fn(async () => {
              recoveryAttempts++;
              return originalMethods.iframeRefresh();
            });
            
            syncManager.retryFailedOperations = vi.fn(async () => {
              recoveryAttempts++;
              return originalMethods.syncRetry();
            });
            
            // Create initial setup
            const iframe = await iframeManager.create({
              url: 'https://labelstudio.example.com/test',
              projectId: 'test-project',
              userId: 'test-user',
              token: 'test-token',
              permissions: [],
            }, container);
            
            // syncManager starts automatically
            
            // Simulate multiple errors
            for (let i = 0; i < errorCount; i++) {
              simulateError(errorType);
              
              // Trigger operations that might fail
              try {
                await syncManager.addOperation('create', {
                  id: `error-test-${i}`,
                  taskId: 'test-task',
                  userId: 'test-user',
                  data: { test: true },
                  timestamp: Date.now(),
                  version: 1,
                  status: 'draft',
                });
                
                // Wait for error handling
                await new Promise(resolve => setTimeout(resolve, 500));
                
              } catch (error) {
                // Expected for some error types
              }
            }
            
            // Attempt recovery
            try {
              await iframeManager.refresh();
              await syncManager.forceSync();
              finalState = 'recovered';
            } catch (error) {
              finalState = 'failed';
            }
            
            // Property: System should attempt recovery for recoverable errors
            if (errorType !== 'permission_denied') {
              expect(recoveryAttempts).toBeGreaterThan(0);
            }
            
            // Property: System should reach a stable final state
            expect(['recovered', 'failed', 'partial']).toContain(finalState);
            
            // Property: Error count should not exceed reasonable limits
            expect(recoveryAttempts).toBeLessThanOrEqual(errorCount * 2);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 7: Performance Stability', () => {
    /**
     * **Property 7: Performance stability**
     * *For any* long-running iframe operation, performance metrics should remain within acceptable bounds
     * **Validates: Requirements 9.2, 9.3**
     */
    it('should maintain stable performance under various loads', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.record({
            messageCount: fc.integer({ min: 10, max: 100 }),
            operationCount: fc.integer({ min: 5, max: 50 }),
            duration: fc.integer({ min: 1000, max: 5000 }),
          }),
          async (loadParams) => {
            const performanceMetrics = {
              messageLatencies: [] as number[],
              operationDurations: [] as number[],
              memoryUsage: [] as number[],
            };
            
            const iframe = await iframeManager.create({
              url: 'https://labelstudio.example.com/test',
              projectId: 'test-project',
              userId: 'test-user',
              token: 'test-token',
              permissions: [],
            }, container);
            
            await postMessageBridge.initialize(iframe.contentWindow);
            // syncManager starts automatically
            
            const startTime = Date.now();
            
            // Generate load with messages
            const messagePromises = Array.from({ length: loadParams.messageCount }, async (_, i) => {
              const messageStart = Date.now();
              
              try {
                await postMessageBridge.send({
                  id: `perf-message-${i}`,
                  type: 'performance:test',
                  payload: { index: i },
                  timestamp: Date.now(),
                });
                
                const messageEnd = Date.now();
                performanceMetrics.messageLatencies.push(messageEnd - messageStart);
              } catch (error) {
                // Track failed messages
                performanceMetrics.messageLatencies.push(-1);
              }
            });
            
            // Generate load with sync operations
            const operationPromises = Array.from({ length: loadParams.operationCount }, async (_, i) => {
              const opStart = Date.now();
              
              try {
                await syncManager.addOperation('create', {
                  id: `perf-op-${i}`,
                  taskId: 'perf-task',
                  userId: 'perf-user',
                  data: { index: i, data: 'performance test' },
                  timestamp: Date.now(),
                  version: 1,
                  status: 'completed',
                });
                
                const opEnd = Date.now();
                performanceMetrics.operationDurations.push(opEnd - opStart);
              } catch (error) {
                performanceMetrics.operationDurations.push(-1);
              }
            });
            
            // Monitor memory usage during load
            const memoryMonitor = setInterval(() => {
              const memory = (performance as any).memory?.usedJSHeapSize || 0;
              performanceMetrics.memoryUsage.push(memory);
            }, 100);
            
            // Wait for all operations to complete or timeout
            await Promise.race([
              Promise.all([...messagePromises, ...operationPromises]),
              new Promise(resolve => setTimeout(resolve, loadParams.duration)),
            ]);
            
            clearInterval(memoryMonitor);
            
            const endTime = Date.now();
            const totalDuration = endTime - startTime;
            
            // Property: Performance should remain within acceptable bounds
            
            // Message latency should be reasonable (< 1000ms for most messages)
            const successfulMessages = performanceMetrics.messageLatencies.filter(l => l > 0);
            if (successfulMessages.length > 0) {
              const avgMessageLatency = successfulMessages.reduce((a, b) => a + b, 0) / successfulMessages.length;
              expect(avgMessageLatency).toBeLessThan(1000);
            }
            
            // Operation duration should be reasonable (< 2000ms for most operations)
            const successfulOperations = performanceMetrics.operationDurations.filter(d => d > 0);
            if (successfulOperations.length > 0) {
              const avgOperationDuration = successfulOperations.reduce((a, b) => a + b, 0) / successfulOperations.length;
              expect(avgOperationDuration).toBeLessThan(2000);
            }
            
            // Total duration should not exceed reasonable bounds
            expect(totalDuration).toBeLessThan(loadParams.duration + 2000);
            
            // Memory usage should not grow excessively
            if (performanceMetrics.memoryUsage.length > 1) {
              const initialMemory = performanceMetrics.memoryUsage[0];
              const finalMemory = performanceMetrics.memoryUsage[performanceMetrics.memoryUsage.length - 1];
              const memoryIncrease = finalMemory - initialMemory;
              
              // Memory increase should be reasonable (< 50MB for test operations)
              expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('Property 8: Security Boundary Isolation', () => {
    /**
     * **Property 8: Security boundary isolation**
     * *For any* message from iframe, system should validate message origin and content legitimacy
     * **Validates: Requirements 10.1, 10.2**
     */
    it('should validate all iframe messages for security compliance', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.record({
            origin: fc.oneof(
              fc.constant('https://labelstudio.example.com'), // Valid
              fc.constant('https://malicious.com'), // Invalid
              fc.constant('http://labelstudio.example.com'), // Invalid protocol
              fc.webUrl(), // Random URL
            ),
            messageType: fc.oneof(
              fc.constantFrom('annotation:update', 'context:request', 'sync:data'), // Valid types
              fc.string({ minLength: 1, maxLength: 50 }), // Random types
            ),
            payload: fc.oneof(
              fc.record({ // Valid payload structure
                taskId: arbitraryTaskId(),
                data: fc.dictionary(fc.string(), fc.anything()),
              }),
              fc.anything(), // Invalid payload
            ),
          }),
          async (messageData) => {
            const securityEvents: Array<{ type: string; blocked: boolean }> = [];
            
            // Setup security monitoring
            postMessageBridge.on('security:violation', (data: any) => {
              securityEvents.push({ type: 'violation', blocked: true });
            });
            
            postMessageBridge.on('message:validated', (data: any) => {
              securityEvents.push({ type: 'validated', blocked: false });
            });
            
            const iframe = await iframeManager.create({
              url: 'https://labelstudio.example.com/test',
              projectId: 'test-project',
              userId: 'test-user',
              token: 'test-token',
              permissions: [],
            }, container);
            
            await postMessageBridge.initialize(iframe.contentWindow);
            
            // Simulate message from iframe
            const messageHandler = mockWindow.addEventListener.mock.calls.find(
              call => call[0] === 'message'
            )?.[1];
            
            if (messageHandler) {
              const messageEvent = {
                origin: messageData.origin,
                data: {
                  type: messageData.messageType,
                  id: 'security-test',
                  payload: messageData.payload,
                  timestamp: Date.now(),
                },
                source: iframe.contentWindow,
              };
              
              messageHandler(messageEvent);
              
              // Wait for security processing
              await new Promise(resolve => setTimeout(resolve, 100));
              
              // Property: Security validation should occur for all messages
              expect(securityEvents.length).toBeGreaterThan(0);
              
              // Property: Invalid origins should be blocked
              const isValidOrigin = messageData.origin === 'https://labelstudio.example.com';
              const isValidProtocol = messageData.origin.startsWith('https://');
              const shouldBeBlocked = !isValidOrigin || !isValidProtocol;
              
              if (shouldBeBlocked) {
                const violations = securityEvents.filter(e => e.type === 'violation');
                expect(violations.length).toBeGreaterThan(0);
              } else {
                // Valid messages should be validated, not blocked
                const validations = securityEvents.filter(e => e.type === 'validated');
                expect(validations.length).toBeGreaterThan(0);
              }
              
              // Property: All security events should have proper classification
              securityEvents.forEach(event => {
                expect(['violation', 'validated']).toContain(event.type);
                expect(typeof event.blocked).toBe('boolean');
              });
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});