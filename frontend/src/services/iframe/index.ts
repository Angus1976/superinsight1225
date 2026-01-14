/**
 * iframe service exports
 */

export { IframeManager } from './IframeManager';
export { PostMessageBridge } from './PostMessageBridge';
export { MessageSecurity } from './MessageSecurity';
export { ContextManager } from './ContextManager';
export { PermissionController } from './PermissionController';
export { SyncManager } from './SyncManager';
export { EventEmitter, globalEventEmitter, AnnotationEvent } from './EventEmitter';
export { AnnotationEventHandler, globalAnnotationEventHandler, initializeGlobalAnnotationEventHandler } from './AnnotationEventHandler';
export { UICoordinator } from './UICoordinator';
export { KeyboardManager } from './KeyboardManager';
export { FocusManager } from './FocusManager';
export { DataTransformer } from './DataTransformer';
export { ErrorHandler, ErrorType, ErrorSeverity, RecoveryAction } from './ErrorHandler';
export { AutoRecoveryManager } from './AutoRecoveryManager';
export { ErrorLogger, LogLevel } from './ErrorLogger';
export { SecurityPolicyManager, createDefaultSecurityPolicy, createLabelStudioSecurityPolicy } from './SecurityPolicyManager';
export { DataEncryption, DataDesensitization, createDefaultDesensitizationConfig } from './DataEncryption';
export { SecurityAuditLogger, createDefaultAuditConfig, getGlobalSecurityAuditLogger, initializeGlobalSecurityAuditLogger } from './SecurityAuditLogger';
export type {
  IframeConfig,
  Permission,
  IframeStatus,
  IframeLifecycleEvent,
  IframeLoadState,
  IframeEventCallback,
  Message,
  Response,
  MessageHandler,
  PostMessageBridgeConfig,
  BridgeStatus,
  UserInfo,
  ProjectInfo,
  TaskInfo,
  AnnotationContext,
  ContextManagerConfig,
  AnnotationData,
  SyncOperation,
  SyncConflict,
  SyncManagerConfig,
  SyncStats,
  SyncEventCallback,
  SyncEvent,
  EventRecord,
  EventHandler,
  EventEmitterConfig,
  EventSubscription,
} from './types';
export type { AnnotationEventData } from './AnnotationEventHandler';
export type { 
  UICoordinatorConfig, 
  UIState, 
  UIEvent, 
  UIEventCallback 
} from './UICoordinator';
export type { 
  KeyboardShortcut as KeyboardManagerShortcut, 
  KeySequence, 
  KeyboardContext, 
  KeyboardEvent as KeyboardManagerEvent, 
  KeyboardEventHandler 
} from './KeyboardManager';
export type { 
  FocusableElement, 
  FocusState, 
  FocusEvent as FocusManagerEvent, 
  FocusEventHandler 
} from './FocusManager';
export type {
  DataTransformConfig,
  TransformRule,
  ValidationRule,
  TransformResult,
  DataFormat,
} from './DataTransformer';
export type {
  ErrorInfo,
  ErrorHandlerConfig,
  RecoveryStrategy,
} from './ErrorHandler';
export type {
  AutoRecoveryConfig,
  ConnectionHealth,
  RecoveryMetrics,
  ErrorLogEntry,
} from './AutoRecoveryManager';
export type {
  LoggerConfig,
  LogEntry,
  ErrorAggregation,
  PerformanceMetrics,
} from './ErrorLogger';
export type {
  SecurityPolicyConfig,
  CSPDirective,
  CSPPolicy,
  CORSConfig,
  HTTPSConfig,
  SecurityViolation,
  SecurityEventHandler,
} from './SecurityPolicyManager';
export type {
  EncryptionConfig,
  DesensitizationRule,
  DesensitizationConfig,
  EncryptedData,
  DesensitizedData,
  AuditLogEntry,
  AuditEventHandler,
} from './DataEncryption';
export type {
  SecurityAuditEvent,
  AuditLogConfig,
  AuditQuery,
  AuditSummary,
  AuditEventHandler as SecurityAuditEventHandler,
} from './SecurityAuditLogger';
export { IframeStatus, BridgeStatus, SyncStatus } from './types';

// Template Library and Version Manager
export { TemplateLibrary } from './TemplateLibrary';
export type {
  LabelConfig,
  TemplateConfig,
  TemplateCategory,
  TemplateLibraryConfig,
} from './TemplateLibrary';

export { VersionManager } from './VersionManager';
export type {
  LabelStudioVersion,
  VersionCompatibility,
  VersionManagerConfig,
  VersionCheckResult,
} from './VersionManager';
