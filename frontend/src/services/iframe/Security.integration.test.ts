/**
 * Integration tests for Security components
 * Tests CSP policies, data encryption, and audit logging working together
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  SecurityPolicyManager,
  createLabelStudioSecurityPolicy,
  type SecurityViolation,
} from './SecurityPolicyManager';
import {
  DataEncryption,
  DataDesensitization,
  createDefaultDesensitizationConfig,
  type EncryptionConfig,
} from './DataEncryption';
import {
  SecurityAuditLogger,
  createDefaultAuditConfig,
  type SecurityAuditEvent,
} from './SecurityAuditLogger';

// Mock DOM and Web APIs
const mockDocument = {
  createElement: vi.fn(() => ({ httpEquiv: '', content: '' })),
  head: { appendChild: vi.fn() },
  addEventListener: vi.fn(),
};

const mockWindow = {
  location: {
    protocol: 'https:',
    origin: 'https://app.example.com',
    href: 'https://app.example.com/test',
  },
  addEventListener: vi.fn(),
};

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

const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

// Setup global mocks
Object.defineProperty(global, 'document', { value: mockDocument, writable: true });
Object.defineProperty(global, 'window', { value: mockWindow, writable: true });
Object.defineProperty(global, 'crypto', { value: mockCrypto, writable: true });
Object.defineProperty(global, 'localStorage', { value: mockLocalStorage, writable: true });
Object.defineProperty(global, 'console', {
  value: { log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn() },
  writable: true,
});

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

global.btoa = (str: string) => Buffer.from(str, 'binary').toString('base64');
global.atob = (str: string) => Buffer.from(str, 'base64').toString('binary');

describe('Security Integration Tests', () => {
  let policyManager: SecurityPolicyManager;
  let encryption: DataEncryption;
  let desensitization: DataDesensitization;
  let auditLogger: SecurityAuditLogger;
  
  let violations: SecurityViolation[];
  let auditEvents: SecurityAuditEvent[];

  beforeEach(async () => {
    // Reset mocks
    vi.clearAllMocks();
    violations = [];
    auditEvents = [];
    
    // Setup crypto mocks with more realistic behavior
    const mockKey = { type: 'secret' };
    const encryptedDataStore = new Map<string, string>();
    
    mockCrypto.subtle.importKey.mockResolvedValue(mockKey);
    mockCrypto.subtle.deriveKey.mockResolvedValue(mockKey);
    
    mockCrypto.subtle.encrypt.mockImplementation(async (algorithm, key, data) => {
      const plaintext = new TextDecoder().decode(data);
      const encryptedId = `encrypted-${Date.now()}-${Math.random()}`;
      encryptedDataStore.set(encryptedId, plaintext);
      return new TextEncoder().encode(encryptedId).buffer;
    });
    
    mockCrypto.subtle.decrypt.mockImplementation(async (algorithm, key, data) => {
      const encryptedId = new TextDecoder().decode(data);
      const plaintext = encryptedDataStore.get(encryptedId) || '{"test":"decrypted"}';
      return new TextEncoder().encode(plaintext).buffer;
    });
    mockCrypto.subtle.digest.mockImplementation(async () => {
      return new ArrayBuffer(32);
    });
    mockCrypto.getRandomValues.mockImplementation((array: Uint8Array) => {
      for (let i = 0; i < array.length; i++) {
        array[i] = Math.floor(Math.random() * 256);
      }
      return array;
    });
    
    mockLocalStorage.getItem.mockReturnValue(null);

    // Initialize components
    const labelStudioDomain = 'https://labelstudio.example.com';
    const policyConfig = createLabelStudioSecurityPolicy(labelStudioDomain);
    policyManager = new SecurityPolicyManager(policyConfig);
    
    const encryptionConfig: EncryptionConfig = {
      algorithm: 'AES-GCM',
      keyLength: 256,
      ivLength: 12,
      tagLength: 128,
    };
    encryption = new DataEncryption(encryptionConfig);
    
    const desensitizationConfig = createDefaultDesensitizationConfig();
    desensitization = new DataDesensitization(desensitizationConfig);
    
    const auditConfig = createDefaultAuditConfig();
    auditLogger = new SecurityAuditLogger(auditConfig);

    // Setup event handlers
    policyManager.onViolation((violation) => {
      violations.push(violation);
    });
    
    auditLogger.onEvent((event) => {
      auditEvents.push(event);
    });

    // Initialize all components
    await policyManager.initialize();
    await encryption.initialize('test-encryption-key');
    await auditLogger.initialize();
  });

  afterEach(() => {
    policyManager.cleanup();
    encryption.cleanup();
    desensitization.cleanup();
    auditLogger.cleanup();
  });

  describe('iframe security workflow', () => {
    it('should validate iframe URL and log security events', async () => {
      const iframeUrl = 'https://labelstudio.example.com/projects/1/data/1';
      
      // Validate iframe URL
      const isValid = policyManager.validateIframeURL(iframeUrl);
      expect(isValid).toBe(true);
      
      // Should not have violations for valid URL
      expect(violations).toHaveLength(0);
      
      // Log the validation event
      await auditLogger.logAuthorization('validate_iframe_url', iframeUrl, true);
      
      const authEvents = auditLogger.queryEvents({ type: 'authorization' });
      expect(authEvents).toHaveLength(1);
      expect(authEvents[0].resource).toBe(iframeUrl);
      expect(authEvents[0].success).toBe(true);
    });

    it('should block invalid iframe URLs and log violations', async () => {
      const invalidUrl = 'https://malicious.com/iframe';
      
      // Validate iframe URL
      const isValid = policyManager.validateIframeURL(invalidUrl);
      expect(isValid).toBe(false);
      
      // Should have domain violation
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('domain');
      
      // Log the failed validation
      await auditLogger.logPolicyViolation('untrusted_iframe_domain', {
        url: invalidUrl,
        violation: violations[0],
      });
      
      const violationEvents = auditLogger.queryEvents({ type: 'policy_violation' });
      expect(violationEvents).toHaveLength(1);
      expect(violationEvents[0].riskLevel).toBe('critical');
    });

    it('should handle HTTP iframe URLs in production', async () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      
      // Create a new policy manager with HTTPS enforcement for production
      const prodPolicyConfig = createLabelStudioSecurityPolicy('https://labelstudio.example.com');
      prodPolicyConfig.https.enforceHTTPS = true;
      const prodPolicyManager = new SecurityPolicyManager(prodPolicyConfig);
      
      const prodViolations: SecurityViolation[] = [];
      prodPolicyManager.onViolation((violation) => {
        prodViolations.push(violation);
      });
      
      await prodPolicyManager.initialize();
      
      const httpUrl = 'http://labelstudio.example.com/iframe';
      
      const isValid = prodPolicyManager.validateIframeURL(httpUrl);
      expect(isValid).toBe(false);
      
      // Should have HTTPS violation
      expect(prodViolations).toHaveLength(1);
      expect(prodViolations[0].type).toBe('https');
      
      await auditLogger.logPolicyViolation('http_iframe_in_production', {
        url: httpUrl,
        environment: 'production',
      });
      
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('data protection workflow', () => {
    it('should encrypt sensitive data and log encryption events', async () => {
      const sensitiveData = {
        userId: 'user123',
        email: 'user@example.com',
        annotationData: { labels: ['cat', 'dog'] },
      };
      
      // Encrypt the data
      const encryptedData = await encryption.encrypt(sensitiveData);
      
      expect(encryptedData).toHaveProperty('data');
      expect(encryptedData).toHaveProperty('iv');
      expect(encryptedData.algorithm).toBe('AES-GCM');
      
      // Log encryption event
      await auditLogger.logEncryption('encrypt_annotation_data', true, {
        dataSize: JSON.stringify(sensitiveData).length,
        algorithm: encryptedData.algorithm,
      });
      
      const encryptionEvents = auditLogger.queryEvents({ type: 'encryption' });
      expect(encryptionEvents).toHaveLength(1);
      expect(encryptionEvents[0].success).toBe(true);
    });

    it('should desensitize data and maintain audit trail', async () => {
      const userData = {
        id: 'user123',
        email: 'john.doe@company.com',
        phone: '1234567890',
        password: 'secret123',
        annotationData: { task: 'classify' },
      };
      
      // Desensitize the data
      const desensitizedResult = await desensitization.desensitize(userData);
      
      expect(desensitizedResult.data).toHaveProperty('id', 'user123'); // Whitelisted
      expect((desensitizedResult.data as any).email).toMatch(/jo\*\*\*@company\.com/);
      expect((desensitizedResult.data as any).phone).toBe('123****890');
      expect(desensitizedResult.data).not.toHaveProperty('password'); // Removed
      expect(desensitizedResult.appliedRules).toContain('email');
      expect(desensitizedResult.appliedRules).toContain('phone');
      expect(desensitizedResult.appliedRules).toContain('password');
      
      // Log data access with desensitization
      await auditLogger.logDataAccess('desensitize_user_data', 'user_profile', 'user123', {
        appliedRules: desensitizedResult.appliedRules,
        originalHash: desensitizedResult.originalHash,
      });
      
      const dataAccessEvents = auditLogger.queryEvents({ type: 'data_access' });
      expect(dataAccessEvents).toHaveLength(1);
      expect(dataAccessEvents[0].userId).toBe('user123');
    });

    it('should handle encryption-desensitization workflow', async () => {
      const sensitiveUserData = {
        userId: 'user456',
        email: 'sensitive@example.com',
        creditCard: '1234567890123456',
        annotationResults: { accuracy: 0.95 },
      };
      
      // First desensitize
      const desensitizedResult = await desensitization.desensitize(sensitiveUserData);
      
      // Then encrypt the desensitized data
      const encryptedData = await encryption.encrypt(desensitizedResult.data);
      
      // Decrypt to verify
      const decryptedData = await encryption.decrypt(encryptedData);
      
      expect(decryptedData).toEqual(desensitizedResult.data);
      expect((decryptedData as any).email).toMatch(/se\*\*\*@example\.com/);
      expect((decryptedData as any).creditCard).toBe('1234********3456');
      
      // Log the complete workflow
      await auditLogger.logDataAccess('secure_data_processing', 'annotation_results', 'user456', {
        workflow: 'desensitize_then_encrypt',
        appliedRules: desensitizedResult.appliedRules,
        encrypted: true,
      });
    });
  });

  describe('security violation handling', () => {
    it('should handle CSP violations with audit logging', async () => {
      // Simulate CSP violation
      const cspViolationEvent = {
        violatedDirective: 'script-src',
        blockedURI: 'https://malicious.com/script.js',
        sourceFile: 'https://app.example.com/page.html',
      } as SecurityPolicyViolationEvent;

      // Get the CSP event listener
      const cspListener = mockDocument.addEventListener.mock.calls.find(
        call => call[0] === 'securitypolicyviolation'
      )?.[1];

      expect(cspListener).toBeDefined();
      cspListener(cspViolationEvent);
      
      // Should have CSP violation
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('csp');
      expect(violations[0].severity).toBe('high');
      
      // Log the violation
      await auditLogger.logPolicyViolation('csp_script_violation', {
        directive: cspViolationEvent.violatedDirective,
        blockedUri: cspViolationEvent.blockedURI,
        sourceFile: cspViolationEvent.sourceFile,
      });
      
      const violationEvents = auditLogger.queryEvents({ type: 'policy_violation' });
      expect(violationEvents).toHaveLength(1);
      expect(violationEvents[0].riskLevel).toBe('critical');
    });

    it('should handle CORS violations with audit logging', async () => {
      // Simulate message from unauthorized origin
      const messageEvent = {
        origin: 'https://unauthorized.com',
        data: { type: 'malicious_message' },
      } as MessageEvent;

      // Get the message event listener
      const messageListener = mockWindow.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )?.[1];

      expect(messageListener).toBeDefined();
      messageListener(messageEvent);
      
      // Should have CORS violation
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('cors');
      expect(violations[0].severity).toBe('high');
      
      // Log the violation
      await auditLogger.logPolicyViolation('cors_unauthorized_origin', {
        origin: messageEvent.origin,
        messageType: messageEvent.data?.type,
      });
      
      const violationEvents = auditLogger.queryEvents({ type: 'policy_violation' });
      expect(violationEvents).toHaveLength(1);
    });
  });

  describe('comprehensive security audit', () => {
    it('should generate comprehensive security report', async () => {
      // Simulate various security events
      await auditLogger.logAuthentication('iframe_init', true);
      await auditLogger.logAuthorization('validate_permissions', '/api/annotations', true);
      await auditLogger.logDataAccess('load_annotation_data', '/api/tasks/123', 'user123');
      await auditLogger.logEncryption('encrypt_sensitive_data', true);
      
      // Simulate a violation
      policyManager.validateIframeURL('https://malicious.com');
      await auditLogger.logPolicyViolation('untrusted_domain', { domain: 'malicious.com' });
      
      // Generate summary
      const summary = auditLogger.getSummary();
      
      expect(summary.totalEvents).toBeGreaterThan(5); // Including initialization events
      expect(summary.successfulEvents).toBeGreaterThan(0);
      expect(summary.failedEvents).toBeGreaterThan(0);
      
      // Check risk distribution
      expect(summary.riskDistribution.low).toBeGreaterThan(0);
      expect(summary.riskDistribution.medium).toBeGreaterThan(0);
      expect(summary.riskDistribution.critical).toBeGreaterThan(0);
      
      // Check type distribution
      expect(summary.typeDistribution.authentication).toBeGreaterThan(0);
      expect(summary.typeDistribution.authorization).toBeGreaterThan(0);
      expect(summary.typeDistribution.data_access).toBeGreaterThan(0);
      expect(summary.typeDistribution.encryption).toBeGreaterThan(0);
      expect(summary.typeDistribution.policy_violation).toBeGreaterThan(0);
      
      // Export for analysis
      const exportedLog = auditLogger.exportLog('json');
      const parsedLog = JSON.parse(exportedLog);
      
      expect(Array.isArray(parsedLog)).toBe(true);
      expect(parsedLog.length).toBe(summary.totalEvents);
    });

    it('should handle high-risk security scenarios', async () => {
      // Simulate multiple failed authentication attempts
      for (let i = 0; i < 3; i++) {
        await auditLogger.logAuthentication('iframe_auth_failed', false, {
          attempt: i + 1,
          reason: 'invalid_token',
        });
      }
      
      // Simulate data breach attempt with high risk
      await auditLogger.logDataAccess('unauthorized_access_attempt', '/api/sensitive', undefined, {
        blocked: true,
        reason: 'insufficient_permissions',
      });
      
      // Simulate encryption failure with high risk
      await auditLogger.logEncryption('encrypt_failed', false, {
        error: 'key_not_available',
      });
      
      // Simulate critical security violation
      await auditLogger.logPolicyViolation('critical_security_breach', {
        type: 'data_exfiltration_attempt',
        blocked: true,
      });
      
      // Check high-risk events
      const highRiskEvents = auditLogger.queryEvents({ riskLevel: 'high' });
      const criticalEvents = auditLogger.queryEvents({ riskLevel: 'critical' });
      
      expect(highRiskEvents.length).toBeGreaterThan(0);
      expect(criticalEvents.length).toBeGreaterThan(0);
      
      // Verify failed events are properly tracked
      const failedEvents = auditLogger.queryEvents({ success: false });
      expect(failedEvents.length).toBeGreaterThan(3);
    });
  });

  describe('security configuration validation', () => {
    it('should validate security policy configuration', () => {
      const config = policyManager.getConfig();
      
      // Verify CSP configuration
      expect(config.csp.directives).toBeDefined();
      expect(config.csp.directives.length).toBeGreaterThan(0);
      
      const frameSrcDirective = config.csp.directives.find(d => d.directive === 'frame-src');
      expect(frameSrcDirective).toBeDefined();
      expect(frameSrcDirective!.sources).toContain('https://labelstudio.example.com');
      
      // Verify CORS configuration
      expect(config.cors.allowedOrigins).toContain('https://labelstudio.example.com');
      
      // Verify trusted domains
      expect(config.trustedDomains).toContain('https://labelstudio.example.com');
      
      // Verify HTTPS enforcement
      expect(config.https.enforceHTTPS).toBeDefined();
    });

    it('should validate encryption configuration', () => {
      expect(encryption.isReady()).toBe(true);
      
      // Test encryption/decryption round trip
      const testData = { test: 'security validation' };
      
      return encryption.encrypt(testData)
        .then(encrypted => encryption.decrypt(encrypted))
        .then(decrypted => {
          expect(decrypted).toEqual(testData);
        });
    });

    it('should validate desensitization rules', () => {
      const config = desensitization.getConfig();
      
      expect(config.rules).toBeDefined();
      expect(config.rules.length).toBeGreaterThan(0);
      
      // Check for common sensitive fields
      const ruleFields = config.rules.map(rule => rule.field);
      expect(ruleFields).toContain('email');
      expect(ruleFields).toContain('phone');
      expect(ruleFields).toContain('password');
      expect(ruleFields).toContain('creditCard');
      
      // Check whitelisted fields
      expect(config.whitelistedFields).toContain('id');
      expect(config.whitelistedFields).toContain('timestamp');
    });

    it('should validate audit logger configuration', () => {
      const config = auditLogger.getConfig();
      
      expect(config.maxLogSize).toBeGreaterThan(0);
      expect(config.retentionDays).toBeGreaterThan(0);
      expect(config.enableLocalStorage).toBeDefined();
      expect(config.logLevel).toBeDefined();
      
      expect(auditLogger.isReady()).toBe(true);
    });
  });
});