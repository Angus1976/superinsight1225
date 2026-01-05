/**
 * Tests for DataEncryption and DataDesensitization
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  DataEncryption,
  DataDesensitization,
  createDefaultDesensitizationConfig,
  type EncryptionConfig,
  type DesensitizationConfig,
  type AuditLogEntry,
} from './DataEncryption';

// Mock Web Crypto API
const mockCrypto = {
  subtle: {
    importKey: vi.fn(),
    deriveKey: vi.fn(),
    encrypt: vi.fn(),
    decrypt: vi.fn(),
    digest: vi.fn(),
  },
  getRandomValues: vi.fn(),
};

Object.defineProperty(global, 'crypto', {
  value: mockCrypto,
  writable: true,
});

// Mock TextEncoder/TextDecoder
global.TextEncoder = class {
  encode(input: string): Uint8Array {
    return new Uint8Array(Array.from(input).map(char => char.charCodeAt(0)));
  }
};

global.TextDecoder = class {
  decode(input: ArrayBuffer): string {
    return String.fromCharCode(...new Uint8Array(input));
  }
};

// Mock btoa/atob
global.btoa = (str: string) => Buffer.from(str, 'binary').toString('base64');
global.atob = (str: string) => Buffer.from(str, 'base64').toString('binary');

describe('DataEncryption', () => {
  let encryption: DataEncryption;
  let config: EncryptionConfig;
  let auditEntries: AuditLogEntry[];

  beforeEach(() => {
    config = {
      algorithm: 'AES-GCM',
      keyLength: 256,
      ivLength: 12,
      tagLength: 128,
    };
    
    encryption = new DataEncryption(config);
    auditEntries = [];
    
    // Setup audit handler
    encryption.onAudit((entry) => {
      auditEntries.push(entry);
    });

    // Reset mocks
    vi.clearAllMocks();
    
    // Setup crypto mocks
    mockCrypto.getRandomValues.mockImplementation((array: Uint8Array) => {
      for (let i = 0; i < array.length; i++) {
        array[i] = Math.floor(Math.random() * 256);
      }
      return array;
    });
  });

  afterEach(() => {
    encryption.cleanup();
  });

  describe('initialization', () => {
    it('should initialize with string key material', async () => {
      const mockKey = { type: 'secret' };
      
      mockCrypto.subtle.importKey.mockResolvedValue(mockKey);
      mockCrypto.subtle.deriveKey.mockResolvedValue(mockKey);
      
      await encryption.initialize('test-key-material');
      
      expect(encryption.isReady()).toBe(true);
      expect(mockCrypto.subtle.importKey).toHaveBeenCalledWith(
        'raw',
        expect.any(Uint8Array),
        'PBKDF2',
        false,
        ['deriveKey']
      );
    });

    it('should initialize with ArrayBuffer key material', async () => {
      const mockKey = { type: 'secret' };
      const keyBuffer = new ArrayBuffer(32);
      
      mockCrypto.subtle.importKey.mockResolvedValue(mockKey);
      mockCrypto.subtle.deriveKey.mockResolvedValue(mockKey);
      
      await encryption.initialize(keyBuffer);
      
      expect(encryption.isReady()).toBe(true);
    });

    it('should handle initialization errors', async () => {
      mockCrypto.subtle.importKey.mockRejectedValue(new Error('Crypto error'));
      
      await expect(encryption.initialize('test-key')).rejects.toThrow(
        'Failed to initialize encryption'
      );
    });
  });

  describe('encryption', () => {
    beforeEach(async () => {
      const mockKey = { type: 'secret' };
      mockCrypto.subtle.importKey.mockResolvedValue(mockKey);
      mockCrypto.subtle.deriveKey.mockResolvedValue(mockKey);
      await encryption.initialize('test-key');
    });

    it('should encrypt data successfully', async () => {
      const testData = { message: 'secret data', id: 123 };
      const mockEncryptedBuffer = new ArrayBuffer(16);
      
      mockCrypto.subtle.encrypt.mockResolvedValue(mockEncryptedBuffer);
      
      const result = await encryption.encrypt(testData);
      
      expect(result).toHaveProperty('data');
      expect(result).toHaveProperty('iv');
      expect(result).toHaveProperty('algorithm', 'AES-GCM');
      expect(result).toHaveProperty('timestamp');
      expect(result).toHaveProperty('version', '1.0');
      
      // Should log audit entry
      expect(auditEntries).toHaveLength(1);
      expect(auditEntries[0].operation).toBe('encrypt');
      expect(auditEntries[0].success).toBe(true);
    });

    it('should handle encryption errors', async () => {
      const testData = { message: 'test' };
      
      mockCrypto.subtle.encrypt.mockRejectedValue(new Error('Encryption failed'));
      
      await expect(encryption.encrypt(testData)).rejects.toThrow('Encryption failed');
      
      // Should log failed audit entry
      expect(auditEntries).toHaveLength(1);
      expect(auditEntries[0].success).toBe(false);
    });

    it('should require initialization', async () => {
      const uninitializedEncryption = new DataEncryption(config);
      
      await expect(uninitializedEncryption.encrypt({ test: 'data' })).rejects.toThrow(
        'Encryption not initialized'
      );
    });
  });

  describe('decryption', () => {
    beforeEach(async () => {
      const mockKey = { type: 'secret' };
      mockCrypto.subtle.importKey.mockResolvedValue(mockKey);
      mockCrypto.subtle.deriveKey.mockResolvedValue(mockKey);
      await encryption.initialize('test-key');
    });

    it('should decrypt data successfully', async () => {
      const encryptedData = {
        data: 'encrypted-base64-data',
        iv: 'iv-base64-data',
        algorithm: 'AES-GCM',
        timestamp: Date.now(),
        version: '1.0',
      };
      
      const originalData = { message: 'secret data', id: 123 };
      const mockDecryptedBuffer = new TextEncoder().encode(JSON.stringify(originalData));
      
      mockCrypto.subtle.decrypt.mockResolvedValue(mockDecryptedBuffer.buffer);
      
      const result = await encryption.decrypt(encryptedData);
      
      expect(result).toEqual(originalData);
      
      // Should log audit entry
      expect(auditEntries).toHaveLength(1);
      expect(auditEntries[0].operation).toBe('decrypt');
      expect(auditEntries[0].success).toBe(true);
    });

    it('should handle decryption errors', async () => {
      const encryptedData = {
        data: 'invalid-data',
        iv: 'invalid-iv',
        algorithm: 'AES-GCM',
        timestamp: Date.now(),
        version: '1.0',
      };
      
      mockCrypto.subtle.decrypt.mockRejectedValue(new Error('Decryption failed'));
      
      await expect(encryption.decrypt(encryptedData)).rejects.toThrow('Decryption failed');
      
      // Should log failed audit entry
      expect(auditEntries).toHaveLength(1);
      expect(auditEntries[0].success).toBe(false);
    });

    it('should require initialization', async () => {
      const uninitializedEncryption = new DataEncryption(config);
      const encryptedData = {
        data: 'test',
        iv: 'test',
        algorithm: 'AES-GCM',
        timestamp: Date.now(),
        version: '1.0',
      };
      
      await expect(uninitializedEncryption.decrypt(encryptedData)).rejects.toThrow(
        'Encryption not initialized'
      );
    });
  });

  describe('audit logging', () => {
    beforeEach(async () => {
      const mockKey = { type: 'secret' };
      mockCrypto.subtle.importKey.mockResolvedValue(mockKey);
      mockCrypto.subtle.deriveKey.mockResolvedValue(mockKey);
      await encryption.initialize('test-key');
    });

    it('should track audit entries', async () => {
      mockCrypto.subtle.encrypt.mockResolvedValue(new ArrayBuffer(16));
      
      await encryption.encrypt({ test: 'data' });
      
      const auditLog = encryption.getAuditLog();
      expect(auditLog).toHaveLength(1);
      expect(auditLog[0].operation).toBe('encrypt');
    });

    it('should filter audit entries by operation', async () => {
      mockCrypto.subtle.encrypt.mockResolvedValue(new ArrayBuffer(16));
      mockCrypto.subtle.decrypt.mockResolvedValue(new TextEncoder().encode('{"test":"data"}').buffer);
      
      await encryption.encrypt({ test: 'data' });
      await encryption.decrypt({
        data: 'test',
        iv: 'test',
        algorithm: 'AES-GCM',
        timestamp: Date.now(),
        version: '1.0',
      });
      
      const encryptLog = encryption.getAuditLog('encrypt');
      const decryptLog = encryption.getAuditLog('decrypt');
      
      expect(encryptLog).toHaveLength(1);
      expect(decryptLog).toHaveLength(1);
    });

    it('should clear audit log', () => {
      auditEntries.push({
        id: 'test',
        operation: 'encrypt',
        timestamp: Date.now(),
        success: true,
      });
      
      encryption.clearAuditLog();
      
      const auditLog = encryption.getAuditLog();
      expect(auditLog).toHaveLength(0);
    });

    it('should remove audit handlers', async () => {
      const handler = vi.fn();
      const removeHandler = encryption.onAudit(handler);
      
      mockCrypto.subtle.encrypt.mockResolvedValue(new ArrayBuffer(16));
      await encryption.encrypt({ test: 'data' });
      
      expect(handler).toHaveBeenCalledTimes(1);
      
      removeHandler();
      await encryption.encrypt({ test: 'data2' });
      
      expect(handler).toHaveBeenCalledTimes(1); // Should not be called again
    });
  });
});

describe('DataDesensitization', () => {
  let desensitization: DataDesensitization;
  let config: DesensitizationConfig;
  let auditEntries: AuditLogEntry[];

  beforeEach(() => {
    config = createDefaultDesensitizationConfig();
    desensitization = new DataDesensitization(config);
    auditEntries = [];
    
    // Setup audit handler
    desensitization.onAudit((entry) => {
      auditEntries.push(entry);
    });

    // Mock crypto.subtle.digest for hashing
    mockCrypto.subtle.digest.mockImplementation(async (algorithm: string, data: ArrayBuffer) => {
      // Simple mock hash
      const input = new Uint8Array(data);
      const hash = new ArrayBuffer(32);
      const hashView = new Uint8Array(hash);
      for (let i = 0; i < 32; i++) {
        hashView[i] = (input[i % input.length] + i) % 256;
      }
      return hash;
    });
  });

  afterEach(() => {
    desensitization.cleanup();
  });

  describe('email desensitization', () => {
    it('should mask email addresses', async () => {
      const data = { email: 'user@example.com' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toHaveProperty('email');
      expect((result.data as any).email).toMatch(/us\*\*\*@example\.com/);
      expect(result.appliedRules).toContain('email');
    });

    it('should handle short email addresses', async () => {
      const data = { email: 'a@b.c' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toHaveProperty('email');
      // Short email that doesn't match the pattern should remain unchanged
      expect((result.data as any).email).toBe('a@b.c');
      expect(result.appliedRules).not.toContain('email');
    });
  });

  describe('phone desensitization', () => {
    it('should mask phone numbers', async () => {
      const data = { phone: '1234567890' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toHaveProperty('phone');
      expect((result.data as any).phone).toBe('123****890');
      expect(result.appliedRules).toContain('phone');
    });
  });

  describe('SSN desensitization', () => {
    it('should mask SSN', async () => {
      const data = { ssn: '123-45-6789' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toHaveProperty('ssn');
      expect((result.data as any).ssn).toBe('123-**-6789');
      expect(result.appliedRules).toContain('ssn');
    });
  });

  describe('credit card desensitization', () => {
    it('should mask credit card numbers', async () => {
      const data = { creditCard: '1234567890123456' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toHaveProperty('creditCard');
      expect((result.data as any).creditCard).toBe('1234********3456');
      expect(result.appliedRules).toContain('creditCard');
    });
  });

  describe('password removal', () => {
    it('should remove password fields', async () => {
      const data = { password: 'secret123', username: 'user' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).not.toHaveProperty('password');
      expect(result.data).toHaveProperty('username', 'user');
      expect(result.appliedRules).toContain('password');
    });
  });

  describe('token hashing', () => {
    it('should hash token values', async () => {
      const data = { token: 'secret-token-123' };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toHaveProperty('token');
      expect((result.data as any).token).not.toBe('secret-token-123');
      expect((result.data as any).token).toMatch(/^[a-f0-9]{64}$/); // SHA-256 hex
      expect(result.appliedRules).toContain('token');
    });
  });

  describe('nested field handling', () => {
    it('should handle nested fields', async () => {
      // Add nested field rule
      config.rules.push({
        field: 'user.email',
        type: 'mask',
        pattern: /(.{2}).*(@.*)/,
        replacement: '$1***$2',
      });
      
      desensitization = new DataDesensitization(config);
      
      const data = {
        user: {
          email: 'nested@example.com',
          name: 'John Doe',
        },
      };
      
      const result = await desensitization.desensitize(data);
      
      expect((result.data as any).user.email).toMatch(/ne\*\*\*@example\.com/);
      expect((result.data as any).user.name).toBe('John Doe');
    });

    it('should handle missing nested fields gracefully', async () => {
      config.rules.push({
        field: 'user.nonexistent',
        type: 'mask',
      });
      
      desensitization = new DataDesensitization(config);
      
      const data = { user: { name: 'John' } };
      
      const result = await desensitization.desensitize(data);
      
      expect(result.data).toEqual(data);
    });
  });

  describe('whitelisted fields', () => {
    it('should skip whitelisted fields', async () => {
      config.whitelistedFields = ['email'];
      desensitization = new DataDesensitization(config);
      
      const data = { email: 'user@example.com' };
      
      const result = await desensitization.desensitize(data);
      
      expect((result.data as any).email).toBe('user@example.com');
      expect(result.appliedRules).not.toContain('email');
    });
  });

  describe('configuration management', () => {
    it('should update configuration', () => {
      const newConfig = {
        whitelistedFields: ['newField'],
      };
      
      desensitization.updateConfig(newConfig);
      
      const currentConfig = desensitization.getConfig();
      expect(currentConfig.whitelistedFields).toContain('newField');
    });

    it('should get current configuration', () => {
      const currentConfig = desensitization.getConfig();
      expect(currentConfig).toEqual(config);
    });
  });

  describe('audit logging', () => {
    it('should log desensitization operations', async () => {
      const data = { email: 'user@example.com' };
      
      await desensitization.desensitize(data);
      
      expect(auditEntries.length).toBeGreaterThan(0);
      expect(auditEntries.some(entry => entry.operation === 'desensitize')).toBe(true);
    });

    it('should filter audit log by field', async () => {
      const data = { email: 'user@example.com', phone: '1234567890' };
      
      await desensitization.desensitize(data);
      
      const emailLog = desensitization.getAuditLog('email');
      const phoneLog = desensitization.getAuditLog('phone');
      
      expect(emailLog.length).toBeGreaterThan(0);
      expect(phoneLog.length).toBeGreaterThan(0);
    });

    it('should clear audit log', () => {
      auditEntries.push({
        id: 'test',
        operation: 'desensitize',
        timestamp: Date.now(),
        success: true,
      });
      
      desensitization.clearAuditLog();
      
      const auditLog = desensitization.getAuditLog();
      expect(auditLog).toHaveLength(0);
    });
  });

  describe('error handling', () => {
    it('should handle desensitization errors', async () => {
      // Mock hash function to throw error
      mockCrypto.subtle.digest.mockRejectedValue(new Error('Hash error'));
      
      const data = { token: 'test-token' };
      
      await expect(desensitization.desensitize(data)).rejects.toThrow('Desensitization failed');
    });
  });
});

describe('createDefaultDesensitizationConfig', () => {
  it('should create default configuration', () => {
    const config = createDefaultDesensitizationConfig();
    
    expect(config.rules).toBeDefined();
    expect(config.rules.length).toBeGreaterThan(0);
    expect(config.enableAuditLog).toBe(true);
    expect(config.strictMode).toBe(false);
    expect(config.whitelistedFields).toContain('id');
  });

  it('should include common sensitive field rules', () => {
    const config = createDefaultDesensitizationConfig();
    
    const ruleFields = config.rules.map(rule => rule.field);
    expect(ruleFields).toContain('email');
    expect(ruleFields).toContain('phone');
    expect(ruleFields).toContain('ssn');
    expect(ruleFields).toContain('creditCard');
    expect(ruleFields).toContain('password');
    expect(ruleFields).toContain('token');
  });
});