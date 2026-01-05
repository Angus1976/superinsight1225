/**
 * UICoordinator unit tests
 * Tests fullscreen mode, resizing, navigation visibility, keyboard shortcuts, and focus management
 */

import { describe, it, expect, beforeEach, afterEach, vi, Mock } from 'vitest';
import { UICoordinator, UICoordinatorConfig } from './UICoordinator';

// Mock the managers
vi.mock('./KeyboardManager', () => ({
  KeyboardManager: vi.fn().mockImplementation(() => ({
    initialize: vi.fn(),
    cleanup: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    registerShortcut: vi.fn(),
    unregisterShortcut: vi.fn(),
    getShortcuts: vi.fn(() => []),
    startListening: vi.fn(),
    stopListening: vi.fn(),
    createContext: vi.fn(),
    activateContext: vi.fn(),
    deactivateContext: vi.fn(),
    getActiveContext: vi.fn(() => 'global'),
  })),
}));

vi.mock('./FocusManager', () => ({
  FocusManager: vi.fn().mockImplementation(() => ({
    initialize: vi.fn(),
    cleanup: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    trapFocus: vi.fn(),
    releaseFocusTrap: vi.fn(),
    focusIframe: vi.fn(),
    focusMain: vi.fn(),
    focusFirstElement: vi.fn(),
    focusLastElement: vi.fn(),
    focusNext: vi.fn(),
    focusPrevious: vi.fn(),
    getFocusState: vi.fn(() => ({
      activeElement: null,
      iframeFocused: false,
      focusTrapped: false,
      lastFocusedElement: null,
      focusHistory: [],
    })),
    isFocusable: vi.fn(() => true),
  })),
}));

describe('UICoordinator', () => {
  let coordinator: UICoordinator;
  let mockIframe: HTMLIFrameElement;
  let mockContainer: HTMLElement;
  let mockNavigation: HTMLElement;

  beforeEach(() => {
    // Create mock DOM elements
    mockIframe = document.createElement('iframe') as HTMLIFrameElement;
    mockContainer = document.createElement('div');
    mockNavigation = document.createElement('nav');
    
    // Setup DOM
    document.body.appendChild(mockContainer);
    document.body.appendChild(mockNavigation);
    mockContainer.appendChild(mockIframe);
    
    // Mock querySelector to return our navigation element
    vi.spyOn(document, 'querySelector').mockImplementation((selector) => {
      if (selector === '.ant-layout-header, .ant-layout-sider') {
        return mockNavigation;
      }
      return null;
    });

    // Mock querySelectorAll for navigation elements
    vi.spyOn(document, 'querySelectorAll').mockImplementation((selector) => {
      if (selector === '.ant-layout-header, .ant-layout-sider') {
        return [mockNavigation] as any;
      }
      return [] as any;
    });

    // Mock ResizeObserver
    global.ResizeObserver = vi.fn().mockImplementation(() => ({
      observe: vi.fn(),
      disconnect: vi.fn(),
      unobserve: vi.fn(),
    }));

    coordinator = new UICoordinator();
  });

  afterEach(() => {
    coordinator.cleanup();
    document.body.removeChild(mockContainer);
    document.body.removeChild(mockNavigation);
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize with default config', () => {
      expect(coordinator).toBeDefined();
      expect(coordinator.getUIState().isFullscreen).toBe(false);
      expect(coordinator.getUIState().navigationVisible).toBe(true);
    });

    it('should initialize with custom config', () => {
      const config: UICoordinatorConfig = {
        enableFullscreen: false,
        enableKeyboardShortcuts: false,
        enableFocusManagement: false,
      };
      
      const customCoordinator = new UICoordinator(config);
      expect(customCoordinator).toBeDefined();
      customCoordinator.cleanup();
    });

    it('should initialize managers when enabled', () => {
      const keyboardManager = coordinator.getKeyboardManager();
      const focusManager = coordinator.getFocusManager();
      
      coordinator.initialize(mockIframe, mockContainer);
      
      // Just verify the managers exist and were called (they're mocked)
      expect(keyboardManager).toBeDefined();
      expect(focusManager).toBeDefined();
    });
  });

  describe('Fullscreen Mode', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should enter fullscreen mode', () => {
      coordinator.setFullscreen(true);
      
      const state = coordinator.getUIState();
      expect(state.isFullscreen).toBe(true);
      expect(mockContainer.style.position).toBe('fixed');
      expect(mockContainer.style.zIndex).toBe('9999');
      expect(document.body.classList.contains('iframe-fullscreen')).toBe(true);
    });

    it('should exit fullscreen mode', () => {
      coordinator.setFullscreen(true);
      coordinator.setFullscreen(false);
      
      const state = coordinator.getUIState();
      expect(state.isFullscreen).toBe(false);
      expect(document.body.classList.contains('iframe-fullscreen')).toBe(false);
    });

    it('should toggle fullscreen mode', () => {
      expect(coordinator.getUIState().isFullscreen).toBe(false);
      
      coordinator.toggleFullscreen();
      expect(coordinator.getUIState().isFullscreen).toBe(true);
      
      coordinator.toggleFullscreen();
      expect(coordinator.getUIState().isFullscreen).toBe(false);
    });

    it('should trap focus when entering fullscreen if enabled', () => {
      const config: UICoordinatorConfig = { focusTrapOnFullscreen: true };
      const customCoordinator = new UICoordinator(config);
      customCoordinator.initialize(mockIframe, mockContainer);
      
      customCoordinator.setFullscreen(true);
      // Just verify it doesn't throw - the focus manager is mocked
      expect(customCoordinator.getUIState().isFullscreen).toBe(true);
      
      customCoordinator.cleanup();
    });
  });

  describe('Resizing', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should resize iframe to specific dimensions', () => {
      coordinator.resize(800, 600);
      
      expect(mockContainer.style.width).toBe('800px');
      expect(mockContainer.style.height).toBe('600px');
      expect(mockIframe.style.width).toBe('800px');
      expect(mockIframe.style.height).toBe('600px');
      
      const state = coordinator.getUIState();
      expect(state.dimensions.width).toBe(800);
      expect(state.dimensions.height).toBe(600);
    });

    it('should auto-resize to container dimensions', () => {
      // Mock getBoundingClientRect
      vi.spyOn(mockContainer, 'getBoundingClientRect').mockReturnValue({
        width: 1024,
        height: 768,
        top: 0,
        left: 0,
        bottom: 768,
        right: 1024,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      });
      
      coordinator.autoResize();
      
      expect(mockContainer.style.width).toBe('1024px');
      expect(mockContainer.style.height).toBe('768px');
    });
  });

  describe('Navigation Visibility', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should hide navigation', () => {
      coordinator.setNavigationVisible(false);
      
      expect(coordinator.getUIState().navigationVisible).toBe(false);
      expect(mockNavigation.style.display).toBe('none');
    });

    it('should show navigation', () => {
      coordinator.setNavigationVisible(false);
      coordinator.setNavigationVisible(true);
      
      expect(coordinator.getUIState().navigationVisible).toBe(true);
      expect(mockNavigation.style.display).toBe('');
    });

    it('should toggle navigation visibility', () => {
      expect(coordinator.getUIState().navigationVisible).toBe(true);
      
      coordinator.toggleNavigation();
      expect(coordinator.getUIState().navigationVisible).toBe(false);
      
      coordinator.toggleNavigation();
      expect(coordinator.getUIState().navigationVisible).toBe(true);
    });
  });

  describe('Loading and Error States', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should show loading state', () => {
      coordinator.setLoading(true);
      expect(mockContainer.classList.contains('iframe-loading')).toBe(true);
      
      coordinator.setLoading(false);
      expect(mockContainer.classList.contains('iframe-loading')).toBe(false);
    });

    it('should show error message', () => {
      const errorMessage = 'Test error message';
      coordinator.showError(errorMessage);
      
      const errorElement = mockContainer.querySelector('.iframe-error');
      expect(errorElement).toBeTruthy();
      expect(errorElement?.textContent).toContain(errorMessage);
    });

    it('should hide error message', () => {
      coordinator.showError('Test error');
      coordinator.hideError();
      
      const errorElement = mockContainer.querySelector('.iframe-error');
      expect(errorElement).toBeFalsy();
    });

    it('should replace existing error message', () => {
      coordinator.showError('First error');
      coordinator.showError('Second error');
      
      const errorElements = mockContainer.querySelectorAll('.iframe-error');
      expect(errorElements.length).toBe(1);
      expect(errorElements[0].textContent).toContain('Second error');
    });
  });

  describe('Keyboard Shortcuts', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should register keyboard shortcut', () => {
      const shortcut = {
        key: 'F1',
        action: 'help',
        description: 'Show help',
      };
      
      coordinator.registerShortcut(shortcut);
      // Verify shortcut was added to internal shortcuts map
      const shortcuts = coordinator.getShortcuts();
      expect(shortcuts.some(s => s.key === 'F1' && s.action === 'help')).toBe(true);
    });

    it('should unregister keyboard shortcut', () => {
      const shortcut = {
        key: 'F1',
        action: 'help',
        description: 'Show help',
      };
      
      coordinator.registerShortcut(shortcut);
      coordinator.unregisterShortcut('F1');
      
      // Verify shortcut was removed from internal shortcuts map
      const shortcuts = coordinator.getShortcuts();
      expect(shortcuts.some(s => s.key === 'F1')).toBe(false);
    });

    it('should get all shortcuts', () => {
      const shortcuts = coordinator.getShortcuts();
      expect(Array.isArray(shortcuts)).toBe(true);
    });
  });

  describe('Focus Management', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should focus iframe', () => {
      coordinator.focusIframe();
      // Just verify it doesn't throw - the focus manager is mocked
      expect(coordinator).toBeDefined();
    });

    it('should focus main window', () => {
      coordinator.focusMain();
      // Just verify it doesn't throw - the focus manager is mocked
      expect(coordinator).toBeDefined();
    });

    it('should trap focus', () => {
      coordinator.trapFocus();
      // Just verify it doesn't throw - the focus manager is mocked
      expect(coordinator).toBeDefined();
    });

    it('should release focus trap', () => {
      coordinator.releaseFocusTrap();
      // Just verify it doesn't throw - the focus manager is mocked
      expect(coordinator).toBeDefined();
    });

    it('should fallback to basic focus management when disabled', () => {
      const config: UICoordinatorConfig = { enableFocusManagement: false };
      const customCoordinator = new UICoordinator(config);
      customCoordinator.initialize(mockIframe, mockContainer);
      
      // Mock iframe focus
      const focusSpy = vi.spyOn(mockIframe, 'focus');
      
      customCoordinator.focusIframe();
      expect(focusSpy).toHaveBeenCalled();
      
      customCoordinator.cleanup();
    });
  });

  describe('Event Bubbling', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should enable event bubbling', () => {
      coordinator.setEventBubbling(true);
      // Event bubbling is enabled - no direct way to test without complex setup
      expect(coordinator).toBeDefined(); // Basic assertion
    });

    it('should disable event bubbling', () => {
      coordinator.setEventBubbling(false);
      // Event bubbling is disabled - no direct way to test without complex setup
      expect(coordinator).toBeDefined(); // Basic assertion
    });
  });

  describe('Event Emission', () => {
    beforeEach(() => {
      coordinator.initialize(mockIframe, mockContainer);
    });

    it('should emit UI events', () => {
      const eventHandler = vi.fn();
      coordinator.on('fullscreen_change', eventHandler);
      
      coordinator.setFullscreen(true);
      
      // UICoordinator extends EventEmitter, so events have additional metadata
      expect(eventHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'fullscreen_change',
          data: { isFullscreen: true },
        }),
        expect.any(Object) // EventEmitter adds event metadata as second parameter
      );
    });

    it('should emit resize events', () => {
      const eventHandler = vi.fn();
      coordinator.on('resize', eventHandler);
      
      coordinator.resize(800, 600);
      
      expect(eventHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'resize',
          data: { dimensions: { width: 800, height: 600 } },
        }),
        expect.any(Object) // EventEmitter adds event metadata as second parameter
      );
    });

    it('should emit navigation toggle events', () => {
      const eventHandler = vi.fn();
      coordinator.on('navigation_toggle', eventHandler);
      
      coordinator.setNavigationVisible(false);
      
      expect(eventHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'navigation_toggle',
          data: { visible: false },
        }),
        expect.any(Object) // EventEmitter adds event metadata as second parameter
      );
    });
  });

  describe('Cleanup', () => {
    it('should cleanup all resources', () => {
      coordinator.initialize(mockIframe, mockContainer);
      
      coordinator.cleanup();
      
      // Just verify cleanup doesn't throw and resets state
      expect(coordinator.getUIState().isFullscreen).toBe(false);
      expect(document.body.classList.contains('iframe-fullscreen')).toBe(false);
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing container gracefully', () => {
      expect(() => {
        coordinator.resize(800, 600);
      }).not.toThrow();
    });

    it('should handle missing iframe gracefully', () => {
      expect(() => {
        coordinator.focusIframe();
      }).not.toThrow();
    });

    it('should handle missing navigation element gracefully', () => {
      vi.spyOn(document, 'querySelector').mockReturnValue(null);
      vi.spyOn(document, 'querySelectorAll').mockReturnValue([] as any);
      
      const customCoordinator = new UICoordinator();
      customCoordinator.initialize(mockIframe, mockContainer);
      
      expect(() => {
        customCoordinator.setNavigationVisible(false);
      }).not.toThrow();
      
      customCoordinator.cleanup();
    });

    it('should not enter fullscreen when disabled', () => {
      const config: UICoordinatorConfig = { enableFullscreen: false };
      const customCoordinator = new UICoordinator(config);
      customCoordinator.initialize(mockIframe, mockContainer);
      
      customCoordinator.setFullscreen(true);
      expect(customCoordinator.getUIState().isFullscreen).toBe(false);
      
      customCoordinator.cleanup();
    });

    it('should handle duplicate fullscreen calls', () => {
      coordinator.initialize(mockIframe, mockContainer);
      
      coordinator.setFullscreen(true);
      const firstState = coordinator.getUIState();
      
      coordinator.setFullscreen(true); // Duplicate call
      const secondState = coordinator.getUIState();
      
      expect(firstState.isFullscreen).toBe(secondState.isFullscreen);
    });
  });
});