/**
 * KeyboardManager - Advanced keyboard event handling and shortcut management
 * Handles event bubbling control, key sequence detection, and context-aware shortcuts
 */

export interface KeySequence {
  keys: string[];
  timeout?: number;
  action: string;
  description: string;
  context?: 'global' | 'iframe' | 'main';
}

export interface KeyboardContext {
  name: string;
  active: boolean;
  shortcuts: Map<string, KeyboardShortcut>;
  priority: number;
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  metaKey?: boolean;
  action: string;
  description: string;
  context?: string;
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export interface KeyboardEvent {
  type: 'keydown' | 'keyup' | 'keypress';
  key: string;
  code: string;
  ctrlKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
  target: HTMLElement;
  context: string;
  timestamp: number;
}

export type KeyboardEventHandler = (event: KeyboardEvent) => boolean | void;

export class KeyboardManager {
  private contexts: Map<string, KeyboardContext> = new Map();
  private activeContext: string = 'global';
  private eventHandlers: Map<string, Set<KeyboardEventHandler>> = new Map();
  private keySequences: Map<string, KeySequence> = new Map();
  private currentSequence: string[] = [];
  private sequenceTimeout: NodeJS.Timeout | null = null;
  private isListening = false;
  private iframe: HTMLIFrameElement | null = null;

  constructor() {
    this.initializeDefaultContext();
  }

  /**
   * Initialize keyboard manager with iframe
   */
  initialize(iframe: HTMLIFrameElement): void {
    this.iframe = iframe;
    this.startListening();
  }

  /**
   * Cleanup keyboard manager
   */
  cleanup(): void {
    this.stopListening();
    this.contexts.clear();
    this.eventHandlers.clear();
    this.keySequences.clear();
    this.clearSequenceTimeout();
    this.iframe = null;
  }

  /**
   * Start listening for keyboard events
   */
  startListening(): void {
    if (this.isListening) {
      return;
    }

    document.addEventListener('keydown', this.handleKeyDown, true);
    document.addEventListener('keyup', this.handleKeyUp, true);
    document.addEventListener('keypress', this.handleKeyPress, true);

    // Listen for iframe keyboard events
    if (this.iframe) {
      try {
        const iframeDocument = this.iframe.contentDocument;
        if (iframeDocument) {
          iframeDocument.addEventListener('keydown', this.handleIframeKeyDown, true);
          iframeDocument.addEventListener('keyup', this.handleIframeKeyUp, true);
        }
      } catch (error) {
        // Cross-origin iframe - can't access contentDocument
        console.warn('Cannot access iframe document for keyboard events:', error);
      }
    }

    this.isListening = true;
  }

  /**
   * Stop listening for keyboard events
   */
  stopListening(): void {
    if (!this.isListening) {
      return;
    }

    document.removeEventListener('keydown', this.handleKeyDown, true);
    document.removeEventListener('keyup', this.handleKeyUp, true);
    document.removeEventListener('keypress', this.handleKeyPress, true);

    // Remove iframe listeners
    if (this.iframe) {
      try {
        const iframeDocument = this.iframe.contentDocument;
        if (iframeDocument) {
          iframeDocument.removeEventListener('keydown', this.handleIframeKeyDown, true);
          iframeDocument.removeEventListener('keyup', this.handleIframeKeyUp, true);
        }
      } catch (error) {
        // Ignore cross-origin errors
      }
    }

    this.isListening = false;
  }

  /**
   * Create or get keyboard context
   */
  createContext(name: string, priority: number = 0): KeyboardContext {
    if (this.contexts.has(name)) {
      return this.contexts.get(name)!;
    }

    const context: KeyboardContext = {
      name,
      active: false,
      shortcuts: new Map(),
      priority,
    };

    this.contexts.set(name, context);
    return context;
  }

  /**
   * Activate keyboard context
   */
  activateContext(name: string): void {
    const context = this.contexts.get(name);
    if (!context) {
      throw new Error(`Keyboard context '${name}' not found`);
    }

    // Deactivate current context
    const currentContext = this.contexts.get(this.activeContext);
    if (currentContext) {
      currentContext.active = false;
    }

    // Activate new context
    context.active = true;
    this.activeContext = name;
  }

  /**
   * Deactivate keyboard context
   */
  deactivateContext(name: string): void {
    const context = this.contexts.get(name);
    if (context) {
      context.active = false;
    }

    if (this.activeContext === name) {
      this.activeContext = 'global';
      const globalContext = this.contexts.get('global');
      if (globalContext) {
        globalContext.active = true;
      }
    }
  }

  /**
   * Register keyboard shortcut
   */
  registerShortcut(shortcut: KeyboardShortcut, contextName: string = 'global'): void {
    const context = this.contexts.get(contextName);
    if (!context) {
      throw new Error(`Keyboard context '${contextName}' not found`);
    }

    const key = this.getShortcutKey(shortcut);
    context.shortcuts.set(key, { ...shortcut, context: contextName });
  }

  /**
   * Unregister keyboard shortcut
   */
  unregisterShortcut(key: string, contextName: string = 'global'): void {
    const context = this.contexts.get(contextName);
    if (context) {
      context.shortcuts.delete(key);
    }
  }

  /**
   * Register key sequence
   */
  registerKeySequence(sequence: KeySequence): void {
    const key = sequence.keys.join('+');
    this.keySequences.set(key, sequence);
  }

  /**
   * Unregister key sequence
   */
  unregisterKeySequence(keys: string[]): void {
    const key = keys.join('+');
    this.keySequences.delete(key);
  }

  /**
   * Register event handler
   */
  on(event: string, handler: KeyboardEventHandler): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);
  }

  /**
   * Unregister event handler
   */
  off(event: string, handler: KeyboardEventHandler): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Get all shortcuts for context
   */
  getShortcuts(contextName?: string): KeyboardShortcut[] {
    if (contextName) {
      const context = this.contexts.get(contextName);
      return context ? Array.from(context.shortcuts.values()) : [];
    }

    // Return all shortcuts from all contexts
    const allShortcuts: KeyboardShortcut[] = [];
    this.contexts.forEach(context => {
      allShortcuts.push(...Array.from(context.shortcuts.values()));
    });
    return allShortcuts;
  }

  /**
   * Get active context name
   */
  getActiveContext(): string {
    return this.activeContext;
  }

  /**
   * Check if key combination is pressed
   */
  isKeyPressed(key: string, modifiers?: Partial<Pick<KeyboardShortcut, 'ctrlKey' | 'altKey' | 'shiftKey' | 'metaKey'>>): boolean {
    // This would need to track currently pressed keys
    // For now, return false as this requires more complex state tracking
    return false;
  }

  /**
   * Initialize default global context
   */
  private initializeDefaultContext(): void {
    const globalContext = this.createContext('global', 0);
    globalContext.active = true;
  }

  /**
   * Handle keydown events
   */
  private handleKeyDown = (event: Event): void => {
    const keyboardEvent = this.createKeyboardEvent('keydown', event as globalThis.KeyboardEvent, 'main');
    this.processKeyboardEvent(keyboardEvent, event as globalThis.KeyboardEvent);
  };

  /**
   * Handle keyup events
   */
  private handleKeyUp = (event: Event): void => {
    const keyboardEvent = this.createKeyboardEvent('keyup', event as globalThis.KeyboardEvent, 'main');
    this.processKeyboardEvent(keyboardEvent, event as globalThis.KeyboardEvent);
  };

  /**
   * Handle keypress events
   */
  private handleKeyPress = (event: Event): void => {
    const keyboardEvent = this.createKeyboardEvent('keypress', event as globalThis.KeyboardEvent, 'main');
    this.processKeyboardEvent(keyboardEvent, event as globalThis.KeyboardEvent);
  };

  /**
   * Handle iframe keydown events
   */
  private handleIframeKeyDown = (event: Event): void => {
    const keyboardEvent = this.createKeyboardEvent('keydown', event as globalThis.KeyboardEvent, 'iframe');
    this.processKeyboardEvent(keyboardEvent, event as globalThis.KeyboardEvent);
  };

  /**
   * Handle iframe keyup events
   */
  private handleIframeKeyUp = (event: Event): void => {
    const keyboardEvent = this.createKeyboardEvent('keyup', event as globalThis.KeyboardEvent, 'iframe');
    this.processKeyboardEvent(keyboardEvent, event as globalThis.KeyboardEvent);
  };

  /**
   * Create keyboard event object
   */
  private createKeyboardEvent(type: KeyboardEvent['type'], event: globalThis.KeyboardEvent, context: string): KeyboardEvent {
    return {
      type,
      key: event.key,
      code: event.code,
      ctrlKey: event.ctrlKey,
      altKey: event.altKey,
      shiftKey: event.shiftKey,
      metaKey: event.metaKey,
      target: event.target as HTMLElement,
      context,
      timestamp: Date.now(),
    };
  }

  /**
   * Process keyboard event
   */
  private processKeyboardEvent(keyboardEvent: KeyboardEvent, originalEvent: globalThis.KeyboardEvent): void {
    // Skip if typing in input fields (unless specifically handled)
    if (this.isTypingInInput(keyboardEvent.target)) {
      return;
    }

    // Emit event to handlers
    this.emitEvent(keyboardEvent.type, keyboardEvent);

    // Only process shortcuts on keydown
    if (keyboardEvent.type !== 'keydown') {
      return;
    }

    // Check for key sequences
    this.processKeySequence(keyboardEvent);

    // Check for shortcuts in active contexts
    const handled = this.processShortcuts(keyboardEvent, originalEvent);

    // If handled, prevent default and stop propagation if configured
    if (handled) {
      // Event control is handled by individual shortcuts
    }
  }

  /**
   * Process key sequences
   */
  private processKeySequence(event: KeyboardEvent): void {
    this.currentSequence.push(event.key);
    
    // Clear timeout
    this.clearSequenceTimeout();

    // Check for matching sequences
    const sequenceKey = this.currentSequence.join('+');
    const sequence = this.keySequences.get(sequenceKey);

    if (sequence) {
      // Execute sequence action
      this.emitEvent('sequence_triggered', { sequence, keys: this.currentSequence });
      this.currentSequence = [];
      return;
    }

    // Check if current sequence could be part of a longer sequence
    const hasPartialMatch = Array.from(this.keySequences.keys()).some(key => 
      key.startsWith(sequenceKey + '+')
    );

    if (!hasPartialMatch) {
      // No partial match, reset sequence
      this.currentSequence = [event.key];
    }

    // Set timeout to reset sequence
    const timeout = 1000; // 1 second default
    this.sequenceTimeout = setTimeout(() => {
      this.currentSequence = [];
    }, timeout);
  }

  /**
   * Process shortcuts
   */
  private processShortcuts(event: KeyboardEvent, originalEvent: globalThis.KeyboardEvent): boolean {
    // Get contexts sorted by priority (highest first)
    const sortedContexts = Array.from(this.contexts.values())
      .filter(context => context.active)
      .sort((a, b) => b.priority - a.priority);

    for (const context of sortedContexts) {
      for (const [key, shortcut] of context.shortcuts) {
        if (this.matchesShortcut(event, shortcut)) {
          // Handle event control
          if (shortcut.preventDefault !== false) {
            originalEvent.preventDefault();
          }
          if (shortcut.stopPropagation) {
            originalEvent.stopPropagation();
          }

          // Emit shortcut event
          this.emitEvent('shortcut_triggered', { shortcut, event, context: context.name });
          
          return true; // Handled
        }
      }
    }

    return false; // Not handled
  }

  /**
   * Check if event matches shortcut
   */
  private matchesShortcut(event: KeyboardEvent, shortcut: KeyboardShortcut): boolean {
    return (
      event.key === shortcut.key &&
      !!event.ctrlKey === !!shortcut.ctrlKey &&
      !!event.altKey === !!shortcut.altKey &&
      !!event.shiftKey === !!shortcut.shiftKey &&
      !!event.metaKey === !!shortcut.metaKey
    );
  }

  /**
   * Check if typing in input field
   */
  private isTypingInInput(target: HTMLElement): boolean {
    if (!target || !target.tagName) {
      return false;
    }
    
    const tagName = target.tagName.toLowerCase();
    return (
      tagName === 'input' ||
      tagName === 'textarea' ||
      target.isContentEditable ||
      target.getAttribute('role') === 'textbox'
    );
  }

  /**
   * Get shortcut key string
   */
  private getShortcutKey(shortcut: KeyboardShortcut): string {
    const parts: string[] = [];
    
    if (shortcut.ctrlKey) parts.push('Ctrl');
    if (shortcut.altKey) parts.push('Alt');
    if (shortcut.shiftKey) parts.push('Shift');
    if (shortcut.metaKey) parts.push('Meta');
    parts.push(shortcut.key);
    
    return parts.join('+');
  }

  /**
   * Clear sequence timeout
   */
  private clearSequenceTimeout(): void {
    if (this.sequenceTimeout) {
      clearTimeout(this.sequenceTimeout);
      this.sequenceTimeout = null;
    }
  }

  /**
   * Emit event to handlers
   */
  private emitEvent(event: string, data: unknown): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data as KeyboardEvent);
        } catch (error) {
          console.error(`Error in keyboard event handler for ${event}:`, error);
        }
      });
    }
  }
}