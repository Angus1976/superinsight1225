import type { TFunction } from 'i18next';

/** True if string contains CJK characters (already a display name). */
export function isLikelyChineseDisplayName(text: string): boolean {
  return /[\u4e00-\u9fff]/.test(text);
}

/**
 * Localized skill name from `aiAssistant.skillName.<slug>`.
 * Uses Chinese (or other locale) when i18n language matches resources.
 */
export function skillDisplayName(slug: string, t: TFunction): string {
  if (!slug) return '';
  if (isLikelyChineseDisplayName(slug)) return slug;
  return t(`skillName.${slug}`, { defaultValue: slug });
}

/**
 * Localized skill category from `aiAssistant.skillCategory.<slug>`.
 * Pass `t` from `useTranslation('aiAssistant')`.
 */
export function skillCategoryLabel(cat: string, t: TFunction): string {
  if (!cat) return '';
  if (isLikelyChineseDisplayName(cat)) return cat;
  return t(`skillCategory.${cat}`, { defaultValue: cat });
}
