import React, { useEffect } from 'react';
import { View, Text, TouchableOpacity, Animated, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AlertTriangle, Wifi, X, RefreshCw, AlertCircle, Lock } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { useError, AppError } from '@/contexts/ErrorContext';

const { width: screenWidth } = Dimensions.get('window');

interface ErrorToastProps {
  error: AppError;
  onDismiss: () => void;
}

function ErrorToast({ error, onDismiss }: ErrorToastProps) {
  const slideAnim = new Animated.Value(-100);

  useEffect(() => {
    // Slide in animation
    Animated.spring(slideAnim, {
      toValue: 0,
      useNativeDriver: true,
      tension: 100,
      friction: 8,
    }).start();
  }, []);

  const slideOut = () => {
    Animated.timing(slideAnim, {
      toValue: -100,
      duration: 300,
      useNativeDriver: true,
    }).start(() => {
      onDismiss();
    });
  };

  const getErrorIcon = () => {
    switch (error.type) {
      case 'network':
        return <Wifi size={20} color={Colors.white} />;
      case 'auth':
        return <Lock size={20} color={Colors.white} />;
      case 'api':
        return <AlertCircle size={20} color={Colors.white} />;
      default:
        return <AlertTriangle size={20} color={Colors.white} />;
    }
  };

  const getErrorColor = () => {
    switch (error.type) {
      case 'network':
        return Colors.verdictUncertain;
      case 'auth':
        return Colors.verdictContradicted;
      case 'api':
        return Colors.coolGrey;
      default:
        return Colors.verdictContradicted;
    }
  };

  return (
    <Animated.View
      style={{
        position: 'absolute',
        top: 0,
        left: Spacing.space4,
        right: Spacing.space4,
        zIndex: 1000,
        transform: [{ translateY: slideAnim }],
      }}
    >
      <SafeAreaView edges={['top']}>
        <View style={{
          backgroundColor: getErrorColor(),
          borderRadius: BorderRadius.radiusLg,
          padding: Spacing.space4,
          flexDirection: 'row',
          alignItems: 'flex-start',
          shadowColor: Colors.black,
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.3,
          shadowRadius: 8,
          elevation: 8,
        }}>
          <View style={{
            backgroundColor: 'rgba(255, 255, 255, 0.2)',
            borderRadius: BorderRadius.radiusFull,
            padding: Spacing.space2,
            marginRight: Spacing.space3,
          }}>
            {getErrorIcon()}
          </View>

          <View style={{ flex: 1, marginRight: Spacing.space2 }}>
            <Text style={{
              color: Colors.white,
              fontSize: Typography.textSm,
              fontWeight: Typography.fontWeightSemibold,
              marginBottom: Spacing.space1,
            }}>
              {error.type === 'network' ? 'Connection Error' :
               error.type === 'auth' ? 'Authentication Error' :
               error.type === 'api' ? 'Server Error' :
               'Error'}
            </Text>

            <Text style={{
              color: Colors.white,
              fontSize: Typography.textSm,
              opacity: 0.9,
              lineHeight: Typography.textSm * 1.4,
            }}>
              {error.message}
            </Text>

            {error.retryable && error.onRetry && (
              <TouchableOpacity
                onPress={() => {
                  error.onRetry?.();
                  slideOut();
                }}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  marginTop: Spacing.space3,
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  paddingHorizontal: Spacing.space3,
                  paddingVertical: Spacing.space2,
                  borderRadius: BorderRadius.radiusMd,
                  alignSelf: 'flex-start',
                }}
              >
                <RefreshCw size={14} color={Colors.white} style={{ marginRight: Spacing.space1 }} />
                <Text style={{
                  color: Colors.white,
                  fontSize: Typography.textXs,
                  fontWeight: Typography.fontWeightMedium,
                }}>
                  Retry
                </Text>
              </TouchableOpacity>
            )}
          </View>

          <TouchableOpacity
            onPress={slideOut}
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.2)',
              borderRadius: BorderRadius.radiusFull,
              padding: Spacing.space1,
            }}
          >
            <X size={16} color={Colors.white} />
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </Animated.View>
  );
}

export function ErrorToastContainer() {
  const { errors, dismissError } = useError();

  // Show only the most recent error
  const currentError = errors[errors.length - 1];

  if (!currentError) {
    return null;
  }

  return (
    <ErrorToast
      error={currentError}
      onDismiss={() => dismissError(currentError.id)}
    />
  );
}