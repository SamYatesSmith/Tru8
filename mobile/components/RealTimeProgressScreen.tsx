import { useEffect, useMemo } from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ArrowLeft, RotateCcw } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { useRealTimeProgress } from '@/hooks/use-realtime-progress';
import { ProgressStepper } from './ProgressStepper';

interface RealTimeProgressScreenProps {
  checkId: string;
  onBack: () => void;
  onComplete?: (checkId: string) => void;
}

export function RealTimeProgressScreen({ 
  checkId, 
  onBack, 
  onComplete 
}: RealTimeProgressScreenProps) {
  const {
    stage,
    progress,
    message,
    error,
    isLoading,
    isError,
    isConnected,
    isRealTime,
    isPolling,
    connectionAttempts,
    retry,
  } = useRealTimeProgress(checkId);

  // Navigate to results when complete - Fixed race condition
  useEffect(() => {
    if (stage === 'completed' && onComplete) {
      onComplete(checkId);
    }
  }, [stage, checkId, onComplete]);

  const getConnectionMode = useMemo(() => {
    if (isRealTime) return 'realtime';
    if (isPolling) return 'polling';
    return 'offline';
  }, [isRealTime, isPolling]);

  return (
    <SafeAreaView style={{ 
      flex: 1, 
      backgroundColor: Colors.darkIndigo 
    }}>
      {/* Header */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: Spacing.space4,
        paddingVertical: Spacing.space3,
        borderBottomWidth: 1,
        borderBottomColor: Colors.coolGrey + '30',
      }}>
        <TouchableOpacity
          onPress={onBack}
          style={{
            padding: Spacing.space2,
            marginRight: Spacing.space3,
          }}
        >
          <ArrowLeft size={24} color={Colors.lightGrey} />
        </TouchableOpacity>
        
        <View style={{ flex: 1 }}>
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textLg,
            fontWeight: Typography.fontWeightBold,
          }}>
            Fact-Checking in Progress
          </Text>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
            marginTop: Spacing.space0_5,
          }}>
            ID: {checkId.slice(0, 8)}...
          </Text>
        </View>

        {/* Retry Button */}
        {isError && (
          <TouchableOpacity
            onPress={retry}
            style={{
              padding: Spacing.space2,
              backgroundColor: Colors.deepPurpleGrey,
              borderRadius: BorderRadius.radiusMd,
            }}
          >
            <RotateCcw size={18} color={Colors.lightGrey} />
          </TouchableOpacity>
        )}
      </View>

      {/* Connection Status Banner */}
      {!isConnected && (
        <View style={{
          backgroundColor: Colors.verdictContradicted + '20',
          borderBottomWidth: 1,
          borderBottomColor: Colors.verdictContradicted + '50',
          paddingHorizontal: Spacing.space4,
          paddingVertical: Spacing.space3,
        }}>
          <View style={{
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <View style={{ flex: 1 }}>
              <Text style={{
                color: Colors.verdictContradicted,
                fontSize: Typography.textSm,
                fontWeight: Typography.fontWeightMedium,
              }}>
                Connection Lost
              </Text>
              <Text style={{
                color: Colors.coolGrey,
                fontSize: Typography.textXs,
                marginTop: Spacing.space0_5,
              }}>
                {connectionAttempts > 0 
                  ? `Reconnecting... (${connectionAttempts}/5)`
                  : 'Tap retry to reconnect'
                }
              </Text>
            </View>
            
            {isLoading && (
              <ActivityIndicator size="small" color={Colors.verdictContradicted} />
            )}
          </View>
        </View>
      )}

      {/* Main Progress Content */}
      <View style={{ flex: 1 }}>
        <ProgressStepper
          currentStage={stage}
          progress={progress}
          message={message}
          error={error}
          isConnected={isConnected}
          connectionMode={getConnectionMode}
        />
      </View>

      {/* Footer with additional info */}
      <View style={{
        paddingHorizontal: Spacing.space4,
        paddingVertical: Spacing.space3,
        borderTopWidth: 1,
        borderTopColor: Colors.coolGrey + '30',
      }}>
        <Text style={{
          color: Colors.coolGrey,
          fontSize: Typography.textXs,
          textAlign: 'center',
          lineHeight: Typography.textXs * 1.4,
        }}>
          {stage === 'completed' 
            ? 'Processing complete! Redirecting to results...'
            : stage === 'failed'
              ? 'Processing failed. You can try again from the home screen.'
              : isRealTime
                ? 'Real-time updates active. Processing typically takes 10-30 seconds.'
                : isPolling
                  ? 'Checking for updates every few seconds...'
                  : 'Offline. Updates will resume when connection is restored.'
          }
        </Text>
      </View>
    </SafeAreaView>
  );
}