import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Alert } from 'react-native';

export interface AppError {
  id: string;
  type: 'network' | 'api' | 'auth' | 'validation' | 'runtime' | 'unknown';
  message: string;
  details?: string;
  timestamp: Date;
  stack?: string;
  retryable?: boolean;
  onRetry?: () => void;
}

interface ErrorContextType {
  errors: AppError[];
  showError: (error: Partial<AppError> & { message: string }) => void;
  showNetworkError: (message?: string, onRetry?: () => void) => void;
  showApiError: (status: number, message: string, onRetry?: () => void) => void;
  showAuthError: (message?: string) => void;
  dismissError: (id: string) => void;
  clearErrors: () => void;
  hasErrors: boolean;
  lastError?: AppError;
}

const ErrorContext = createContext<ErrorContextType | undefined>(undefined);

interface ErrorProviderProps {
  children: ReactNode;
}

export function ErrorProvider({ children }: ErrorProviderProps) {
  const [errors, setErrors] = useState<AppError[]>([]);

  const generateId = useCallback(() => {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  const showError = useCallback((error: Partial<AppError> & { message: string }) => {
    const newError: AppError = {
      id: generateId(),
      type: 'unknown',
      timestamp: new Date(),
      ...error,
    };

    setErrors(prev => [...prev, newError]);

    // Auto-dismiss error after 10 seconds for non-critical errors
    if (newError.type !== 'auth' && newError.type !== 'runtime') {
      setTimeout(() => {
        setErrors(prev => prev.filter(e => e.id !== newError.id));
      }, 10000);
    }
  }, [generateId]);

  const showNetworkError = useCallback((
    message = 'Network connection failed. Please check your internet connection.',
    onRetry?: () => void
  ) => {
    showError({
      type: 'network',
      message,
      retryable: true,
      onRetry,
    });
  }, [showError]);

  const showApiError = useCallback((
    status: number, 
    message: string, 
    onRetry?: () => void
  ) => {
    let userFriendlyMessage = message;

    // Convert technical API errors to user-friendly messages
    switch (status) {
      case 400:
        userFriendlyMessage = 'Invalid request. Please check your input and try again.';
        break;
      case 401:
        userFriendlyMessage = 'Authentication failed. Please sign in again.';
        break;
      case 403:
        userFriendlyMessage = 'Access denied. You don\'t have permission for this action.';
        break;
      case 404:
        userFriendlyMessage = 'The requested resource was not found.';
        break;
      case 429:
        userFriendlyMessage = 'Too many requests. Please wait a moment and try again.';
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        userFriendlyMessage = 'Server error. Our team has been notified. Please try again later.';
        break;
    }

    showError({
      type: 'api',
      message: userFriendlyMessage,
      details: `HTTP ${status}: ${message}`,
      retryable: status >= 500 || status === 429,
      onRetry,
    });
  }, [showError]);

  const showAuthError = useCallback((
    message = 'Authentication failed. Please sign in again.'
  ) => {
    showError({
      type: 'auth',
      message,
      retryable: false,
    });

    // Show authentication error as an alert since it's critical
    Alert.alert(
      'Authentication Error',
      message,
      [
        { text: 'OK', style: 'default' }
      ]
    );
  }, [showError]);

  const dismissError = useCallback((id: string) => {
    setErrors(prev => prev.filter(error => error.id !== id));
  }, []);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  const contextValue: ErrorContextType = {
    errors,
    showError,
    showNetworkError,
    showApiError,
    showAuthError,
    dismissError,
    clearErrors,
    hasErrors: errors.length > 0,
    lastError: errors[errors.length - 1],
  };

  return (
    <ErrorContext.Provider value={contextValue}>
      {children}
    </ErrorContext.Provider>
  );
}

export function useError(): ErrorContextType {
  const context = useContext(ErrorContext);
  if (context === undefined) {
    throw new Error('useError must be used within an ErrorProvider');
  }
  return context;
}

// Hook for API error handling
export function useApiError() {
  const { showApiError, showNetworkError, showAuthError, showError } = useError();

  const handleError = useCallback((
    errorTypeOrError: any | 'network' | 'api' | 'auth' | 'authentication' | 'system',
    message?: string,
    retryable?: boolean,
    onRetry?: () => void
  ) => {
    // Handle string-based error types (for convenience)
    if (typeof errorTypeOrError === 'string') {
      const errorType = errorTypeOrError === 'authentication' ? 'auth' : errorTypeOrError as any;
      
      switch (errorType) {
        case 'network':
          showNetworkError(message, onRetry);
          break;
        case 'auth':
          showAuthError(message);
          break;
        case 'api':
        case 'system':
          showApiError(500, message || 'An error occurred', onRetry);
          break;
        default:
          showError({
            type: 'unknown',
            message: message || 'An unexpected error occurred',
            retryable: retryable || false,
            onRetry,
          });
      }
      return;
    }

    // Handle error objects
    const error = errorTypeOrError;
    if (error.name === 'ApiError') {
      if (error.status === 401) {
        showAuthError();
      } else {
        showApiError(error.status, error.message, onRetry);
      }
    } else if (error.name === 'NetworkError' || error.code === 'NETWORK_ERROR') {
      showNetworkError(undefined, onRetry);
    } else {
      showApiError(500, error.message || 'An unexpected error occurred', onRetry);
    }
  }, [showApiError, showNetworkError, showAuthError, showError]);

  return { handleError };
}

// Hook for async operations with error handling
export function useAsyncError() {
  const { handleError } = useApiError();

  const executeAsync = useCallback(async (
    asyncFn: () => Promise<any>,
    onRetry?: () => void
  ): Promise<any | null> => {
    try {
      return await asyncFn();
    } catch (error) {
      handleError(error, undefined, undefined, onRetry);
      return null;
    }
  }, [handleError]);

  return { executeAsync };
}