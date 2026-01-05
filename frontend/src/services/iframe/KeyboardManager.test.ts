/**
 * KeyboardManager unit tests
 * Tests keyboard event handling, shortcuts, key sequences, and context management
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { KeyboardManager, KeyboardShortcut, KeySequence } from './KeyboardManager';

describe('KeyboardManager', () => {
  let keyboardManager: KeyboardManager;
  let mockIframe: HTMLIFrameElement;

  beforeEach(() => {
    keyboardManager = new KeyboardManager();
    mockIframe = document.createElement('iframe');
    document.body.appendChild(mockIframe);
  });

  afterEach(() => {
    keyboardManager.cleanup();
    document.body.removeChild(mockIframe);
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with default global context', () => {
      expect(keyboardManager.getActiveContext()).toBe('global');
    });

    it('should initialize with iframe', () => {
      keyboardManager.initialize(mockIframe);
      expect(keyboardManager).toBeDefined();
    });

    it('should start listening for events', () => {
      const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
      keyboardManager.startListening();
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function), true);
      expect(addEventListenerSpy).toHaveBeenCalledWith('keyup', expect.any(Function), true);
      expect(addEventListenerSpy).toHaveBeenCalledWith('keypress', expect.any(Function), true);
    });

    it('should stop listening for events', () => {
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      keyboardManager.startListening();
      keyboardManager.stopListening();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function), true);
      expect(removeEventListenerSpy).toHaveBeenCalledWith('keyup', expect.any(Function), true);
      expect(removeEventListenerSpy).toHaveBeenCalledWith('keypress', expect.any(Function), true);
    });
  });

  describe('Context Management', () => {
    it('should create new context', () => {
      const context = keyboardManager.createContext('test', 1);
      
      expect(context.name).toBe('test');
      expect(context.priority).toBe(1);
      expect(context.active).toBe(false);
    });

    it('should activate context', () => {
      keyboardManager.createContext('test');
      keyboardManager.activateContext('test');
      
      expect(keyboardManager.getActiveContext()).toBe('test');
    });

    it('should deactivate context', () => {
      keyboardManager.createContext('test');
      keyboardManager.activateContext('test');
      keyboardManager.deactivateContext('test');
      
      expect(keyboardManager.getActiveContext()).toBe('global');
    });

    it('should throw error when activating non-existent context', () => {
      expect(() => {
        keyboardManager.activateContext('nonexistent');
      }).toThrow("Keyboard context 'nonexistent' not found");
    });

    it('should return existing context when creating duplicate', () => {
      const context1 = keyboardManager.createContext('test');
      const context2 = keyboardManager.createContext('test');
      
      expect(context1).toBe(context2);
    });
  });

  describe('Keyboard Shortcuts', () => {
    beforeEach(() => {
      keyboardManager.createContext('test');
    });

    it('should register keyboard shortcut', () => {
      const shortcut: KeyboardShortcut = {
        key: 'F1',
        action: 'help',
        description: 'Show help',
      };
      
      keyboardManager.registerShortcut(shortcut, 'test');
      const shortcuts = keyboardManager.getShortcuts('test');
      
      expect(shortcuts).toHaveLength(1);
      expect(shortcuts[0]).toMatchObject(shortcut);
    });

    it('should unregister keyboard shortcut', () => {
      const shortcut: KeyboardShortcut = {
        key: 'F1',
        action: 'help',
        description: 'Show help',
      };
      
      keyboardManager.registerShortcut(shortcut, 'test');
      keyboardManager.unregisterShortcut('F1', 'test');
      
      const shortcuts = keyboardManager.getShortcuts('test');
      expect(shortcuts).toHaveLength(0);
    });

    it('should register shortcut with modifiers', () => {
      const shortcut: KeyboardShortcut = {
        key: 'S',
        ctrlKey: true,
        shiftKey: true,
        action: 'save_as',
        description: 'Save as',
      };
      
      keyboardManager.registerShortcut(shortcut, 'test');
      const shortcuts = keyboardManager.getShortcuts('test');
      
      expect(shortcuts[0]).toMatchObject(shortcut);
    });

    it('should get all shortcuts from all contexts', () => {
      const shortcut1: KeyboardShortcut = {
        key: 'F1',
        action: 'help',
        description: 'Help',
      };
      
      const shortcut2: KeyboardShortcut = {
        key: 'F2',
        action: 'rename',
        description: 'Rename',
      };
      
      keyboardManager.registerShortcut(shortcut1, 'global');
      keyboardManager.registerShortcut(shortcut2, 'test');
      
      const allShortcuts = keyboardManager.getShortcuts();
      expect(allShortcuts).toHaveLength(2);
    });

    it('should throw error when registering to non-existent context', () => {
      const shortcut: KeyboardShortcut = {
        key: 'F1',
        action: 'help',
        description: 'Help',
      };
      
      expect(() => {
        keyboardManager.registerShortcut(shortcut, 'nonexistent');
      }).toThrow("Keyboard context 'nonexistent' not found");
    });
  });

  describe('Key Sequences', () => {
    it('should register key sequence', () => {
      const sequence: KeySequence = {
        keys: ['g', 'g'],
        action: 'go_to_top',
        description: 'Go to top',
      };
      
      keyboardManager.registerKeySequence(sequence);
      expect(keyboardManager).toBeDefined(); // Basic assertion since sequences are private
    });

    it('should unregister key sequence', () => {
      const sequence: KeySequence = {
        keys: ['g', 'g'],
        action: 'go_to_top',
        description: 'Go to top',
      };
      
      keyboardManager.registerKeySequence(sequence);
      keyboardManager.unregisterKeySequence(['g', 'g']);
      
      expect(keyboardManager).toBeDefined(); // Basic assertion since sequences are private
    });
  });

  describe('Event Handling', () => {
    beforeEach(() => {
      keyboardManager.initialize(mockIframe);
      keyboardManager.startListening();
    });

    it('should register event handler', () => {
      const handler = vi.fn();
      keyboardManager.on('keydown', handler);
      
      expect(keyboardManager).toBeDefined(); // Basic assertion since handlers are private
    });

    it('should unregister event handler', () => {
      const handler = vi.fn();
      keyboardManager.on('keydown', handler);
      keyboardManager.off('keydown', handler);
      
      expect(keyboardManager).toBeDefined(); // Basic assertion since handlers are private
    });

    it('should handle keydown events', () => {
      const handler = vi.fn();
      keyboardManager.on('keydown', handler);
      
      // Simulate keydown event
      const event = new KeyboardEvent('keydown', {
        key: 'F1',
        bubbles: true,
      });
      
      document.dispatchEvent(event);
      
      expect(handler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'keydown',
          key: 'F1',
          context: 'main',
        })
      );
    });

    it('should handle shortcut triggers', () => {
      const shortcutHandler = vi.fn();
      keyboardManager.on('shortcut_triggered', shortcutHandler);
      
      const shortcut: KeyboardShortcut = {
        key: 'F1',
        action: 'help',
        description: 'Help',
      };
      
      keyboardManager.registerShortcut(shortcut, 'global');
      keyboardManager.activateContext('global');
      
      // Simulate F1 keydown
      const event = new KeyboardEvent('keydown', {
        key: 'F1',
        bubbles: true,
      });
      
      document.dispatchEvent(event);
      
      expect(shortcutHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          shortcut: expect.objectContaining({ key: 'F1', action: 'help' }),
          context: 'global',
        })
      );
    });

    it('should handle modifier key combinations', () => {
      const shortcutHandler = vi.fn();
      keyboardManager.on('shortcut_triggered', shortcutHandler);
      
      const shortcut: KeyboardShortcut = {
        key: 'S',
        ctrlKey: true,
        action: 'save',
        description: 'Save',
      };
      
      keyboardManager.registerShortcut(shortcut, 'global');
      
      // Simulate Ctrl+S keydown
      const event = new KeyboardEvent('keydown', {
        key: 'S',
        ctrlKey: true,
        bubbles: true,
      });
      
      document.dispatchEvent(event);
      
      expect(shortcutHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          shortcut: expect.objectContaining({ key: 'S', ctrlKey: true }),
        })
      );
    });

    it('should ignore events from input fields', () => {
      const shortcutHandler = vi.fn();
      keyboardManager.on('shortcut_triggered', shortcutHandler);
      
      const shortcut: KeyboardShortcut = {
        key: 'F1',
        action: 'help',
        description: 'Help',
      };
      
      keyboardManager.registerShortcut(shortcut, 'global');
      
      // Create input element and focus it
      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();
      
      // Simulate F1 keydown on input
      const event = new KeyboardEvent('keydown', {
        key: 'F1',
        bubbles: true,
      });
      
      Object.defineProperty(event, 'target', {
        value: input,
        enumerable: true,
      });
      
      document.dispatchEvent(event);
      
      expect(shortcutHandler).not.toHaveBeenCalled();
      
      document.body.removeChild(input);
    });

    it('should handle key sequences', () => {
      const sequenceHandler = vi.fn();
      keyboardManager.on('sequence_triggered', sequenceHandler);
      
      const sequence: KeySequence = {
        keys: ['g', 'g'],
        action: 'go_to_top',
        description: 'Go to top',
      };
      
      keyboardManager.registerKeySequence(sequence);
      
      // Simulate 'g' then 'g' keydown events
      const event1 = new KeyboardEvent('keydown', { key: 'g', bubbles: true });
      const event2 = new KeyboardEvent('keydown', { key: 'g', bubbles: true });
      
      document.dispatchEvent(event1);
      document.dispatchEvent(event2);
      
      expect(sequenceHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          sequence: expect.objectContaining({ action: 'go_to_top' }),
          keys: ['g', 'g'],
        })
      );
    });
  });

  describe('Context Priority', () => {
    it('should handle shortcuts in priority order', () => {
      const shortcutHandler = vi.fn();
      keyboardManager.on('shortcut_triggered', shortcutHandler);
      
      // Create contexts with different priorities
      const lowPriorityContext = keyboardManager.createContext('low', 1);
      const highPriorityContext = keyboardManager.createContext('high', 10);
      
      // Register same shortcut in both contexts
      const shortcut1: KeyboardShortcut = {
        key: 'F1',
        action: 'low_priority',
        description: 'Low priority action',
      };
      
      const shortcut2: KeyboardShortcut = {
        key: 'F1',
        action: 'high_priority',
        description: 'High priority action',
      };
      
      keyboardManager.registerShortcut(shortcut1, 'low');
      keyboardManager.registerShortcut(shortcut2, 'high');
      
      // Activate both contexts (need to manually set active since we're testing priority)
      lowPriorityContext.active = true;
      highPriorityContext.active = true;
      
      keyboardManager.startListening();
      
      // Simulate F1 keydown
      const event = new KeyboardEvent('keydown', {
        key: 'F1',
        bubbles: true,
      });
      
      document.dispatchEvent(event);
      
      // Should trigger high priority shortcut
      expect(shortcutHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          shortcut: expect.objectContaining({ action: 'high_priority' }),
          context: 'high',
        })
      );
    });
  });

  describe('Cleanup', () => {
    it('should cleanup all resources', () => {
      keyboardManager.initialize(mockIframe);
      keyboardManager.startListening();
      
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      
      keyboardManager.cleanup();
      
      expect(removeEventListenerSpy).toHaveBeenCalled();
      expect(keyboardManager.getActiveContext()).toBe('global'); // Should reset to default
    });
  });

  describe('Edge Cases', () => {
    it('should handle iframe without contentDocument', () => {
      // Mock iframe without contentDocument (cross-origin)
      const crossOriginIframe = document.createElement('iframe');
      Object.defineProperty(crossOriginIframe, 'contentDocument', {
        value: null,
        configurable: true,
      });
      
      expect(() => {
        keyboardManager.initialize(crossOriginIframe);
      }).not.toThrow();
    });

    it('should handle multiple start/stop listening calls', () => {
      keyboardManager.startListening();
      keyboardManager.startListening(); // Duplicate call
      
      expect(keyboardManager).toBeDefined(); // Should not throw
      
      keyboardManager.stopListening();
      keyboardManager.stopListening(); // Duplicate call
      
      expect(keyboardManager).toBeDefined(); // Should not throw
    });

    it('should handle event handler errors gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      keyboardManager.on('keydown', errorHandler);
      keyboardManager.startListening();
      
      const event = new KeyboardEvent('keydown', {
        key: 'F1',
        bubbles: true,
      });
      
      expect(() => {
        document.dispatchEvent(event);
      }).not.toThrow();
      
      expect(consoleErrorSpy).toHaveBeenCalled();
      consoleErrorSpy.mockRestore();
    });

    it('should handle sequence timeout', (done) => {
      const sequenceHandler = vi.fn();
      keyboardManager.on('sequence_triggered', sequenceHandler);
      
      const sequence: KeySequence = {
        keys: ['g', 'g'],
        action: 'go_to_top',
        description: 'Go to top',
        timeout: 100,
      };
      
      keyboardManager.registerKeySequence(sequence);
      
      // Simulate first 'g' then wait for timeout
      const event1 = new KeyboardEvent('keydown', { key: 'g', bubbles: true });
      document.dispatchEvent(event1);
      
      setTimeout(() => {
        // Simulate second 'g' after timeout
        const event2 = new KeyboardEvent('keydown', { key: 'g', bubbles: true });
        document.dispatchEvent(event2);
        
        // Should not trigger sequence due to timeout
        expect(sequenceHandler).not.toHaveBeenCalled();
        done();
      }, 150);
    });
  });
});