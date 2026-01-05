/**
 * PostMessageBridge - Manages bidirectional communication between main window and iframe
 * Implements message queue, retry logic, timeout control, and security features
 */

import type {
  Message,
  Response,
  MessageHandler,
  PostMessageBridgeConfig,
  BridgeStatus,
} from './types';
import { BridgeStatus as BridgeStatusEnum } from './types';
import { MessageSecurity } from './MessageSecurity';

interface PendingRequest {
  resolve: (value: Response) => void;
  reject: (reason?: unknown) => void;
  timeout: NodeJS.Timeout;
  retries: number;
}

interface QueuedMessage {
  message: Message;
  retries: number;
  timestamp: number;
}

export class PostMessageBridge {
  private iframe: HTMLIFrameElement | null = null;
  private status: BridgeStatus = BridgeStatusEnum.DISCONNECTED;
  private config: Required<PostMessageBridgeConfig>;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private messageQueue: QueuedMessage[] = [];
  private messageCounter: number = 0;
  private isProcessingQueue: boolean = false;
  private messageListener: ((event: MessageEvent) => void) | null = null;
  private security: MessageSecurity;

  constructor(config: PostMessageBridgeConfig = {}) {
    this.config = {
      targetOrigin: config.targetOrigin || '*',
      timeout: config.timeout || 5000,
      maxRetries: config.maxRetries || 3,
      enableEncryption: config.enableEncryption || false,
      enableSignature: config.enableSignature || false,
    };

    this.security = new MessageSecurity({
      enableSignature: this.config.enableSignature,
      enableEncryption: this.config.enableEncryption,
      secretKey: (config as any).secretKey,
    });
  }

  /**
   * Initialize bridge with iframe reference
   */
  initialize(iframe: HTMLIFrameElement): void {
    if (this.iframe) {
      throw new Error('Bridge already initialized');
    }

    this.iframe = iframe;
    this.setupMessageListener();
    this.status = BridgeStatusEnum.CONNECTED;
  }

  /**
   * Send message to iframe and wait for response
   */
  async send(message: Omit<Message, 'id' | 'timestamp'>): Promise<Response> {
    if (!this.iframe) {
      throw new Error('Bridge not initialized. Call initialize() first.');
    }

    const id = this.generateMessageId();
    const fullMessage: Message = {
      ...message,
      id,
      timestamp: Date.now(),
      source: 'main',
    };

    // Add signature if enabled
    if (this.config.enableSignature) {
      fullMessage.signature = this.security.generateSignature(fullMessage);
    }

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Message timeout: ${message.type}`));
      }, this.config.timeout);

      this.pendingRequests.set(id, {
        resolve,
        reject,
        timeout,
        retries: 0,
      });

      this.queueMessage(fullMessage);
    });
  }

  /**
   * Register message handler for specific message type
   */
  on(type: string, handler: MessageHandler): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);
  }

  /**
   * Unregister message handler
   */
  off(type: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Get current bridge status
   */
  getStatus(): BridgeStatus {
    return this.status;
  }

  /**
   * Cleanup and disconnect bridge
   */
  cleanup(): void {
    if (this.messageListener) {
      window.removeEventListener('message', this.messageListener);
      this.messageListener = null;
    }

    // Clear pending requests
    this.pendingRequests.forEach(({ timeout }) => {
      clearTimeout(timeout);
    });
    this.pendingRequests.clear();

    // Clear message queue
    this.messageQueue = [];

    this.iframe = null;
    this.status = BridgeStatusEnum.DISCONNECTED;
  }

  /**
   * Setup message event listener
   */
  private setupMessageListener(): void {
    this.messageListener = (event: MessageEvent) => {
      // Verify origin
      if (!this.security.validateOrigin(event.origin, this.config.targetOrigin)) {
        console.warn(`Message from untrusted origin: ${event.origin}`);
        return;
      }

      const message = event.data as Message;

      // Validate message structure
      if (!this.isValidMessage(message)) {
        console.warn('Invalid message structure:', message);
        return;
      }

      // Verify signature if enabled
      if (this.config.enableSignature && !this.security.verifySignature(message)) {
        console.warn('Message signature verification failed');
        return;
      }

      // Sanitize payload
      const sanitizedMessage: Message = {
        ...message,
        payload: this.security.sanitizePayload(message.payload),
      };

      // Handle response to pending request
      if (this.pendingRequests.has(message.id)) {
        this.handleResponse(sanitizedMessage as Response);
      } else {
        // Handle incoming message
        this.handleIncomingMessage(sanitizedMessage);
      }
    };

    window.addEventListener('message', this.messageListener);
  }

  /**
   * Queue message for sending
   */
  private queueMessage(message: Message): void {
    this.messageQueue.push({
      message,
      retries: 0,
      timestamp: Date.now(),
    });

    this.processQueue();
  }

  /**
   * Process message queue
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessingQueue || this.messageQueue.length === 0) {
      return;
    }

    this.isProcessingQueue = true;

    while (this.messageQueue.length > 0) {
      const queued = this.messageQueue.shift();
      if (!queued) break;

      try {
        this.postMessage(queued.message);
      } catch (error) {
        // Re-queue message if sending failed
        if (queued.retries < this.config.maxRetries) {
          queued.retries++;
          this.messageQueue.unshift(queued);
          await new Promise((resolve) => setTimeout(resolve, 100 * queued.retries));
        } else {
          // Max retries exceeded
          const pending = this.pendingRequests.get(queued.message.id);
          if (pending) {
            clearTimeout(pending.timeout);
            this.pendingRequests.delete(queued.message.id);
            pending.reject(new Error('Failed to send message after max retries'));
          }
        }
      }
    }

    this.isProcessingQueue = false;
  }

  /**
   * Post message to iframe
   */
  private postMessage(message: Message): void {
    if (!this.iframe || !this.iframe.contentWindow) {
      throw new Error('iframe not available');
    }

    this.iframe.contentWindow.postMessage(message, this.config.targetOrigin);
  }

  /**
   * Handle response to pending request
   */
  private handleResponse(response: Response): void {
    const pending = this.pendingRequests.get(response.id);
    if (!pending) return;

    clearTimeout(pending.timeout);
    this.pendingRequests.delete(response.id);

    if (response.success) {
      pending.resolve(response);
    } else {
      pending.reject(new Error(response.error || 'Unknown error'));
    }
  }

  /**
   * Handle incoming message
   */
  private async handleIncomingMessage(message: Message): Promise<void> {
    const handlers = this.messageHandlers.get(message.type);
    if (!handlers) {
      console.warn(`No handlers registered for message type: ${message.type}`);
      return;
    }

    for (const handler of handlers) {
      try {
        await handler(message);
      } catch (error) {
        console.error(`Error in message handler for ${message.type}:`, error);
      }
    }
  }

  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${++this.messageCounter}`;
  }

  /**
   * Validate message structure
   */
  private isValidMessage(message: unknown): message is Message {
    if (typeof message !== 'object' || message === null) {
      return false;
    }

    const msg = message as Record<string, unknown>;
    // For responses, we only need id and success
    if ('success' in msg) {
      return typeof msg.id === 'string';
    }
    // For regular messages, we need id, type, and timestamp
    return (
      typeof msg.id === 'string' &&
      typeof msg.type === 'string' &&
      typeof msg.timestamp === 'number'
    );
  }
}
