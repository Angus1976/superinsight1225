import i18n from '@/locales/config';
import type { HelpContext } from '@/types/help';
import { isValidHelpKey, HELP_KEY_PATTERN } from '@/types/help';

/**
 * 从路由路径提取页面标识
 * 例: '/dashboard' → 'dashboard', '/tasks/123' → 'tasks', '/' → 'general'
 */
export function extractPageFromRoute(pathname: string): string {
  const segment = pathname.split('/').filter(Boolean)[0];
  return segment || 'general';
}

/**
 * 从 HelpContext 生成 i18n 帮助键（带回退）
 *
 * 优先级：element+component → component → page
 * 查找第一个在 i18n help namespace 中存在的键，最终回退到 page
 */
export function resolveHelpKey(context: HelpContext): string {
  const { page, component, element } = context;

  const candidates = [
    element && component ? `${page}.${component}.${element}` : null,
    component ? `${page}.${component}` : null,
    page,
  ].filter(Boolean) as string[];

  for (const key of candidates) {
    if (i18n.exists(`help:${key}.title`)) {
      return key;
    }
  }

  return page;
}

/**
 * 校验 data-help-key 格式：仅允许 [a-zA-Z0-9._]
 * 委托给 types/help.ts 中的 isValidHelpKey
 */
export const validateHelpKey = isValidHelpKey;

// 重新导出，方便外部统一从 helpUtils 引入
export { HELP_KEY_PATTERN };
