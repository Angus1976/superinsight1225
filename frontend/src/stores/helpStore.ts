import { create } from 'zustand';
import type { HelpState } from '@/types/help';

export const useHelpStore = create<HelpState>()((set, get) => ({
  visible: false,
  currentHelpKey: null,
  position: null,

  showHelp: (helpKey, position) => {
    if (!helpKey) return;

    set({
      visible: true,
      currentHelpKey: helpKey,
      ...(position ? { position } : {}),
    });
  },

  hideHelp: () => {
    set({
      visible: false,
      currentHelpKey: null,
      position: null,
    });
  },

  toggleHelp: () => {
    const { visible } = get();
    if (visible) {
      set({
        visible: false,
        currentHelpKey: null,
        position: null,
      });
    }
    // When toggling to visible, caller should use showHelp with a helpKey
    // to maintain the invariant: visible === true ⟹ currentHelpKey !== null
  },
}));
