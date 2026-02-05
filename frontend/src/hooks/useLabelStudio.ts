/**
 * Label Studio 综合 Hook
 * 
 * 提供 Label Studio 集成的完整功能：
 * - URL 构建（使用 useLabelStudioUrl）
 * - 项目管理
 * - 错误处理
 * - 窗口操作
 * 
 * @example
 * const { openLabelStudio, handleError, isValidProject } = useLabelStudio();
 * 
 * // 打开 Label Studio
 * openLabelStudio(projectId);
 * 
 * // 处理错误
 * const errorInfo = handleError(error);
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { useTranslation } from 'react-i18next';
import { useLabelStudioUrl } from './useLabelStudioUrl';
import {
  LABEL_STUDIO_ERROR_TYPES,
  LABEL_STUDIO_WINDOW_OPTIONS,
  type LabelStudioErrorType,
} from '@/constants/labelStudio';
import { labelStudioLogger } from '@/utils/labelStudioLogger';
import type { AxiosError } from 'axios';

/**
 * Label Studio 错误信息
 */
export interface LabelStudioError {
  type: LabelStudioErrorType;
  message: string;
  details?: string;
}

/**
 * useLabelStudio Hook 返回类型
 */
export interface UseLabelStudioReturn {
  /** URL 构建函数 */
  buildLabelStudioUrl: (projectId: number, taskId?: number) => string;
  /** 构建项目设置 URL */
  buildProjectSettingsUrl: (projectId: number) => string;
  /** 构建登录 URL */
  buildLoginUrl: () => string;
  /** 获取 Label Studio 语言代码 */
  getLabelStudioLanguage: () => string;
  /** 获取基础 URL */
  getBaseUrl: () => string;
  /** 在新窗口中打开 Label Studio */
  openLabelStudio: (projectId: number, taskId?: number) => void;
  /** 在新窗口中打开项目设置 */
  openProjectSettings: (projectId: number) => void;
  /** 处理 Label Studio 相关错误 */
  handleError: (error: unknown) => LabelStudioError;
  /** 检查项目 ID 是否有效 */
  isValidProject: (projectId: number | string | null | undefined) => boolean;
  /** 导航到标注页面 */
  navigateToAnnotate: (taskId: string) => void;
  /** 导航到任务详情 */
  navigateToTaskDetail: (taskId: string) => void;
}

/**
 * Label Studio 综合 Hook
 * 
 * 整合 URL 构建、项目管理、错误处理等功能
 */
export const useLabelStudio = (): UseLabelStudioReturn => {
  const navigate = useNavigate();
  const { t } = useTranslation('tasks');
  const {
    buildLabelStudioUrl,
    buildProjectSettingsUrl,
    buildLoginUrl,
    getLabelStudioLanguage,
    getBaseUrl,
  } = useLabelStudioUrl();

  /**
   * 在新窗口中打开 Label Studio 数据管理器
   */
  const openLabelStudio = useCallback((projectId: number, taskId?: number) => {
    const url = buildLabelStudioUrl(projectId, taskId);
    const requestId = labelStudioLogger.logWindowOpen(projectId, url, taskId);
    
    window.open(url, '_blank', LABEL_STUDIO_WINDOW_OPTIONS);
    
    labelStudioLogger.endOperation('Open Label Studio Window', requestId, true, {
      projectId,
      taskId,
      url,
    });
    message.success(t('openedLabelStudioDataManager'));
  }, [buildLabelStudioUrl, t]);

  /**
   * 在新窗口中打开项目设置
   */
  const openProjectSettings = useCallback((projectId: number) => {
    const url = buildProjectSettingsUrl(projectId);
    const requestId = labelStudioLogger.startOperation('Open Project Settings', { projectId, url });
    
    window.open(url, '_blank', LABEL_STUDIO_WINDOW_OPTIONS);
    
    labelStudioLogger.endOperation('Open Project Settings', requestId, true);
  }, [buildProjectSettingsUrl]);

  /**
   * 处理 Label Studio 相关错误
   * 将各种错误类型转换为统一的错误信息格式
   */
  const handleError = useCallback((error: unknown): LabelStudioError => {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    const status = axiosError.response?.status;
    const errorDetail = axiosError.response?.data?.detail || axiosError.response?.data?.message;

    let errorType: LabelStudioErrorType;
    let errorMessage: string;
    let errorDetails: string | undefined;

    // 404 - 项目不存在
    if (status === 404) {
      errorType = LABEL_STUDIO_ERROR_TYPES.NOT_FOUND;
      errorMessage = t('annotate.projectNotFound');
      errorDetails = t('annotate.projectNotFoundDescription');
    }
    // 401/403 - 认证失败
    else if (status === 401 || status === 403) {
      errorType = LABEL_STUDIO_ERROR_TYPES.AUTH;
      errorMessage = t('annotate.authenticationFailed');
      errorDetails = errorDetail;
    }
    // 502/503/504 - 服务不可用
    else if (status === 502 || status === 503 || status === 504) {
      errorType = LABEL_STUDIO_ERROR_TYPES.SERVICE;
      errorMessage = t('annotate.serviceUnavailable');
      errorDetails = errorDetail;
    }
    // 网络错误
    else if (axiosError.code === 'ECONNABORTED' || axiosError.code === 'ERR_NETWORK') {
      errorType = LABEL_STUDIO_ERROR_TYPES.NETWORK;
      errorMessage = t('annotate.networkError');
      errorDetails = axiosError.message;
    }
    // 未知错误
    else {
      errorType = LABEL_STUDIO_ERROR_TYPES.UNKNOWN;
      errorMessage = t('annotate.unexpectedError');
      errorDetails = errorDetail || (error instanceof Error ? error.message : undefined);
    }

    // 记录错误日志
    labelStudioLogger.logError('Handle Label Studio Error', error, undefined, {
      errorType,
      status,
      errorDetail,
    });

    return {
      type: errorType,
      message: errorMessage,
      details: errorDetails,
    };
  }, [t]);

  /**
   * 检查项目 ID 是否有效
   */
  const isValidProject = useCallback((projectId: number | string | null | undefined): boolean => {
    if (projectId === null || projectId === undefined) return false;
    if (typeof projectId === 'string') {
      const parsed = parseInt(projectId, 10);
      return !isNaN(parsed) && parsed > 0;
    }
    return typeof projectId === 'number' && projectId > 0;
  }, []);

  /**
   * 导航到标注页面
   */
  const navigateToAnnotate = useCallback((taskId: string) => {
    navigate(`/tasks/${taskId}/annotate`);
  }, [navigate]);

  /**
   * 导航到任务详情
   */
  const navigateToTaskDetail = useCallback((taskId: string) => {
    navigate(`/tasks/${taskId}`);
  }, [navigate]);

  return {
    // URL 构建函数（来自 useLabelStudioUrl）
    buildLabelStudioUrl,
    buildProjectSettingsUrl,
    buildLoginUrl,
    getLabelStudioLanguage,
    getBaseUrl,
    // 窗口操作
    openLabelStudio,
    openProjectSettings,
    // 错误处理
    handleError,
    // 工具函数
    isValidProject,
    navigateToAnnotate,
    navigateToTaskDetail,
  };
};

export default useLabelStudio;
