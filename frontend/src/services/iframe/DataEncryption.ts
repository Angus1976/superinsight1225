/**
 * Data Encryption and Desensitization for iframe integration
 * Handles sensitive data encryption, decryption, and masking
 */

export interface EncryptionConfig {
  algorithm: 'AES-GCM' | 'AES-CBC';
  keyLength: 128 | 192 | 256;
  ivLength: number;
  tagLength?: number;
  enableCompression?: boolean;
}

export interface DesensitizationRule {
  field: string;
  type: 'mask' | 'hash' | 'remove' | 'replace';
  pattern?: RegExp;
  replacement?: string;
  preserveLength?: boolean;
  maskChar?: string;
  hashAlgorithm?: 'SHA-256' | 'SHA-512';
}

export interface DesensitizationConfig {
  rules: DesensitizationRule[];
  enableAuditLog: boolean;
  strictMode: boolean;
  whitelistedFields: string[];
}

export interface EncryptedData {
  data: string;
  iv: string;
  tag?: string;
  algorithm: string;
  timestamp: number;
  version: string;
}

export interface DesensitizedData {
  data: unknown;
  appliedRules: string[];
  timestamp: number;
  originalHash: string;
}

export interface AuditLogEntry {
  id: string;
  operation: 'encrypt' | 'decrypt' | 'desensitize' | 'restore';
  field?: string;
  rule?: string;
  timestamp: number;
  userId?: string;
  sessionId?: string;
  success: boolean;
  error?: string;
}

export type AuditEventHandler = (entry: AuditLogEntry) => void;

export class DataEncryption {
  private config: EncryptionConfig;
  private key: CryptoKey | null = null;
  private auditHandlers: AuditEventHandler[] = [];
  private auditLog: AuditLogEntry[] = [];

  constructor(config: EncryptionConfig) {
    this.config = config;
  }

  /**
   * Initialize encryption with key
   */
  public async initialize(keyMaterial: string | ArrayBuffer): Promise<void> {
    try {
      let keyData: ArrayBuffer;
      
      if (typeof keyMaterial === 'string') {
        keyData = new TextEncoder().encode(keyMaterial);
      } else {
        keyData = keyMaterial;
      }

      // Derive key using PBKDF2
      const baseKey = await crypto.subtle.importKey(
        'raw',
        keyData,
        'PBKDF2',
        false,
        ['deriveKey']
      );

      // Use a fixed salt for consistency (in production, use a proper salt)
      const salt = new TextEncoder().encode('iframe-encryption-salt');

      this.key = await crypto.subtle.deriveKey(
        {
          name: 'PBKDF2',
          salt: salt,
          iterations: 100000,
          hash: 'SHA-256',
        },
        baseKey,
        {
          name: this.config.algorithm,
          length: this.config.keyLength,
        },
        false,
        ['encrypt', 'decrypt']
      );
    } catch (error) {
      throw new Error(`Failed to initialize encryption: ${error}`);
    }
  }

  /**
   * Encrypt data
   */
  public async encrypt(data: unknown): Promise<EncryptedData> {
    if (!this.key) {
      throw new Error('Encryption not initialized');
    }

    const auditId = this.generateId();
    
    try {
      // Serialize data
      const plaintext = JSON.stringify(data);
      const plaintextBuffer = new TextEncoder().encode(plaintext);

      // Generate IV
      const iv = crypto.getRandomValues(new Uint8Array(this.config.ivLength));

      // Encrypt
      const encryptResult = await crypto.subtle.encrypt(
        {
          name: this.config.algorithm,
          iv: iv,
          ...(this.config.algorithm === 'AES-GCM' && this.config.tagLength ? 
            { tagLength: this.config.tagLength } : {}),
        },
        this.key,
        plaintextBuffer
      );

      let encryptedData: ArrayBuffer;
      let tag: string | undefined;

      if (this.config.algorithm === 'AES-GCM') {
        encryptedData = encryptResult;
      } else {
        encryptedData = encryptResult;
      }

      const result: EncryptedData = {
        data: this.arrayBufferToBase64(encryptedData),
        iv: this.arrayBufferToBase64(iv),
        algorithm: this.config.algorithm,
        timestamp: Date.now(),
        version: '1.0',
        ...(tag && { tag }),
      };

      this.logAudit({
        id: auditId,
        operation: 'encrypt',
        timestamp: Date.now(),
        success: true,
      });

      return result;
    } catch (error) {
      this.logAudit({
        id: auditId,
        operation: 'encrypt',
        timestamp: Date.now(),
        success: false,
        error: String(error),
      });
      throw new Error(`Encryption failed: ${error}`);
    }
  }

  /**
   * Decrypt data
   */
  public async decrypt(encryptedData: EncryptedData): Promise<unknown> {
    if (!this.key) {
      throw new Error('Encryption not initialized');
    }

    const auditId = this.generateId();

    try {
      const ciphertext = this.base64ToArrayBuffer(encryptedData.data);
      const iv = this.base64ToArrayBuffer(encryptedData.iv);

      const decryptResult = await crypto.subtle.decrypt(
        {
          name: encryptedData.algorithm,
          iv: iv,
          ...(encryptedData.algorithm === 'AES-GCM' && encryptedData.tag ? 
            { tag: this.base64ToArrayBuffer(encryptedData.tag) } : {}),
        },
        this.key,
        ciphertext
      );

      const plaintext = new TextDecoder().decode(decryptResult);
      const data = JSON.parse(plaintext);

      this.logAudit({
        id: auditId,
        operation: 'decrypt',
        timestamp: Date.now(),
        success: true,
      });

      return data;
    } catch (error) {
      this.logAudit({
        id: auditId,
        operation: 'decrypt',
        timestamp: Date.now(),
        success: false,
        error: String(error),
      });
      throw new Error(`Decryption failed: ${error}`);
    }
  }

  /**
   * Convert ArrayBuffer to Base64
   */
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Convert Base64 to ArrayBuffer
   */
  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Log audit entry
   */
  private logAudit(entry: AuditLogEntry): void {
    this.auditLog.push(entry);
    
    // Limit audit log size
    if (this.auditLog.length > 10000) {
      this.auditLog = this.auditLog.slice(-5000);
    }

    // Notify handlers
    this.auditHandlers.forEach(handler => {
      try {
        handler(entry);
      } catch (error) {
        console.error('Error in audit handler:', error);
      }
    });
  }

  /**
   * Add audit handler
   */
  public onAudit(handler: AuditEventHandler): () => void {
    this.auditHandlers.push(handler);
    
    return () => {
      const index = this.auditHandlers.indexOf(handler);
      if (index > -1) {
        this.auditHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Get audit log
   */
  public getAuditLog(operation?: AuditLogEntry['operation']): AuditLogEntry[] {
    if (operation) {
      return this.auditLog.filter(entry => entry.operation === operation);
    }
    return [...this.auditLog];
  }

  /**
   * Clear audit log
   */
  public clearAuditLog(): void {
    this.auditLog = [];
  }

  /**
   * Check if encryption is ready
   */
  public isReady(): boolean {
    return this.key !== null;
  }

  /**
   * Cleanup resources
   */
  public cleanup(): void {
    this.key = null;
    this.auditHandlers = [];
    this.auditLog = [];
  }
}

export class DataDesensitization {
  private config: DesensitizationConfig;
  private auditHandlers: AuditEventHandler[] = [];
  private auditLog: AuditLogEntry[] = [];

  constructor(config: DesensitizationConfig) {
    this.config = config;
  }

  /**
   * Desensitize data according to rules
   */
  public async desensitize(data: unknown): Promise<DesensitizedData> {
    const auditId = this.generateId();
    const appliedRules: string[] = [];

    try {
      // Create deep copy
      const sensitizedData = JSON.parse(JSON.stringify(data));
      const originalHash = await this.hashData(data);

      // Apply desensitization rules
      for (const rule of this.config.rules) {
        if (this.shouldApplyRule(sensitizedData, rule)) {
          await this.applyRule(sensitizedData, rule);
          appliedRules.push(rule.field);
          
          if (this.config.enableAuditLog) {
            this.logAudit({
              id: this.generateId(),
              operation: 'desensitize',
              field: rule.field,
              rule: rule.type,
              timestamp: Date.now(),
              success: true,
            });
          }
        }
      }

      const result: DesensitizedData = {
        data: sensitizedData,
        appliedRules,
        timestamp: Date.now(),
        originalHash,
      };

      this.logAudit({
        id: auditId,
        operation: 'desensitize',
        timestamp: Date.now(),
        success: true,
      });

      return result;
    } catch (error) {
      this.logAudit({
        id: auditId,
        operation: 'desensitize',
        timestamp: Date.now(),
        success: false,
        error: String(error),
      });
      throw new Error(`Desensitization failed: ${error}`);
    }
  }

  /**
   * Check if rule should be applied
   */
  private shouldApplyRule(data: unknown, rule: DesensitizationRule): boolean {
    // Check if field is whitelisted
    if (this.config.whitelistedFields.includes(rule.field)) {
      return false;
    }

    // Check if field exists in data
    if (!this.hasField(data, rule.field)) {
      return false;
    }

    // For mask rules with patterns, check if the pattern matches
    if (rule.type === 'mask' && rule.pattern) {
      const value = this.getFieldValue(data, rule.field);
      if (value !== undefined && value !== null) {
        return rule.pattern.test(String(value));
      }
    }

    return true;
  }

  /**
   * Apply desensitization rule
   */
  private async applyRule(data: unknown, rule: DesensitizationRule): Promise<void> {
    const value = this.getFieldValue(data, rule.field);
    
    if (value === undefined || value === null) {
      return;
    }

    let newValue: unknown;

    switch (rule.type) {
      case 'mask':
        newValue = this.maskValue(String(value), rule);
        break;
      case 'hash':
        newValue = await this.hashValue(String(value), rule.hashAlgorithm || 'SHA-256');
        break;
      case 'remove':
        this.removeField(data, rule.field);
        return;
      case 'replace':
        newValue = rule.replacement || '[REDACTED]';
        break;
      default:
        throw new Error(`Unknown desensitization type: ${rule.type}`);
    }

    this.setFieldValue(data, rule.field, newValue);
  }

  /**
   * Mask value
   */
  private maskValue(value: string, rule: DesensitizationRule): string {
    const maskChar = rule.maskChar || '*';
    
    if (rule.pattern && rule.replacement) {
      return value.replace(rule.pattern, rule.replacement);
    }
    
    if (rule.pattern) {
      return value.replace(rule.pattern, (match) => {
        return rule.preserveLength ? maskChar.repeat(match.length) : maskChar;
      });
    }
    
    // Default masking: show first and last character
    if (value.length <= 2) {
      return maskChar.repeat(value.length);
    }
    
    const start = value.charAt(0);
    const end = value.charAt(value.length - 1);
    const middle = maskChar.repeat(value.length - 2);
    
    return start + middle + end;
  }

  /**
   * Hash value
   */
  private async hashValue(value: string, algorithm: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(value);
    const hashBuffer = await crypto.subtle.digest(algorithm, data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Hash entire data object
   */
  private async hashData(data: unknown): Promise<string> {
    const serialized = JSON.stringify(data);
    return this.hashValue(serialized, 'SHA-256');
  }

  /**
   * Check if object has field (supports nested paths)
   */
  private hasField(obj: unknown, field: string): boolean {
    const parts = field.split('.');
    let current = obj;
    
    for (const part of parts) {
      if (current === null || current === undefined || typeof current !== 'object') {
        return false;
      }
      
      if (!(part in (current as Record<string, unknown>))) {
        return false;
      }
      
      current = (current as Record<string, unknown>)[part];
    }
    
    return true;
  }

  /**
   * Get field value (supports nested paths)
   */
  private getFieldValue(obj: unknown, field: string): unknown {
    const parts = field.split('.');
    let current = obj;
    
    for (const part of parts) {
      if (current === null || current === undefined || typeof current !== 'object') {
        return undefined;
      }
      
      current = (current as Record<string, unknown>)[part];
    }
    
    return current;
  }

  /**
   * Set field value (supports nested paths)
   */
  private setFieldValue(obj: unknown, field: string, value: unknown): void {
    const parts = field.split('.');
    let current = obj as Record<string, unknown>;
    
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      
      if (!(part in current) || typeof current[part] !== 'object') {
        current[part] = {};
      }
      
      current = current[part] as Record<string, unknown>;
    }
    
    current[parts[parts.length - 1]] = value;
  }

  /**
   * Remove field (supports nested paths)
   */
  private removeField(obj: unknown, field: string): void {
    const parts = field.split('.');
    let current = obj as Record<string, unknown>;
    
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      
      if (!(part in current) || typeof current[part] !== 'object') {
        return;
      }
      
      current = current[part] as Record<string, unknown>;
    }
    
    delete current[parts[parts.length - 1]];
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Log audit entry
   */
  private logAudit(entry: AuditLogEntry): void {
    this.auditLog.push(entry);
    
    // Limit audit log size
    if (this.auditLog.length > 10000) {
      this.auditLog = this.auditLog.slice(-5000);
    }

    // Notify handlers
    this.auditHandlers.forEach(handler => {
      try {
        handler(entry);
      } catch (error) {
        console.error('Error in audit handler:', error);
      }
    });
  }

  /**
   * Add audit handler
   */
  public onAudit(handler: AuditEventHandler): () => void {
    this.auditHandlers.push(handler);
    
    return () => {
      const index = this.auditHandlers.indexOf(handler);
      if (index > -1) {
        this.auditHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Get audit log
   */
  public getAuditLog(field?: string): AuditLogEntry[] {
    if (field) {
      return this.auditLog.filter(entry => entry.field === field);
    }
    return [...this.auditLog];
  }

  /**
   * Clear audit log
   */
  public clearAuditLog(): void {
    this.auditLog = [];
  }

  /**
   * Update configuration
   */
  public updateConfig(config: Partial<DesensitizationConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  public getConfig(): DesensitizationConfig {
    return { ...this.config };
  }

  /**
   * Cleanup resources
   */
  public cleanup(): void {
    this.auditHandlers = [];
    this.auditLog = [];
  }
}

/**
 * Create default desensitization configuration
 */
export function createDefaultDesensitizationConfig(): DesensitizationConfig {
  return {
    rules: [
      {
        field: 'email',
        type: 'mask',
        pattern: /(.{2}).*(@.*)$/,
        replacement: '$1***$2',
      },
      {
        field: 'phone',
        type: 'mask',
        pattern: /(\d{3})\d{4}(\d{3})/,
        replacement: '$1****$2',
      },
      {
        field: 'ssn',
        type: 'mask',
        pattern: /(\d{3})-\d{2}-(\d{4})/,
        replacement: '$1-**-$2',
      },
      {
        field: 'creditCard',
        type: 'mask',
        pattern: /(\d{4})\d{8}(\d{4})/,
        replacement: '$1********$2',
      },
      {
        field: 'password',
        type: 'remove',
      },
      {
        field: 'token',
        type: 'hash',
        hashAlgorithm: 'SHA-256',
      },
    ],
    enableAuditLog: true,
    strictMode: false,
    whitelistedFields: ['id', 'timestamp', 'version'],
  };
}