/**
 * Unit tests for MessageSecurity
 * Tests message signing, verification, encryption, and sanitization
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { MessageSecurity } from './MessageSecurity';
import type { Message } from './types';

describe('MessageSecurity', () => {
  let security: MessageSecurity;

  describe('signature generation and verification', () => {
    beforeEach(() => {
      security = new MessageSecurity({
        enableSignature: true,
        enableEncryption: false,
        secretKey: 'test-secret-key',
      });
    });

    it('should generate signature for message', () => {
      const message: Omit<Message, 'signature'> = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
      };

      const signature = security.generateSignature(message);

      expect(signature).toBeDefined();
      expect(typeof signature).toBe('string');
      expect(signature.length).toBeGreaterThan(0);
    });

    it('should verify valid signature', () => {
      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
        signature: '',
      };

      message.signature = security.generateSignature(message);

      expect(security.verifySignature(message)).toBe(true);
    });

    it('should reject invalid signature', () => {
      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
        signature: 'invalid-signature',
      };

      expect(security.verifySignature(message)).toBe(false);
    });

    it('should reject message without signature', () => {
      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
      };

      expect(security.verifySignature(message)).toBe(false);
    });

    it('should generate different signatures for different messages', () => {
      const message1: Omit<Message, 'signature'> = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test1' },
        timestamp: 1000,
      };

      const message2: Omit<Message, 'signature'> = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test2' },
        timestamp: 1000,
      };

      const sig1 = security.generateSignature(message1);
      const sig2 = security.generateSignature(message2);

      expect(sig1).not.toBe(sig2);
    });

    it('should not verify signature when signature is disabled', () => {
      const noSigSecurity = new MessageSecurity({
        enableSignature: false,
      });

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
      };

      expect(noSigSecurity.verifySignature(message)).toBe(true);
    });
  });

  describe('encryption and decryption', () => {
    beforeEach(() => {
      security = new MessageSecurity({
        enableSignature: false,
        enableEncryption: true,
        secretKey: 'test-secret-key',
      });
    });

    it('should encrypt payload', () => {
      const payload = { data: 'test', value: 123 };

      const encrypted = security.encryptPayload(payload);

      expect(encrypted).toBeDefined();
      expect(typeof encrypted).toBe('string');
      expect(encrypted).not.toContain('test');
      expect(encrypted).not.toContain('123');
    });

    it('should decrypt encrypted payload', () => {
      const payload = { data: 'test', value: 123 };

      const encrypted = security.encryptPayload(payload);
      const decrypted = security.decryptPayload(encrypted);

      expect(decrypted).toEqual(payload);
    });

    it('should not encrypt when encryption is disabled', () => {
      const noEncSecurity = new MessageSecurity({
        enableEncryption: false,
      });

      const payload = { data: 'test' };
      const result = noEncSecurity.encryptPayload(payload);

      expect(result).toBe(JSON.stringify(payload));
    });

    it('should not decrypt when encryption is disabled', () => {
      const noEncSecurity = new MessageSecurity({
        enableEncryption: false,
      });

      const payload = { data: 'test' };
      const jsonString = JSON.stringify(payload);
      const result = noEncSecurity.decryptPayload(jsonString);

      expect(result).toEqual(payload);
    });

    it('should handle complex nested objects', () => {
      const payload = {
        user: {
          id: 1,
          name: 'Test User',
          roles: ['admin', 'user'],
        },
        data: {
          items: [1, 2, 3],
          nested: {
            value: 'test',
          },
        },
      };

      const encrypted = security.encryptPayload(payload);
      const decrypted = security.decryptPayload(encrypted);

      expect(decrypted).toEqual(payload);
    });
  });

  describe('origin validation', () => {
    beforeEach(() => {
      security = new MessageSecurity();
    });

    it('should accept matching origin', () => {
      expect(security.validateOrigin('http://localhost:8080', 'http://localhost:8080')).toBe(
        true
      );
    });

    it('should reject non-matching origin', () => {
      expect(security.validateOrigin('http://untrusted.com', 'http://localhost:8080')).toBe(
        false
      );
    });

    it('should accept any origin with wildcard', () => {
      expect(security.validateOrigin('http://any-origin.com', '*')).toBe(true);
      expect(security.validateOrigin('http://another-origin.com', '*')).toBe(true);
    });
  });

  describe('payload sanitization', () => {
    beforeEach(() => {
      security = new MessageSecurity();
    });

    it('should sanitize string payload', () => {
      const payload = '<script>alert("xss")</script>';

      const sanitized = security.sanitizePayload(payload);

      expect(sanitized).not.toContain('<script>');
      expect(sanitized).toContain('&lt;script&gt;');
    });

    it('should sanitize nested object payloads', () => {
      const payload = {
        message: '<img src=x onerror="alert(1)">',
        nested: {
          content: '<iframe src="evil.com"></iframe>',
        },
      };

      const sanitized = security.sanitizePayload(payload) as Record<string, unknown>;

      expect((sanitized.message as string)).not.toContain('<img');
      expect((sanitized.nested as Record<string, unknown>).content as string).not.toContain(
        '<iframe'
      );
    });

    it('should sanitize array payloads', () => {
      const payload = [
        '<script>alert(1)</script>',
        { content: '<img src=x onerror="alert(1)">' },
      ];

      const sanitized = security.sanitizePayload(payload) as unknown[];

      expect((sanitized[0] as string)).not.toContain('<script>');
      expect(
        ((sanitized[1] as Record<string, unknown>).content as string).indexOf('<img')
      ).toBe(-1);
    });

    it('should preserve non-string values', () => {
      const payload = {
        number: 123,
        boolean: true,
        null: null,
        undefined: undefined,
      };

      const sanitized = security.sanitizePayload(payload);

      expect(sanitized).toEqual(payload);
    });

    it('should handle mixed payloads', () => {
      const payload = {
        safe: 'normal text',
        unsafe: '<script>alert(1)</script>',
        number: 42,
        nested: {
          safe: 'text',
          unsafe: '<img src=x>',
        },
        array: ['<script>', 'safe', 123],
      };

      const sanitized = security.sanitizePayload(payload) as Record<string, unknown>;

      expect((sanitized.safe as string)).toBe('normal text');
      expect((sanitized.unsafe as string)).not.toContain('<script>');
      expect((sanitized.number as number)).toBe(42);
      expect(
        ((sanitized.nested as Record<string, unknown>).unsafe as string).indexOf('<img')
      ).toBe(-1);
    });
  });

  describe('combined security features', () => {
    beforeEach(() => {
      security = new MessageSecurity({
        enableSignature: true,
        enableEncryption: true,
        secretKey: 'test-secret-key',
      });
    });

    it('should handle signature and encryption together', () => {
      const message: Omit<Message, 'signature'> = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
      };

      const signature = security.generateSignature(message);
      const encrypted = security.encryptPayload(message.payload);

      expect(signature).toBeDefined();
      expect(encrypted).toBeDefined();
      expect(encrypted).not.toContain('test');
    });

    it('should sanitize and encrypt payload', () => {
      const payload = {
        safe: 'text',
        unsafe: '<script>alert(1)</script>',
      };

      const sanitized = security.sanitizePayload(payload);
      const encrypted = security.encryptPayload(sanitized);

      expect(encrypted).toBeDefined();
      expect(encrypted).not.toContain('<script>');
    });
  });

  describe('default configuration', () => {
    it('should use default config when not provided', () => {
      const defaultSecurity = new MessageSecurity();

      const message: Message = {
        id: 'msg_1',
        type: 'test',
        payload: { data: 'test' },
        timestamp: 1000,
      };

      // Should not verify signature (disabled by default)
      expect(defaultSecurity.verifySignature(message)).toBe(true);

      // Should not encrypt (disabled by default)
      const payload = { data: 'test' };
      const encrypted = defaultSecurity.encryptPayload(payload);
      expect(encrypted).toBe(JSON.stringify(payload));
    });
  });
});
