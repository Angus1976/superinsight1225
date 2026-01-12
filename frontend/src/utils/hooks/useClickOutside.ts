/**
 * useClickOutside Hook
 * 
 * A hook for detecting clicks outside of a referenced element.
 * Useful for closing dropdowns, modals, and popovers.
 * 
 * @module hooks/useClickOutside
 * @version 1.0.0
 */

import { useEffect, useRef, useCallback, type RefObject } from 'react';

/**
 * Options for useClickOutside
 */
export interface UseClickOutsideOptions {
  /** Event type to listen for */
  eventType?: 'mousedown' | 'mouseup' | 'click';
  /** Ignore elements matching selector */
  ignoreSelector?: string;
  /** Enabled state */
  enabled?: boolean;
}

/**
 * Hook for detecting clicks outside of an element
 * 
 * @param handler - Callback when click outside occurs
 * @param options - Configuration options
 * @returns Ref to attach to the element
 * 
 * @example
 * ```typescript
 * const MyDropdown = () => {
 *   const [isOpen, setIsOpen] = useState(false);
 *   const ref = useClickOutside(() => setIsOpen(false), { enabled: isOpen });
 *   
 *   return (
 *     <div ref={ref}>
 *       <button onClick={() => setIsOpen(true)}>Open</button>
 *       {isOpen && <div>Dropdown content</div>}
 *     </div>
 *   );
 * };
 * ```
 */
export function useClickOutside<T extends HTMLElement = HTMLElement>(
  handler: (event: MouseEvent | TouchEvent) => void,
  options: UseClickOutsideOptions = {}
): RefObject<T | null> {
  const { eventType = 'mousedown', ignoreSelector, enabled = true } = options;
  const ref = useRef<T | null>(null);

  const handleClickOutside = useCallback(
    (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node;

      // Check if click is inside the ref element
      if (ref.current && ref.current.contains(target)) {
        return;
      }

      // Check if click is on an ignored element
      if (ignoreSelector && target instanceof Element) {
        if (target.closest(ignoreSelector)) {
          return;
        }
      }

      handler(event);
    },
    [handler, ignoreSelector]
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener(eventType, handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);

    return () => {
      document.removeEventListener(eventType, handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [eventType, handleClickOutside, enabled]);

  return ref;
}

/**
 * Hook for detecting clicks outside of multiple elements
 * 
 * @param handler - Callback when click outside occurs
 * @param refs - Array of refs to check
 * @param options - Configuration options
 */
export function useClickOutsideMultiple(
  handler: (event: MouseEvent | TouchEvent) => void,
  refs: RefObject<HTMLElement>[],
  options: UseClickOutsideOptions = {}
): void {
  const { eventType = 'mousedown', ignoreSelector, enabled = true } = options;

  const handleClickOutside = useCallback(
    (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node;

      // Check if click is inside any of the ref elements
      const isInside = refs.some(ref => ref.current && ref.current.contains(target));
      if (isInside) {
        return;
      }

      // Check if click is on an ignored element
      if (ignoreSelector && target instanceof Element) {
        if (target.closest(ignoreSelector)) {
          return;
        }
      }

      handler(event);
    },
    [handler, refs, ignoreSelector]
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener(eventType, handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);

    return () => {
      document.removeEventListener(eventType, handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [eventType, handleClickOutside, enabled]);
}

export default useClickOutside;
