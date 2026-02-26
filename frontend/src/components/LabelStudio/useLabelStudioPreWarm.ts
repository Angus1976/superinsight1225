/**
 * Pre-warm hook for Label Studio iframe
 *
 * Creates a hidden iframe in the background to preload Label Studio,
 * reducing perceived load time when the user navigates to the annotation page.
 *
 * Usage: Call on the task list page (or any page before annotation).
 *
 * Validates: Requirement 3.3
 */

import { useEffect, useRef } from 'react';
import { useLanguageStore } from '@/stores/languageStore';

const PREWARM_IFRAME_ID = 'ls-prewarm-iframe';

interface PreWarmOptions {
  /** Base URL for Label Studio (default: '/label-studio') */
  baseUrl?: string;
  /** Whether pre-warm is enabled (default: true) */
  enabled?: boolean;
}

/**
 * Create and append a hidden iframe for pre-warming Label Studio.
 * Returns the created iframe element.
 */
function createHiddenIframe(src: string): HTMLIFrameElement {
  const iframe = document.createElement('iframe');
  iframe.id = PREWARM_IFRAME_ID;
  iframe.src = src;
  iframe.setAttribute('aria-hidden', 'true');
  iframe.setAttribute('tabindex', '-1');
  Object.assign(iframe.style, {
    position: 'absolute',
    width: '0',
    height: '0',
    border: 'none',
    visibility: 'hidden',
    pointerEvents: 'none',
  });
  document.body.appendChild(iframe);
  return iframe;
}

/**
 * Remove the pre-warm iframe from the DOM if it exists.
 */
function removePreWarmIframe(): void {
  document.getElementById(PREWARM_IFRAME_ID)?.remove();
}

/**
 * Pre-warm Label Studio by loading a hidden iframe in the background.
 *
 * The iframe loads the Label Studio base URL with the current language param,
 * warming up the server connection, static assets, and session cookies.
 * It is automatically cleaned up on unmount.
 */
export function useLabelStudioPreWarm({
  baseUrl = '/label-studio',
  enabled = true,
}: PreWarmOptions = {}): void {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const language = useLanguageStore((s) => s.language);

  useEffect(() => {
    if (!enabled) return;

    // Avoid duplicate iframes
    if (document.getElementById(PREWARM_IFRAME_ID)) return;

    const src = `${baseUrl}/?lang=${language}`;
    iframeRef.current = createHiddenIframe(src);

    return () => {
      removePreWarmIframe();
      iframeRef.current = null;
    };
  }, [baseUrl, enabled, language]);
}
