/**
 * Accessibility Utilities
 * 
 * Comprehensive accessibility utilities for WCAG 2.1 compliance.
 * Provides functions for focus management, ARIA attributes, and screen reader support.
 */

// ============================================
// Focus Management
// ============================================

/**
 * Get all focusable elements within a container
 */
export const getFocusableElements = (container: HTMLElement): HTMLElement[] => {
  const focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]',
    'audio[controls]',
    'video[controls]',
    'details > summary:first-of-type',
  ].join(', ');

  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors))
    .filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null);
};

/**
 * Trap focus within a container (for modals, dialogs)
 */
export const trapFocus = (container: HTMLElement): (() => void) => {
  const focusableElements = getFocusableElements(container);
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      if (document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
    } else {
      if (document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    }
  };

  container.addEventListener('keydown', handleKeyDown);
  firstElement?.focus();

  return () => {
    container.removeEventListener('keydown', handleKeyDown);
  };
};

/**
 * Restore focus to a previously focused element
 */
export const restoreFocus = (element: HTMLElement | null): void => {
  if (element && typeof element.focus === 'function') {
    // Small delay to ensure DOM is ready
    requestAnimationFrame(() => {
      element.focus();
    });
  }
};

/**
 * Move focus to the first focusable element in a container
 */
export const focusFirstElement = (container: HTMLElement): void => {
  const focusableElements = getFocusableElements(container);
  focusableElements[0]?.focus();
};

// ============================================
// Screen Reader Announcements
// ============================================

let liveRegion: HTMLElement | null = null;

/**
 * Initialize the live region for screen reader announcements
 */
export const initLiveRegion = (): void => {
  if (liveRegion) return;

  liveRegion = document.createElement('div');
  liveRegion.setAttribute('role', 'status');
  liveRegion.setAttribute('aria-live', 'polite');
  liveRegion.setAttribute('aria-atomic', 'true');
  liveRegion.className = 'sr-only';
  liveRegion.id = 'a11y-live-region';
  document.body.appendChild(liveRegion);
};

/**
 * Announce a message to screen readers
 */
export const announce = (
  message: string,
  priority: 'polite' | 'assertive' = 'polite'
): void => {
  if (!liveRegion) {
    initLiveRegion();
  }

  if (liveRegion) {
    liveRegion.setAttribute('aria-live', priority);
    // Clear and set message to trigger announcement
    liveRegion.textContent = '';
    requestAnimationFrame(() => {
      if (liveRegion) {
        liveRegion.textContent = message;
      }
    });
  }
};

/**
 * Announce an error message (assertive)
 */
export const announceError = (message: string): void => {
  announce(message, 'assertive');
};

/**
 * Announce a success message
 */
export const announceSuccess = (message: string): void => {
  announce(message, 'polite');
};

// ============================================
// ARIA Helpers
// ============================================

/**
 * Generate a unique ID for ARIA relationships
 */
export const generateAriaId = (prefix: string = 'a11y'): string => {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Create ARIA describedby relationship
 */
export const createAriaDescribedBy = (
  element: HTMLElement,
  description: string
): string => {
  const id = generateAriaId('desc');
  const descElement = document.createElement('span');
  descElement.id = id;
  descElement.className = 'sr-only';
  descElement.textContent = description;
  element.parentNode?.insertBefore(descElement, element.nextSibling);
  element.setAttribute('aria-describedby', id);
  return id;
};

/**
 * Get appropriate ARIA role for element type
 */
export const getAriaRole = (type: string): string => {
  const roleMap: Record<string, string> = {
    button: 'button',
    link: 'link',
    checkbox: 'checkbox',
    radio: 'radio',
    tab: 'tab',
    tabpanel: 'tabpanel',
    menu: 'menu',
    menuitem: 'menuitem',
    dialog: 'dialog',
    alert: 'alert',
    alertdialog: 'alertdialog',
    progressbar: 'progressbar',
    slider: 'slider',
    spinbutton: 'spinbutton',
    status: 'status',
    timer: 'timer',
    tooltip: 'tooltip',
    tree: 'tree',
    treeitem: 'treeitem',
    grid: 'grid',
    gridcell: 'gridcell',
    listbox: 'listbox',
    option: 'option',
    combobox: 'combobox',
    searchbox: 'searchbox',
    textbox: 'textbox',
    navigation: 'navigation',
    main: 'main',
    banner: 'banner',
    contentinfo: 'contentinfo',
    complementary: 'complementary',
    region: 'region',
    article: 'article',
    form: 'form',
    search: 'search',
  };
  return roleMap[type] || type;
};

// ============================================
// Keyboard Navigation
// ============================================

export type KeyboardHandler = (event: KeyboardEvent) => void;

/**
 * Create keyboard navigation handler for lists/menus
 */
export const createKeyboardNavigation = (
  items: HTMLElement[],
  options: {
    orientation?: 'horizontal' | 'vertical';
    loop?: boolean;
    onSelect?: (item: HTMLElement, index: number) => void;
    onEscape?: () => void;
  } = {}
): KeyboardHandler => {
  const { orientation = 'vertical', loop = true, onSelect, onEscape } = options;
  let currentIndex = 0;

  return (event: KeyboardEvent) => {
    const prevKey = orientation === 'vertical' ? 'ArrowUp' : 'ArrowLeft';
    const nextKey = orientation === 'vertical' ? 'ArrowDown' : 'ArrowRight';

    switch (event.key) {
      case prevKey:
        event.preventDefault();
        if (currentIndex > 0) {
          currentIndex--;
        } else if (loop) {
          currentIndex = items.length - 1;
        }
        items[currentIndex]?.focus();
        break;

      case nextKey:
        event.preventDefault();
        if (currentIndex < items.length - 1) {
          currentIndex++;
        } else if (loop) {
          currentIndex = 0;
        }
        items[currentIndex]?.focus();
        break;

      case 'Home':
        event.preventDefault();
        currentIndex = 0;
        items[currentIndex]?.focus();
        break;

      case 'End':
        event.preventDefault();
        currentIndex = items.length - 1;
        items[currentIndex]?.focus();
        break;

      case 'Enter':
      case ' ':
        event.preventDefault();
        onSelect?.(items[currentIndex], currentIndex);
        break;

      case 'Escape':
        event.preventDefault();
        onEscape?.();
        break;
    }
  };
};

// ============================================
// Color Contrast
// ============================================

/**
 * Calculate relative luminance of a color
 */
export const getLuminance = (r: number, g: number, b: number): number => {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
};

/**
 * Calculate contrast ratio between two colors
 */
export const getContrastRatio = (
  color1: [number, number, number],
  color2: [number, number, number]
): number => {
  const l1 = getLuminance(...color1);
  const l2 = getLuminance(...color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
};

/**
 * Check if contrast ratio meets WCAG requirements
 */
export const meetsContrastRequirement = (
  ratio: number,
  level: 'AA' | 'AAA' = 'AA',
  isLargeText: boolean = false
): boolean => {
  if (level === 'AAA') {
    return isLargeText ? ratio >= 4.5 : ratio >= 7;
  }
  return isLargeText ? ratio >= 3 : ratio >= 4.5;
};

/**
 * Parse hex color to RGB
 */
export const hexToRgb = (hex: string): [number, number, number] | null => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
    : null;
};

// ============================================
// Reduced Motion
// ============================================

/**
 * Check if user prefers reduced motion
 */
export const prefersReducedMotion = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

/**
 * Get animation duration based on user preference
 */
export const getAnimationDuration = (defaultDuration: number): number => {
  return prefersReducedMotion() ? 0 : defaultDuration;
};

// ============================================
// High Contrast Mode
// ============================================

/**
 * Check if user prefers high contrast
 */
export const prefersHighContrast = (): boolean => {
  if (typeof window === 'undefined') return false;
  return (
    window.matchMedia('(prefers-contrast: more)').matches ||
    window.matchMedia('(-ms-high-contrast: active)').matches
  );
};

// ============================================
// Text Sizing
// ============================================

/**
 * Calculate relative font size based on user preferences
 */
export const getRelativeFontSize = (baseSizePx: number): string => {
  // Use rem for scalability with user font size preferences
  return `${baseSizePx / 16}rem`;
};

/**
 * Ensure minimum touch target size (44x44px for WCAG)
 */
export const ensureMinTouchTarget = (
  element: HTMLElement,
  minSize: number = 44
): void => {
  const rect = element.getBoundingClientRect();
  if (rect.width < minSize || rect.height < minSize) {
    element.style.minWidth = `${minSize}px`;
    element.style.minHeight = `${minSize}px`;
  }
};

// ============================================
// Form Accessibility
// ============================================

/**
 * Associate label with form control
 */
export const associateLabel = (
  input: HTMLElement,
  labelText: string
): HTMLLabelElement => {
  const id = input.id || generateAriaId('input');
  input.id = id;

  const label = document.createElement('label');
  label.htmlFor = id;
  label.textContent = labelText;

  return label;
};

/**
 * Add error message to form control
 */
export const addErrorMessage = (
  input: HTMLElement,
  errorMessage: string
): string => {
  const errorId = generateAriaId('error');
  const errorElement = document.createElement('span');
  errorElement.id = errorId;
  errorElement.className = 'form-error';
  errorElement.setAttribute('role', 'alert');
  errorElement.textContent = errorMessage;

  input.setAttribute('aria-invalid', 'true');
  input.setAttribute('aria-describedby', errorId);
  input.parentNode?.appendChild(errorElement);

  return errorId;
};

/**
 * Remove error message from form control
 */
export const removeErrorMessage = (input: HTMLElement, errorId: string): void => {
  const errorElement = document.getElementById(errorId);
  errorElement?.remove();
  input.removeAttribute('aria-invalid');
  input.removeAttribute('aria-describedby');
};

// ============================================
// Skip Links
// ============================================

/**
 * Create skip link for keyboard navigation
 */
export const createSkipLink = (
  targetId: string,
  text: string = 'Skip to main content'
): HTMLAnchorElement => {
  const link = document.createElement('a');
  link.href = `#${targetId}`;
  link.className = 'skip-link';
  link.textContent = text;

  link.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus();
      target.removeAttribute('tabindex');
    }
  });

  return link;
};

export default {
  getFocusableElements,
  trapFocus,
  restoreFocus,
  focusFirstElement,
  initLiveRegion,
  announce,
  announceError,
  announceSuccess,
  generateAriaId,
  createAriaDescribedBy,
  getAriaRole,
  createKeyboardNavigation,
  getLuminance,
  getContrastRatio,
  meetsContrastRequirement,
  hexToRgb,
  prefersReducedMotion,
  getAnimationDuration,
  prefersHighContrast,
  getRelativeFontSize,
  ensureMinTouchTarget,
  associateLabel,
  addErrorMessage,
  removeErrorMessage,
  createSkipLink,
};
