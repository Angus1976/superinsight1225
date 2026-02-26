/** 帮助条目 */
export interface HelpEntry {
  title: string;
  description: string;
  shortcut?: string;
  related?: string[];
}

/** 帮助上下文 */
export interface HelpContext {
  page: string;
  component?: string;
  element?: string;
}

/** 帮助状态（Zustand store） */
export interface HelpState {
  visible: boolean;
  currentHelpKey: string | null;
  position: { x: number; y: number } | null;

  showHelp: (helpKey: string, position?: { x: number; y: number }) => void;
  hideHelp: () => void;
  toggleHelp: () => void;
}

/** data-help-key 合法格式：仅允许 [a-zA-Z0-9._] */
export const HELP_KEY_PATTERN = /^[a-zA-Z0-9._]+$/;

/** 校验 data-help-key 值 */
export function isValidHelpKey(key: string): boolean {
  return HELP_KEY_PATTERN.test(key);
}
