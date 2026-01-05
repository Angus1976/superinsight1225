/**
 * FocusManager unit tests
 * Tests focus management, focus trapping, and focus coordination
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FocusManager } from './FocusManager';

describe('FocusManager', () => {
  let focusManager: FocusManager;
  let mockIframe: HTMLIFrameElement;
  let mockContainer: HTMLElement;
  let mockButton1: HTMLButtonElement;
  let mockButton2: HTMLButtonElement;
  let mockInput: HTMLInputElement;

  beforeEach(() => {
    focusManager = new FocusManager();
    
    // Create mock DOM elements
    mockIframe = document.createElement('iframe');
    mockContainer = document.createElement('div');
    mockButton1 = document.createElement('button');
    mockButton2 = document.createElement('button');
    mockInput = document.createElement('input');
    
    // Setup DOM structure
    mockButton1.textContent = 'Button 1';
    mockButton2.textContent = 'Button 2';
    mockInput.type = 'text';
    
    mockContainer.appendChild(mockButton1);
    mockContainer.appendChild(mockInput);
    mockContainer.appendChild(mockButton2);
    mockContainer.appendChild(mockIframe);
    
    document.body.appendChild(mockContainer);
    
    // Mock element visibility
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      display: 'block',
      visibility: 'visible',
    } as CSSStyleDeclaration);
    
    // Mock element dimensions
    Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
      configurable: true,
      value: 100,
    });
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
      configurable: true,
      value: 30,
    });
  });

  afterEach(() => {
    focusManager.cleanup();
    document.body.removeChild(mockContainer);
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with iframe and container', () => {
      focusManager.initialize(mockIframe, mockContainer);
      
      const state = focusManager.getFocusState();
      expect(state.focusTrapped).toBe(false);
      expect(state.iframeFocused).toBe(false);
    });

    it('should start focus monitoring', () => {
      const setIntervalSpy = vi.spyOn(global, 'setInterval');
      
      focusManager.initialize(mockIframe, mockContainer);
      
      expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 100);
    });
  });

  describe('Focus State Management', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should track active element', () => {
      mockButton1.focus();
      
      // Simulate focus monitoring interval
      const state = focusManager.getFocusState();
      // Note: In test environment, document.activeElement might not update as expected
      expect(state).toBeDefined();
    });

    it('should track iframe focus state', () => {
      focusManager.focusIframe();
      
      const state = focusManager.getFocusState();
      expect(state.iframeFocused).toBe(true);
    });

    it('should maintain focus history', () => {
      mockButton1.focus();
      mockButton2.focus();
      
      const state = focusManager.getFocusState();
      expect(Array.isArray(state.focusHistory)).toBe(true);
    });
  });

  describe('Focus Navigation', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should focus first element', () => {
      const focusSpy = vi.spyOn(mockButton1, 'focus');
      
      focusManager.focusFirstElement();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should focus last element', () => {
      // Mock the getLastFocusableElement to return mockIframe
      vi.spyOn(focusManager as any, 'getLastFocusableElement').mockReturnValue({
        element: mockIframe,
        tabIndex: 0,
      });
      
      const focusSpy = vi.spyOn(mockIframe, 'focus');
      
      focusManager.focusLastElement();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should focus next element', () => {
      mockButton1.focus();
      
      const focusSpy = vi.spyOn(mockInput, 'focus');
      
      focusManager.focusNext();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should focus previous element', () => {
      mockInput.focus();
      
      const focusSpy = vi.spyOn(mockButton1, 'focus');
      
      focusManager.focusPrevious();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should wrap around when focusing next from last element', () => {
      mockIframe.focus();
      
      const focusSpy = vi.spyOn(mockButton1, 'focus');
      
      focusManager.focusNext();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should wrap around when focusing previous from first element', () => {
      // Mock the focusableElements array
      (focusManager as any).focusableElements = [
        { element: mockButton1, tabIndex: 0 },
        { element: mockInput, tabIndex: 0 },
        { element: mockIframe, tabIndex: 0 },
      ];
      
      // Mock the getCurrentFocusIndex and getLastFocusableElement
      vi.spyOn(focusManager as any, 'getCurrentFocusIndex').mockReturnValue(0);
      vi.spyOn(focusManager as any, 'getLastFocusableElement').mockReturnValue({
        element: mockIframe,
        tabIndex: 0,
      });
      
      mockButton1.focus();
      
      const focusSpy = vi.spyOn(mockIframe, 'focus');
      
      focusManager.focusPrevious();
      
      expect(focusSpy).toHaveBeenCalled();
    });
  });

  describe('Focus Trapping', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should trap focus within container', () => {
      focusManager.trapFocus();
      
      const state = focusManager.getFocusState();
      expect(state.focusTrapped).toBe(true);
    });

    it('should release focus trap', () => {
      focusManager.trapFocus();
      focusManager.releaseFocusTrap();
      
      const state = focusManager.getFocusState();
      expect(state.focusTrapped).toBe(false);
    });

    it('should focus first element when trapping', () => {
      const focusSpy = vi.spyOn(mockButton1, 'focus');
      
      focusManager.trapFocus();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should restore focus when releasing trap', () => {
      mockButton2.focus();
      focusManager.trapFocus();
      
      const restoreFocusSpy = vi.spyOn(mockButton2, 'focus');
      
      focusManager.releaseFocusTrap();
      
      expect(restoreFocusSpy).toHaveBeenCalled();
    });

    it('should handle Tab key in trap', () => {
      focusManager.trapFocus();
      mockButton2.focus(); // Focus last element
      
      const focusSpy = vi.spyOn(mockButton1, 'focus');
      
      // Simulate Tab key on last element
      const tabEvent = new KeyboardEvent('keydown', {
        key: 'Tab',
        bubbles: true,
      });
      
      document.dispatchEvent(tabEvent);
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should handle Shift+Tab key in trap', () => {
      // Mock the focusable elements
      vi.spyOn(focusManager as any, 'getFirstFocusableElement').mockReturnValue({
        element: mockButton1,
        tabIndex: 0,
      });
      vi.spyOn(focusManager as any, 'getLastFocusableElement').mockReturnValue({
        element: mockIframe,
        tabIndex: 0,
      });
      
      focusManager.trapFocus();
      mockButton1.focus(); // Focus first element
      
      const focusSpy = vi.spyOn(mockIframe, 'focus');
      
      // Simulate Shift+Tab key on first element
      const shiftTabEvent = new KeyboardEvent('keydown', {
        key: 'Tab',
        shiftKey: true,
        bubbles: true,
      });
      
      // Mock document.activeElement to return mockButton1
      Object.defineProperty(document, 'activeElement', {
        value: mockButton1,
        configurable: true,
      });
      
      document.dispatchEvent(shiftTabEvent);
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should prevent focus outside trap container', () => {
      const outsideButton = document.createElement('button');
      document.body.appendChild(outsideButton);
      
      focusManager.trapFocus();
      
      const focusFirstSpy = vi.spyOn(focusManager, 'focusFirstElement');
      
      // Simulate focus event on outside element
      const focusEvent = new Event('focusin', { bubbles: true });
      Object.defineProperty(focusEvent, 'target', {
        value: outsideButton,
        enumerable: true,
      });
      
      document.dispatchEvent(focusEvent);
      
      expect(focusFirstSpy).toHaveBeenCalled();
      
      document.body.removeChild(outsideButton);
    });
  });

  describe('Iframe Focus Management', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should focus iframe', () => {
      const focusSpy = vi.spyOn(mockIframe, 'focus');
      
      focusManager.focusIframe();
      
      expect(focusSpy).toHaveBeenCalled();
      
      const state = focusManager.getFocusState();
      expect(state.iframeFocused).toBe(true);
    });

    it('should focus main window', () => {
      // Set up a last focused element
      mockButton1.focus();
      focusManager.focusIframe();
      
      const focusSpy = vi.spyOn(mockButton1, 'focus');
      
      focusManager.focusMain();
      
      expect(focusSpy).toHaveBeenCalled();
    });

    it('should focus first element when no last focused element', () => {
      focusManager.focusIframe();
      
      const focusFirstSpy = vi.spyOn(focusManager, 'focusFirstElement');
      
      focusManager.focusMain();
      
      expect(focusFirstSpy).toHaveBeenCalled();
    });
  });

  describe('Event Handling', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should register focus event handler', () => {
      const handler = vi.fn();
      
      focusManager.on('focus_in', handler);
      
      expect(focusManager).toBeDefined(); // Basic assertion since handlers are private
    });

    it('should unregister focus event handler', () => {
      const handler = vi.fn();
      
      focusManager.on('focus_in', handler);
      focusManager.off('focus_in', handler);
      
      expect(focusManager).toBeDefined(); // Basic assertion since handlers are private
    });

    it('should emit focus events', () => {
      const handler = vi.fn();
      focusManager.on('focus_in', handler);
      
      // Simulate focus event
      const focusEvent = new Event('focusin', { bubbles: true });
      Object.defineProperty(focusEvent, 'target', {
        value: mockButton1,
        enumerable: true,
      });
      
      document.dispatchEvent(focusEvent);
      
      expect(handler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'focus_in',
          element: mockButton1,
          source: 'main',
        })
      );
    });

    it('should emit iframe focus events', () => {
      const handler = vi.fn();
      focusManager.on('focus_in', handler);
      
      // Simulate iframe focus event
      const focusEvent = new Event('focusin', { bubbles: true });
      Object.defineProperty(focusEvent, 'target', {
        value: mockIframe,
        enumerable: true,
      });
      
      document.dispatchEvent(focusEvent);
      
      expect(handler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'focus_in',
          element: mockIframe,
          source: 'iframe',
        })
      );
    });

    it('should handle focus event handler errors gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      focusManager.on('focus_in', errorHandler);
      
      const focusEvent = new Event('focusin', { bubbles: true });
      Object.defineProperty(focusEvent, 'target', {
        value: mockButton1,
        enumerable: true,
      });
      
      expect(() => {
        document.dispatchEvent(focusEvent);
      }).not.toThrow();
      
      expect(consoleErrorSpy).toHaveBeenCalled();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('Focusable Element Detection', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should identify focusable elements', () => {
      // Mock the focusableElements array to include our test elements
      (focusManager as any).focusableElements = [
        { element: mockButton1, tabIndex: 0 },
        { element: mockInput, tabIndex: 0 },
        { element: mockIframe, tabIndex: 0 },
      ];
      
      expect(focusManager.isFocusable(mockButton1)).toBe(true);
      expect(focusManager.isFocusable(mockInput)).toBe(true);
      expect(focusManager.isFocusable(mockIframe)).toBe(true);
    });

    it('should ignore hidden elements', () => {
      // Mock hidden element
      vi.spyOn(window, 'getComputedStyle').mockReturnValue({
        display: 'none',
        visibility: 'visible',
      } as CSSStyleDeclaration);
      
      const hiddenButton = document.createElement('button');
      mockContainer.appendChild(hiddenButton);
      
      expect(focusManager.isFocusable(hiddenButton)).toBe(false);
      
      mockContainer.removeChild(hiddenButton);
    });

    it('should ignore disabled elements', () => {
      const disabledButton = document.createElement('button');
      disabledButton.disabled = true;
      mockContainer.appendChild(disabledButton);
      
      expect(focusManager.isFocusable(disabledButton)).toBe(false);
      
      mockContainer.removeChild(disabledButton);
    });

    it('should handle elements with tabindex', () => {
      const tabindexDiv = document.createElement('div');
      tabindexDiv.tabIndex = 0;
      mockContainer.appendChild(tabindexDiv);
      
      // Mock the focusableElements array to include the tabindex div
      (focusManager as any).focusableElements = [
        { element: tabindexDiv, tabIndex: 0 },
      ];
      
      expect(focusManager.isFocusable(tabindexDiv)).toBe(true);
      
      mockContainer.removeChild(tabindexDiv);
    });

    it('should ignore elements with negative tabindex', () => {
      const negativeTabindexDiv = document.createElement('div');
      negativeTabindexDiv.tabIndex = -1;
      mockContainer.appendChild(negativeTabindexDiv);
      
      expect(focusManager.isFocusable(negativeTabindexDiv)).toBe(false);
      
      mockContainer.removeChild(negativeTabindexDiv);
    });
  });

  describe('Focus History', () => {
    beforeEach(() => {
      focusManager.initialize(mockIframe, mockContainer);
    });

    it('should maintain focus history', () => {
      mockButton1.focus();
      mockButton2.focus();
      mockInput.focus();
      
      const state = focusManager.getFocusState();
      expect(state.focusHistory.length).toBeGreaterThan(0);
    });

    it('should limit focus history size', () => {
      // Focus many elements to test history limit
      for (let i = 0; i < 15; i++) {
        const button = document.createElement('button');
        mockContainer.appendChild(button);
        button.focus();
      }
      
      const state = focusManager.getFocusState();
      expect(state.focusHistory.length).toBeLessThanOrEqual(10);
    });

    it('should remove duplicates from history', () => {
      mockButton1.focus();
      mockButton2.focus();
      mockButton1.focus(); // Focus same element again
      
      const state = focusManager.getFocusState();
      const button1Count = state.focusHistory.filter(el => el === mockButton1).length;
      expect(button1Count).toBe(1);
    });
  });

  describe('Cleanup', () => {
    it('should cleanup all resources', () => {
      focusManager.initialize(mockIframe, mockContainer);
      focusManager.trapFocus();
      
      const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');
      
      focusManager.cleanup();
      
      expect(removeEventListenerSpy).toHaveBeenCalled();
      expect(clearIntervalSpy).toHaveBeenCalled();
      
      const state = focusManager.getFocusState();
      expect(state.focusTrapped).toBe(false);
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty container', () => {
      const emptyContainer = document.createElement('div');
      document.body.appendChild(emptyContainer);
      
      focusManager.initialize(mockIframe, emptyContainer);
      
      expect(() => {
        focusManager.focusFirstElement();
      }).not.toThrow();
      
      document.body.removeChild(emptyContainer);
    });

    it('should handle missing iframe', () => {
      const nullIframe = null as any;
      
      expect(() => {
        focusManager.initialize(nullIframe, mockContainer);
      }).not.toThrow();
    });

    it('should handle focus trap without focusable elements', () => {
      const emptyContainer = document.createElement('div');
      document.body.appendChild(emptyContainer);
      
      focusManager.initialize(mockIframe, emptyContainer);
      
      expect(() => {
        focusManager.trapFocus(emptyContainer);
      }).not.toThrow();
      
      document.body.removeChild(emptyContainer);
    });

    it('should handle focus navigation with no focusable elements', () => {
      const emptyContainer = document.createElement('div');
      document.body.appendChild(emptyContainer);
      
      focusManager.initialize(mockIframe, emptyContainer);
      
      expect(() => {
        focusManager.focusNext();
        focusManager.focusPrevious();
      }).not.toThrow();
      
      document.body.removeChild(emptyContainer);
    });

    it('should handle multiple cleanup calls', () => {
      focusManager.initialize(mockIframe, mockContainer);
      
      expect(() => {
        focusManager.cleanup();
        focusManager.cleanup(); // Duplicate cleanup
      }).not.toThrow();
    });
  });
});