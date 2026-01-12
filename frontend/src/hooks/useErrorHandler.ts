/**
 * useErrorHandler Hook
 * 
 * Comprehensive error handling hook for managing errors throughout the application.
 * Provides error transformation, notification, retry logic, and recovery actions.
 */

import { useCallback, useState, useRef } from 'react';
import { message, notification } from 'antd';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type {
  AppError,
  ErrorCategory,
  RecoveryAction,
  ErrorNotificationOptions,
  ErrorHandlerConfig,
  DEFAULT_ERROR_CONFIG,
} from '@/types/error';
import { transformError, isRetryableError } from '@/utils/errorHandler';
import { useAnnounce } from './useAccessibility';

// Error state interface
interface ErrorState {
  errors: AppError[];
  lastError: AppError | null;
  isLoading: boolean;
}

// Hook options
interface UseErrorHandlerOptions extends Partial<ErrorHandlerConfig> {
  onError?: (error: AppError) => void;
  onRecovery?: (error: AppError, action: RecoveryAction) => void;
}

// Default configuration
const defaultConfig: ErrorHandlerConfig = {
  enableNotifications: true,
  enableLogging: true,
  enableReporting: true,
  defaultMaxRetries: 3,
  retryDelay: 1000,
  retryBackoffMultiplier: 2,
  defaultNotificationDuration: 5000,
  notificationPosition: 'topRight',
};

/**
 * Main error handler hook
 */
export const useErrorHandler = (options: UseErrorHandlerOptions = {}) => {
  const { t } = useTranslation('common');
  const navigate = useNavigate();
  const { announceError } = useAnnounce();
  
  const config = { ...defaultConfig, ...options };
  
  const [state, setState] = useState<ErrorState>({
    errors: [],
    lastError: null,
    isLoading: false,
  });
  
  const retryCountRef = useRef<Map<string, number>>(new Map());

  // Show error notification
  const showErrorNotification = useCallback((
    error: AppError,
    notificationOptions?: ErrorNotificationOptions
  ) => {
    if (!config.enableNotifications) return;
    
    const {
      duration = config.defaultNotificationDuration,
      position = config.notificationPosition,
      showIcon = true,
      closable = true,
    } = notificationOptions || {};
    
    // Get translated message
    const translatedMessage = t(error.message, { defaultValue: error.technicalMessage });
    
    // Announce for screen readers
    announceError(translatedMessage);
    
    // Show notification based on severity
    const notificationConfig = {
      message: t('error.title'),
      description: translatedMessage,
      duration: duration / 1000,
      placement: position,
      showProgress: true,
      pauseOnHover: true,
    };
    
    switch (error.severity) {
      case 'info':
        notification.info(notificationConfig);
        break;
      case 'warning':
        notification.warning(notificationConfig);
        break;
      case 'critical':
      case 'error':
      default:
        notification.error(notificationConfig);
        break;
    }
  }, [config, t, announceError]);

  // Log error
  const logError = useCallback((error: AppError) => {
    if (!config.enableLogging) return;
    
    console.group(`🚨 Error [${error.code}]`);
    console.error('Message:', error.message);
    console.error('Technical:', error.technicalMessage);
    console.error('Category:', error.category);
    console.error('Severity:', error.severity);
    if (error.endpoint) {
      console.error('Endpoint:', `${error.method} ${error.endpoint}`);
    }
    if (error.fieldErrors?.length) {
      console.error('Field Errors:', error.fieldErrors);
    }
    console.error('Context:', error.context);
    console.groupEnd();
  }, [config.enableLogging]);

  // Report error to monitoring service
  const reportError = useCallback((error: AppError) => {
    if (!config.enableReporting) return;
    
    // TODO: Integrate with error monitoring service (e.g., Sentry)
    // For now, just mark as reported
    error.reported = true;
  }, [config.enableReporting]);

  // Handle error
  const handleError = useCallback((
    error: unknown,
    notificationOptions?: ErrorNotificationOptions
  ): AppError => {
    const appError = transformError(error);
    
    // Log error
    logError(appError);
    
    // Report error
    reportError(appError);
    
    // Show notification
    showErrorNotification(appError, notificationOptions);
    
    // Update state
    setState(prev => ({
      ...prev,
      errors: [...prev.errors, appError],
      lastError: appError,
    }));
    
    // Call custom error handler
    config.onError?.(appError);
    
    return appError;
  }, [logError, reportError, showErrorNotification, config]);

  // Execute recovery action
  const executeRecoveryAction = useCallback(async (
    error: AppError,
    action: RecoveryAction,
    customHandler?: () => void | Promise<void>
  ) => {
    setState(prev => ({ ...prev, isLoading: true }));
    
    try {
      switch (action) {
        case 'retry':
          // Retry logic is handled by the caller
          break;
          
        case 'refresh':
          window.location.reload();
          break;
          
        case 'login':
          navigate('/login');
          break;
          
        case 'goBack':
          navigate(-1);
          break;
          
        case 'goHome':
          navigate('/');
          break;
          
        case 'contact':
          // Open support contact (could be a modal or external link)
          window.open('/support', '_blank');
          break;
          
        case 'dismiss':
          dismissError(error.id);
          break;
          
        case 'custom':
          if (customHandler) {
            await customHandler();
          }
          break;
      }
      
      // Call recovery callback
      config.onRecovery?.(error, action);
      
    } finally {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, [navigate, config]);

  // Dismiss error
  const dismissError = useCallback((errorId: string) => {
    setState(prev => ({
      ...prev,
      errors: prev.errors.map(e => 
        e.id === errorId ? { ...e, dismissed: true } : e
      ),
      lastError: prev.lastError?.id === errorId 
        ? { ...prev.lastError, dismissed: true } 
        : prev.lastError,
    }));
  }, []);

  // Clear all errors
  const clearErrors = useCallback(() => {
    setState({
      errors: [],
      lastError: null,
      isLoading: false,
    });
    retryCountRef.current.clear();
  }, []);

  // Retry operation with exponential backoff
  const retryOperation = useCallback(async <T>(
    operation: () => Promise<T>,
    errorId?: string
  ): Promise<T> => {
    const key = errorId || 'default';
    const currentRetry = retryCountRef.current.get(key) || 0;
    
    if (currentRetry >= config.defaultMaxRetries) {
      throw new Error('Max retries exceeded');
    }
    
    // Calculate delay with exponential backoff
    const delay = config.retryDelay * Math.pow(config.retryBackoffMultiplier, currentRetry);
    
    // Wait before retry
    await new Promise(resolve => setTimeout(resolve, delay));
    
    // Increment retry count
    retryCountRef.current.set(key, currentRetry + 1);
    
    try {
      const result = await operation();
      // Reset retry count on success
      retryCountRef.current.delete(key);
      return result;
    } catch (error) {
      const appError = transformError(error);
      
      if (appError.canRetry && currentRetry + 1 < config.defaultMaxRetries) {
        // Show retry notification
        message.loading({
          content: t('error.retrying', { attempt: currentRetry + 2, max: config.defaultMaxRetries }),
          key: 'retry-notification',
        });
        
        return retryOperation(operation, key);
      }
      
      throw error;
    }
  }, [config, t]);

  // Wrap async operation with error handling
  const withErrorHandling = useCallback(<T>(
    operation: () => Promise<T>,
    options?: {
      showNotification?: boolean;
      autoRetry?: boolean;
      onSuccess?: (result: T) => void;
      onError?: (error: AppError) => void;
    }
  ): Promise<T | null> => {
    const { showNotification = true, autoRetry = false, onSuccess, onError } = options || {};
    
    setState(prev => ({ ...prev, isLoading: true }));
    
    const execute = async (): Promise<T | null> => {
      try {
        const result = autoRetry 
          ? await retryOperation(operation)
          : await operation();
        
        onSuccess?.(result);
        return result;
      } catch (error) {
        const appError = handleError(error, { 
          duration: showNotification ? config.defaultNotificationDuration : 0 
        });
        onError?.(appError);
        return null;
      } finally {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };
    
    return execute();
  }, [handleError, retryOperation, config]);

  // Get active (non-dismissed) errors
  const activeErrors = state.errors.filter(e => !e.dismissed);

  return {
    // State
    errors: state.errors,
    activeErrors,
    lastError: state.lastError,
    isLoading: state.isLoading,
    hasErrors: activeErrors.length > 0,
    
    // Actions
    handleError,
    dismissError,
    clearErrors,
    executeRecoveryAction,
    retryOperation,
    withErrorHandling,
    showErrorNotification,
  };
};

/**
 * Hook for field-level validation errors
 */
export const useFieldErrors = () => {
  const [fieldErrors, setFieldErrors] = useState<Map<string, string>>(new Map());
  
  const setFieldError = useCallback((field: string, message: string) => {
    setFieldErrors(prev => new Map(prev).set(field, message));
  }, []);
  
  const clearFieldError = useCallback((field: string) => {
    setFieldErrors(prev => {
      const next = new Map(prev);
      next.delete(field);
      return next;
    });
  }, []);
  
  const clearAllFieldErrors = useCallback(() => {
    setFieldErrors(new Map());
  }, []);
  
  const getFieldError = useCallback((field: string): string | undefined => {
    return fieldErrors.get(field);
  }, [fieldErrors]);
  
  const hasFieldError = useCallback((field: string): boolean => {
    return fieldErrors.has(field);
  }, [fieldErrors]);
  
  const setFieldErrorsFromAppError = useCallback((error: AppError) => {
    if (error.fieldErrors) {
      const newErrors = new Map<string, string>();
      for (const fieldError of error.fieldErrors) {
        newErrors.set(fieldError.field, fieldError.message);
      }
      setFieldErrors(newErrors);
    }
  }, []);
  
  return {
    fieldErrors,
    setFieldError,
    clearFieldError,
    clearAllFieldErrors,
    getFieldError,
    hasFieldError,
    setFieldErrorsFromAppError,
    hasErrors: fieldErrors.size > 0,
  };
};

export default useErrorHandler;
