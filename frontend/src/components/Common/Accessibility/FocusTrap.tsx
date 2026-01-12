/**
 * FocusTrap Component
 * 
 * Traps focus within a container for modals and dialogs.
 * WCAG 2.1 Success Criterion 2.4.3 - Focus Order
 */

import { memo, useEffect, useRef, ReactNode, useCallback } from 'react';
import { getFocusableElements } from '@/utils/accessibility';

interface FocusTrapProps {
  children: ReactNode;
  active?: boolean;
  restoreFocus?: boolean;
  autoFocus?: boolean;
  initialFocusRef?: React.RefObject<HTMLElement>;
  finalFocusRef?: React.RefObject<HTMLElement>;
  onEscape?: () => void;
  className?: string;
}

export const FocusTrap = memo<FocusTrapProps>(({
  children,
  active = true,
  restoreFocus = true,
  autoFocus = true,
  initialFocusRef,
  finalFocusRef,
  onEscape,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  // Store the previously focused element
  useEffect(() => {
    if (active) {
      previousFocusRef.current = document.activeElement as HTMLElement;
    }
  }, [active]);

  // Set initial focus
  useEffect(() => {
    if (!active || !autoFocus) return;

    const setInitialFocus = () => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus();
      } else if (containerRef.current) {
        const focusableElements = getFocusableElements(containerRef.current);
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        } else {
          // If no focusable elements, focus the container itself
          containerRef.current.setAttribute('tabindex', '-1');
          containerRef.current.focus();
        }
      }
    };

    // Small delay to ensure DOM is ready
    requestAnimationFrame(setInitialFocus);
  }, [active, autoFocus, initialFocusRef]);

  // Restore focus on unmount
  useEffect(() => {
    return () => {
      if (restoreFocus) {
        const elementToFocus = finalFocusRef?.current || previousFocusRef.current;
        if (elementToFocus && typeof elementToFocus.focus === 'function') {
          requestAnimationFrame(() => {
            elementToFocus.focus();
          });
        }
      }
    };
  }, [restoreFocus, finalFocusRef]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (!active || !containerRef.current) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      onEscape?.();
      return;
    }

    if (event.key !== 'Tab') return;

    const focusableElements = getFocusableElements(containerRef.current);
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey) {
      // Shift + Tab: Move focus backwards
      if (document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
    } else {
      // Tab: Move focus forwards
      if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  }, [active, onEscape]);

  if (!active) {
    return <>{children}</>;
  }

  return (
    <div
      ref={containerRef}
      onKeyDown={handleKeyDown}
      className={className}
    >
      {children}
    </div>
  );
});

FocusTrap.displayName = 'FocusTrap';

export default FocusTrap;
