import { View, Text } from 'react-native';
import { CheckCircle, Clock, Circle } from 'lucide-react-native';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';

type PipelineStage = 'pending' | 'processing' | 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'completed' | 'failed';

interface ProgressStepperProps {
  currentStage: PipelineStage;
  progress: number; // 0-100
  message?: string;
  error?: string;
  isConnected?: boolean;
  connectionMode?: 'realtime' | 'polling' | 'offline';
}

const stages = [
  { 
    key: 'ingest' as const, 
    label: 'Processing', 
    description: 'Analyzing your content...' 
  },
  { 
    key: 'extract' as const, 
    label: 'Extracting', 
    description: 'Finding claims to fact-check...' 
  },
  { 
    key: 'retrieve' as const, 
    label: 'Researching', 
    description: 'Gathering evidence from sources...' 
  },
  { 
    key: 'verify' as const, 
    label: 'Verifying', 
    description: 'Checking claims against evidence...' 
  },
  { 
    key: 'judge' as const, 
    label: 'Analyzing', 
    description: 'Generating verdict and rationale...' 
  },
];

function getStageIndex(stage: PipelineStage): number {
  if (stage === 'completed') return stages.length;
  if (stage === 'failed') return -1;
  if (stage === 'pending' || stage === 'processing') return 0;
  return stages.findIndex(s => s.key === stage);
}

export function ProgressStepper({ 
  currentStage, 
  progress, 
  message, 
  error,
  isConnected = false,
  connectionMode = 'polling'
}: ProgressStepperProps) {
  const currentIndex = getStageIndex(currentStage);
  const isComplete = currentStage === 'completed';
  const isFailed = currentStage === 'failed';

  return (
    <View style={{ 
      padding: Spacing.space6, 
      gap: Spacing.space6 
    }}>
      {/* Connection Status Indicator */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: Spacing.space2,
        marginBottom: Spacing.space2,
      }}>
        <View style={{
          width: 8,
          height: 8,
          borderRadius: 4,
          backgroundColor: isConnected 
            ? connectionMode === 'realtime' 
              ? Colors.verdictSupported 
              : Colors.verdictUncertain
            : Colors.verdictContradicted,
        }} />
        <Text style={{
          color: Colors.coolGrey,
          fontSize: Typography.textXs,
          fontWeight: Typography.fontWeightMedium,
        }}>
          {isConnected 
            ? connectionMode === 'realtime' 
              ? 'Live updates' 
              : 'Polling updates'
            : 'Offline'
          }
        </Text>
      </View>

      {/* Overall Progress */}
      <View style={{ gap: Spacing.space2 }}>
        <View style={{
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <Text style={{
            color: Colors.lightGrey,
            fontSize: Typography.textBase,
            fontWeight: Typography.fontWeightMedium,
          }}>
            {error || isFailed 
              ? 'Processing failed' 
              : isComplete 
                ? 'Complete!' 
                : 'Processing...'}
          </Text>
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textBase,
          }}>
            {progress}%
          </Text>
        </View>
        
        {/* Progress Bar */}
        <View style={{
          height: 12,
          backgroundColor: Colors.deepPurpleGrey,
          borderRadius: BorderRadius.radiusFull,
          overflow: 'hidden',
        }}>
          <View style={{
            height: '100%',
            width: `${progress}%`,
            backgroundColor: isFailed 
              ? Colors.verdictContradicted 
              : isComplete 
                ? Colors.verdictSupported 
                : Colors.lightGrey,
            borderRadius: BorderRadius.radiusFull,
          }} />
        </View>
        
        {message && (
          <Text style={{
            color: Colors.coolGrey,
            fontSize: Typography.textSm,
          }}>
            {message}
          </Text>
        )}
        {error && (
          <Text style={{
            color: Colors.verdictContradicted,
            fontSize: Typography.textSm,
          }}>
            {error}
          </Text>
        )}
      </View>

      {/* Stage Steps */}
      <View style={{ gap: Spacing.space4 }}>
        {stages.map((stage, index) => {
          const isCompleted = index < currentIndex || isComplete;
          const isCurrent = index === currentIndex && !isComplete && !isFailed;
          const isPending = index > currentIndex && !isFailed;
          const isStepFailed = isFailed && index === currentIndex;

          return (
            <View
              key={stage.key}
              style={{
                flexDirection: 'row',
                alignItems: 'flex-start',
                gap: Spacing.space3,
                padding: Spacing.space3,
                borderRadius: BorderRadius.radiusLg,
                borderWidth: 2,
                borderColor: isCurrent
                  ? Colors.lightGrey
                  : isCompleted
                    ? Colors.coolGrey
                    : isStepFailed
                      ? Colors.verdictContradicted
                      : Colors.coolGrey + '50',
                backgroundColor: isCurrent
                  ? Colors.lightGrey + '20'
                  : isCompleted
                    ? Colors.deepPurpleGrey + '80'
                    : isStepFailed
                      ? Colors.verdictContradicted + '20'
                      : 'transparent',
              }}
            >
              <View style={{ marginTop: 2 }}>
                {isCompleted ? (
                  <CheckCircle size={20} color={Colors.lightGrey} />
                ) : isCurrent ? (
                  <Clock size={20} color={Colors.lightGrey} />
                ) : isStepFailed ? (
                  <Circle size={20} color={Colors.verdictContradicted} />
                ) : (
                  <Circle size={20} color={Colors.coolGrey} />
                )}
              </View>
              
              <View style={{ flex: 1 }}>
                <Text style={{
                  color: isCurrent 
                    ? Colors.lightGrey
                    : isCompleted 
                      ? Colors.lightGrey
                      : isStepFailed
                        ? Colors.verdictContradicted
                        : Colors.coolGrey,
                  fontSize: Typography.textBase,
                  fontWeight: Typography.fontWeightMedium,
                }}>
                  {stage.label}
                </Text>
                <Text style={{
                  color: Colors.coolGrey,
                  fontSize: Typography.textSm,
                  marginTop: Spacing.space1,
                }}>
                  {stage.description}
                </Text>
              </View>
            </View>
          );
        })}

        {/* Completion Step */}
        {isComplete && (
          <View style={{
            flexDirection: 'row',
            alignItems: 'flex-start',
            gap: Spacing.space3,
            padding: Spacing.space3,
            borderRadius: BorderRadius.radiusLg,
            borderWidth: 2,
            borderColor: Colors.lightGrey,
            backgroundColor: Colors.lightGrey + '20',
          }}>
            <CheckCircle size={20} color={Colors.lightGrey} style={{ marginTop: 2 }} />
            <View>
              <Text style={{
                color: Colors.lightGrey,
                fontSize: Typography.textBase,
                fontWeight: Typography.fontWeightMedium,
              }}>
                Complete!
              </Text>
              <Text style={{
                color: Colors.coolGrey,
                fontSize: Typography.textSm,
                marginTop: Spacing.space1,
              }}>
                Your fact-check results are ready.
              </Text>
            </View>
          </View>
        )}

        {/* Failed Step */}
        {isFailed && (
          <View style={{
            flexDirection: 'row',
            alignItems: 'flex-start',
            gap: Spacing.space3,
            padding: Spacing.space3,
            borderRadius: BorderRadius.radiusLg,
            borderWidth: 2,
            borderColor: Colors.verdictContradicted,
            backgroundColor: Colors.verdictContradicted + '20',
          }}>
            <Circle size={20} color={Colors.verdictContradicted} style={{ marginTop: 2 }} />
            <View>
              <Text style={{
                color: Colors.verdictContradicted,
                fontSize: Typography.textBase,
                fontWeight: Typography.fontWeightMedium,
              }}>
                Failed
              </Text>
              <Text style={{
                color: Colors.coolGrey,
                fontSize: Typography.textSm,
                marginTop: Spacing.space1,
              }}>
                {error || 'Processing encountered an error. Please try again.'}
              </Text>
            </View>
          </View>
        )}
      </View>
    </View>
  );
}