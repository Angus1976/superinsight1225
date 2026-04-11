/**
 * 在 iframe 内时，用顶层窗口打开同源的登录 URL，避免子 frame 内路由与父页面不同源导致失败。
 * 父页面为 chrome-error:// 时脚本通常无法替用户完成跳转，需在地址栏直接打开站点。
 */
export function assignTopWindowSameOrigin(pathWithLeadingSlash: string): boolean {
  if (typeof window === 'undefined') return false;
  if (window.self === window.top) return false;
  try {
    const url = `${window.location.origin}${pathWithLeadingSlash}`;
    window.top?.location.assign(url);
    return true;
  } catch {
    return false;
  }
}
