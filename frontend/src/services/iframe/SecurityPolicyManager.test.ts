/**
 * Tests for SecurityPolicyManager
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  SecurityPolicyManager,
  createDefaultSecurityPolicy,
  createLabelStudioSecurityPolicy,
  type SecurityPolicyConfig,
  type SecurityViolation,
} from './SecurityPolicyManager';

// Mock DOM APIs
const mockMeta = {
  httpEquiv: '',
  content: '',
};

const mockDocument = {
  createElement: vi.fn(() => mockMeta),
  head: {
    appendChild: vi.fn(),
  },
  addEventListener: vi.fn(),
};

const mockWindow = {
  location: {
    protocol: 'https:',
    origin: 'https://example.com',
    href: 'https://example.com/test',
  },
  addEventListener: vi.fn(),
};

// Mock global objects
Object.defineProperty(global, 'document', {
  value: mockDocument,
  writable: true,
});

Object.defineProperty(global, 'window', {
  value: mockWindow,
  writable: true,
});

Object.defineProperty(global, 'console', {
  value: {
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  writable: true,
});

describe('SecurityPolicyManager', () => {
  let manager: SecurityPolicyManager;
  let config: SecurityPolicyConfig;
  let violations: SecurityViolation[];

  beforeEach(() => {
    config = createDefaultSecurityPolicy();
    manager = new SecurityPolicyManager(config);
    violations = [];

    // Reset mocks
    vi.clearAllMocks();
    mockDocument.createElement.mockReturnValue(mockMeta);
    
    // Setup violation handler
    manager.onViolation((violation) => {
      violations.push(violation);
    });
  });

  afterEach(() => {
    manager.cleanup();
  });

  describe('initialization', () => {
    it('should initialize security policies', async () => {
      await manager.initialize();
      
      expect(manager.isReady()).toBe(true);
    });

    it('should not initialize twice', async () => {
      await manager.initialize();
      await manager.initialize();
      
      expect(manager.isReady()).toBe(true);
    });

    it('should handle initialization errors', async () => {
      // Mock error in setup
      mockDocument.createElement.mockImplementation(() => {
        throw new Error('DOM error');
      });

      await expect(manager.initialize()).rejects.toThrow('Failed to initialize security policies');
    });
  });

  describe('HTTPS enforcement', () => {
    it('should allow HTTPS in production', async () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      
      mockWindow.location.protocol = 'https:';
      
      await manager.initialize();
      
      expect(manager.isReady()).toBe(true);
      
      process.env.NODE_ENV = originalEnv;
    });

    it('should warn about HTTP in development', async () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';
      
      // Create a new manager with HTTPS enforcement enabled
      config.https.enforceHTTPS = true;
      manager = new SecurityPolicyManager(config);
      mockWindow.location.protocol = 'http:';
      
      await manager.initialize();
      
      expect(console.warn).toHaveBeenCalledWith(
        expect.stringContaining('HTTPS enforcement is enabled but running on HTTP')
      );
      
      process.env.NODE_ENV = originalEnv;
    });

    it('should redirect to HTTPS in production', async () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      
      // Create a new manager with HTTPS enforcement enabled
      config.https.enforceHTTPS = true;
      manager = new SecurityPolicyManager(config);
      mockWindow.location.protocol = 'http:';
      mockWindow.location.href = 'http://example.com/test';
      
      await manager.initialize();
      
      expect(mockWindow.location.href).toBe('https://example.com/test');
      
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('CSP setup', () => {
    it('should setup CSP headers', async () => {
      await manager.initialize();
      
      expect(mockDocument.createElement).toHaveBeenCalledWith('meta');
      expect(mockMeta.httpEquiv).toBe('Content-Security-Policy');
      expect(mockMeta.content).toContain("default-src 'self'");
    });

    it('should setup CSP report-only mode', async () => {
      config.csp.reportOnly = true;
      manager = new SecurityPolicyManager(config);
      
      await manager.initialize();
      
      expect(mockMeta.httpEquiv).toBe('Content-Security-Policy-Report-Only');
    });

    it('should handle CSP violations', async () => {
      await manager.initialize();
      
      // Simulate CSP violation event
      const violationEvent = {
        violatedDirective: 'script-src',
        blockedURI: 'https://evil.com/script.js',
        sourceFile: 'https://example.com/page.html',
      } as SecurityPolicyViolationEvent;

      // Get the event listener that was registered
      const eventListener = mockDocument.addEventListener.mock.calls.find(
        call => call[0] === 'securitypolicyviolation'
      )?.[1];

      expect(eventListener).toBeDefined();
      
      // Call the event listener
      eventListener(violationEvent);
      
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('csp');
      expect(violations[0].severity).toBe('high');
    });
  });

  describe('CORS validation', () => {
    it('should allow same origin messages', async () => {
      await manager.initialize();
      
      // Simulate message from same origin
      const messageEvent = {
        origin: 'https://example.com',
      } as MessageEvent;

      // Get the message event listener
      const eventListener = mockWindow.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )?.[1];

      expect(eventListener).toBeDefined();
      
      // Call the event listener
      eventListener(messageEvent);
      
      expect(violations).toHaveLength(0);
    });

    it('should block unauthorized origins', async () => {
      config.cors.allowedOrigins = ['https://trusted.com'];
      manager = new SecurityPolicyManager(config);
      manager.onViolation((violation) => {
        violations.push(violation);
      });
      
      await manager.initialize();
      
      // Simulate message from unauthorized origin
      const messageEvent = {
        origin: 'https://evil.com',
      } as MessageEvent;

      // Get the message event listener
      const eventListener = mockWindow.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )?.[1];

      eventListener(messageEvent);
      
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('cors');
      expect(violations[0].severity).toBe('high');
    });

    it('should support wildcard origins', async () => {
      config.cors.allowedOrigins = ['*'];
      manager = new SecurityPolicyManager(config);
      
      await manager.initialize();
      
      const messageEvent = {
        origin: 'https://any-domain.com',
      } as MessageEvent;

      const eventListener = mockWindow.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )?.[1];

      eventListener(messageEvent);
      
      expect(violations).toHaveLength(0);
    });

    it('should support wildcard subdomains', async () => {
      config.cors.allowedOrigins = ['*.example.com'];
      manager = new SecurityPolicyManager(config);
      
      await manager.initialize();
      
      const messageEvent = {
        origin: 'https://sub.example.com',
      } as MessageEvent;

      const eventListener = mockWindow.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )?.[1];

      eventListener(messageEvent);
      
      expect(violations).toHaveLength(0);
    });
  });

  describe('iframe URL validation', () => {
    beforeEach(async () => {
      // Set up config with specific trusted domains for testing
      config.trustedDomains = ['trusted.com'];
      manager = new SecurityPolicyManager(config);
      manager.onViolation((violation) => {
        violations.push(violation);
      });
      await manager.initialize();
    });

    it('should validate HTTPS URLs', () => {
      const result = manager.validateIframeURL('https://trusted.com/iframe');
      expect(result).toBe(true);
    });

    it('should reject HTTP URLs when HTTPS is enforced', () => {
      // Enable HTTPS enforcement for this test
      config.https.enforceHTTPS = true;
      manager = new SecurityPolicyManager(config);
      manager.onViolation((violation) => {
        violations.push(violation);
      });
      
      const result = manager.validateIframeURL('http://trusted.com/iframe');
      expect(result).toBe(false);
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('https');
    });

    it('should validate trusted domains', () => {
      config.trustedDomains = ['trusted.com'];
      manager = new SecurityPolicyManager(config);
      
      const result = manager.validateIframeURL('https://trusted.com/iframe');
      expect(result).toBe(true);
    });

    it('should reject untrusted domains', () => {
      const result = manager.validateIframeURL('https://untrusted.com/iframe');
      expect(result).toBe(false);
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('domain');
    });

    it('should handle invalid URLs', () => {
      const result = manager.validateIframeURL('invalid-url');
      expect(result).toBe(false);
      expect(violations).toHaveLength(1);
      expect(violations[0].type).toBe('domain');
    });
  });

  describe('trusted domain checking', () => {
    it('should check exact domain matches', () => {
      config.trustedDomains = ['example.com'];
      manager = new SecurityPolicyManager(config);
      
      expect(manager.isDomainTrusted('example.com')).toBe(true);
      expect(manager.isDomainTrusted('other.com')).toBe(false);
    });

    it('should support wildcard domains', () => {
      config.trustedDomains = ['*.example.com'];
      manager = new SecurityPolicyManager(config);
      
      expect(manager.isDomainTrusted('sub.example.com')).toBe(true);
      expect(manager.isDomainTrusted('deep.sub.example.com')).toBe(true);
      expect(manager.isDomainTrusted('example.com')).toBe(false); // Base domain should not match wildcard
      expect(manager.isDomainTrusted('other.com')).toBe(false);
    });

    it('should support wildcard all domains', () => {
      config.trustedDomains = ['*'];
      manager = new SecurityPolicyManager(config);
      
      expect(manager.isDomainTrusted('any-domain.com')).toBe(true);
    });
  });

  describe('violation handling', () => {
    beforeEach(async () => {
      await manager.initialize();
    });

    it('should track violations', () => {
      manager.validateIframeURL('http://untrusted.com');
      
      const allViolations = manager.getViolations();
      expect(allViolations).toHaveLength(1);
    });

    it('should filter violations by type', () => {
      // Create a fresh manager for this test with HTTPS enforcement
      const testConfig = { ...config };
      testConfig.https.enforceHTTPS = true;
      testConfig.trustedDomains = ['trusted.com'];
      
      const testManager = new SecurityPolicyManager(testConfig);
      const testViolations: SecurityViolation[] = [];
      testManager.onViolation((violation) => {
        testViolations.push(violation);
      });
      
      testManager.validateIframeURL('http://trusted.com'); // HTTPS violation
      testManager.validateIframeURL('https://untrusted.com'); // Domain violation
      
      const httpsViolations = testManager.getViolations('https');
      const domainViolations = testManager.getViolations('domain');
      
      expect(httpsViolations).toHaveLength(1);
      expect(domainViolations).toHaveLength(1);
    });

    it('should clear violations', () => {
      manager.validateIframeURL('http://untrusted.com');
      expect(manager.getViolations()).toHaveLength(1);
      
      manager.clearViolations();
      expect(manager.getViolations()).toHaveLength(0);
    });

    it('should remove violation handlers', () => {
      const handler = vi.fn();
      const removeHandler = manager.onViolation(handler);
      
      manager.validateIframeURL('http://untrusted.com');
      expect(handler).toHaveBeenCalledTimes(1);
      
      removeHandler();
      manager.validateIframeURL('http://untrusted.com');
      expect(handler).toHaveBeenCalledTimes(1); // Should not be called again
    });
  });

  describe('configuration management', () => {
    it('should update configuration', () => {
      const newConfig = {
        trustedDomains: ['new-domain.com'],
      };
      
      manager.updateConfig(newConfig);
      
      const currentConfig = manager.getConfig();
      expect(currentConfig.trustedDomains).toContain('new-domain.com');
    });

    it('should get current configuration', () => {
      const currentConfig = manager.getConfig();
      expect(currentConfig).toEqual(config);
    });
  });

  describe('cleanup', () => {
    it('should cleanup resources', async () => {
      await manager.initialize();
      expect(manager.isReady()).toBe(true);
      
      manager.cleanup();
      expect(manager.isReady()).toBe(false);
    });
  });
});

describe('createDefaultSecurityPolicy', () => {
  it('should create default policy', () => {
    const policy = createDefaultSecurityPolicy();
    
    expect(policy.csp.directives).toBeDefined();
    expect(policy.cors.allowedOrigins).toContain('*');
    expect(policy.https.enforceHTTPS).toBe(process.env.NODE_ENV === 'production');
    expect(policy.enableSecurityHeaders).toBe(true);
  });
});

describe('createLabelStudioSecurityPolicy', () => {
  it('should create Label Studio specific policy', () => {
    const labelStudioDomain = 'https://labelstudio.example.com';
    const policy = createLabelStudioSecurityPolicy(labelStudioDomain);
    
    expect(policy.cors.allowedOrigins).toContain(labelStudioDomain);
    expect(policy.trustedDomains).toContain(labelStudioDomain);
    
    // Should have frame-src directive for Label Studio
    const frameSrcDirective = policy.csp.directives.find(d => d.directive === 'frame-src');
    expect(frameSrcDirective?.sources).toContain(labelStudioDomain);
  });
});