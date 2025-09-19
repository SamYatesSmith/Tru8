import React, { Component, ErrorInfo, ReactNode } from 'react';
import { View, Text, TouchableOpacity, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { router } from 'expo-router';
import { errorReporting } from '@/services/error-reporting';

interface Props {
  children: ReactNode;
  fallback?: React.ComponentType<ErrorBoundaryFallbackProps>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export interface ErrorBoundaryFallbackProps {
  error?: Error;
  errorInfo?: ErrorInfo;
  resetError: () => void;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // TODO: Send error to monitoring service (Sentry, etc.)
    this.logErrorToService(error, errorInfo);
  }

  private logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    try {
      // Report to error reporting service
      errorReporting.reportError(
        error,
        'crash',
        'critical',
        {
          componentStack: errorInfo.componentStack,
          errorBoundary: true,
        }
      );
    } catch (loggingError) {
      console.error('Failed to log error:', loggingError);
    }
  };

  private resetError = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  private goHome = () => {
    this.resetError();
    router.push('/(tabs)/' as any);
  };

  public render() {
    if (this.state.hasError) {
      // Use custom fallback component if provided
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent
            error={this.state.error}
            errorInfo={this.state.errorInfo}
            resetError={this.resetError}
          />
        );
      }

      // Default fallback UI
      return (
        <SafeAreaView style={{ 
          flex: 1, 
          backgroundColor: Colors.darkIndigo 
        }}>
          <View style={{
            flex: 1,
            justifyContent: 'center',
            alignItems: 'center',
            paddingHorizontal: Spacing.space6,
          }}>
            <View style={{
              backgroundColor: Colors.deepPurpleGrey,
              borderRadius: BorderRadius.radiusXl,
              padding: Spacing.space8,
              alignItems: 'center',
              maxWidth: 400,
              width: '100%',
            }}>
              <View style={{
                backgroundColor: Colors.verdictContradicted + '20',
                borderRadius: BorderRadius.radiusFull,
                padding: Spacing.space4,
                marginBottom: Spacing.space6,
              }}>
                <AlertTriangle 
                  size={48} 
                  color={Colors.verdictContradicted} 
                />
              </View>

              <Text style={{
                color: Colors.lightGrey,
                fontSize: Typography.text2xl,
                fontWeight: Typography.fontWeightBold,
                textAlign: 'center',
                marginBottom: Spacing.space4,
              }}>
                Oops! Something went wrong
              </Text>

              <Text style={{
                color: Colors.coolGrey,
                fontSize: Typography.textBase,
                textAlign: 'center',
                lineHeight: Typography.textBase * 1.5,
                marginBottom: Spacing.space8,
              }}>
                An unexpected error occurred. This has been reported and we're working on it.
              </Text>

              {/* Error Details (in development) */}
              {__DEV__ && this.state.error && (
                <ScrollView style={{
                  backgroundColor: Colors.coolGrey + '10',
                  borderRadius: BorderRadius.radiusMd,
                  padding: Spacing.space4,
                  maxHeight: 200,
                  width: '100%',
                  marginBottom: Spacing.space6,
                }}>
                  <Text style={{
                    color: Colors.coolGrey,
                    fontSize: Typography.textSm,
                    fontFamily: 'monospace',
                  }}>
                    {this.state.error.message}
                    {'\n\n'}
                    {this.state.error.stack}
                  </Text>
                </ScrollView>
              )}

              <View style={{
                flexDirection: 'row',
                gap: Spacing.space4,
                width: '100%',
              }}>
                <TouchableOpacity
                  onPress={this.resetError}
                  style={{
                    flex: 1,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'transparent',
                    borderWidth: 1,
                    borderColor: Colors.lightGrey,
                    borderRadius: BorderRadius.radiusLg,
                    paddingVertical: Spacing.space4,
                    paddingHorizontal: Spacing.space6,
                  }}
                >
                  <RefreshCw 
                    size={20} 
                    color={Colors.lightGrey}
                    style={{ marginRight: Spacing.space2 }}
                  />
                  <Text style={{
                    color: Colors.lightGrey,
                    fontSize: Typography.textBase,
                    fontWeight: Typography.fontWeightSemibold,
                  }}>
                    Try Again
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  onPress={this.goHome}
                  style={{
                    flex: 1,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: Colors.lightGrey,
                    borderRadius: BorderRadius.radiusLg,
                    paddingVertical: Spacing.space4,
                    paddingHorizontal: Spacing.space6,
                  }}
                >
                  <Home 
                    size={20} 
                    color={Colors.darkIndigo}
                    style={{ marginRight: Spacing.space2 }}
                  />
                  <Text style={{
                    color: Colors.darkIndigo,
                    fontSize: Typography.textBase,
                    fontWeight: Typography.fontWeightSemibold,
                  }}>
                    Go Home
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </SafeAreaView>
      );
    }

    return this.props.children;
  }
}

// Specific error boundary for individual screens
export function ScreenErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Screen-specific error handling
        console.error('Screen error:', error.message);
      }}
    >
      {children}
    </ErrorBoundary>
  );
}

// Error boundary for critical app components
export function CriticalErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Critical error - might need app restart
        console.error('Critical error:', error.message);
        // TODO: Force app restart or show critical error screen
      }}
    >
      {children}
    </ErrorBoundary>
  );
}

// Hook for triggering error boundary from child components
export function useErrorHandler() {
  return (error: Error) => {
    // Throw error to be caught by nearest error boundary
    throw error;
  };
}