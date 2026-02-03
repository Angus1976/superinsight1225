/**
 * Label Studio URL 构建工具
 * 
 * 用于构建 Label Studio 的 URL，支持语言同步
 * 
 * @example
 * const { buildLabelStudioUrl } = useLabelStudioUrl();
 * const url = buildLabelStudioUrl(123); // 打开项目 123 的数据管理器
 * const url = buildLabelStudioUrl(123, 456); // 打开项目 123 的任务 456
 */

import { useTranslation } from 'react-i18next';

/**
 * 语言映射：前端语言代码 -> Label Studio 语言代码
 */
const LANGUAGE_MAP: Record<string, string> = {
  'zh': 'zh-cn',      // 中文简体
  'zh-CN': 'zh-cn',   // 中文简体（完整代码）
  'zh-TW': 'zh-tw',   // 中文繁体
  'en': 'en',         // 英文
  'en-US': 'en',      // 英文（美国）
  'en-GB': 'en',      // 英文（英国）
};

/**
 * 默认语言代码
 */
const DEFAULT_LANGUAGE = 'zh-cn';

/**
 * Label Studio URL 构建 Hook
 * 
 * 提供构建 Label Studio URL 的方法，自动同步前端语言设置
 */
export const useLabelStudioUrl = () => {
  const { i18n } = useTranslation();
  
  /**
   * 获取 Label Studio 语言代码
   * 
   * @returns Label Studio 支持的语言代码
   */
  const getLabelStudioLanguage = (): string => {
    const currentLanguage = i18n.language;
    return LANGUAGE_MAP[currentLanguage] || DEFAULT_LANGUAGE;
  };
  
  /**
   * 获取 Label Studio 基础 URL
   * 
   * @returns Label Studio 服务的基础 URL
   */
  const getBaseUrl = (): string => {
    return import.meta.env.VITE_LABEL_STUDIO_URL || 'http://localhost:8080';
  };
  
  /**
   * 构建 Label Studio 数据管理器 URL
   * 
   * @param projectId - Label Studio 项目 ID
   * @param taskId - 可选的任务 ID，用于预选特定任务
   * @returns 完整的 Label Studio URL
   * 
   * @example
   * // 打开项目数据管理器
   * const url = buildLabelStudioUrl(123);
   * // => http://localhost:8080/projects/123/data?lang=zh-cn
   * 
   * // 打开项目数据管理器并预选任务
   * const url = buildLabelStudioUrl(123, 456);
   * // => http://localhost:8080/projects/123/data?lang=zh-cn&task=456
   */
  const buildLabelStudioUrl = (projectId: number, taskId?: number): string => {
    const baseUrl = getBaseUrl();
    const language = getLabelStudioLanguage();
    
    // 构建基础 URL - 使用 /data 端点显示数据管理器（任务列表）
    let url = `${baseUrl}/projects/${projectId}/data`;
    
    // 添加语言参数
    url += `?lang=${language}`;
    
    // 可选：添加任务 ID 参数
    if (taskId !== undefined && taskId !== null) {
      url += `&task=${taskId}`;
    }
    
    return url;
  };
  
  /**
   * 构建 Label Studio 项目设置 URL
   * 
   * @param projectId - Label Studio 项目 ID
   * @returns 项目设置页面 URL
   */
  const buildProjectSettingsUrl = (projectId: number): string => {
    const baseUrl = getBaseUrl();
    const language = getLabelStudioLanguage();
    
    return `${baseUrl}/projects/${projectId}/settings?lang=${language}`;
  };
  
  /**
   * 构建 Label Studio 登录 URL
   * 
   * @returns 登录页面 URL
   */
  const buildLoginUrl = (): string => {
    const baseUrl = getBaseUrl();
    const language = getLabelStudioLanguage();
    
    return `${baseUrl}/user/login?lang=${language}`;
  };
  
  return {
    buildLabelStudioUrl,
    buildProjectSettingsUrl,
    buildLoginUrl,
    getLabelStudioLanguage,
    getBaseUrl,
  };
};

export default useLabelStudioUrl;
