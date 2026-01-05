/**
 * SyncManager - 数据同步管理器
 * 
 * 实现标注数据的增量同步、全量同步、冲突检测和离线缓存功能
 */

import {
  AnnotationData,
  SyncOperation,
  SyncConflict,
  SyncManagerConfig,
  SyncStatus,
  SyncStats,
  SyncEventCallback,
  SyncEvent,
} from './types';

export class SyncManager {
  private config: Required<SyncManagerConfig>;
  private status: SyncStatus = SyncStatus.IDLE;
  private operations: Map<string, SyncOperation> = new Map();
  private conflicts: Map<string, SyncConflict> = new Map();
  private cache: Map<string, AnnotationData> = new Map();
  private eventListeners: Set<SyncEventCallback> = new Set();
  private syncTimer: NodeJS.Timeout | null = null;
  private stats: SyncStats = {
    totalOperations: 0,
    completedOperations: 0,
    failedOperations: 0,
    conflictsResolved: 0,
    lastSyncTime: 0,
    syncDuration: 0,
  };

  constructor(config: SyncManagerConfig = {}) {
    this.config = {
      enableIncrementalSync: config.enableIncrementalSync ?? true,
      syncInterval: config.syncInterval ?? 30000, // 30 seconds
      maxRetries: config.maxRetries ?? 3,
      conflictResolution: config.conflictResolution ?? 'manual',
      enableOfflineCache: config.enableOfflineCache ?? true,
      cacheSize: config.cacheSize ?? 1000,
    };

    this.initializeSync();
    this.setupNetworkMonitoring();
  }

  /**
   * 初始化同步机制
   */
  private initializeSync(): void {
    if (this.config.enableIncrementalSync) {
      this.startPeriodicSync();
    }

    // 从本地存储恢复数据
    this.restoreFromLocalStorage();

    // 监听页面可见性变化
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden && this.status === SyncStatus.OFFLINE) {
          this.resumeSync();
        }
      });

      // 监听页面卸载，保存数据到本地存储
      window.addEventListener('beforeunload', () => {
        this.saveToLocalStorage();
      });
    }

    console.log('SyncManager initialized with config:', this.config);
  }

  /**
   * 设置网络监控
   */
  private setupNetworkMonitoring(): void {
    if (typeof navigator !== 'undefined' && 'onLine' in navigator) {
      window.addEventListener('online', () => {
        console.log('Network connection restored');
        this.resumeSync();
      });

      window.addEventListener('offline', () => {
        console.log('Network connection lost');
        this.handleOfflineMode();
      });
    }
  }

  /**
   * 开始周期性同步
   */
  private startPeriodicSync(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
    }

    this.syncTimer = setInterval(() => {
      if (this.status === SyncStatus.IDLE && this.operations.size > 0) {
        this.performIncrementalSync();
      }
    }, this.config.syncInterval);
  }

  /**
   * 停止周期性同步
   */
  private stopPeriodicSync(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }

  /**
   * 添加同步操作
   */
  public addOperation(type: 'create' | 'update' | 'delete', data: AnnotationData): string {
    const operation: SyncOperation = {
      id: this.generateOperationId(),
      type,
      data,
      timestamp: Date.now(),
      retryCount: 0,
      status: 'pending',
    };

    this.operations.set(operation.id, operation);
    this.stats.totalOperations++;

    // 如果启用了离线缓存，将数据缓存到本地
    if (this.config.enableOfflineCache) {
      this.cacheData(data);
    }

    console.log(`Added ${type} operation for annotation ${data.id}`);
    return operation.id;
  }

  /**
   * 执行增量同步
   */
  public async performIncrementalSync(): Promise<void> {
    if (this.status === SyncStatus.SYNCING) {
      console.log('Sync already in progress, skipping');
      return;
    }

    this.setStatus(SyncStatus.SYNCING);
    this.emitEvent({ type: 'sync_start', timestamp: Date.now() });

    const startTime = Date.now();
    const pendingOperations = Array.from(this.operations.values())
      .filter(op => op.status === 'pending' || op.status === 'failed');

    try {
      for (const operation of pendingOperations) {
        await this.syncOperation(operation);
      }

      this.stats.lastSyncTime = Date.now();
      this.stats.syncDuration = Date.now() - startTime;
      
      this.setStatus(SyncStatus.IDLE);
      this.emitEvent({ 
        type: 'sync_complete', 
        timestamp: Date.now(),
        data: { duration: this.stats.syncDuration, operations: pendingOperations.length }
      });

      console.log(`Incremental sync completed in ${this.stats.syncDuration}ms`);
    } catch (error) {
      this.setStatus(SyncStatus.ERROR);
      this.emitEvent({ 
        type: 'sync_error', 
        timestamp: Date.now(),
        data: { error: error instanceof Error ? error.message : 'Unknown error' }
      });
      console.error('Incremental sync failed:', error);
    }
  }

  /**
   * 执行全量同步
   */
  public async performFullSync(): Promise<void> {
    if (this.status === SyncStatus.SYNCING) {
      throw new Error('Sync already in progress');
    }

    this.setStatus(SyncStatus.SYNCING);
    this.emitEvent({ type: 'sync_start', timestamp: Date.now() });

    const startTime = Date.now();

    try {
      // 获取所有远程数据
      const remoteData = await this.fetchRemoteData();
      
      // 检测冲突
      const conflicts = this.detectConflicts(remoteData);
      
      if (conflicts.length > 0) {
        await this.handleConflicts(conflicts);
      }

      // 同步所有操作
      const allOperations = Array.from(this.operations.values());
      for (const operation of allOperations) {
        await this.syncOperation(operation);
      }

      this.stats.lastSyncTime = Date.now();
      this.stats.syncDuration = Date.now() - startTime;
      
      this.setStatus(SyncStatus.IDLE);
      this.emitEvent({ 
        type: 'sync_complete', 
        timestamp: Date.now(),
        data: { duration: this.stats.syncDuration, operations: allOperations.length }
      });

      console.log(`Full sync completed in ${this.stats.syncDuration}ms`);
    } catch (error) {
      this.setStatus(SyncStatus.ERROR);
      this.emitEvent({ 
        type: 'sync_error', 
        timestamp: Date.now(),
        data: { error: error instanceof Error ? error.message : 'Unknown error' }
      });
      console.error('Full sync failed:', error);
      throw error;
    }
  }

  /**
   * 同步单个操作
   */
  private async syncOperation(operation: SyncOperation): Promise<void> {
    operation.status = 'syncing';

    try {
      // 模拟 API 调用
      await this.simulateApiCall(operation);
      
      operation.status = 'completed';
      this.stats.completedOperations++;
      
      // 从操作队列中移除已完成的操作
      this.operations.delete(operation.id);
      
      console.log(`Operation ${operation.id} completed successfully`);
    } catch (error) {
      operation.retryCount++;
      
      if (operation.retryCount >= this.config.maxRetries) {
        operation.status = 'failed';
        this.stats.failedOperations++;
        console.error(`Operation ${operation.id} failed after ${operation.retryCount} retries:`, error);
      } else {
        operation.status = 'pending';
        console.warn(`Operation ${operation.id} failed, will retry (${operation.retryCount}/${this.config.maxRetries})`);
      }
      
      throw error;
    }
  }

  /**
   * 模拟 API 调用
   */
  private async simulateApiCall(operation: SyncOperation): Promise<void> {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));
    
    // 模拟随机失败（10% 概率）
    if (Math.random() < 0.1) {
      throw new Error(`Simulated API error for operation ${operation.id}`);
    }
    
    console.log(`API call successful for ${operation.type} operation on ${operation.data.id}`);
  }

  /**
   * 获取远程数据
   */
  private async fetchRemoteData(): Promise<AnnotationData[]> {
    // 模拟获取远程数据
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 返回模拟数据
    return Array.from(this.cache.values()).map(data => ({
      ...data,
      version: data.version + 1, // 模拟版本变更
    }));
  }

  /**
   * 检测冲突
   */
  public detectConflicts(remoteData: AnnotationData[]): SyncConflict[] {
    const conflicts: SyncConflict[] = [];
    
    for (const remoteItem of remoteData) {
      const localItem = this.cache.get(remoteItem.id);
      
      if (localItem && localItem.version !== remoteItem.version) {
        const conflict: SyncConflict = {
          id: this.generateConflictId(),
          localData: localItem,
          remoteData: remoteItem,
          conflictType: localItem.timestamp > remoteItem.timestamp ? 'concurrent' : 'version',
          timestamp: Date.now(),
          resolved: false,
        };
        
        conflicts.push(conflict);
        this.conflicts.set(conflict.id, conflict);
      }
    }
    
    if (conflicts.length > 0) {
      this.emitEvent({
        type: 'conflict_detected',
        timestamp: Date.now(),
        data: { conflicts: conflicts.length }
      });
    }
    
    return conflicts;
  }

  /**
   * 处理冲突
   */
  private async handleConflicts(conflicts: SyncConflict[]): Promise<void> {
    for (const conflict of conflicts) {
      switch (this.config.conflictResolution) {
        case 'local':
          await this.resolveConflictWithLocal(conflict);
          break;
        case 'remote':
          await this.resolveConflictWithRemote(conflict);
          break;
        case 'manual':
          // 手动解决冲突需要外部处理
          console.log(`Manual conflict resolution required for ${conflict.id}`);
          break;
      }
    }
  }

  /**
   * 使用本地数据解决冲突
   */
  private async resolveConflictWithLocal(conflict: SyncConflict): Promise<void> {
    // 使用本地数据覆盖远程数据
    conflict.resolved = true;
    this.stats.conflictsResolved++;
    
    console.log(`Conflict ${conflict.id} resolved with local data`);
  }

  /**
   * 使用远程数据解决冲突
   */
  private async resolveConflictWithRemote(conflict: SyncConflict): Promise<void> {
    // 使用远程数据覆盖本地数据
    this.cache.set(conflict.remoteData.id, conflict.remoteData);
    conflict.resolved = true;
    this.stats.conflictsResolved++;
    
    console.log(`Conflict ${conflict.id} resolved with remote data`);
  }

  /**
   * 手动解决冲突
   */
  public async resolveConflictManually(conflictId: string, resolution: 'local' | 'remote' | 'merge', mergedData?: AnnotationData): Promise<void> {
    const conflict = this.conflicts.get(conflictId);
    if (!conflict) {
      throw new Error(`Conflict ${conflictId} not found`);
    }

    switch (resolution) {
      case 'local':
        await this.resolveConflictWithLocal(conflict);
        break;
      case 'remote':
        await this.resolveConflictWithRemote(conflict);
        break;
      case 'merge':
        if (!mergedData) {
          throw new Error('Merged data is required for merge resolution');
        }
        this.cache.set(mergedData.id, mergedData);
        conflict.resolved = true;
        this.stats.conflictsResolved++;
        console.log(`Conflict ${conflict.id} resolved with merged data`);
        break;
    }

    this.conflicts.delete(conflictId);
  }

  /**
   * 缓存数据
   */
  private cacheData(data: AnnotationData): void {
    // 检查缓存大小限制
    if (this.cache.size >= this.config.cacheSize) {
      // 删除最旧的数据
      const oldestKey = Array.from(this.cache.keys())[0];
      this.cache.delete(oldestKey);
    }
    
    this.cache.set(data.id, { ...data });
    console.log(`Data cached for annotation ${data.id}`);
  }

  /**
   * 处理离线模式
   */
  private handleOfflineMode(): void {
    this.setStatus(SyncStatus.OFFLINE);
    this.stopPeriodicSync();
    
    this.emitEvent({
      type: 'offline_mode',
      timestamp: Date.now(),
    });
    
    console.log('Entered offline mode');
  }

  /**
   * 恢复同步
   */
  private async resumeSync(): Promise<void> {
    if (this.status === SyncStatus.OFFLINE) {
      this.setStatus(SyncStatus.IDLE);
      this.startPeriodicSync();
      
      // 执行网络恢复处理
      await this.handleNetworkRecovery();
      
      console.log('Resumed sync after network recovery');
    }
  }

  /**
   * 设置状态
   */
  private setStatus(status: SyncStatus): void {
    this.status = status;
    console.log(`SyncManager status changed to: ${status}`);
  }

  /**
   * 发射事件
   */
  private emitEvent(event: SyncEvent): void {
    this.eventListeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('Error in sync event listener:', error);
      }
    });
  }

  /**
   * 生成操作 ID
   */
  private generateOperationId(): string {
    return `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 生成冲突 ID
   */
  private generateConflictId(): string {
    return `conflict_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Public API methods

  /**
   * 添加事件监听器
   */
  public addEventListener(listener: SyncEventCallback): void {
    this.eventListeners.add(listener);
  }

  /**
   * 移除事件监听器
   */
  public removeEventListener(listener: SyncEventCallback): void {
    this.eventListeners.delete(listener);
  }

  /**
   * 获取同步状态
   */
  public getStatus(): SyncStatus {
    return this.status;
  }

  /**
   * 获取同步统计
   */
  public getStats(): SyncStats {
    return { ...this.stats };
  }

  /**
   * 获取待处理操作数量
   */
  public getPendingOperationsCount(): number {
    return Array.from(this.operations.values())
      .filter(op => op.status === 'pending' || op.status === 'failed').length;
  }

  /**
   * 获取冲突列表
   */
  public getConflicts(): SyncConflict[] {
    return Array.from(this.conflicts.values());
  }

  /**
   * 获取缓存数据
   */
  public getCachedData(id?: string): AnnotationData | AnnotationData[] | null {
    if (id) {
      return this.cache.get(id) || null;
    }
    return Array.from(this.cache.values());
  }

  /**
   * 清理缓存
   */
  public clearCache(): void {
    this.cache.clear();
    console.log('Cache cleared');
  }

  /**
   * 强制同步
   */
  public async forceSync(): Promise<void> {
    await this.performIncrementalSync();
  }

  /**
   * 销毁同步管理器
   */
  public destroy(): void {
    // 保存数据到本地存储
    this.saveToLocalStorage();
    
    this.stopPeriodicSync();
    this.operations.clear();
    this.conflicts.clear();
    this.cache.clear();
    this.eventListeners.clear();
    this.setStatus(SyncStatus.IDLE);
    
    console.log('SyncManager destroyed');
  }

  /**
   * 保存数据到本地存储
   */
  private saveToLocalStorage(): void {
    if (!this.config.enableOfflineCache || typeof localStorage === 'undefined') {
      return;
    }

    try {
      const dataToSave = {
        operations: Array.from(this.operations.entries()),
        cache: Array.from(this.cache.entries()),
        conflicts: Array.from(this.conflicts.entries()),
        stats: this.stats,
        timestamp: Date.now(),
      };

      localStorage.setItem('syncManager_data', JSON.stringify(dataToSave));
      console.log('Data saved to localStorage');
    } catch (error) {
      console.error('Failed to save data to localStorage:', error);
    }
  }

  /**
   * 从本地存储恢复数据
   */
  private restoreFromLocalStorage(): void {
    if (!this.config.enableOfflineCache || typeof localStorage === 'undefined') {
      return;
    }

    try {
      const savedData = localStorage.getItem('syncManager_data');
      if (!savedData) {
        return;
      }

      const data = JSON.parse(savedData);
      
      // 检查数据是否过期（24小时）
      const maxAge = 24 * 60 * 60 * 1000; // 24 hours
      if (Date.now() - data.timestamp > maxAge) {
        localStorage.removeItem('syncManager_data');
        console.log('Expired data removed from localStorage');
        return;
      }

      // 恢复操作
      this.operations = new Map(data.operations || []);
      
      // 恢复缓存
      this.cache = new Map(data.cache || []);
      
      // 恢复冲突
      this.conflicts = new Map(data.conflicts || []);
      
      // 恢复统计
      if (data.stats) {
        this.stats = { ...this.stats, ...data.stats };
      }

      console.log(`Restored ${this.operations.size} operations, ${this.cache.size} cached items, and ${this.conflicts.size} conflicts from localStorage`);
    } catch (error) {
      console.error('Failed to restore data from localStorage:', error);
      // 清除损坏的数据
      localStorage.removeItem('syncManager_data');
    }
  }

  /**
   * 清理本地存储
   */
  public clearLocalStorage(): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('syncManager_data');
      console.log('Local storage cleared');
    }
  }

  /**
   * 获取本地存储大小
   */
  public getLocalStorageSize(): number {
    if (typeof localStorage === 'undefined') {
      return 0;
    }

    try {
      const data = localStorage.getItem('syncManager_data');
      return data ? new Blob([data]).size : 0;
    } catch (error) {
      console.error('Failed to get localStorage size:', error);
      return 0;
    }
  }

  /**
   * 网络恢复后的同步处理
   */
  private async handleNetworkRecovery(): Promise<void> {
    console.log('Handling network recovery...');
    
    // 检查是否有待处理的操作
    const pendingOperations = Array.from(this.operations.values())
      .filter(op => op.status === 'pending' || op.status === 'failed');

    if (pendingOperations.length > 0) {
      console.log(`Found ${pendingOperations.length} pending operations, starting recovery sync`);
      
      // 重置失败操作的重试计数
      pendingOperations.forEach(op => {
        if (op.status === 'failed') {
          op.status = 'pending';
          op.retryCount = 0;
        }
      });

      // 执行恢复同步
      await this.performIncrementalSync();
    }

    // 检查是否有未解决的冲突
    const unresolvedConflicts = Array.from(this.conflicts.values())
      .filter(conflict => !conflict.resolved);

    if (unresolvedConflicts.length > 0) {
      console.log(`Found ${unresolvedConflicts.length} unresolved conflicts`);
      this.emitEvent({
        type: 'conflict_detected',
        timestamp: Date.now(),
        data: { conflicts: unresolvedConflicts.length, recovery: true }
      });
    }
  }
}