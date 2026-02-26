import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import type { HelpContext } from '@/types/help';
import { extractPageFromRoute } from '@/utils/helpUtils';

// 重新导出，保持向后兼容
export { extractPageFromRoute };

/** 从 activeElement 的 data-help-key 解析组件/元素标识 */
function resolveElementContext(activeEl: Element | null): Pick<HelpContext, 'component' | 'element'> {
  if (!activeEl) return {};

  const helpKey = (activeEl as HTMLElement)
    .closest('[data-help-key]')
    ?.getAttribute('data-help-key');

  if (!helpKey) return {};

  const parts = helpKey.split('.');
  return {
    component: parts.length > 1 ? parts[0] : undefined,
    element: parts.length > 1 ? parts[1] : parts[0],
  };
}

/**
 * 上下文感知 Hook：根据当前路由和聚焦元素返回 HelpContext
 *
 * - 路由变化时自动更新 page
 * - 读取 document.activeElement 上最近的 data-help-key 属性
 * - 无 data-help-key 时回退到页面级上下文
 */
export function useHelpContext(): HelpContext {
  const { pathname } = useLocation();
  const page = useMemo(() => extractPageFromRoute(pathname), [pathname]);

  // activeElement 是瞬时值，每次调用时实时读取
  const elementCtx = resolveElementContext(document.activeElement);

  return { page, ...elementCtx };
}
