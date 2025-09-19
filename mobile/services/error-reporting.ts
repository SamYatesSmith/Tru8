import { Platform } from 'react-native';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface ErrorReport {
  id: string;
  message: string;
  stack?: string;
  type: 'javascript' | 'api' | 'network' | 'auth' | 'crash';
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  userId?: string;
  userEmail?: string;
  platform: string;
  appVersion: string;
  buildNumber: string;
  deviceInfo: {
    platform: string;
    osVersion?: string;
    deviceModel?: string;
    screenSize?: string;
  };
  breadcrumbs?: ErrorBreadcrumb[];
  tags?: Record<string, string>;
  extra?: Record<string, any>;
}

export interface ErrorBreadcrumb {
  timestamp: string;
  category: 'navigation' | 'api' | 'user' | 'system';
  message: string;
  level: 'info' | 'warning' | 'error';
  data?: Record<string, any>;
}

class ErrorReportingService {
  private breadcrumbs: ErrorBreadcrumb[] = [];
  private maxBreadcrumbs = 50;
  private userId?: string;
  private userEmail?: string;
  private isEnabled = true;
  
  constructor() {
    this.loadSettings();
  }

  private async loadSettings() {
    try {
      const settings = await AsyncStorage.getItem('error_reporting_settings');
      if (settings) {
        const parsed = JSON.parse(settings);
        this.isEnabled = parsed.enabled !== false;
      }
    } catch (error) {
      console.warn('Failed to load error reporting settings:', error);
    }
  }

  public async setEnabled(enabled: boolean) {
    this.isEnabled = enabled;
    try {
      await AsyncStorage.setItem('error_reporting_settings', JSON.stringify({ enabled }));
    } catch (error) {
      console.warn('Failed to save error reporting settings:', error);
    }
  }

  public setUser(userId: string, email?: string) {
    this.userId = userId;
    this.userEmail = email;
  }

  public addBreadcrumb(breadcrumb: Omit<ErrorBreadcrumb, 'timestamp'>) {
    if (!this.isEnabled) return;

    const timestampedBreadcrumb: ErrorBreadcrumb = {
      ...breadcrumb,
      timestamp: new Date().toISOString(),
    };

    this.breadcrumbs.push(timestampedBreadcrumb);
    
    // Keep only the most recent breadcrumbs
    if (this.breadcrumbs.length > this.maxBreadcrumbs) {
      this.breadcrumbs = this.breadcrumbs.slice(-this.maxBreadcrumbs);
    }
  }

  public async reportError(
    error: Error | string,
    type: ErrorReport['type'] = 'javascript',
    severity: ErrorReport['severity'] = 'medium',
    extra?: Record<string, any>
  ): Promise<void> {
    if (!this.isEnabled) return;

    try {
      const errorMessage = typeof error === 'string' ? error : error.message;
      const errorStack = typeof error === 'string' ? undefined : error.stack;

      const report: ErrorReport = {
        id: this.generateErrorId(),
        message: errorMessage,
        stack: errorStack,
        type,
        severity,
        timestamp: new Date().toISOString(),
        userId: this.userId,
        userEmail: this.userEmail,
        platform: Platform.OS,
        appVersion: Constants.expoConfig?.version || '0.0.0',
        buildNumber: Constants.expoConfig?.ios?.buildNumber || Constants.expoConfig?.android?.versionCode?.toString() || '0',
        deviceInfo: {
          platform: Platform.OS,
          osVersion: Platform.Version?.toString(),
          deviceModel: Constants.deviceName,
          screenSize: `${Constants.screenDimensions?.width}x${Constants.screenDimensions?.height}`,
        },
        breadcrumbs: [...this.breadcrumbs], // Copy breadcrumbs at time of error
        extra: {
          ...extra,
          memoryUsage: await this.getMemoryUsage(),
        },
      };

      // Log to console in development
      if (__DEV__) {
        console.group(`🚨 Error Report [${severity.toUpperCase()}]`);
        console.error('Message:', errorMessage);
        if (errorStack) console.error('Stack:', errorStack);
        console.log('Type:', type);
        console.log('Extra:', extra);
        console.log('Recent breadcrumbs:', this.breadcrumbs.slice(-5));
        console.groupEnd();
      }

      // Store locally for offline support
      await this.storeErrorLocally(report);

      // Send to monitoring service
      await this.sendToMonitoring(report);

    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    }
  }

  private generateErrorId(): string {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private async getMemoryUsage(): Promise<Record<string, number> | undefined> {
    try {
      // This would use native modules to get memory usage
      // For now, return undefined as it requires native implementation
      return undefined;
    } catch {
      return undefined;
    }
  }

  private async storeErrorLocally(report: ErrorReport): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('error_reports');
      const reports: ErrorReport[] = stored ? JSON.parse(stored) : [];
      
      reports.push(report);
      
      // Keep only the last 10 reports locally
      const recentReports = reports.slice(-10);
      
      await AsyncStorage.setItem('error_reports', JSON.stringify(recentReports));
    } catch (error) {
      console.warn('Failed to store error locally:', error);
    }
  }

  private async sendToMonitoring(report: ErrorReport): Promise<void> {
    try {
      // This would integrate with Sentry, Bugsnag, or another service
      // For now, we'll simulate sending to a generic endpoint
      
      const endpoint = process.env.EXPO_PUBLIC_ERROR_REPORTING_URL;
      if (!endpoint) return;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(report),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

    } catch (error) {
      console.warn('Failed to send error to monitoring service:', error);
      // Error is already stored locally, so we don't lose it
    }
  }

  public async getStoredErrors(): Promise<ErrorReport[]> {
    try {
      const stored = await AsyncStorage.getItem('error_reports');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  public async clearStoredErrors(): Promise<void> {
    try {
      await AsyncStorage.removeItem('error_reports');
    } catch (error) {
      console.warn('Failed to clear stored errors:', error);
    }
  }

  // Convenience methods for common error types
  public reportAPIError(status: number, message: string, endpoint?: string) {
    const severity = status >= 500 ? 'high' : status >= 400 ? 'medium' : 'low';
    this.reportError(
      `API Error ${status}: ${message}`,
      'api',
      severity,
      { endpoint, statusCode: status }
    );
  }

  public reportNetworkError(message: string = 'Network request failed') {
    this.reportError(message, 'network', 'medium');
  }

  public reportAuthError(message: string) {
    this.reportError(message, 'auth', 'high');
  }

  public reportCrash(error: Error) {
    this.reportError(error, 'crash', 'critical');
  }

  // Navigation tracking
  public trackNavigation(from: string, to: string) {
    this.addBreadcrumb({
      category: 'navigation',
      message: `Navigated from ${from} to ${to}`,
      level: 'info',
      data: { from, to },
    });
  }

  // API call tracking
  public trackAPICall(method: string, endpoint: string, status?: number) {
    this.addBreadcrumb({
      category: 'api',
      message: `${method} ${endpoint}`,
      level: status && status >= 400 ? 'error' : 'info',
      data: { method, endpoint, status },
    });
  }

  // User action tracking
  public trackUserAction(action: string, data?: Record<string, any>) {
    this.addBreadcrumb({
      category: 'user',
      message: action,
      level: 'info',
      data,
    });
  }
}

// Singleton instance
export const errorReporting = new ErrorReportingService();

// Global error handler setup
export function setupGlobalErrorHandlers() {
  // Handle unhandled promise rejections (React Native specific)
  if (global.HermesInternal || global.__DEV__) {
    // For React Native with Hermes or in development
    const originalHandler = global.Promise?.prototype?.catch;
    if (originalHandler) {
      global.addEventListener = global.addEventListener || (() => {});
      try {
        global.addEventListener('unhandledrejection', (event: any) => {
          console.error('Unhandled promise rejection:', event.reason);
          errorReporting.reportError(
            event.reason || 'Unhandled promise rejection',
            'javascript',
            'high'
          );
        });
      } catch (error) {
        console.warn('Failed to setup unhandled rejection handler:', error);
      }
    }
  }

  // Handle uncaught exceptions (React Native specific)
  const originalErrorHandler = global.ErrorUtils?.getGlobalHandler();
  global.ErrorUtils?.setGlobalHandler((error: Error, isFatal?: boolean) => {
    console.error('Uncaught exception:', error);
    
    errorReporting.reportError(
      error,
      'crash',
      isFatal ? 'critical' : 'high'
    );

    // Call original handler
    if (originalErrorHandler) {
      originalErrorHandler(error, isFatal);
    }
  });
}

// Hook for easy error reporting in components
export function useErrorReporting() {
  return {
    reportError: errorReporting.reportError.bind(errorReporting),
    reportAPIError: errorReporting.reportAPIError.bind(errorReporting),
    reportNetworkError: errorReporting.reportNetworkError.bind(errorReporting),
    trackUserAction: errorReporting.trackUserAction.bind(errorReporting),
    trackNavigation: errorReporting.trackNavigation.bind(errorReporting),
  };
}