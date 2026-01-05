/**
 * Security Policy Manager for iframe integration
 * Handles CSP, CORS, and HTTPS enforcement
 */

export interface CSPDirective {
  directive: string;
  sources: string[];
}

export interface CSPPolicy {
  directives: CSPDirective[];
  reportUri?: string;
  reportOnly?: boolean;
}

export interface CORSConfig {
  allowedOrigins: string[];
  allowedMethods: string[];
  allowedHeaders: string[];
  allowCredentials: boolean;
  maxAge?: number;
}

export interface HTTPSConfig {
  enforceHTTPS: boolean;
  strictTransportSecurity: boolean;
  maxAge: number;
  includeSubdomains: boolean;
  preload: boolean;
}

export interface SecurityPolicyConfig {
  csp: CSPPolicy;
  cors: CORSConfig;
  https: HTTPSConfig;
  enableSecurityHeaders: boolean;
  trustedDomains: string[];
}

export interface SecurityViolation {
  type: 'csp' | 'cors' | 'https' | 'domain';
  message: string;
  source: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  blocked: boolean;
}

export type SecurityEventHandler = (violation: SecurityViolation) => void;

export class SecurityPolicyManager {
  private config: SecurityPolicyConfig;
  private violationHandlers: SecurityEventHandler[] = [];
  private violations: SecurityViolation[] = [];
  private isInitialized = false;

  constructor(config: SecurityPolicyConfig) {
    this.config = config;
  }

  /**
   * Initialize security policies
   */
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      await this.enforceHTTPS();
      this.setupCSP();
      this.setupCORS();
      this.setupSecurityHeaders();
      this.setupViolationReporting();
      
      this.isInitialized = true;
    } catch (error) {
      throw new Error(`Failed to initialize security policies: ${error}`);
    }
  }

  /**
   * Enforce HTTPS if configured
   */
  private async enforceHTTPS(): Promise<void> {
    if (!this.config.https.enforceHTTPS) {
      return;
    }

    // Check if current protocol is HTTPS
    if (window.location.protocol !== 'https:') {
      if (process.env.NODE_ENV === 'production') {
        // Redirect to HTTPS in production
        window.location.href = window.location.href.replace('http:', 'https:');
        return;
      } else {
        // Log warning in development
        console.warn('HTTPS enforcement is enabled but running on HTTP in development mode');
      }
    }

    // Set Strict Transport Security header if supported
    if (this.config.https.strictTransportSecurity) {
      this.setSecurityHeader('Strict-Transport-Security', this.buildHSTSHeader());
    }
  }

  /**
   * Setup Content Security Policy
   */
  private setupCSP(): void {
    const cspHeader = this.buildCSPHeader();
    const headerName = this.config.csp.reportOnly ? 
      'Content-Security-Policy-Report-Only' : 
      'Content-Security-Policy';
    
    this.setSecurityHeader(headerName, cspHeader);
    
    // Listen for CSP violations
    document.addEventListener('securitypolicyviolation', (event) => {
      this.handleCSPViolation(event as SecurityPolicyViolationEvent);
    });
  }

  /**
   * Setup CORS configuration
   */
  private setupCORS(): void {
    // CORS is typically handled by the server, but we can validate origins
    window.addEventListener('message', (event) => {
      if (!this.isOriginAllowed(event.origin)) {
        this.reportViolation({
          type: 'cors',
          message: `Message from unauthorized origin: ${event.origin}`,
          source: event.origin,
          timestamp: Date.now(),
          severity: 'high',
          blocked: true,
        });
        return;
      }
    });
  }

  /**
   * Setup additional security headers
   */
  private setupSecurityHeaders(): void {
    if (!this.config.enableSecurityHeaders) {
      return;
    }

    // X-Frame-Options (for iframe protection)
    this.setSecurityHeader('X-Frame-Options', 'SAMEORIGIN');
    
    // X-Content-Type-Options
    this.setSecurityHeader('X-Content-Type-Options', 'nosniff');
    
    // X-XSS-Protection
    this.setSecurityHeader('X-XSS-Protection', '1; mode=block');
    
    // Referrer-Policy
    this.setSecurityHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Permissions-Policy
    this.setSecurityHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  }

  /**
   * Setup violation reporting
   */
  private setupViolationReporting(): void {
    // Report CSP violations
    if (this.config.csp.reportUri) {
      // CSP reporting is handled by the browser automatically
      console.log(`CSP violations will be reported to: ${this.config.csp.reportUri}`);
    }
  }

  /**
   * Build CSP header string
   */
  private buildCSPHeader(): string {
    const directives = this.config.csp.directives.map(directive => {
      const sources = directive.sources.join(' ');
      return `${directive.directive} ${sources}`;
    });

    if (this.config.csp.reportUri) {
      directives.push(`report-uri ${this.config.csp.reportUri}`);
    }

    return directives.join('; ');
  }

  /**
   * Build HSTS header string
   */
  private buildHSTSHeader(): string {
    let header = `max-age=${this.config.https.maxAge}`;
    
    if (this.config.https.includeSubdomains) {
      header += '; includeSubDomains';
    }
    
    if (this.config.https.preload) {
      header += '; preload';
    }
    
    return header;
  }

  /**
   * Set security header (meta tag approach for client-side)
   */
  private setSecurityHeader(name: string, value: string): void {
    // For client-side, we can only set some headers via meta tags
    // Most security headers should be set by the server
    if (name === 'Content-Security-Policy' || name === 'Content-Security-Policy-Report-Only') {
      const meta = document.createElement('meta');
      meta.httpEquiv = name;
      meta.content = value;
      document.head.appendChild(meta);
    }
    
    // Log for server-side implementation
    console.log(`Security header should be set by server: ${name}: ${value}`);
  }

  /**
   * Handle CSP violations
   */
  private handleCSPViolation(event: SecurityPolicyViolationEvent): void {
    const violation: SecurityViolation = {
      type: 'csp',
      message: `CSP violation: ${event.violatedDirective} - ${event.blockedURI}`,
      source: event.sourceFile || 'unknown',
      timestamp: Date.now(),
      severity: this.getViolationSeverity(event.violatedDirective),
      blocked: true,
    };

    this.reportViolation(violation);
  }

  /**
   * Check if origin is allowed
   */
  private isOriginAllowed(origin: string): boolean {
    // Allow same origin
    if (origin === window.location.origin) {
      return true;
    }

    // Check against allowed origins
    return this.config.cors.allowedOrigins.some(allowedOrigin => {
      if (allowedOrigin === '*') {
        return true;
      }
      
      // Support wildcard subdomains
      if (allowedOrigin.startsWith('*.')) {
        const domain = allowedOrigin.substring(2);
        return origin.endsWith(domain);
      }
      
      return origin === allowedOrigin;
    });
  }

  /**
   * Check if domain is trusted
   */
  public isDomainTrusted(domain: string): boolean {
    return this.config.trustedDomains.some(trustedDomain => {
      if (trustedDomain === '*') {
        return true;
      }
      
      // Support wildcard subdomains
      if (trustedDomain.startsWith('*.')) {
        const baseDomain = trustedDomain.substring(2);
        return domain.endsWith(baseDomain) && domain !== baseDomain;
      }
      
      return domain === trustedDomain;
    });
  }

  /**
   * Validate iframe URL
   */
  public validateIframeURL(url: string): boolean {
    try {
      const urlObj = new URL(url);
      
      // Check HTTPS requirement first
      if (this.config.https.enforceHTTPS && urlObj.protocol !== 'https:') {
        this.reportViolation({
          type: 'https',
          message: `iframe URL must use HTTPS: ${url}`,
          source: url,
          timestamp: Date.now(),
          severity: 'high',
          blocked: true,
        });
        return false;
      }
      
      // Then check trusted domains
      if (!this.isDomainTrusted(urlObj.hostname)) {
        this.reportViolation({
          type: 'domain',
          message: `iframe URL from untrusted domain: ${urlObj.hostname}`,
          source: url,
          timestamp: Date.now(),
          severity: 'high',
          blocked: true,
        });
        return false;
      }
      
      return true;
    } catch (error) {
      this.reportViolation({
        type: 'domain',
        message: `Invalid iframe URL: ${url}`,
        source: url,
        timestamp: Date.now(),
        severity: 'medium',
        blocked: true,
      });
      return false;
    }
  }

  /**
   * Get violation severity based on directive
   */
  private getViolationSeverity(directive: string): SecurityViolation['severity'] {
    const highSeverityDirectives = ['script-src', 'object-src', 'base-uri'];
    const mediumSeverityDirectives = ['style-src', 'img-src', 'font-src'];
    
    if (highSeverityDirectives.some(d => directive.includes(d))) {
      return 'high';
    }
    
    if (mediumSeverityDirectives.some(d => directive.includes(d))) {
      return 'medium';
    }
    
    return 'low';
  }

  /**
   * Report security violation
   */
  private reportViolation(violation: SecurityViolation): void {
    this.violations.push(violation);
    
    // Limit violation history
    if (this.violations.length > 1000) {
      this.violations = this.violations.slice(-500);
    }
    
    // Notify handlers
    this.violationHandlers.forEach(handler => {
      try {
        handler(violation);
      } catch (error) {
        console.error('Error in security violation handler:', error);
      }
    });
    
    // Log violation
    console.warn('Security violation detected:', violation);
  }

  /**
   * Add violation handler
   */
  public onViolation(handler: SecurityEventHandler): () => void {
    this.violationHandlers.push(handler);
    
    return () => {
      const index = this.violationHandlers.indexOf(handler);
      if (index > -1) {
        this.violationHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Get violation history
   */
  public getViolations(type?: SecurityViolation['type']): SecurityViolation[] {
    if (type) {
      return this.violations.filter(v => v.type === type);
    }
    return [...this.violations];
  }

  /**
   * Clear violation history
   */
  public clearViolations(): void {
    this.violations = [];
  }

  /**
   * Update security configuration
   */
  public updateConfig(config: Partial<SecurityPolicyConfig>): void {
    this.config = { ...this.config, ...config };
    
    // Re-initialize if already initialized
    if (this.isInitialized) {
      this.isInitialized = false;
      this.initialize();
    }
  }

  /**
   * Get current configuration
   */
  public getConfig(): SecurityPolicyConfig {
    return { ...this.config };
  }

  /**
   * Check if security policies are initialized
   */
  public isReady(): boolean {
    return this.isInitialized;
  }

  /**
   * Cleanup resources
   */
  public cleanup(): void {
    this.violationHandlers = [];
    this.violations = [];
    this.isInitialized = false;
  }
}

/**
 * Create default security policy configuration
 */
export function createDefaultSecurityPolicy(): SecurityPolicyConfig {
  return {
    csp: {
      directives: [
        {
          directive: 'default-src',
          sources: ["'self'"],
        },
        {
          directive: 'script-src',
          sources: ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        },
        {
          directive: 'style-src',
          sources: ["'self'", "'unsafe-inline'"],
        },
        {
          directive: 'img-src',
          sources: ["'self'", 'data:', 'https:'],
        },
        {
          directive: 'font-src',
          sources: ["'self'", 'https:'],
        },
        {
          directive: 'connect-src',
          sources: ["'self'", 'https:'],
        },
        {
          directive: 'frame-src',
          sources: ["'self'"],
        },
        {
          directive: 'object-src',
          sources: ["'none'"],
        },
        {
          directive: 'base-uri',
          sources: ["'self'"],
        },
      ],
      reportOnly: false,
    },
    cors: {
      allowedOrigins: ['*'],
      allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
      allowCredentials: true,
      maxAge: 86400,
    },
    https: {
      enforceHTTPS: process.env.NODE_ENV === 'production',
      strictTransportSecurity: true,
      maxAge: 31536000, // 1 year
      includeSubdomains: true,
      preload: false,
    },
    enableSecurityHeaders: true,
    trustedDomains: ['localhost', '127.0.0.1', '*.example.com'],
  };
}

/**
 * Create Label Studio specific security policy
 */
export function createLabelStudioSecurityPolicy(labelStudioDomain: string): SecurityPolicyConfig {
  const defaultPolicy = createDefaultSecurityPolicy();
  
  // Update frame-src directive to include Label Studio domain
  const updatedDirectives = defaultPolicy.csp.directives.map(directive => {
    if (directive.directive === 'frame-src') {
      return {
        ...directive,
        sources: [...directive.sources, labelStudioDomain],
      };
    }
    return directive;
  });
  
  return {
    ...defaultPolicy,
    csp: {
      ...defaultPolicy.csp,
      directives: updatedDirectives,
    },
    cors: {
      ...defaultPolicy.cors,
      allowedOrigins: [window.location.origin, labelStudioDomain],
    },
    trustedDomains: [...defaultPolicy.trustedDomains, labelStudioDomain],
  };
}