import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useHelpShortcut } from '../useHelpShortcut';
import { useHelpStore } from '@/stores/helpStore';

/** Dispatch a keydown event on document, optionally targeting a specific element */
function pressKey(key: string, target?: EventTarget) {
  const event = new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    cancelable: true,
  });

  if (target) {
    Object.defineProperty(event, 'target', { value: target, writable: false });
  }

  document.dispatchEvent(event);
  return event;
}

function resetStore() {
  useHelpStore.setState({
    visible: false,
    currentHelpKey: null,
    position: null,
  });
}

describe('useHelpShortcut', () => {
  beforeEach(() => {
    resetStore();
  });

  afterEach(() => {
    resetStore();
  });

  it('F1 triggers showHelp', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    pressKey('F1');

    const state = useHelpStore.getState();
    expect(state.visible).toBe(true);
    expect(state.currentHelpKey).toBeTruthy();

    unmount();
  });

  it('? key triggers showHelp', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    pressKey('?');

    const state = useHelpStore.getState();
    expect(state.visible).toBe(true);
    expect(state.currentHelpKey).toBeTruthy();

    unmount();
  });

  it('? key suppressed when target is INPUT', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    pressKey('?', input);

    expect(useHelpStore.getState().visible).toBe(false);

    document.body.removeChild(input);
    unmount();
  });

  it('? key suppressed when target is TEXTAREA', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    textarea.focus();

    pressKey('?', textarea);

    expect(useHelpStore.getState().visible).toBe(false);

    document.body.removeChild(textarea);
    unmount();
  });

  it('? key suppressed when target is SELECT', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const select = document.createElement('select');
    document.body.appendChild(select);
    select.focus();

    pressKey('?', select);

    expect(useHelpStore.getState().visible).toBe(false);

    document.body.removeChild(select);
    unmount();
  });

  it('? key suppressed when target is contentEditable', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const div = document.createElement('div');
    div.contentEditable = 'true';
    // jsdom may not reflect isContentEditable correctly, so define it explicitly
    Object.defineProperty(div, 'isContentEditable', { value: true, writable: false });
    document.body.appendChild(div);
    div.focus();

    pressKey('?', div);

    expect(useHelpStore.getState().visible).toBe(false);

    document.body.removeChild(div);
    unmount();
  });

  it('F1 works even when focus is in INPUT', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    pressKey('F1', input);

    expect(useHelpStore.getState().visible).toBe(true);

    document.body.removeChild(input);
    unmount();
  });

  it('toggle: pressing shortcut when help is visible hides it', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    // First press: show
    pressKey('F1');
    expect(useHelpStore.getState().visible).toBe(true);

    // Second press: hide
    pressKey('F1');
    expect(useHelpStore.getState().visible).toBe(false);

    unmount();
  });

  it('cleanup: keydown no longer triggers after unmount', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    unmount();

    pressKey('F1');

    expect(useHelpStore.getState().visible).toBe(false);
  });

  it('event.preventDefault is called for F1', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const event = pressKey('F1');

    expect(event.defaultPrevented).toBe(true);

    unmount();
  });

  it('event.preventDefault is called for ?', () => {
    const { unmount } = renderHook(() => useHelpShortcut());

    const event = pressKey('?');

    expect(event.defaultPrevented).toBe(true);

    unmount();
  });
});
