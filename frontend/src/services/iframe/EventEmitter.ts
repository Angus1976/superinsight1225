/**
 * EventEmitter - Advanced event handling system for iframe integration
 * 
 * Features:
 * - Event listening and cancellation
 * - Event priority support
 * - Event history recording
 * - Async event handling
 * - Once-only event subscriptions
 */

import {
  EventRecord,
  EventHandler,
  EventEmitterConfig,
  EventSubscription,
  AnnotationEvent,
} from './types';

export class EventEmitter {
  private subscriptions: Map<string, EventSubscription[]> = new Map();
  private history: EventRecord[] = [];
  private config: Required<EventEmitterConfig>;
  private subscriptionIdCounter = 0;

  constructor(config: EventEmitterConfig = {}) {
    this.config = {
      maxHistorySize: config.maxHistorySize ?? 1000,
      enablePriority: config.enablePriority ?? true,
      enableAsync: config.enableAsync ?? true,
      defaultPriority: config.defaultPriority ?? 0,
    };
  }

  /**
   * Subscribe to an event
   */
  on(event: string, handler: EventHandler, priority: number = this.config.defaultPriority): string {
    return this.subscribe(event, handler, priority, false);
  }

  /**
   * Subscribe to an event (one-time only)
   */
  once(event: string, handler: EventHandler, priority: number = this.config.defaultPriority): string {
    return this.subscribe(event, handler, priority, true);
  }

  /**
   * Unsubscribe from an event
   */
  off(event: string, handlerOrId?: EventHandler | string): boolean {
    const subscriptions = this.subscriptions.get(event);
    if (!subscriptions) {
      return false;
    }

    if (!handlerOrId) {
      // Remove all subscriptions for this event
      this.subscriptions.delete(event);
      return true;
    }

    const isId = typeof handlerOrId === 'string';
    const index = subscriptions.findIndex(sub => 
      isId ? sub.id === handlerOrId : sub.handler === handlerOrId
    );

    if (index !== -1) {
      subscriptions.splice(index, 1);
      if (subscriptions.length === 0) {
        this.subscriptions.delete(event);
      }
      return true;
    }

    return false;
  }

  /**
   * Emit an event to all subscribers
   */
  async emit(event: string, data: unknown, source: 'iframe' | 'main' = 'main'): Promise<void> {
    const eventRecord: EventRecord = {
      event,
      data,
      timestamp: Date.now(),
      source,
      priority: 0,
      id: this.generateEventId(),
    };

    // Add to history regardless of subscribers
    this.addToHistory(eventRecord);

    const subscriptions = this.subscriptions.get(event);
    if (!subscriptions || subscriptions.length === 0) {
      return;
    }

    // Sort by priority if enabled
    const sortedSubscriptions = this.config.enablePriority
      ? [...subscriptions].sort((a, b) => b.priority - a.priority)
      : subscriptions;

    // Execute handlers
    const promises: Promise<void>[] = [];

    for (const subscription of sortedSubscriptions) {
      if (!subscription.active) {
        continue;
      }

      const executeHandler = async () => {
        try {
          await subscription.handler(data, eventRecord);
          
          // Remove one-time subscriptions
          if (subscription.once) {
            this.off(event, subscription.id);
          }
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
          // Emit error event
          this.emit('error', { originalEvent: event, error, subscription: subscription.id });
        }
      };

      if (this.config.enableAsync) {
        promises.push(executeHandler());
      } else {
        await executeHandler();
      }
    }

    // Wait for all async handlers to complete
    if (promises.length > 0) {
      await Promise.all(promises);
    }
  }

  /**
   * Get event history
   */
  getHistory(event?: string): EventRecord[] {
    if (event) {
      return this.history.filter(record => record.event === event);
    }
    return [...this.history];
  }

  /**
   * Clear event history
   */
  clearHistory(event?: string): void {
    if (event) {
      this.history = this.history.filter(record => record.event !== event);
    } else {
      this.history = [];
    }
  }

  /**
   * Get active subscriptions
   */
  getSubscriptions(event?: string): EventSubscription[] {
    if (event) {
      return this.subscriptions.get(event) || [];
    }

    const allSubscriptions: EventSubscription[] = [];
    for (const subscriptions of this.subscriptions.values()) {
      allSubscriptions.push(...subscriptions);
    }
    return allSubscriptions;
  }

  /**
   * Get subscription count
   */
  getSubscriptionCount(event?: string): number {
    if (event) {
      return this.subscriptions.get(event)?.length || 0;
    }

    let total = 0;
    for (const subscriptions of this.subscriptions.values()) {
      total += subscriptions.length;
    }
    return total;
  }

  /**
   * Enable/disable a subscription
   */
  toggleSubscription(subscriptionId: string, active: boolean): boolean {
    for (const subscriptions of this.subscriptions.values()) {
      const subscription = subscriptions.find(sub => sub.id === subscriptionId);
      if (subscription) {
        subscription.active = active;
        return true;
      }
    }
    return false;
  }

  /**
   * Remove all subscriptions and clear history
   */
  destroy(): void {
    this.subscriptions.clear();
    this.history = [];
  }

  /**
   * Get event statistics
   */
  getStats(): {
    totalSubscriptions: number;
    activeSubscriptions: number;
    historySize: number;
    eventTypes: string[];
  } {
    let totalSubscriptions = 0;
    let activeSubscriptions = 0;
    const eventTypes = new Set<string>();

    for (const [event, subscriptions] of this.subscriptions.entries()) {
      eventTypes.add(event);
      totalSubscriptions += subscriptions.length;
      activeSubscriptions += subscriptions.filter(sub => sub.active).length;
    }

    return {
      totalSubscriptions,
      activeSubscriptions,
      historySize: this.history.length,
      eventTypes: Array.from(eventTypes),
    };
  }

  private subscribe(
    event: string,
    handler: EventHandler,
    priority: number,
    once: boolean
  ): string {
    const subscription: EventSubscription = {
      id: this.generateSubscriptionId(),
      event,
      handler,
      priority,
      once,
      active: true,
    };

    if (!this.subscriptions.has(event)) {
      this.subscriptions.set(event, []);
    }

    this.subscriptions.get(event)!.push(subscription);
    return subscription.id;
  }

  private addToHistory(record: EventRecord): void {
    this.history.push(record);

    // Trim history if it exceeds max size
    if (this.history.length > this.config.maxHistorySize) {
      this.history = this.history.slice(-this.config.maxHistorySize);
    }
  }

  private generateSubscriptionId(): string {
    return `sub_${++this.subscriptionIdCounter}_${Date.now()}`;
  }

  private generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Export singleton instance for global use
export const globalEventEmitter = new EventEmitter();

// Export annotation event constants
export { AnnotationEvent };