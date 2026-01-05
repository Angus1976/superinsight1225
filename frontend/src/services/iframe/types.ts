/**
 * Type definitions for iframe management
 */

export interface IframeConfig {
  url: string;
  projectId: string;
  taskId?: string;
  userId: string;
  token: string;
  permissions: Permission[];
  theme?: 'light' | 'dark';
  fullscreen?: boolean;
  timeout?: number;
  retryAttempts?: number;
}

export interface Permission {
  action: string;
  resource: string;
  allowed: boolean;
}

export enum IframeStatus {
  LOADING = 'loading',
  READY = 'ready',
  ERROR = 'error',
  DESTROYED = 'destroyed',
}

export interface IframeLifecycleEvent {
  type: 'load' | 'error' | 'ready' | 'destroy' | 'refresh';
  timestamp: number;
  data?: unknown;
}

export interface IframeLoadState {
  isLoading: boolean;
  progress: number;
  error: string | null;
  status: IframeStatus;
  loadStartTime?: number;
  loadEndTime?: number;
}

export type IframeEventCallback = (event: IframeLifecycleEvent) => void;

// PostMessage Bridge Types
export interface Message {
  id: string;
  type: string;
  payload: unknown;
  timestamp: number;
  signature?: string;
  source?: 'main' | 'iframe';
}

export interface Response {
  id: string;
  success: boolean;
  data?: unknown;
  error?: string;
}

export enum BridgeStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  ERROR = 'error',
}

export type MessageHandler = (message: Message) => void | Promise<void>;

export interface PostMessageBridgeConfig {
  targetOrigin?: string;
  timeout?: number;
  maxRetries?: number;
  enableEncryption?: boolean;
  enableSignature?: boolean;
}

// Context Management Types
export interface UserInfo {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar?: string;
}

export interface ProjectInfo {
  id: string;
  name: string;
  description: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface TaskInfo {
  id: string;
  name: string;
  status: string;
  progress: number;
  assignedTo?: string;
  dueDate?: string;
}

export interface AnnotationContext {
  user: UserInfo;
  project: ProjectInfo;
  task: TaskInfo;
  permissions: Permission[];
  timestamp: number;
  sessionId?: string;
  metadata?: Record<string, unknown>;
}

export interface ContextManagerConfig {
  enableEncryption?: boolean;
  encryptionKey?: string;
  sessionTimeout?: number;
  autoRefresh?: boolean;
}

// Data Synchronization Types
export interface AnnotationData {
  id: string;
  taskId: string;
  userId: string;
  data: Record<string, unknown>;
  timestamp: number;
  version: number;
  status: 'draft' | 'completed' | 'reviewed';
  metadata?: Record<string, unknown>;
}

export interface SyncOperation {
  id: string;
  type: 'create' | 'update' | 'delete';
  data: AnnotationData;
  timestamp: number;
  retryCount: number;
  status: 'pending' | 'syncing' | 'completed' | 'failed';
}

export interface SyncConflict {
  id: string;
  localData: AnnotationData;
  remoteData: AnnotationData;
  conflictType: 'version' | 'concurrent' | 'deleted';
  timestamp: number;
  resolved: boolean;
}

export interface SyncManagerConfig {
  enableIncrementalSync?: boolean;
  syncInterval?: number;
  maxRetries?: number;
  conflictResolution?: 'local' | 'remote' | 'manual';
  enableOfflineCache?: boolean;
  cacheSize?: number;
}

export enum SyncStatus {
  IDLE = 'idle',
  SYNCING = 'syncing',
  OFFLINE = 'offline',
  ERROR = 'error',
}

export interface SyncStats {
  totalOperations: number;
  completedOperations: number;
  failedOperations: number;
  conflictsResolved: number;
  lastSyncTime: number;
  syncDuration: number;
}

export type SyncEventCallback = (event: SyncEvent) => void;

export interface SyncEvent {
  type: 'sync_start' | 'sync_complete' | 'sync_error' | 'conflict_detected' | 'offline_mode';
  timestamp: number;
  data?: unknown;
}

// Event System Types
export interface EventRecord {
  event: string;
  data: unknown;
  timestamp: number;
  source: 'iframe' | 'main';
  priority: number;
  id: string;
}

export enum AnnotationEvent {
  STARTED = 'annotation:started',
  UPDATED = 'annotation:updated',
  COMPLETED = 'annotation:completed',
  SAVED = 'annotation:saved',
  ERROR = 'annotation:error',
  PROGRESS = 'annotation:progress',
  CANCELLED = 'annotation:cancelled',
}

export type EventHandler = (data: unknown, event: EventRecord) => void | Promise<void>;

export interface EventEmitterConfig {
  maxHistorySize?: number;
  enablePriority?: boolean;
  enableAsync?: boolean;
  defaultPriority?: number;
}

export interface EventSubscription {
  id: string;
  event: string;
  handler: EventHandler;
  priority: number;
  once: boolean;
  active: boolean;
}
