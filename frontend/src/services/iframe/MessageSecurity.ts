/**
 * MessageSecurity - Handles message signing, verification, and encryption
 * Provides security features for PostMessage communication
 */

import type { Message } from './types';

export interface SecurityConfig {
  enableSignature: boolean;
  enableEncryption: boolean;
  secretKey?: string;
}

export class MessageSecurity {
  private config: SecurityConfig;
  private secretKey: string;

  constructor(config: SecurityConfig = { enableSignature: false, enableEncryption: false }) {
    this.config = config;
    // Use provided secret key or generate a default one
    this.secretKey = config.secretKey || this.generateDefaultKey();
  }

  /**
   * Generate signature for message
   */
  generateSignature(message: Omit<Message, 'signature'>): string {
    if (!this.config.enableSignature) {
      return '';
    }

    const data = JSON.stringify({
      type: message.type,
      payload: message.payload,
      timestamp: message.timestamp,
      id: message.id,
    });

    return this.hmacSha256(data, this.secretKey);
  }

  /**
   * Verify message signature
   */
  verifySignature(message: Message): boolean {
    if (!this.config.enableSignature) {
      return true;
    }

    if (!message.signature) {
      return false;
    }

    const expectedSignature = this.generateSignature({
      id: message.id,
      type: message.type,
      payload: message.payload,
      timestamp: message.timestamp,
      source: message.source,
    });

    return this.constantTimeCompare(message.signature, expectedSignature);
  }

  /**
   * Encrypt message payload
   */
  encryptPayload(payload: unknown): string {
    if (!this.config.enableEncryption) {
      return JSON.stringify(payload);
    }

    const jsonString = JSON.stringify(payload);
    return this.encryptString(jsonString, this.secretKey);
  }

  /**
   * Decrypt message payload
   */
  decryptPayload(encryptedPayload: string): unknown {
    if (!this.config.enableEncryption) {
      return JSON.parse(encryptedPayload);
    }

    const decrypted = this.decryptString(encryptedPayload, this.secretKey);
    return JSON.parse(decrypted);
  }

  /**
   * HMAC-SHA256 implementation using Web Crypto API
   */
  private async hmacSha256Async(data: string, key: string): Promise<string> {
    const encoder = new TextEncoder();
    const keyData = encoder.encode(key);
    const messageData = encoder.encode(data);

    const cryptoKey = await crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );

    const signature = await crypto.subtle.sign('HMAC', cryptoKey, messageData);
    return this.arrayBufferToHex(signature);
  }

  /**
   * Synchronous HMAC-SHA256 using simple hash
   * Note: This is a simplified version for demo purposes
   * In production, use proper cryptographic libraries
   */
  private hmacSha256(data: string, key: string): string {
    // Simple hash-based signature for demo
    const combined = key + data;
    let hash = 0;
    for (let i = 0; i < combined.length; i++) {
      const char = combined.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16);
  }

  /**
   * Simple encryption using XOR with key
   * Note: This is a simplified version for demo purposes
   * In production, use proper encryption libraries like TweetNaCl.js
   */
  private encryptString(text: string, key: string): string {
    let result = '';
    for (let i = 0; i < text.length; i++) {
      const charCode = text.charCodeAt(i) ^ key.charCodeAt(i % key.length);
      result += String.fromCharCode(charCode);
    }
    return btoa(result); // Base64 encode
  }

  /**
   * Simple decryption using XOR with key
   */
  private decryptString(encrypted: string, key: string): string {
    const decoded = atob(encrypted); // Base64 decode
    let result = '';
    for (let i = 0; i < decoded.length; i++) {
      const charCode = decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length);
      result += String.fromCharCode(charCode);
    }
    return result;
  }

  /**
   * Constant time string comparison to prevent timing attacks
   */
  private constantTimeCompare(a: string, b: string): boolean {
    if (a.length !== b.length) {
      return false;
    }

    let result = 0;
    for (let i = 0; i < a.length; i++) {
      result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }

    return result === 0;
  }

  /**
   * Convert ArrayBuffer to hex string
   */
  private arrayBufferToHex(buffer: ArrayBuffer): string {
    const view = new Uint8Array(buffer);
    let hex = '';
    for (let i = 0; i < view.length; i++) {
      hex += ('00' + view[i].toString(16)).slice(-2);
    }
    return hex;
  }

  /**
   * Generate default secret key
   */
  private generateDefaultKey(): string {
    return 'default-secret-key-' + Math.random().toString(36).substring(2, 15);
  }

  /**
   * Validate message origin
   */
  validateOrigin(messageOrigin: string, allowedOrigin: string): boolean {
    if (allowedOrigin === '*') {
      return true;
    }

    return messageOrigin === allowedOrigin;
  }

  /**
   * Sanitize message payload to prevent XSS
   */
  sanitizePayload(payload: unknown): unknown {
    if (typeof payload === 'string') {
      return this.sanitizeString(payload);
    }

    if (typeof payload === 'object' && payload !== null) {
      if (Array.isArray(payload)) {
        return payload.map((item) => this.sanitizePayload(item));
      }

      const sanitized: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(payload)) {
        sanitized[key] = this.sanitizePayload(value);
      }
      return sanitized;
    }

    return payload;
  }

  /**
   * Sanitize string to prevent XSS
   */
  private sanitizeString(str: string): string {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
