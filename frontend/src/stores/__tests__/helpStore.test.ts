import { describe, it, expect, beforeEach } from 'vitest';
import { useHelpStore } from '../helpStore';

describe('helpStore', () => {
  beforeEach(() => {
    // Reset to initial state
    useHelpStore.setState({
      visible: false,
      currentHelpKey: null,
      position: null,
    });
  });

  describe('initial state', () => {
    it('starts with visible false', () => {
      expect(useHelpStore.getState().visible).toBe(false);
    });

    it('starts with currentHelpKey null', () => {
      expect(useHelpStore.getState().currentHelpKey).toBeNull();
    });

    it('starts with position null', () => {
      expect(useHelpStore.getState().position).toBeNull();
    });
  });

  describe('showHelp', () => {
    it('sets visible to true and currentHelpKey', () => {
      useHelpStore.getState().showHelp('dashboard');

      const state = useHelpStore.getState();
      expect(state.visible).toBe(true);
      expect(state.currentHelpKey).toBe('dashboard');
    });

    it('updates position when provided', () => {
      useHelpStore.getState().showHelp('tasks', { x: 100, y: 200 });

      const state = useHelpStore.getState();
      expect(state.position).toEqual({ x: 100, y: 200 });
    });

    it('does not overwrite position when not provided', () => {
      useHelpStore.getState().showHelp('dashboard', { x: 50, y: 60 });
      useHelpStore.getState().showHelp('tasks');

      expect(useHelpStore.getState().position).toEqual({ x: 50, y: 60 });
    });

    it('ignores empty helpKey', () => {
      useHelpStore.getState().showHelp('');

      const state = useHelpStore.getState();
      expect(state.visible).toBe(false);
      expect(state.currentHelpKey).toBeNull();
    });
  });

  describe('hideHelp', () => {
    it('resets all state to initial values', () => {
      useHelpStore.getState().showHelp('dashboard', { x: 10, y: 20 });
      useHelpStore.getState().hideHelp();

      const state = useHelpStore.getState();
      expect(state.visible).toBe(false);
      expect(state.currentHelpKey).toBeNull();
      expect(state.position).toBeNull();
    });
  });

  describe('toggleHelp', () => {
    it('hides help when currently visible', () => {
      useHelpStore.getState().showHelp('dashboard');
      useHelpStore.getState().toggleHelp();

      const state = useHelpStore.getState();
      expect(state.visible).toBe(false);
      expect(state.currentHelpKey).toBeNull();
    });

    it('does not set visible to true without helpKey (invariant protection)', () => {
      useHelpStore.getState().toggleHelp();

      // toggleHelp alone cannot set visible=true because it has no helpKey
      // Caller must use showHelp to provide a helpKey
      expect(useHelpStore.getState().visible).toBe(false);
    });
  });

  describe('state invariants', () => {
    it('visible true implies currentHelpKey is not null', () => {
      useHelpStore.getState().showHelp('dashboard');
      const state = useHelpStore.getState();

      if (state.visible) {
        expect(state.currentHelpKey).not.toBeNull();
      }
    });

    it('visible false implies currentHelpKey is null after hideHelp', () => {
      useHelpStore.getState().showHelp('dashboard');
      useHelpStore.getState().hideHelp();
      const state = useHelpStore.getState();

      if (!state.visible) {
        expect(state.currentHelpKey).toBeNull();
      }
    });
  });
});
