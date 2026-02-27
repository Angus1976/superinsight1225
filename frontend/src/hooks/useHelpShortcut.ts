import { useEffect } from 'react';
import { useHelpStore } from '@/stores/helpStore';
import { extractPageFromRoute, resolveHelpKey } from '@/utils/helpUtils';
import type { HelpContext } from '@/types/help';

/** 解析当前上下文：路由 + activeElement 的 data-help-key */
function resolveCurrentContext(): HelpContext {
  const page = extractPageFromRoute(window.location.pathname);

  const activeEl = document.activeElement as HTMLElement | null;
  const helpKey = activeEl
    ?.closest('[data-help-key]')
    ?.getAttribute('data-help-key');

  if (helpKey) {
    const parts = helpKey.split('.');
    return {
      page,
      component: parts.length > 1 ? parts[0] : undefined,
      element: parts.length > 1 ? parts[1] : parts[0],
    };
  }

  return { page };
}

/**
 * 全局快捷键 Hook：F1 和 ? 触发帮助浮层
 *
 * - F1：任何场景均可触发
 * - ?：输入框（INPUT/TEXTAREA/SELECT/contentEditable）内不触发
 * - 组件卸载时自动清理监听器
 */
export function useHelpShortcut(): void {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      const isF1 = event.key === 'F1';
      const isQuestionMark = event.key === '?';

      if (!isF1 && !isQuestionMark) return;

      // ? 键在输入类元素内不触发，避免干扰输入
      if (isQuestionMark) {
        const tag = (event.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if ((event.target as HTMLElement)?.isContentEditable) return;
      }

      event.preventDefault();

      const context = resolveCurrentContext();
      const helpKey = resolveHelpKey(context);

      // 获取聚焦元素位置用于定位浮层
      const activeEl = document.activeElement as HTMLElement | null;
      const rect = activeEl?.getBoundingClientRect();
      const position = rect
        ? { x: rect.left + rect.width / 2, y: rect.top }
        : undefined;

      const store = useHelpStore.getState();

      if (store.visible) {
        store.hideHelp();
      } else {
        store.showHelp(helpKey, position);
      }
    }

    document.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => document.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, []);
}
