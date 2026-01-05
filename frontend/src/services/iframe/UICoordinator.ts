/**
 * UICoordinator - Manages UI coordination and interaction between iframe and main window
 * Handles fullscreen mode, resizing, navigation visibility, keyboard shortcuts, and focus management
 */

import { EventEmitter } from './EventEmitter';
import { KeyboardManager, KeyboardShortcut } from './KeyboardManager';
import { FocusManager } from './FocusManager';

export interface UICoordinatorConfig {
  enableFullscreen?: boolean;
  enableKeyboardShortcuts?: boolean;
  enableFocusManagement?: boolean;
  enableEventBubbling?: boolean;
  navigationSelector?: string;
  containerSelector?: string;
  shortcuts?: Record<string, string>;
  focusTrapOnFullscreen?: boolean;
}

export interface UIState {
  isFullscreen: boolean;
  navigationVisible: boolean;
  iframeFocused: boolean;
  dimensions: {
    width: number;
    height: number;
  };
}

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
  metaKey?: boolean;
  action: string;
  description: string;
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export interface UIEvent {
  type: 'fullscreen_change' | 'resize' | 'navigation_toggle' | 'focus_change' | 'shortcut_triggered';
  timestamp: number;
  data?: unknown;
}

export type UIEventCallback = (event: UIEvent) => void;

export class UICoordinator extends EventEmitter {
  private config: UICoordinatorConfig;
  private iframe: HTMLIFrameElement | null = null;
  private container: HTMLElement | null = null;
  private navigationElement: HTMLElement | null = null;
  private keyboardManager: KeyboardManager;
  private focusManager: FocusManager;
  private uiState: UIState = {
    isFullscreen: false,
    navigationVisible: true,
    iframeFocused: false,
    dimensions: { width: 0, height: 0 },
  };
  private shortcuts: Map<string, KeyboardShortcut> = new Map();
  private resizeObserver: ResizeObserver | null = null;
  private keyboardListenerActive = false;
  private originalStyles: Map<HTMLElement, string> = new Map();

  constructor(config: UICoordinatorConfig = {}) {
    super();
    this.config = {
      enableFullscreen: true,
      enableKeyboardShortcuts: true,
      enableFocusManagement: true,
      enableEventBubbling: false,
      navigationSelector: '.ant-layout-header, .ant-layout-sider',
      containerSelector: '.iframe-container',
      focusTrapOnFullscreen: true,
      shortcuts: {
        'F11': 'toggle_fullscreen',
        'Escape': 'exit_fullscreen',
        'Ctrl+Shift+F': 'toggle_fullscreen',
        'Ctrl+H': 'toggle_navigation',
        'Ctrl+Shift+I': 'focus_iframe',
        'Ctrl+Shift+M': 'focus_main',
      },
      ...config,
    };

    this.keyboardManager = new KeyboardManager();
    this.focusManager = new FocusManager();
    this.initializeShortcuts();
    this.setupManagerEventHandlers();
  }

  /**
   * Initialize UI coordinator with iframe and container
   */
  initialize(iframe: HTMLIFrameElement, container: HTMLElement): void {
    this.iframe = iframe;
    this.container = container;
    this.navigationElement = this.findNavigationElement();

    // Initialize managers
    if (this.config.enableKeyboardShortcuts && this.keyboardManager && typeof this.keyboardManager.initialize === 'function') {
      this.keyboardManager.initialize(iframe);
    }
    
    if (this.config.enableFocusManagement && this.focusManager && typeof this.focusManager.initialize === 'function') {
      this.focusManager.initialize(iframe, container);
    }

    // Initialize dimensions
    this.updateDimensions();

    // Setup event listeners
    this.setupEventListeners();

    // Setup resize observer
    this.setupResizeObserver();

    // Setup keyboard shortcuts
    if (this.config.enableKeyboardShortcuts) {
      this.enableKeyboardShortcuts();
    }

    // Setup focus management
    if (this.config.enableFocusManagement) {
      this.setupFocusManagement();
    }

    this.emitUIEvent('resize', { dimensions: this.uiState.dimensions });
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.removeEventListeners();
    this.disableKeyboardShortcuts();
    this.cleanupResizeObserver();
    this.exitFullscreen();
    this.showNavigation();
    
    // Cleanup managers
    if (this.keyboardManager && typeof this.keyboardManager.cleanup === 'function') {
      this.keyboardManager.cleanup();
    }
    if (this.focusManager && typeof this.focusManager.cleanup === 'function') {
      this.focusManager.cleanup();
    }
    
    this.iframe = null;
    this.container = null;
    this.navigationElement = null;
    this.originalStyles.clear();
  }

  /**
   * Toggle fullscreen mode
   */
  setFullscreen(enabled: boolean): void {
    if (enabled === this.uiState.isFullscreen) {
      return;
    }

    if (enabled) {
      this.enterFullscreen();
    } else {
      this.exitFullscreen();
    }
  }

  /**
   * Toggle fullscreen mode
   */
  toggleFullscreen(): void {
    this.setFullscreen(!this.uiState.isFullscreen);
  }

  /**
   * Resize iframe to specific dimensions
   */
  resize(width: number, height: number): void {
    if (!this.iframe || !this.container) {
      return;
    }

    // Update container dimensions
    this.container.style.width = `${width}px`;
    this.container.style.height = `${height}px`;

    // Update iframe dimensions
    this.iframe.style.width = `${width}px`;
    this.iframe.style.height = `${height}px`;

    // Update state
    this.uiState.dimensions = { width, height };

    this.emitUIEvent('resize', { dimensions: { width, height } });
  }

  /**
   * Auto-resize iframe to fit container
   */
  autoResize(): void {
    if (!this.container) {
      return;
    }

    const rect = this.container.getBoundingClientRect();
    this.resize(rect.width, rect.height);
  }

  /**
   * Show/hide navigation elements
   */
  setNavigationVisible(visible: boolean): void {
    if (visible === this.uiState.navigationVisible) {
      return;
    }

    if (visible) {
      this.showNavigation();
    } else {
      this.hideNavigation();
    }
  }

  /**
   * Toggle navigation visibility
   */
  toggleNavigation(): void {
    this.setNavigationVisible(!this.uiState.navigationVisible);
  }

  /**
   * Show loading indicator
   */
  setLoading(loading: boolean): void {
    if (!this.container) {
      return;
    }

    const loadingClass = 'iframe-loading';
    if (loading) {
      this.container.classList.add(loadingClass);
    } else {
      this.container.classList.remove(loadingClass);
    }
  }

  /**
   * Show error message
   */
  showError(message: string): void {
    if (!this.container) {
      return;
    }

    // Remove existing error elements
    const existingError = this.container.querySelector('.iframe-error');
    if (existingError) {
      existingError.remove();
    }

    // Create error element
    const errorElement = document.createElement('div');
    errorElement.className = 'iframe-error';
    errorElement.innerHTML = `
      <div class="iframe-error-content">
        <div class="iframe-error-icon">⚠️</div>
        <div class="iframe-error-message">${message}</div>
        <button class="iframe-error-retry" onclick="this.parentElement.parentElement.remove()">
          Dismiss
        </button>
      </div>
    `;

    this.container.appendChild(errorElement);
  }

  /**
   * Hide error message
   */
  hideError(): void {
    if (!this.container) {
      return;
    }

    const errorElement = this.container.querySelector('.iframe-error');
    if (errorElement) {
      errorElement.remove();
    }
  }

  /**
   * Get current UI state
   */
  getUIState(): UIState {
    return { ...this.uiState };
  }

  /**
   * Register keyboard shortcut
   */
  registerShortcut(shortcut: KeyboardShortcut): void {
    const key = this.getShortcutKey(shortcut);
    this.shortcuts.set(key, shortcut);
    
    if (this.keyboardManager && typeof this.keyboardManager.registerShortcut === 'function') {
      this.keyboardManager.registerShortcut(shortcut, 'global');
    }
  }

  /**
   * Unregister keyboard shortcut
   */
  unregisterShortcut(key: string): void {
    this.shortcuts.delete(key);
    
    if (this.keyboardManager && typeof this.keyboardManager.unregisterShortcut === 'function') {
      this.keyboardManager.unregisterShortcut(key, 'global');
    }
  }

  /**
   * Get all registered shortcuts
   */
  getShortcuts(): KeyboardShortcut[] {
    return Array.from(this.shortcuts.values());
  }

  /**
   * Focus iframe
   */
  focusIframe(): void {
    if (this.config.enableFocusManagement && this.focusManager && typeof this.focusManager.focusIframe === 'function') {
      this.focusManager.focusIframe();
    } else if (this.iframe) {
      this.iframe.focus();
    }
  }

  /**
   * Focus main window
   */
  focusMain(): void {
    if (this.config.enableFocusManagement && this.focusManager && typeof this.focusManager.focusMain === 'function') {
      this.focusManager.focusMain();
    } else {
      // Fallback focus management
      const firstFocusable = document.querySelector('button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])') as HTMLElement;
      if (firstFocusable) {
        firstFocusable.focus();
      }
    }
  }

  /**
   * Enable/disable event bubbling
   */
  setEventBubbling(enabled: boolean): void {
    this.config.enableEventBubbling = enabled;
    
    if (enabled) {
      // Allow events to bubble from iframe to main window
      this.enableEventBubbling();
    } else {
      // Prevent event bubbling
      this.disableEventBubbling();
    }
  }

  /**
   * Trap focus within container (useful for modal-like behavior)
   */
  trapFocus(): void {
    if (this.config.enableFocusManagement && this.container && this.focusManager && typeof this.focusManager.trapFocus === 'function') {
      this.focusManager.trapFocus(this.container);
    }
  }

  /**
   * Release focus trap
   */
  releaseFocusTrap(): void {
    if (this.config.enableFocusManagement && this.focusManager && typeof this.focusManager.releaseFocusTrap === 'function') {
      this.focusManager.releaseFocusTrap();
    }
  }

  /**
   * Get keyboard manager instance
   */
  getKeyboardManager(): KeyboardManager {
    return this.keyboardManager;
  }

  /**
   * Get focus manager instance
   */
  getFocusManager(): FocusManager {
    return this.focusManager;
  }

  /**
   * Enter fullscreen mode
   */
  private enterFullscreen(): void {
    if (!this.container || !this.config.enableFullscreen) {
      return;
    }

    // Store original styles
    this.storeOriginalStyles();

    // Apply fullscreen styles
    this.container.style.position = 'fixed';
    this.container.style.top = '0';
    this.container.style.left = '0';
    this.container.style.width = '100vw';
    this.container.style.height = '100vh';
    this.container.style.zIndex = '9999';
    this.container.style.backgroundColor = '#fff';

    // Hide navigation
    this.hideNavigation();

    // Trap focus if enabled
    if (this.config.focusTrapOnFullscreen && this.config.enableFocusManagement) {
      this.trapFocus();
    }

    // Update state
    this.uiState.isFullscreen = true;
    this.updateDimensions();

    // Add fullscreen class
    document.body.classList.add('iframe-fullscreen');

    this.emitUIEvent('fullscreen_change', { isFullscreen: true });
  }

  /**
   * Exit fullscreen mode
   */
  private exitFullscreen(): void {
    if (!this.container || !this.uiState.isFullscreen) {
      return;
    }

    // Release focus trap
    if (this.config.focusTrapOnFullscreen && this.config.enableFocusManagement) {
      this.releaseFocusTrap();
    }

    // Restore original styles
    this.restoreOriginalStyles();

    // Show navigation
    this.showNavigation();

    // Update state
    this.uiState.isFullscreen = false;
    this.updateDimensions();

    // Remove fullscreen class
    document.body.classList.remove('iframe-fullscreen');

    this.emitUIEvent('fullscreen_change', { isFullscreen: false });
  }

  /**
   * Hide navigation elements
   */
  private hideNavigation(): void {
    if (!this.navigationElement) {
      return;
    }

    const elements = this.findAllNavigationElements();
    elements.forEach(element => {
      if (!this.originalStyles.has(element)) {
        this.originalStyles.set(element, element.style.display || '');
      }
      element.style.display = 'none';
    });

    this.uiState.navigationVisible = false;
    this.emitUIEvent('navigation_toggle', { visible: false });
  }

  /**
   * Show navigation elements
   */
  private showNavigation(): void {
    if (!this.navigationElement) {
      return;
    }

    const elements = this.findAllNavigationElements();
    elements.forEach(element => {
      const originalDisplay = this.originalStyles.get(element) || '';
      element.style.display = originalDisplay;
    });

    this.uiState.navigationVisible = true;
    this.emitUIEvent('navigation_toggle', { visible: true });
  }

  /**
   * Find navigation element
   */
  private findNavigationElement(): HTMLElement | null {
    const selector = this.config.navigationSelector!;
    return document.querySelector(selector) as HTMLElement;
  }

  /**
   * Find all navigation elements
   */
  private findAllNavigationElements(): HTMLElement[] {
    const selector = this.config.navigationSelector!;
    return Array.from(document.querySelectorAll(selector)) as HTMLElement[];
  }

  /**
   * Store original styles
   */
  private storeOriginalStyles(): void {
    if (!this.container) {
      return;
    }

    this.originalStyles.set(this.container, this.container.getAttribute('style') || '');
  }

  /**
   * Restore original styles
   */
  private restoreOriginalStyles(): void {
    this.originalStyles.forEach((style, element) => {
      if (style) {
        element.setAttribute('style', style);
      } else {
        element.removeAttribute('style');
      }
    });
    this.originalStyles.clear();
  }

  /**
   * Update dimensions
   */
  private updateDimensions(): void {
    if (!this.container) {
      return;
    }

    const rect = this.container.getBoundingClientRect();
    this.uiState.dimensions = {
      width: rect.width,
      height: rect.height,
    };
  }

  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    if (!this.iframe) {
      return;
    }

    // Listen for iframe focus events
    this.iframe.addEventListener('focus', this.handleIframeFocus);
    this.iframe.addEventListener('blur', this.handleIframeBlur);

    // Listen for window resize
    window.addEventListener('resize', this.handleWindowResize);

    // Listen for escape key to exit fullscreen
    document.addEventListener('keydown', this.handleEscapeKey);
  }

  /**
   * Remove event listeners
   */
  private removeEventListeners(): void {
    if (this.iframe) {
      this.iframe.removeEventListener('focus', this.handleIframeFocus);
      this.iframe.removeEventListener('blur', this.handleIframeBlur);
    }

    window.removeEventListener('resize', this.handleWindowResize);
    document.removeEventListener('keydown', this.handleEscapeKey);
  }

  /**
   * Setup resize observer
   */
  private setupResizeObserver(): void {
    if (!this.container || !window.ResizeObserver) {
      return;
    }

    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        this.uiState.dimensions = { width, height };
        this.emitUIEvent('resize', { dimensions: { width, height } });
      }
    });

    this.resizeObserver.observe(this.container);
  }

  /**
   * Cleanup resize observer
   */
  private cleanupResizeObserver(): void {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
  }

  /**
   * Setup focus management
   */
  private setupFocusManagement(): void {
    if (!this.iframe) {
      return;
    }

    // Monitor iframe focus state
    const checkFocus = () => {
      const focused = document.activeElement === this.iframe;
      if (focused !== this.uiState.iframeFocused) {
        this.uiState.iframeFocused = focused;
        this.emitUIEvent('focus_change', { focused });
      }
    };

    // Check focus periodically
    setInterval(checkFocus, 100);
  }

  /**
   * Initialize default shortcuts
   */
  private initializeShortcuts(): void {
    const defaultShortcuts = this.config.shortcuts!;
    
    Object.entries(defaultShortcuts).forEach(([key, action]) => {
      const shortcut = this.parseShortcutKey(key, action);
      if (shortcut) {
        this.shortcuts.set(key, shortcut);
      }
    });
  }

  /**
   * Parse shortcut key string
   */
  private parseShortcutKey(keyString: string, action: string): KeyboardShortcut | null {
    const parts = keyString.split('+');
    const key = parts[parts.length - 1];
    
    return {
      key,
      ctrlKey: parts.includes('Ctrl'),
      altKey: parts.includes('Alt'),
      shiftKey: parts.includes('Shift'),
      metaKey: parts.includes('Meta') || parts.includes('Cmd'),
      action,
      description: `${action.replace('_', ' ')} (${keyString})`,
    };
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
   * Enable keyboard shortcuts
   */
  private enableKeyboardShortcuts(): void {
    if (this.keyboardListenerActive) {
      return;
    }

    document.addEventListener('keydown', this.handleKeyboardShortcut);
    this.keyboardListenerActive = true;
  }

  /**
   * Disable keyboard shortcuts
   */
  private disableKeyboardShortcuts(): void {
    if (!this.keyboardListenerActive) {
      return;
    }

    document.removeEventListener('keydown', this.handleKeyboardShortcut);
    this.keyboardListenerActive = false;
  }

  /**
   * Handle iframe focus
   */
  private handleIframeFocus = (): void => {
    this.uiState.iframeFocused = true;
    this.emitUIEvent('focus_change', { focused: true });
  };

  /**
   * Handle iframe blur
   */
  private handleIframeBlur = (): void => {
    this.uiState.iframeFocused = false;
    this.emitUIEvent('focus_change', { focused: false });
  };

  /**
   * Handle window resize
   */
  private handleWindowResize = (): void => {
    if (this.uiState.isFullscreen) {
      this.updateDimensions();
      this.emitUIEvent('resize', { dimensions: this.uiState.dimensions });
    }
  };

  /**
   * Handle escape key
   */
  private handleEscapeKey = (event: KeyboardEvent): void => {
    if (event.key === 'Escape' && this.uiState.isFullscreen) {
      event.preventDefault();
      this.exitFullscreen();
    }
  };

  /**
   * Handle keyboard shortcuts
   */
  private handleKeyboardShortcut = (event: KeyboardEvent): void => {
    // Don't handle shortcuts if typing in input fields
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      return;
    }

    // Find matching shortcut
    for (const [key, shortcut] of this.shortcuts) {
      if (this.matchesShortcut(event, shortcut)) {
        event.preventDefault();
        this.executeShortcutAction(shortcut);
        this.emitUIEvent('shortcut_triggered', { shortcut, key });
        break;
      }
    }
  };

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
   * Execute shortcut action
   */
  private executeShortcutAction(shortcut: KeyboardShortcut): void {
    switch (shortcut.action) {
      case 'toggle_fullscreen':
        this.toggleFullscreen();
        break;
      case 'exit_fullscreen':
        this.exitFullscreen();
        break;
      case 'toggle_navigation':
        this.toggleNavigation();
        break;
      case 'focus_iframe':
        this.focusIframe();
        break;
      case 'focus_main':
        this.focusMain();
        break;
      default:
        // Emit custom action event
        this.emit('shortcut_action', { action: shortcut.action, shortcut });
        break;
    }
  }

  /**
   * Setup manager event handlers
   */
  private setupManagerEventHandlers(): void {
    // Keyboard manager events
    if (this.keyboardManager && typeof this.keyboardManager.on === 'function') {
      this.keyboardManager.on('shortcut_triggered', (data: any) => {
        const { shortcut } = data;
        this.executeShortcutAction(shortcut);
        this.emitUIEvent('shortcut_triggered', data);
      });
    }

    // Focus manager events
    if (this.focusManager && typeof this.focusManager.on === 'function') {
      this.focusManager.on('focus_event', (event: any) => {
        if (event.source === 'iframe') {
          this.uiState.iframeFocused = event.type === 'focus_in';
        }
        this.emitUIEvent('focus_change', event);
      });
    }
  }

  /**
   * Enable event bubbling
   */
  private enableEventBubbling(): void {
    if (!this.iframe) {
      return;
    }

    // Allow certain events to bubble from iframe to main window
    const eventTypes = ['click', 'keydown', 'keyup', 'mousedown', 'mouseup'];
    
    eventTypes.forEach(eventType => {
      this.iframe!.addEventListener(eventType, (event) => {
        // Create and dispatch equivalent event on main window
        const newEvent = new Event(event.type, {
          bubbles: true,
          cancelable: true,
        });
        
        // Copy relevant properties
        Object.defineProperty(newEvent, 'target', {
          value: this.iframe,
          enumerable: true,
        });
        
        document.dispatchEvent(newEvent);
      }, true);
    });
  }

  /**
   * Disable event bubbling
   */
  private disableEventBubbling(): void {
    // Event bubbling is controlled by the enableEventBubbling method
    // This method exists for API completeness but doesn't need implementation
    // since we don't store references to the event listeners
  }

  /**
   * Emit UI event
   */
  private emitUIEvent(type: UIEvent['type'], data?: unknown): void {
    const event: UIEvent = {
      type,
      timestamp: Date.now(),
      data,
    };

    this.emit('ui_event', event);
    this.emit(type, event);
  }
}