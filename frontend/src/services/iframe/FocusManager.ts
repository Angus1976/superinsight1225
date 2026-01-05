/**
 * FocusManager - Advanced focus management for iframe integration
 * Handles focus trapping, restoration, and coordination between main window and iframe
 */

export interface FocusableElement {
  element: HTMLElement;
  tabIndex: number;
  originalTabIndex?: number;
}

export interface FocusState {
  activeElement: HTMLElement | null;
  iframeFocused: boolean;
  focusTrapped: boolean;
  lastFocusedElement: HTMLElement | null;
  focusHistory: HTMLElement[];
}

export interface FocusEvent {
  type: 'focus_in' | 'focus_out' | 'focus_trapped' | 'focus_restored' | 'focus_moved';
  element: HTMLElement | null;
  source: 'main' | 'iframe';
  timestamp: number;
}

export type FocusEventHandler = (event: FocusEvent) => void;

export class FocusManager {
  private iframe: HTMLIFrameElement | null = null;
  private container: HTMLElement | null = null;
  private focusState: FocusState = {
    activeElement: null,
    iframeFocused: false,
    focusTrapped: false,
    lastFocusedElement: null,
    focusHistory: [],
  };
  private eventHandlers: Map<string, Set<FocusEventHandler>> = new Map();
  private focusableElements: FocusableElement[] = [];
  private isListening = false;
  private focusCheckInterval: NodeJS.Timeout | null = null;
  private trapContainer: HTMLElement | null = null;

  /**
   * Initialize focus manager
   */
  initialize(iframe: HTMLIFrameElement, container: HTMLElement): void {
    this.iframe = iframe;
    this.container = container;
    this.updateFocusableElements();
    this.startListening();
    this.startFocusMonitoring();
  }

  /**
   * Cleanup focus manager
   */
  cleanup(): void {
    this.stopListening();
    this.stopFocusMonitoring();
    this.releaseFocusTrap();
    this.restoreTabIndices();
    
    this.iframe = null;
    this.container = null;
    this.focusableElements = [];
    this.eventHandlers.clear();
  }

  /**
   * Trap focus within container
   */
  trapFocus(container?: HTMLElement): void {
    const trapContainer = container || this.container;
    if (!trapContainer) {
      return;
    }

    this.trapContainer = trapContainer;
    this.focusState.focusTrapped = true;
    
    // Store current focus
    this.focusState.lastFocusedElement = document.activeElement as HTMLElement;
    
    // Update focusable elements within trap container
    this.updateFocusableElements(trapContainer);
    
    // Add trap listeners
    document.addEventListener('keydown', this.handleTrapKeyDown, true);
    document.addEventListener('focusin', this.handleTrapFocusIn, true);
    
    // Focus first element in trap
    this.focusFirstElement();
    
    this.emitFocusEvent('focus_trapped', null, 'main');
  }

  /**
   * Release focus trap
   */
  releaseFocusTrap(): void {
    if (!this.focusState.focusTrapped) {
      return;
    }

    this.focusState.focusTrapped = false;
    this.trapContainer = null;
    
    // Remove trap listeners
    document.removeEventListener('keydown', this.handleTrapKeyDown, true);
    document.removeEventListener('focusin', this.handleTrapFocusIn, true);
    
    // Restore focus
    if (this.focusState.lastFocusedElement) {
      this.focusState.lastFocusedElement.focus();
    }
    
    // Update focusable elements for entire document
    this.updateFocusableElements();
    
    this.emitFocusEvent('focus_restored', this.focusState.lastFocusedElement, 'main');
  }

  /**
   * Focus iframe
   */
  focusIframe(): void {
    if (!this.iframe) {
      return;
    }

    this.iframe.focus();
    this.focusState.iframeFocused = true;
    this.focusState.activeElement = this.iframe;
    this.addToFocusHistory(this.iframe);
    
    this.emitFocusEvent('focus_in', this.iframe, 'iframe');
  }

  /**
   * Focus main window
   */
  focusMain(): void {
    if (this.focusState.lastFocusedElement && this.focusState.lastFocusedElement !== this.iframe) {
      this.focusState.lastFocusedElement.focus();
    } else {
      this.focusFirstElement();
    }
    
    this.focusState.iframeFocused = false;
    this.emitFocusEvent('focus_out', null, 'iframe');
  }

  /**
   * Focus first focusable element
   */
  focusFirstElement(): void {
    const firstElement = this.getFirstFocusableElement();
    if (firstElement) {
      firstElement.element.focus();
      this.focusState.activeElement = firstElement.element;
      this.addToFocusHistory(firstElement.element);
    }
  }

  /**
   * Focus last focusable element
   */
  focusLastElement(): void {
    const lastElement = this.getLastFocusableElement();
    if (lastElement) {
      lastElement.element.focus();
      this.focusState.activeElement = lastElement.element;
      this.addToFocusHistory(lastElement.element);
    }
  }

  /**
   * Focus next element
   */
  focusNext(): void {
    const currentIndex = this.getCurrentFocusIndex();
    const nextIndex = (currentIndex + 1) % this.focusableElements.length;
    const nextElement = this.focusableElements[nextIndex];
    
    if (nextElement) {
      nextElement.element.focus();
      this.focusState.activeElement = nextElement.element;
      this.addToFocusHistory(nextElement.element);
    }
  }

  /**
   * Focus previous element
   */
  focusPrevious(): void {
    const currentIndex = this.getCurrentFocusIndex();
    const prevIndex = currentIndex === 0 ? this.focusableElements.length - 1 : currentIndex - 1;
    const prevElement = this.focusableElements[prevIndex];
    
    if (prevElement) {
      prevElement.element.focus();
      this.focusState.activeElement = prevElement.element;
      this.addToFocusHistory(prevElement.element);
    }
  }

  /**
   * Get current focus state
   */
  getFocusState(): FocusState {
    return { ...this.focusState, focusHistory: [...this.focusState.focusHistory] };
  }

  /**
   * Check if element is focusable
   */
  isFocusable(element: HTMLElement): boolean {
    return this.focusableElements.some(fe => fe.element === element);
  }

  /**
   * Register focus event handler
   */
  on(event: string, handler: FocusEventHandler): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);
  }

  /**
   * Unregister focus event handler
   */
  off(event: string, handler: FocusEventHandler): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Update focusable elements
   */
  private updateFocusableElements(container?: HTMLElement): void {
    const root = container || document;
    const selector = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');

    const elements = Array.from(root.querySelectorAll(selector)) as HTMLElement[];
    
    this.focusableElements = elements
      .filter(element => this.isElementVisible(element))
      .map(element => ({
        element,
        tabIndex: element.tabIndex,
        originalTabIndex: element.hasAttribute('tabindex') ? element.tabIndex : undefined,
      }))
      .sort((a, b) => {
        // Sort by tab index, then by DOM order
        if (a.tabIndex !== b.tabIndex) {
          return a.tabIndex - b.tabIndex;
        }
        return a.element.compareDocumentPosition(b.element) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
      });
  }

  /**
   * Check if element is visible
   */
  private isElementVisible(element: HTMLElement): boolean {
    const style = window.getComputedStyle(element);
    return (
      style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      element.offsetWidth > 0 &&
      element.offsetHeight > 0
    );
  }

  /**
   * Get first focusable element
   */
  private getFirstFocusableElement(): FocusableElement | null {
    return this.focusableElements[0] || null;
  }

  /**
   * Get last focusable element
   */
  private getLastFocusableElement(): FocusableElement | null {
    return this.focusableElements[this.focusableElements.length - 1] || null;
  }

  /**
   * Get current focus index
   */
  private getCurrentFocusIndex(): number {
    const activeElement = document.activeElement as HTMLElement;
    return this.focusableElements.findIndex(fe => fe.element === activeElement);
  }

  /**
   * Add element to focus history
   */
  private addToFocusHistory(element: HTMLElement): void {
    // Remove element if already in history
    const index = this.focusState.focusHistory.indexOf(element);
    if (index > -1) {
      this.focusState.focusHistory.splice(index, 1);
    }
    
    // Add to beginning of history
    this.focusState.focusHistory.unshift(element);
    
    // Limit history size
    if (this.focusState.focusHistory.length > 10) {
      this.focusState.focusHistory = this.focusState.focusHistory.slice(0, 10);
    }
  }

  /**
   * Start listening for focus events
   */
  private startListening(): void {
    if (this.isListening) {
      return;
    }

    document.addEventListener('focusin', this.handleFocusIn, true);
    document.addEventListener('focusout', this.handleFocusOut, true);
    
    this.isListening = true;
  }

  /**
   * Stop listening for focus events
   */
  private stopListening(): void {
    if (!this.isListening) {
      return;
    }

    document.removeEventListener('focusin', this.handleFocusIn, true);
    document.removeEventListener('focusout', this.handleFocusOut, true);
    
    this.isListening = false;
  }

  /**
   * Start focus monitoring
   */
  private startFocusMonitoring(): void {
    this.focusCheckInterval = setInterval(() => {
      const activeElement = document.activeElement as HTMLElement;
      const wasIframeFocused = this.focusState.iframeFocused;
      const isIframeFocused = activeElement === this.iframe;
      
      if (isIframeFocused !== wasIframeFocused) {
        this.focusState.iframeFocused = isIframeFocused;
        
        if (isIframeFocused) {
          this.emitFocusEvent('focus_in', this.iframe, 'iframe');
        } else {
          this.emitFocusEvent('focus_out', null, 'iframe');
        }
      }
      
      if (activeElement !== this.focusState.activeElement) {
        this.focusState.activeElement = activeElement;
        if (activeElement) {
          this.addToFocusHistory(activeElement);
        }
      }
    }, 100);
  }

  /**
   * Stop focus monitoring
   */
  private stopFocusMonitoring(): void {
    if (this.focusCheckInterval) {
      clearInterval(this.focusCheckInterval);
      this.focusCheckInterval = null;
    }
  }

  /**
   * Restore original tab indices
   */
  private restoreTabIndices(): void {
    this.focusableElements.forEach(fe => {
      if (fe.originalTabIndex !== undefined) {
        fe.element.tabIndex = fe.originalTabIndex;
      } else {
        fe.element.removeAttribute('tabindex');
      }
    });
  }

  /**
   * Handle focus in events
   */
  private handleFocusIn = (event: FocusEvent): void => {
    const target = event.target as HTMLElement;
    this.focusState.activeElement = target;
    this.addToFocusHistory(target);
    
    const source = target === this.iframe ? 'iframe' : 'main';
    this.emitFocusEvent('focus_in', target, source);
  };

  /**
   * Handle focus out events
   */
  private handleFocusOut = (event: FocusEvent): void => {
    const target = event.target as HTMLElement;
    const source = target === this.iframe ? 'iframe' : 'main';
    this.emitFocusEvent('focus_out', target, source);
  };

  /**
   * Handle trap keydown events
   */
  private handleTrapKeyDown = (event: KeyboardEvent): void => {
    if (!this.focusState.focusTrapped || event.key !== 'Tab') {
      return;
    }

    const firstElement = this.getFirstFocusableElement();
    const lastElement = this.getLastFocusableElement();
    
    if (!firstElement || !lastElement) {
      return;
    }

    if (event.shiftKey) {
      // Shift+Tab - move to previous element
      if (document.activeElement === firstElement.element) {
        event.preventDefault();
        lastElement.element.focus();
      }
    } else {
      // Tab - move to next element
      if (document.activeElement === lastElement.element) {
        event.preventDefault();
        firstElement.element.focus();
      }
    }
  };

  /**
   * Handle trap focus in events
   */
  private handleTrapFocusIn = (event: Event): void => {
    if (!this.focusState.focusTrapped || !this.trapContainer) {
      return;
    }

    const target = event.target as HTMLElement;
    
    // Check if focus is outside trap container
    if (!this.trapContainer.contains(target) && target !== this.iframe) {
      event.preventDefault();
      this.focusFirstElement();
    }
  };

  /**
   * Emit focus event
   */
  private emitFocusEvent(type: FocusEvent['type'], element: HTMLElement | null, source: 'main' | 'iframe'): void {
    const event: FocusEvent = {
      type,
      element,
      source,
      timestamp: Date.now(),
    };

    const handlers = this.eventHandlers.get(type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error(`Error in focus event handler for ${type}:`, error);
        }
      });
    }

    // Also emit to generic 'focus_event' handlers
    const genericHandlers = this.eventHandlers.get('focus_event');
    if (genericHandlers) {
      genericHandlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error(`Error in generic focus event handler:`, error);
        }
      });
    }
  }
}